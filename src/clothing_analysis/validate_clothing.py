import io

import torch
from PIL import Image, UnidentifiedImageError
from transformers import CLIPModel, CLIPProcessor

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

LABELS = [
    "a clothing item",
    "a pair of shoes",
    "a hat or cap",
    "a clothing item held by a person",
    "a full body photo of a person",
    "a person wearing clothes",
    "a portrait photo",
    "a selfie",
    "a person posing",
    "an everyday object",
]

VALID_CLOTHING_LABELS = {
    "a clothing item",
    "a pair of shoes",
    "a hat or cap",
    "a clothing item held by a person",
}

INVALID_LABELS = {
    "a portrait photo",
    "a selfie",
    "a person posing",
    "an everyday object",
}

def validate_clothing(image_bytes: bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError:
        raise ValueError("Imagem inválida")

    inputs = processor(
        text=LABELS,
        images=image,
        return_tensors="pt",
        padding=True,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits_per_image
        probs = logits.softmax(dim=1)

    scores = {
        LABELS[index]: probs[0][index].item()
        for index in range(len(LABELS))
    }

    best_label = max(scores, key=scores.get)
    confidence = scores[best_label]

    best_person_score = max(
        scores["a full body photo of a person"],
        scores["a person wearing clothes"],
        scores["a portrait photo"],
        scores["a selfie"],
        scores["a person posing"],
    )

    best_clothing_score = max(
        scores["a clothing item"],
        scores["a pair of shoes"],
        scores["a hat or cap"],
        scores["a clothing item held by a person"],
    )

    if best_person_score >= 0.20 and (best_clothing_score - best_person_score) < 0.30:
        return {
            "isClothing": False,
            "confidence": round(best_person_score, 2),
            "reason": "PERSON_DETECTED",
        }

    if best_label in VALID_CLOTHING_LABELS:
        return {
            "isClothing": True,
            "confidence": round(confidence, 2),
            "reason": None,
        }

    reason = "PERSON_DETECTED" if best_label in {
        "a portrait photo",
        "a selfie",
        "a person posing",
    } else "NOT_CLOTHING"

    return {
        "isClothing": False,
        "confidence": round(confidence, 2),
        "reason": reason,
    }