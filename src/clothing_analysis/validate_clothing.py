import io

import torch
from PIL import Image, UnidentifiedImageError
from transformers import CLIPModel, CLIPProcessor

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
model.eval()

# A validacao roda em duas etapas, cada uma com o seu conjunto de rotulos:
#
#   1. PESSOA: a foto e de alguem vestindo a roupa (selfie, retrato, corpo
#      inteiro)? Essa etapa ja funcionava bem e continua igual.
#   2. ROUPA x OBJETO: a foto e de uma peca ou de um objeto qualquer?
#
# So passa o que pode ser cadastrado (as categorias de taxonomy.py). Bone e
# chapeu ficam de fora: nao entram em looks.
#
# A segunda etapa existia como um rotulo generico "a clothing item" contra um
# unico "an everyday object". Qualquer coisa de tecido ou com ziper -- uma
# necessaire, um estojo, uma toalha -- ficava mais perto de "roupa" do que de
# "objeto qualquer" e era aceita. Agora cada lado tem descricoes especificas,
# inclusive dos objetos que mais se parecem com roupa, e a decisao soma as
# probabilidades de cada grupo em vez de olhar um rotulo so.

# --- Etapa 1: pessoa -------------------------------------------------------

PERSON_STAGE_LABELS = [
    "a clothing item",
    "a pair of shoes",
    "a handbag or backpack",
    "a hat or cap",
    "a necktie",
    "a clothing item held by a person",
    "a full body photo of a person",
    "a person wearing clothes",
    "a portrait photo",
    "a selfie",
    "a person posing",
    "an everyday object",
]

PERSON_LABELS = {
    "a full body photo of a person",
    "a person wearing clothes",
    "a portrait photo",
    "a selfie",
    "a person posing",
}

PERSON_STAGE_CLOTHING_LABELS = {
    "a clothing item",
    "a pair of shoes",
    "a handbag or backpack",
    "a clothing item held by a person",
}

# Rotulos que, quando vencem sozinhos, indicam uma foto de pessoa.
PORTRAIT_LABELS = {"a portrait photo", "a selfie", "a person posing"}

# Bone, chapeu e gravata continuam como rotulo para o CLIP ter onde encaixa-los (senao
# caem em "a clothing item"), mas quando vencem a foto e recusada.
NOT_REGISTRABLE_LABELS = {"a hat or cap", "a necktie"}

# --- Etapa 2: roupa x objeto ----------------------------------------------

CLOTHING_LABELS = [
    "a photo of a t-shirt",
    "a photo of a shirt",
    "a photo of a blouse",
    "a photo of a sweater",
    "a photo of a hoodie",
    "a photo of a jacket or coat",
    "a photo of a blazer",
    "a photo of a dress",
    "a photo of a skirt",
    "a photo of pants or jeans",
    "a photo of shorts",
    "a photo of sneakers",
    "a photo of shoes",
    "a photo of boots",
    "a photo of sandals",
    "a photo of a scarf",
    "a photo of a handbag or purse",
    "a photo of a backpack",
    "a photo of a clothing item on a hanger",
    "a photo of a folded piece of clothing",
]

# Bone, chapeu e gravata entram como objeto porque nao sao cadastraveis. Os seguintes sao
# os que mais se confundem com roupa: tecido, ziper, formato de bolsa. Sem
# eles, o modelo nao tem para onde mandar essas fotos.
OBJECT_LABELS = [
    "a photo of a cap or hat",
    "a photo of a necktie",
    "a photo of a cosmetic bag",
    "a photo of a makeup pouch",
    "a photo of a toiletry bag",
    "a photo of a pencil case",
    "a photo of a zippered pouch",
    "a photo of a wallet",
    "a photo of a towel",
    "a photo of a pillow or cushion",
    "a photo of a blanket",
    "a photo of a stuffed toy",
    "a photo of a mug or cup",
    "a photo of a phone",
    "a photo of a book",
    "a photo of a box",
    "a photo of furniture",
    "a photo of an everyday object",
]

CATEGORY_STAGE_LABELS = CLOTHING_LABELS + OBJECT_LABELS


def _como_tensor(saida) -> torch.Tensor:
    """
    get_text_features/get_image_features devolvem o tensor direto no
    transformers 4.x (o fixado no requirements.txt) e um objeto com
    pooler_output no 5.x. Aceita os dois.
    """
    return saida if isinstance(saida, torch.Tensor) else saida.pooler_output


def _encode_texts(labels: list[str]) -> torch.Tensor:
    inputs = processor(text=labels, return_tensors="pt", padding=True)

    with torch.no_grad():
        features = _como_tensor(model.get_text_features(**inputs))

    return features / features.norm(dim=-1, keepdim=True)


# Os textos nao mudam entre uma foto e outra: sao codificados uma vez so, na
# subida do servico. A cada foto so a imagem e processada.
_PERSON_STAGE_FEATURES = _encode_texts(PERSON_STAGE_LABELS)
_CATEGORY_STAGE_FEATURES = _encode_texts(CATEGORY_STAGE_LABELS)


def _scores(image_features: torch.Tensor, text_features: torch.Tensor, labels: list[str]):
    """Probabilidade de cada rotulo, igual ao softmax do CLIPModel."""
    with torch.no_grad():
        logits = model.logit_scale.exp() * image_features @ text_features.T
        probs = logits.softmax(dim=-1)[0]

    return {label: probs[index].item() for index, label in enumerate(labels)}


def validate_clothing(image_bytes: bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError:
        raise ValueError("Imagem inválida")

    with torch.no_grad():
        pixel_values = processor(images=image, return_tensors="pt")["pixel_values"]
        image_features = _como_tensor(model.get_image_features(pixel_values=pixel_values))

    image_features = image_features / image_features.norm(dim=-1, keepdim=True)

    # Etapa 1: pessoa.
    person_stage = _scores(image_features, _PERSON_STAGE_FEATURES, PERSON_STAGE_LABELS)

    best_person_score = max(person_stage[label] for label in PERSON_LABELS)
    best_clothing_score = max(person_stage[label] for label in PERSON_STAGE_CLOTHING_LABELS)

    if best_person_score >= 0.20 and (best_clothing_score - best_person_score) < 0.30:
        return {
            "isClothing": False,
            "confidence": round(best_person_score, 2),
            "reason": "PERSON_DETECTED",
        }

    best_label = max(person_stage, key=person_stage.get)

    if best_label in PORTRAIT_LABELS:
        return {
            "isClothing": False,
            "confidence": round(person_stage[best_label], 2),
            "reason": "PERSON_DETECTED",
        }

    if best_label in NOT_REGISTRABLE_LABELS:
        return {
            "isClothing": False,
            "confidence": round(person_stage[best_label], 2),
            "reason": "NOT_CLOTHING",
        }

    # Etapa 2: roupa x objeto.
    category_stage = _scores(image_features, _CATEGORY_STAGE_FEATURES, CATEGORY_STAGE_LABELS)

    clothing_score = sum(category_stage[label] for label in CLOTHING_LABELS)
    object_score = sum(category_stage[label] for label in OBJECT_LABELS)

    if clothing_score > object_score:
        return {
            "isClothing": True,
            "confidence": round(clothing_score, 2),
            "reason": None,
        }

    return {
        "isClothing": False,
        "confidence": round(object_score, 2),
        "reason": "NOT_CLOTHING",
    }
