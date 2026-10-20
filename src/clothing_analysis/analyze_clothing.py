import base64
import io
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from src.clothing_analysis.taxonomy import (
    CATEGORIES,
    CATEGORIES_WITHOUT_SLEEVE,
    MATERIALS,
    OCCASIONS,
    PATTERNS,
    SLEEVES,
    STYLES,
    WARMTH,
    describe,
    normalize_value,
)
from src.color_detection.coloradd import SYMBOLS, symbol_color
from src.image_io import open_srgb

load_dotenv()

# Modelo configuravel por ambiente, para trocar sem mexer no codigo.
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# A foto do celular chega com resolucao cheia. Para reconhecer a peca isso e'
# desperdicio: o custo da chamada cresce com o tamanho da imagem, e 512px de
# lado bastam.
MAX_LADO = 512
JPEG_QUALIDADE = 80

# Fracao do menor lado usada no recorte de detalhe do tecido. Reduzida a 512px,
# a foto inteira perde a textura: uma blusa de paete parecia estampa de
# florzinhas. O recorte vai em resolucao maior, junto com a foto inteira.
DETALHE_FRACAO = 0.4

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


def _jpeg(imagem: Image.Image, max_lado: int) -> bytes:
    if max(imagem.size) > max_lado:
        imagem = imagem.copy()
        imagem.thumbnail((max_lado, max_lado), Image.LANCZOS)

    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=JPEG_QUALIDADE)

    return buffer.getvalue()


def preparar_imagens(image_bytes: bytes, max_lado: int = MAX_LADO) -> tuple[bytes, bytes]:
    """
    A foto inteira reduzida e um recorte do centro, para o detalhe do tecido.

    Reduzir diminui custo e latencia. As duas saem em sRGB e em pe': o JPEG
    reduzido nao leva o perfil P3 nem a orientacao do EXIF, e sem a conversao
    o GPT recebia a foto desbotada e deitada.
    """
    imagem = open_srgb(image_bytes)

    largura, altura = imagem.size
    lado = int(min(largura, altura) * DETALHE_FRACAO)
    esquerda = (largura - lado) // 2
    topo = (altura - lado) // 2
    detalhe = imagem.crop((esquerda, topo, esquerda + lado, topo + lado))

    return _jpeg(imagem, max_lado), _jpeg(detalhe, max_lado)

SYSTEM_PROMPT = f"""
Você é um analisador de roupas para um aplicativo de moda acessível, usado por
pessoas daltônicas. A imagem já foi validada como uma peça de roupa.

Analise a imagem e preencha os campos com os códigos das listas abaixo.

Regras:
- category:
{describe(CATEGORIES)}
  Regata comprida (até o quadril) é CAMISETA sem manga; regata ou camiseta
  cortada acima do umbigo é CROPPED; TOP é só o que cobre o busto e termina
  logo abaixo dele. Tomara que caia que vai além do busto é CROPPED. Na
  dúvida entre TOP e CROPPED, escolha CROPPED: TOP é só top de academia, top
  de bojo ou faixa estreita.
  Moletom aberto na frente com zíper é JAQUETA com material MOLETOM.
  Vestido é comprido: cobre o quadril e vai pelo menos até o meio da coxa.
  Peça de cima curta com alças, decote ou amarração é BLUSA, não VESTIDO.
  Parte de cima de pijama sem manga é CAMISETA (regata).
- pajama: true se for roupa de dormir: estampa de pijama (corações, laços,
  bichinhos), conjunto de dormir, camisola, tecido de dormir (soft, malha leve
  e larga). Calça de moletom de sair NÃO é pijama.
- partyDetail: true se o tecido tiver brilho (paetê, lantejoula, lurex,
  metalizado, cetim brilhante), renda ou transparência. Decida pela segunda
  imagem, o detalhe: na peça inteira, paetê parece estampa de bolinhas ou
  florzinhas.
- sleeve: a manga da peça; null para calça, short, saia e calçado:
{describe(SLEEVES)}
- style:
{describe(STYLES)}
- pattern:
{describe(PATTERNS)}
- occasions: todas as ocasiões em que a peça funciona (de 1 a 3):
{describe(OCCASIONS)}
  Peça de sair com decote marcado, frente única ou costas abertas inclui FESTA.
- warmth: o quanto a peça esquenta, pela espessura e pelo material visíveis:
{describe(WARMTH)}
- material: o tecido mais provável pela aparência (espessura, brilho, textura,
  caimento). Use null só se não der para ter ideia:
{describe(MATERIALS)}
- A primeira imagem é a peça inteira: as cores, a categoria e o formato vêm
  dela. A segunda é um detalhe ampliado do centro, só para ver o tecido
  (textura, brilho, paetê, renda, trama do jeans).
- primaryColor e secondaryColor: códigos do ColorADD: {", ".join(SYMBOLS)}.
  - A foto pode ter luz amarela de lâmpada: diga a cor real do tecido, como uma
    pessoa descreveria a peça (uma calça azul bebê sob luz amarela continua
    AZUL_CLARO). Ignore o fundo (cama, lençol, chão).
  - Rosa bebê e salmão = VERMELHO_CLARO; pink e rosa choque = ROXO_CLARO;
    bege = CASTANHO_CLARO; marrom = CASTANHO; vinho = VERMELHO_ESCURO;
    marinho = AZUL_ESCURO; off-white = BRANCO; não existe cinza médio.
  - primaryColor: a cor que ocupa a maior parte da peça.
  - secondaryColor: só se a peça tiver uma segunda cor bem visível (estampa,
    listra, xadrez, detalhe grande). Peça lisa = null. Não conte costura,
    etiqueta, botão ou zíper.
"""


