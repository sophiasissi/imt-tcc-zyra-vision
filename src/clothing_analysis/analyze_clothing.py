import base64
import io
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image, UnidentifiedImageError

from src.color_detection.detect_color import (
    COLOR_SYMBOLS,
    color_from_symbol,
    symbol_name,
)
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

# Cores que a analise pode devolver como cor secundaria: os simbolos ColorADD
# que o app desenha. Rosa e' vermelho claro; bege e marrom sao castanho.
SECONDARY_COLORS = {symbol: symbol_name(symbol) for symbol in COLOR_SYMBOLS}

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
  "occasions": string[],
  "secondary_color": string | null
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
- secondary_color: a segunda cor da peça, só quando ela tem duas cores bem
  visíveis (listras, xadrez, estampa, recortes de cor) e a segunda ocupa uma
  parte relevante da peça. Peça de uma cor só, ou com detalhe pequeno (costura,
  botão, logo pequeno, etiqueta), é null. Ignore o fundo da foto. Rosa é
  VERMELHO_CLARO; bege e marrom são CASTANHO (com _CLARO ou _ESCURO). Códigos:
{describe(SECONDARY_COLORS)}
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

    pattern = normalize_value(data.get("pattern"), PATTERNS)
    secondary = normalize_value(data.get("secondary_color"), SECONDARY_COLORS)

    return {
        "category": normalize_value(data.get("category"), CATEGORIES),
        "style": normalize_value(data.get("style"), STYLES),
        "pattern": pattern,
        "warmth": normalize_value(data.get("warmth"), WARMTH),
        "material": normalize_value(data.get("material"), MATERIALS),
        "occasions": normalized_occasions,
        # Peca lisa nao tem segunda cor, mesmo que a IA aponte uma.
        "secondaryColor": (
            color_from_symbol(image_bytes, secondary)
            if secondary and pattern != "LISO"
            else None
        ),
    }
