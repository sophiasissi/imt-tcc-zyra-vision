import math
import os

import numpy as np


# ---------------------------------------------------------------------------
# FAMILIA da cor: modelo de nomes de cor de van de Weijer et al. (2009),
# "Learning Color Names for Real-World Applications", IEEE Transactions on
# Image Processing. Aprendido a partir de milhares de fotos reais, ele da' o
# nome basico mais provavel (entre 11) para cada cor do sRGB, numa grade
# 32x32x32. data/w2c_nomes.npy guarda so' o indice desse nome, gerado do
# w2c.mat original dos autores.
#
# Substituiu os limiares escolhidos a mao (croma < 12 = neutro e matiz mais
# proximo de uma ancora). Em 39 fotos de pecas reais, simulando a mira da
# camera, a familia certa subiu de 54% para 64%: jeans e preto deixaram de
# virar cinza, e marrom escuro deixou de virar cinza escuro.
#
# O ColorADD e' construido sobre azul, amarelo e vermelho, com preto e branco
# marcando escuro e claro. Nao ha simbolo proprio de rosa: rosa e' vermelho
# claro.
# ---------------------------------------------------------------------------
_W2C_NOMES = np.load(os.path.join(os.path.dirname(__file__), "data", "w2c_nomes.npy"))

_W2C_FAMILIAS = [
    "Preto", "Azul", "Castanho", "Cinza", "Verde", "Laranja",
    "Rosa", "Roxo", "Vermelho", "Branco", "Amarelo",
]

# Cor canonica de cada familia cromatica, usada so' para decidir claro/escuro.
FAMILY_BASES = {
    "Vermelho": [255, 0, 0],
    "Laranja": [255, 140, 0],
    "Amarelo": [255, 235, 0],
    "Verde": [0, 190, 60],
    "Azul": [0, 90, 220],
    "Roxo": [128, 0, 190],
    "Castanho": [120, 72, 35],
}

TONE_DELTA = 12.0

# Faixas de L* para o tom do cinza. Preto e branco vem da tabela de nomes.
# As fronteiras com eles sao ambiguas por natureza: sem referencia de branco
# na cena, uma camisa branca com pouca luz e uma cinza clara com luz forte
# geram o mesmo pixel. Por isso o aviso de iluminacao importa tanto aqui.
CINZA_ESCURO_MAX_LIGHTNESS = 38.0
CINZA_CLARO_MIN_LIGHTNESS = 62.0

# Um pastel e' a versao "lavada" da cor: mesma familia, croma bem menor.
# Necessario porque o amarelo ja' nasce quase no teto de L*, entao o
# amarelo claro nunca seria alcancado so' por diferenca de luminosidade.
PASTEL_CHROMA_RATIO = 0.60


def rgb_to_hex(rgb: list[int]) -> str:
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


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


def match_family(rgb: list[int]) -> str:
    """Nome basico mais provavel da cor, pela tabela de van de Weijer."""
    r, g, b = (int(value) // 8 for value in rgb)

    return _W2C_FAMILIAS[_W2C_NOMES[r + 32 * g + 1024 * b]]


def gray_tone(lightness: float):
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


def map_rgb_to_color(rgb: list[int]):
    warning_code = detect_lighting_warning_code(rgb)
    lightness, chroma, _ = rgb_to_lch(rgb)

    family = match_family(rgb)

    if family in ("Preto", "Branco"):
        result = {"colorName": family, "colorAddSymbol": f"COLORADD_{family.upper()}"}
    elif family == "Cinza":
        result = gray_tone(lightness)
    elif family == "Rosa":
        result = {"colorName": "Vermelho Claro", "colorAddSymbol": "COLORADD_VERMELHO_CLARO"}
    else:
        result = apply_tone(
            family,
            f"COLORADD_{family.upper()}",
            lightness,
            chroma,
            FAMILY_BASES[family],
        )

    return {
        "colorName": result["colorName"],
        "hex": rgb_to_hex(rgb),
        "colorAddSymbol": result["colorAddSymbol"],
        "warningCode": warning_code,
    }
