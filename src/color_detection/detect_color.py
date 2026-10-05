import cv2
import numpy as np

from src.color_detection.color_mapper import FAMILY_BASES, map_rgb_to_color, rgb_to_lab

# Fracao da menor dimensao usada como area de leitura. Mantida proxima do
# tamanho da mira desenhada na tela, para o app medir o que o usuario apontou.
CROP_RATIO = 0.12

CLUSTERS = 3
MAX_PIXELS = 20000
MIN_DOMINANCE = 0.55

# Distancia RGB abaixo da qual dois pixels sao considerados a mesma cor.
# Cobre variacao de sombra e ruido de sensor dentro de uma peca lisa.
SAME_COLOR_DISTANCE = 60.0

# Leitura da PECA (area="peca"), usada no cadastro: a cor principal e a
# secundaria saem da parte central da foto, nao so da mira. Numa camiseta
# cinza com estampa vermelha no peito, a mira pode cair na estampa; a cor da
# peca e' a que ocupa mais area. A area nao vai alem de 35% do lado menor:
# maior que isso, o fundo da foto (cama, chao, parede) comeca a aparecer como
# se fosse uma cor da peca.
PIECE_CROP_RATIO = 0.35
SECONDARY_CLUSTERS = 4
# Fracao minima da area que a segunda cor precisa ocupar, e distancia minima
# da cor principal. Valores conservadores de proposito: nas 39 fotos reais de
# tests/eval, limites mais frouxos achavam no maximo 2 de 10 segundas cores e
# inventavam uma segunda cor em ate 9 de 29 pecas de uma cor so. Para quem e'
# daltonico, uma cor errada e' pior que nenhuma. Medir com
# `python -m tests.eval.avaliar_cor`.
MIN_SECONDARY_SHARE = 0.30
MIN_SECONDARY_DISTANCE = 110.0
# Duas cores da mesma familia (azul e azul escuro, branco e cinza) so contam
# como cores diferentes com esta diferenca de luminosidade L*. Marinho com azul
# claro passa; o lado sombreado de um tecido azul nao.
MIN_SAME_FAMILY_LIGHTNESS_GAP = 35.0

NEUTRAL_SYMBOLS = {"PRETO", "CINZA", "BRANCO"}


def color_family(color_add_symbol: str) -> str:
    """Familia ColorADD sem o tom: COLORADD_AZUL_ESCURO -> AZUL; neutros juntos."""
    family = color_add_symbol.removeprefix("COLORADD_")
    family = family.removesuffix("_CLARO").removesuffix("_ESCURO")

    return "NEUTRO" if family in NEUTRAL_SYMBOLS else family


