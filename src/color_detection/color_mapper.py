import colorsys
import math


# ---------------------------------------------------------------------------
# Referencias de MATIZ.
#
# O ColorADD e' construido sobre azul, amarelo e vermelho, com preto e branco
# marcando escuro e claro. Nao ha simbolo proprio de rosa: rosa e' vermelho
# claro. (Se voces adicionarem um asset de rosa, ver nota no fim do arquivo.)
#
# Cada entrada tem duas cores:
#   - "anchor": usada so' para achar a familia pelo matiz;
#   - "base":   a cor canonica da familia, usada para decidir claro/escuro.
# Varias ancoras podem apontar para a mesma base (ex.: 3 ancoras de azul),
# o que cobre bem a faixa de cada familia sem inventar cores novas.
# ---------------------------------------------------------------------------
HUE_REFERENCES = [
    {"colorName": "Vermelho", "anchor": [255, 0, 0], "base": [255, 0, 0],
     "colorAddSymbol": "COLORADD_VERMELHO"},
    {"colorName": "Vermelho", "anchor": [230, 0, 90], "base": [255, 0, 0],
     "colorAddSymbol": "COLORADD_VERMELHO"},

    {"colorName": "Laranja", "anchor": [205, 95, 40], "base": [255, 140, 0],
     "colorAddSymbol": "COLORADD_LARANJA"},
    {"colorName": "Laranja", "anchor": [255, 140, 0], "base": [255, 140, 0],
     "colorAddSymbol": "COLORADD_LARANJA"},

    {"colorName": "Amarelo", "anchor": [255, 235, 0], "base": [255, 235, 0],
     "colorAddSymbol": "COLORADD_AMARELO"},

    {"colorName": "Verde", "anchor": [130, 200, 0], "base": [0, 190, 60],
     "colorAddSymbol": "COLORADD_VERDE"},
    {"colorName": "Verde", "anchor": [0, 190, 60], "base": [0, 190, 60],
     "colorAddSymbol": "COLORADD_VERDE"},
    {"colorName": "Verde", "anchor": [0, 180, 150], "base": [0, 190, 60],
     "colorAddSymbol": "COLORADD_VERDE"},

    {"colorName": "Azul", "anchor": [0, 150, 210], "base": [0, 90, 220],
     "colorAddSymbol": "COLORADD_AZUL"},
    {"colorName": "Azul", "anchor": [0, 90, 220], "base": [0, 90, 220],
     "colorAddSymbol": "COLORADD_AZUL"},
    {"colorName": "Azul", "anchor": [20, 0, 255], "base": [0, 90, 220],
     "colorAddSymbol": "COLORADD_AZUL"},

    {"colorName": "Roxo", "anchor": [130, 0, 220], "base": [128, 0, 190],
     "colorAddSymbol": "COLORADD_ROXO"},
    {"colorName": "Roxo", "anchor": [180, 0, 190], "base": [128, 0, 190],
     "colorAddSymbol": "COLORADD_ROXO"},
]

CASTANHO_BASE = [120, 72, 35]

NEUTRAL_MAX_CHROMA = 12.0
NEUTRAL_MAX_SATURATION = 0.15
TONE_DELTA = 12.0

# Faixas de L* para os neutros. As fronteiras branco/cinza claro e
# preto/cinza escuro sao ambiguas por natureza: sem referencia de branco na
# cena, uma camisa branca com pouca luz e uma cinza clara com luz forte geram
# o mesmo pixel. Por isso o aviso de iluminacao importa tanto aqui.
PRETO_MAX_LIGHTNESS = 20.0
CINZA_ESCURO_MAX_LIGHTNESS = 38.0
CINZA_CLARO_MIN_LIGHTNESS = 62.0
BRANCO_MIN_LIGHTNESS = 78.0

# Um pastel e' a versao "lavada" da cor: mesma familia, croma bem menor.
# Necessario porque o amarelo ja' nasce quase no teto de L*, entao o
# amarelo claro nunca seria alcancado so' por diferenca de luminosidade.
PASTEL_CHROMA_RATIO = 0.60


def rgb_to_hex(rgb: list[int]) -> str:
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


def get_saturation(rgb: list[int]) -> float:
    r, g, b = [x / 255 for x in rgb]
    _, s, _ = colorsys.rgb_to_hsv(r, g, b)
    return s


def pivot_rgb(value: float) -> float:
    value = value / 255
    if value > 0.04045:
        return ((value + 0.055) / 1.055) ** 2.4
    return value / 12.92


def pivot_xyz(value: float) -> float:
    if value > 0.008856:
        return value ** (1 / 3)
    return (7.787 * value) + (16 / 116)


