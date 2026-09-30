import base64
import io
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, UnidentifiedImageError

from src.clothing_analysis.taxonomy import (
    CATEGORIES,
    OCCASIONS,
    PATTERNS,
    STYLES,
    describe,
    normalize_value,
)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = f"""
Você é um analisador de roupas para um aplicativo de moda acessível.
A imagem já foi validada como uma peça de roupa.

Analise a imagem e responda SOMENTE JSON com:

{{
  "category": string | null,
  "style": string | null,
  "pattern": string | null,
  "fabric": string | null,
  "occasions": string[]
}}

Regras:
- category, style, pattern e occasions devem usar EXATAMENTE um dos códigos
  das listas abaixo (em maiúsculas). Se nenhum servir, use null.
- category:
{describe(CATEGORIES)}
- style:
{describe(STYLES)}
- pattern:
{describe(PATTERNS)}
- occasions: todas as ocasiões em que a peça funciona (de 1 a 3):
{describe(OCCASIONS)}
- fabric é texto livre, em minúsculas, com o material predominante
  (ex: algodão, jeans, couro, linho, malha, poliéster, lã, seda, veludo).
"""


def analyze_clothing(image_bytes: bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image_format = image.format
        image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValueError("Imagem inválida")

    mime_type = Image.MIME.get(image_format, "image/jpeg")

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analise esta imagem.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        },
                    },
                ],
            },
        ],
    )

    content = response.choices[0].message.content

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise ValueError("Resposta inválida da IA")

    occasions = data.get("occasions") or []
    if not isinstance(occasions, list):
        occasions = [occasions]

    normalized_occasions = []
    for occasion in occasions:
        value = normalize_value(occasion, OCCASIONS)
        if value and value not in normalized_occasions:
            normalized_occasions.append(value)

    fabric = data.get("fabric")

    return {
        "category": normalize_value(data.get("category"), CATEGORIES),
        "style": normalize_value(data.get("style"), STYLES),
        "pattern": normalize_value(data.get("pattern"), PATTERNS),
        "fabric": fabric.strip().lower() if isinstance(fabric, str) else None,
        "occasions": normalized_occasions,
    }