def _codigo(lista) -> dict:
    return {"type": ["string", "null"], "enum": [*lista, None]}


# Structured Outputs: a resposta so pode trazer codigos das listas. Com o modo
# JSON simples, o modelo as vezes inventava um codigo ("REGATA"), o valor era
# descartado e a peca ficava sem categoria -- e o cadastro falhava.
RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "analise_da_peca",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "category",
                "pajama",
                "partyDetail",
                "sleeve",
                "style",
                "pattern",
                "warmth",
                "material",
                "occasions",
                "primaryColor",
                "secondaryColor",
            ],
            "properties": {
                "category": _codigo(CATEGORIES),
                "pajama": {"type": "boolean"},
                "partyDetail": {"type": "boolean"},
                "sleeve": _codigo(SLEEVES),
                "style": _codigo(STYLES),
                "pattern": _codigo(PATTERNS),
                "warmth": _codigo(WARMTH),
                "material": _codigo(MATERIALS),
                "occasions": {"type": "array", "items": {"type": "string", "enum": [*OCCASIONS]}},
                "primaryColor": _codigo(SYMBOLS),
                "secondaryColor": _codigo(SYMBOLS),
            },
        },
    },
}


def analyze_clothing(image_bytes: bytes):
    # Sempre reenviada como JPEG reduzido, qualquer que seja o formato original.
    # Imagem ilegivel ou truncada levanta ValueError("Imagem inválida").
    inteira, detalhe = preparar_imagens(image_bytes)

    def como_url(jpeg: bytes) -> dict:
        codificada = base64.b64encode(jpeg).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{codificada}"}}

    response = get_cliente().chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format=RESPONSE_FORMAT,
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
                        "text": "Analise esta peça. Imagem 1: a peça inteira. Imagem 2: detalhe do tecido.",
                    },
                    como_url(inteira),
                    como_url(detalhe),
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

    # Pijama fica so' em casa: com dia a dia ou festa marcados, o motor
    # sugeria a camisola de renda para sair.
    if data.get("pajama") is True:
        normalized_occasions = ["CASA"]
    elif data.get("partyDetail") is True and "FESTA" not in normalized_occasions:
        # Brilho, paete, renda e transparencia sao de festa. Pela ocasiao o
        # modelo esquecia: a blusa de paete preta saia so' dia a dia e praia.
        normalized_occasions.append("FESTA")

    category = normalize_value(data.get("category"), CATEGORIES)
    sleeve = normalize_value(data.get("sleeve"), SLEEVES)

    # Parte de cima de pijama sem manga e' regata (camiseta sem manga), mesmo
    # com renda ou decote: o modelo insistia em BLUSA.
    if data.get("pajama") is True and category == "BLUSA" and sleeve == "SEM_MANGA":
        category = "CAMISETA"
    if category in CATEGORIES_WITHOUT_SLEEVE:
        sleeve = None

    primary_color = symbol_color(data.get("primaryColor"))
    secondary_color = symbol_color(data.get("secondaryColor"))
    # Repetir a cor principal como secundaria nao informa nada.
    if (
        secondary_color
        and primary_color
        and secondary_color["colorAddSymbol"] == primary_color["colorAddSymbol"]
    ):
        secondary_color = None

    return {
        "category": category,
        "sleeve": sleeve,
        "style": normalize_value(data.get("style"), STYLES),
        "pattern": normalize_value(data.get("pattern"), PATTERNS),
        "warmth": normalize_value(data.get("warmth"), WARMTH),
        "material": normalize_value(data.get("material"), MATERIALS),
        "occasions": normalized_occasions,
        # {colorName, colorAddSymbol, hex}, com o hex de referencia do simbolo.
        "primaryColor": primary_color,
        "secondaryColor": secondary_color,
    }