def rgb_to_lab(rgb: list[int]) -> list[float]:
    r, g, b = [pivot_rgb(value) for value in rgb]

    x = pivot_xyz((r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047)
    y = pivot_xyz((r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.00000)
    z = pivot_xyz((r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883)

    return [(116 * y) - 16, 500 * (x - y), 200 * (y - z)]


def rgb_to_lch(rgb: list[int]) -> tuple[float, float, float]:
    """Devolve (luminosidade L*, croma C*, matiz H em graus)."""
    lightness, a, b = rgb_to_lab(rgb)

    return lightness, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def get_lightness(rgb: list[int]) -> float:
    """Luminosidade percebida (L* do CIELAB), de 0 a 100."""
    return rgb_to_lab(rgb)[0]


def hue_distance(hue_a: float, hue_b: float) -> float:
    """Menor distancia angular entre dois matizes."""
    diff = abs(hue_a - hue_b) % 360

    return min(diff, 360 - diff)


def detect_neutral_color(rgb: list[int]):
    lightness, chroma, _ = rgb_to_lch(rgb)

    if chroma >= NEUTRAL_MAX_CHROMA and get_saturation(rgb) >= NEUTRAL_MAX_SATURATION:
        return None

    if lightness < PRETO_MAX_LIGHTNESS:
        return {"colorName": "Preto", "colorAddSymbol": "COLORADD_PRETO"}

    if lightness > BRANCO_MIN_LIGHTNESS:
        return {"colorName": "Branco", "colorAddSymbol": "COLORADD_BRANCO"}

    if lightness < CINZA_ESCURO_MAX_LIGHTNESS:
        return {"colorName": "Cinza Escuro", "colorAddSymbol": "COLORADD_CINZA_ESCURO"}

    if lightness > CINZA_CLARO_MIN_LIGHTNESS:
        return {"colorName": "Cinza Claro", "colorAddSymbol": "COLORADD_CINZA_CLARO"}

    return {"colorName": "Cinza", "colorAddSymbol": "COLORADD_CINZA"}


def apply_tone(
    color_name: str,
    base_symbol: str,
    lightness: float,
    chroma: float,
    base_rgb: list[int],
):
    """
    Decide claro/escuro comparando a luminosidade da cor lida com a
    luminosidade da PROPRIA cor de referencia. Um amarelo e' naturalmente
    claro e um azul e' naturalmente escuro, entao um limiar fixo nao serve.
    """
    base_lightness, base_chroma, _ = rgb_to_lch(base_rgb)
    delta = lightness - base_lightness

    is_pastel = (
        chroma < base_chroma * PASTEL_CHROMA_RATIO
        and lightness >= base_lightness
    )

    if delta > TONE_DELTA or is_pastel:
        return {
            "colorName": f"{color_name} Claro",
            "colorAddSymbol": f"{base_symbol}_CLARO",
        }

    if delta < -TONE_DELTA:
        return {
            "colorName": f"{color_name} Escuro",
            "colorAddSymbol": f"{base_symbol}_ESCURO",
        }

    return {"colorName": color_name, "colorAddSymbol": base_symbol}


def detect_lighting_warning_code(rgb: list[int]):
    """
    So' avisa quando a imagem perdeu informacao de verdade: escura ou clara
    demais para restar sinal de cor. Uma peca preta ou branca bem fotografada
    NAO deve disparar aviso, senao o usuario aprende a ignora-lo.
    """
    lightness, _, _ = rgb_to_lch(rgb)

    # Limiares deliberadamente extremos: o aviso so deve aparecer quando a
    # imagem perdeu sinal de cor de verdade. Uma peca preta ou branca bem
    # fotografada NAO pode dispara-lo, senao o usuario aprende a ignorar.
    if lightness < 8:
        return "LOW_LIGHT"

    if lightness > 97:
        return "HIGH_LIGHT"

    return None


def match_hue_family(rgb: list[int]):
    """Escolhe a familia pelo MATIZ, independente de quao clara ou escura a peca esta."""
    _, _, hue = rgb_to_lch(rgb)

    return min(
        HUE_REFERENCES,
        key=lambda reference: hue_distance(hue, rgb_to_lch(reference["anchor"])[2]),
    )


def is_castanho(color_name: str, lightness: float, chroma: float) -> bool:
    """Castanho e' laranja/amarelo escurecido ou dessaturado."""
    if color_name not in ("Laranja", "Amarelo"):
        return False

    return lightness < 48 or (chroma < 28 and lightness < 88)


def map_rgb_to_color(rgb: list[int]):
    warning_code = detect_lighting_warning_code(rgb)
    lightness, chroma, _ = rgb_to_lch(rgb)

    neutral = detect_neutral_color(rgb)

    if neutral:
        return {
            "colorName": neutral["colorName"],
            "hex": rgb_to_hex(rgb),
            "colorAddSymbol": neutral["colorAddSymbol"],
            "warningCode": warning_code,
        }

    reference = match_hue_family(rgb)

    color_name = reference["colorName"]
    base_symbol = reference["colorAddSymbol"]
    base_rgb = reference["base"]

    if is_castanho(color_name, lightness, chroma):
        color_name = "Castanho"
        base_symbol = "COLORADD_CASTANHO"
        base_rgb = CASTANHO_BASE

    tone_result = apply_tone(color_name, base_symbol, lightness, chroma, base_rgb)

    return {
        "colorName": tone_result["colorName"],
        "hex": rgb_to_hex(rgb),
        "colorAddSymbol": tone_result["colorAddSymbol"],
        "warningCode": warning_code,
    }