def crop_center(image, crop_ratio: float = CROP_RATIO):
    height, width, _ = image.shape

    crop_size = max(int(min(width, height) * crop_ratio), 1)

    center_x = width // 2
    center_y = height // 2

    x1 = max(center_x - crop_size // 2, 0)
    x2 = min(center_x + crop_size // 2, width)
    y1 = max(center_y - crop_size // 2, 0)
    y2 = min(center_y + crop_size // 2, height)

    return image[y1:y2, x1:x2]


def _kmeans(sample: np.ndarray, clusters: int):
    """
    k-means do OpenCV com semente fixa. Sem ela o ponto de partida e' sorteado
    e a mesma foto pode dar cores diferentes a cada chamada.
    """
    cv2.setRNGSeed(0)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)

    _, labels, centers = cv2.kmeans(
        sample, clusters, None, criteria, 5, cv2.KMEANS_PP_CENTERS
    )

    return labels, centers


def find_dominant_color(pixels: np.ndarray, clusters: int = CLUSTERS):
    """
    Agrupa os pixels e devolve o centro do maior grupo, com a fracao de pixels
    que ele representa.

    A media nao serve: sombra, brilho, listra ou estampa puxam o resultado
    para uma cor que nao existe na peca. Uma calca preta com um reflexo de luz
    tem media cinza, e uma camisa vermelha listrada de branco tem media rosa.
    """
    sample = pixels

    if len(sample) > MAX_PIXELS:
        indices = np.random.default_rng(0).choice(
            len(sample), MAX_PIXELS, replace=False
        )
        sample = sample[indices]

    sample = np.float32(sample)

    cores_distintas = len(np.unique(sample, axis=0))
    effective_clusters = max(min(clusters, cores_distintas), 1)

    labels, centers = _kmeans(sample, effective_clusters)

    labels = labels.flatten()
    counts = np.bincount(labels, minlength=effective_clusters)
    winner = int(np.argmax(counts))

    dominant = [int(value) for value in centers[winner]]

    # A confianca NAO e' o tamanho do cluster vencedor: textura e sombra
    # partem uma peca lisa em varios clusters proximos e derrubariam o numero
    # sem que a leitura estivesse errada. O que interessa e' quantos pixels
    # estao perto da cor vencedora, mesmo que tenham caido em outro cluster.
    distancias = np.linalg.norm(sample - centers[winner], axis=1)
    confidence = float((distancias < SAME_COLOR_DISTANCE).mean())

    return dominant, confidence


def find_secondary_color(pixels: np.ndarray, primary_rgb: list[int]):
    """
    Procura uma segunda cor relevante, diferente da principal.

    Devolve None quando a peca e' de uma cor so. O back ainda descarta a
    secundaria se a analise da peca disser que ela e' lisa: em foto com fundo
    aparecendo, o fundo pode passar por segunda cor.
    """
    sample = pixels

    if len(sample) > MAX_PIXELS:
        indices = np.random.default_rng(0).choice(
            len(sample), MAX_PIXELS, replace=False
        )
        sample = sample[indices]

    sample = np.float32(sample)
    primary = np.float32(primary_rgb)

    cores_distintas = len(np.unique(sample, axis=0))
    effective_clusters = max(min(SECONDARY_CLUSTERS, cores_distintas), 1)

    labels, centers = _kmeans(sample, effective_clusters)

    counts = np.bincount(labels.flatten(), minlength=effective_clusters)
    primary_info = map_rgb_to_color(primary_rgb)

    for index in np.argsort(counts)[::-1]:
        center = centers[index]

        if np.linalg.norm(center - primary) < MIN_SECONDARY_DISTANCE:
            continue

        # Como na confianca da principal: conta os pixels perto desta cor,
        # mesmo que a sombra os tenha espalhado por outro grupo.
        perto = np.linalg.norm(sample - center, axis=1) < SAME_COLOR_DISTANCE
        share = float(perto.mean())

        if share < MIN_SECONDARY_SHARE:
            continue

        rgb = [int(value) for value in center]
        info = map_rgb_to_color(rgb)

        if info["colorAddSymbol"] == primary_info["colorAddSymbol"]:
            continue

        same_family = color_family(info["colorAddSymbol"]) == color_family(
            primary_info["colorAddSymbol"]
        )
        # L* do CIELAB: luminosidade percebida, de 0 a 100.
        lightness_gap = abs(rgb_to_lab(rgb)[0] - rgb_to_lab(primary_rgb)[0])

        if same_family and lightness_gap < MIN_SAME_FAMILY_LIGHTNESS_GAP:
            continue

        return {
            "colorName": info["colorName"],
            "hex": info["hex"],
            "colorAddSymbol": info["colorAddSymbol"],
            "rgb": rgb,
            "share": round(share, 2),
        }

    return None


# Simbolos ColorADD que a visao gera e o app sabe desenhar, sem o prefixo:
# as 7 cores cromaticas em tres tons, mais preto, branco e tres cinzas.
COLOR_SYMBOLS = [
    f"{family.upper()}{tone}"
    for family in FAMILY_BASES
    for tone in ("", "_CLARO", "_ESCURO")
] + ["PRETO", "BRANCO", "CINZA", "CINZA_CLARO", "CINZA_ESCURO"]

# Cores de referencia fixas, usadas so quando a foto nao tem nenhum grupo de
# pixels do simbolo pedido. Os neutros, e o amarelo claro (a base clareada
# pela metade ainda e' lida como amarelo). Cada uma e' lida de volta como o
# proprio simbolo; o teste fica em tests/eval/avaliar_cor.py.
FIXED_REFERENCES = {
    "PRETO": [25, 25, 25],
    "BRANCO": [240, 240, 240],
    "CINZA": [128, 128, 128],
    "CINZA_CLARO": [190, 190, 190],
    "CINZA_ESCURO": [82, 82, 82],
    "AMARELO_CLARO": [250, 240, 170],
}

PIECE_CLUSTERS = 5


def reference_rgb(symbol: str) -> list[int]:
    """Cor de referencia de um simbolo: a base da familia clareada ou escurecida."""
    if symbol in FIXED_REFERENCES:
        return FIXED_REFERENCES[symbol]

    family = symbol.removesuffix("_CLARO").removesuffix("_ESCURO")
    base = FAMILY_BASES[family.capitalize()]

    if symbol.endswith("_CLARO"):
        return [round(v + (255 - v) * 0.5) for v in base]

    if symbol.endswith("_ESCURO"):
        return [round(v * 0.55) for v in base]

    return base


def symbol_name(symbol: str) -> str:
    """AZUL_ESCURO -> 'Azul Escuro', no mesmo formato do colorName."""
    return " ".join(part.capitalize() for part in symbol.split("_"))


def color_from_symbol(image_bytes: bytes, symbol: str):
    """
    Monta a cor completa (nome, hex e simbolo) a partir de um simbolo ColorADD
    sem prefixo, como o que a analise da peca devolve para a cor secundaria.

    O hex vem da propria foto: o grupo de pixels da peca com exatamente esse
    simbolo. Sem ele, usa a cor de referencia do simbolo. Um grupo so da mesma
    familia nao serve: daria, por exemplo, um azul claro para "azul escuro".
    """
    full_symbol = f"COLORADD_{symbol}"
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

    rgb = None

    if image is not None:
        piece = crop_center(cv2.cvtColor(image, cv2.COLOR_BGR2RGB), PIECE_CROP_RATIO)
        sample = np.float32(piece.reshape((-1, 3)))

        if len(sample) > MAX_PIXELS:
            indices = np.random.default_rng(0).choice(len(sample), MAX_PIXELS, replace=False)
            sample = sample[indices]

        clusters = max(min(PIECE_CLUSTERS, len(np.unique(sample, axis=0))), 1)
        labels, centers = _kmeans(sample, clusters)
        counts = np.bincount(labels.flatten(), minlength=clusters)

        same_symbol = [
            ([int(v) for v in centers[i]], counts[i])
            for i in range(clusters)
            if map_rgb_to_color([int(v) for v in centers[i]])["colorAddSymbol"] == full_symbol
        ]

        if same_symbol:
            rgb = max(same_symbol, key=lambda c: c[1])[0]

    if rgb is None:
        rgb = reference_rgb(symbol)

    return {
        "colorName": symbol_name(symbol),
        "hex": "#{:02X}{:02X}{:02X}".format(*rgb),
        "colorAddSymbol": full_symbol,
    }


def detect_dominant_color(image_bytes: bytes, area: str = "mira"):
    """
    area="mira": cor do ponto que a pessoa aponta (loop da camera). Rapido, sem
    cor secundaria.
    area="peca": cor principal e secundaria da peca inteira (cadastro).
    """
    np_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Imagem inválida")

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    piece_crop = crop_center(image_rgb, PIECE_CROP_RATIO)
    center_crop = piece_crop if area == "peca" else crop_center(image_rgb)

    pixels = center_crop.reshape((-1, 3))

    if len(pixels) == 0:
        raise ValueError("Imagem inválida")

    rgb, confidence = find_dominant_color(pixels)

    result = map_rgb_to_color(rgb)
    result["rgb"] = rgb
    result["confidence"] = round(confidence, 2)

    # Grupo vencedor fraco significa mira sobre estampa, costura ou borda da
    # peca: a cor lida existe, mas nao representa a peca inteira.
    if confidence < MIN_DOMINANCE and not result.get("warningCode"):
        result["warningCode"] = "LOW_CONFIDENCE"

    result["secondary"] = (
        find_secondary_color(piece_crop.reshape((-1, 3)), rgb) if area == "peca" else None
    )

    return result
