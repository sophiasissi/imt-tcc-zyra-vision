import base64
import io
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, UnidentifiedImageError

from src.clothing_analysis.taxonomy import (
    CATEGORIES,
    MATERIALS,
    OCCASIONS,
    PATTERNS,
    STYLES,
    WARMTH,
    describe,
    normalize_value,
)

load_dotenv()

# Modelo configuravel por ambiente, para trocar sem mexer no codigo.
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# A foto do celular chega com resolucao cheia. Para reconhecer a peca isso e'
# desperdicio: o custo da chamada cresce com o tamanho da imagem, e 512px de
# lado bastam.
MAX_LADO = 512
JPEG_QUALIDADE = 80

_cliente = None


def get_cliente() -> OpenAI:
    """
    Cria o cliente da OpenAI na primeira chamada, nao na importacao do modulo.

    Instanciado no nivel do modulo, sem a chave no ambiente o simples `import`
    levantava OpenAIError e derrubava a API INTEIRA -- incluindo /detect-color
    e /validate-clothing, que nao dependem da OpenAI.
    """
    global _cliente

    if _cliente is None:
        chave = os.getenv("OPENAI_API_KEY")

        if not chave:
            raise RuntimeError(
                "OPENAI_API_KEY nao configurada. Defina no .env do servico de visao."
            )

        _cliente = OpenAI(api_key=chave)

    return _cliente


def reduzir_imagem(image_bytes: bytes, max_lado: int = MAX_LADO) -> bytes:
    """Reduz a foto antes de enviar, para diminuir custo e latencia."""
    imagem = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    if max(imagem.size) > max_lado:
        imagem.thumbnail((max_lado, max_lado), Image.LANCZOS)

    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=JPEG_QUALIDADE)

    return buffer.getvalue()

SYSTEM_PROMPT = f"""
Você é um analisador de roupas para um aplicativo de moda acessível.
A imagem já foi validada como uma peça de roupa.

Analise a imagem e responda SOMENTE JSON com:

{{
  "category": string | null,
  "style": string | null,
  "pattern": string | null,
  "warmth": string | null,
  "material": string | null,
  "occasions": string[]
}}

Regras:
- category, style, pattern, warmth, material e occasions devem usar EXATAMENTE
  um dos códigos das listas abaixo (em maiúsculas). Se nenhum servir, use null.
- category:
{describe(CATEGORIES)}
- style:
{describe(STYLES)}
- pattern:
{describe(PATTERNS)}
- occasions: todas as ocasiões em que a peça funciona (de 1 a 3):
{describe(OCCASIONS)}
- warmth: o quanto a peça esquenta, pela espessura e pelo material visíveis:
{describe(WARMTH)}
- material: só se for claramente um destes; qualquer outro material é null:
{describe(MATERIALS)}
"""


def analyze_clothing(image_bytes: bytes):
    try:
        Image.open(io.BytesIO(image_bytes)).verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValueError("Imagem inválida")

    # Sempre reenviada como JPEG reduzido, qualquer que seja o formato original.
    base64_image = base64.b64encode(reduzir_imagem(image_bytes)).decode("utf-8")

    response = get_cliente().chat.completions.create(
        model=MODEL,
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
                            "url": f"data:image/jpeg;base64,{base64_image}"
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

    return {
        "category": normalize_value(data.get("category"), CATEGORIES),
        "style": normalize_value(data.get("style"), STYLES),
        "pattern": normalize_value(data.get("pattern"), PATTERNS),
        "warmth": normalize_value(data.get("warmth"), WARMTH),
        "material": normalize_value(data.get("material"), MATERIALS),
        "occasions": normalized_occasions,
    }
