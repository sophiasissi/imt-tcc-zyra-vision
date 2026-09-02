import cv2
import numpy as np

from src.color_detection.color_mapper import map_rgb_to_color

# Fracao da menor dimensao usada como area de leitura. Mantida proxima do
# tamanho da mira desenhada na tela, para o app medir o que o usuario apontou.
CROP_RATIO = 0.12

CLUSTERS = 3
MAX_PIXELS = 20000
MIN_DOMINANCE = 0.55

# Distancia RGB abaixo da qual dois pixels sao considerados a mesma cor.
# Cobre variacao de sombra e ruido de sensor dentro de uma peca lisa.
SAME_COLOR_DISTANCE = 60.0


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

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)

    _, labels, centers = cv2.kmeans(
        sample,
        effective_clusters,
        None,
        criteria,
        5,
        cv2.KMEANS_PP_CENTERS,
    )

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


def detect_dominant_color(image_bytes: bytes):
    np_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Imagem inválida")

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    center_crop = crop_center(image_rgb)

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

    return result
