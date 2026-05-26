import colorsys
import math


COLOR_REFERENCES = [
    {
        "colorName": "Vermelho",
        "rgb": [220, 20, 60],
        "colorAddSymbol": "COLORADD_VERMELHO",
    },
    {
        "colorName": "Laranja",
        "rgb": [255, 140, 0],
        "colorAddSymbol": "COLORADD_LARANJA",
    },
    {
        "colorName": "Amarelo",
        "rgb": [235, 215, 120],
        "colorAddSymbol": "COLORADD_AMARELO",
    },
    {
        "colorName": "Verde",
        "rgb": [34, 139, 34],
        "colorAddSymbol": "COLORADD_VERDE",
    },
    {
        "colorName": "Azul",
        "rgb": [30, 90, 168],
        "colorAddSymbol": "COLORADD_AZUL",
    },
    {
        "colorName": "Roxo",
        "rgb": [128, 0, 128],
        "colorAddSymbol": "COLORADD_ROXO",
    },
    {
        "colorName": "Rosa",
        "rgb": [190, 120, 140],
        "colorAddSymbol": "COLORADD_ROSA",
    },
    {
        "colorName": "Castanho",
        "rgb": [120, 72, 35],
        "colorAddSymbol": "COLORADD_CASTANHO",
    }
]


def rgb_to_hex(rgb: list[int]) -> str:
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


def get_brightness(rgb: list[int]) -> float:
    r, g, b = rgb
    return (r + g + b) / 3


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

    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.00000
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883

    x = pivot_xyz(x)
    y = pivot_xyz(y)
    z = pivot_xyz(z)

    l = (116 * y) - 16
    a = 500 * (x - y)
    b_lab = 200 * (y - z)

    return [l, a, b_lab]


def calculate_lab_distance(rgb_a: list[int], rgb_b: list[int]) -> float:
    lab_a = rgb_to_lab(rgb_a)
    lab_b = rgb_to_lab(rgb_b)

    return math.sqrt(
        (lab_a[0] - lab_b[0]) ** 2
        + (lab_a[1] - lab_b[1]) ** 2
        + (lab_a[2] - lab_b[2]) ** 2
    )


def detect_neutral_color(rgb: list[int]):
    brightness = get_brightness(rgb)
    saturation = get_saturation(rgb)

    if saturation < 0.12:
        if brightness < 50:
            return {"colorName": "Preto", "colorAddSymbol": "COLORADD_PRETO"}

        if brightness > 220:
            return {"colorName": "Branco", "colorAddSymbol": "COLORADD_BRANCO"}

        return {"colorName": "Cinza", "colorAddSymbol": "COLORADD_CINZA"}

    return None


def apply_tone(color_name: str, base_symbol: str, brightness: float):
    if brightness > 200:
        return {
            "colorName": f"{color_name} Claro",
            "colorAddSymbol": f"{base_symbol}_CLARO",
        }

    if brightness < 80:
        return {
            "colorName": f"{color_name} Escuro",
            "colorAddSymbol": f"{base_symbol}_ESCURO",
        }

    return {
        "colorName": color_name,
        "colorAddSymbol": base_symbol,
    }


def detect_lighting_warning_code(rgb: list[int]):
    brightness = get_brightness(rgb)
    saturation = get_saturation(rgb)

    if brightness < 60:
        return "LOW_LIGHT"

    if brightness > 230:
        return "HIGH_LIGHT"
    
    if brightness < 90 and saturation < 0.18:

        return "LOW_LIGHT"

    return None

def detect_special_cases(rgb: list[int]):
    r, g, b = rgb
    brightness = get_brightness(rgb)
    saturation = get_saturation(rgb)

    is_beige_like = (
        brightness > 150
        and 0.12 <= saturation <= 0.32
        and r >= g >= b
        and (r - g) <= 25
        and (g - b) <= 35
        and (r - b) <= 60
    )

    if is_beige_like:
        return {
            "colorName": "Castanho Claro",
            "colorAddSymbol": "COLORADD_CASTANHO_CLARO",
        }

    return None

def map_rgb_to_color(rgb: list[int]):
    warning_code = detect_lighting_warning_code(rgb)
    neutral = detect_neutral_color(rgb)

    if neutral:
        return {
            "colorName": neutral["colorName"],
            "hex": rgb_to_hex(rgb),
            "colorAddSymbol": neutral["colorAddSymbol"],
        }

    special_case = detect_special_cases(rgb)

    if special_case:
        return {
            "colorName": special_case["colorName"],
            "hex": rgb_to_hex(rgb),
            "colorAddSymbol": special_case["colorAddSymbol"],
        }

    closest_color = min(
        COLOR_REFERENCES,
        key=lambda color: calculate_lab_distance(rgb, color["rgb"]),
    )

    brightness = get_brightness(rgb)

    tone_result = apply_tone(
        closest_color["colorName"],
        closest_color["colorAddSymbol"],
        brightness,
    )

    return {
        "colorName": tone_result["colorName"],
        "hex": rgb_to_hex(rgb),
        "colorAddSymbol": tone_result["colorAddSymbol"],
        "warningCode": warning_code,
    }
