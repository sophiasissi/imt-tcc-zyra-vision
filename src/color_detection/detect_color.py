import cv2
import numpy as np

from src.color_detection.color_mapper import map_rgb_to_color


def crop_center(image, crop_ratio: float = 0.2):
    height, width, _ = image.shape

    crop_size = int(min(width, height) * crop_ratio)

    center_x = width // 2
    center_y = height // 2

    x1 = max(center_x - crop_size // 2, 0)
    x2 = min(center_x + crop_size // 2, width)
    y1 = max(center_y - crop_size // 2, 0)
    y2 = min(center_y + crop_size // 2, height)

    return image[y1:y2, x1:x2]


def detect_dominant_color(image_bytes: bytes):
    np_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Imagem inválida")

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    center_crop = crop_center(image_rgb)

    pixels = center_crop.reshape((-1, 3))
    average_color = pixels.mean(axis=0)

    r, g, b = average_color.astype(int)
    rgb = [int(r), int(g), int(b)]

    return map_rgb_to_color(rgb)