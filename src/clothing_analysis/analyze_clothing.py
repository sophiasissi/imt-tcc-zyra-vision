import base64
import io
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

from src.clothing_analysis.taxonomy import (
    BOOT_SHAFTS,
    CATEGORIES,
    CATEGORIES_WITH_COLLAR,
    CATEGORIES_WITH_TAILORING,
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
  SUETER é só a blusa de tricô ou lã sem nenhuma abertura na frente. Com uma
  fileira de botões ou zíper descendo pela frente (cardigã), é JAQUETA com
  material TRICO, mesmo abotoado na foto.
  CORSET é a peça de cima estruturada como os corsets antigos. Os sinais
  FORTES são: amarração de cordão ou fita com ilhoses ou passantes (na frente
  ou nas costas), fileira de colchetes ou ganchos, barbatanas aparentes (canaletas
  em relevo, costuradas por fora, com uma haste dentro; uma costura comum
  não é barbatana, mesmo em tecido firme) e barra em V: a borda de
  BAIXO da peça, na cintura, termina em bico apontando para baixo. O V ou a
  curva da borda de CIMA (decote coração, decote em V) não é barra em V, e
  barra reta, arredondada ou com babado (peplum) também não. Os sinais FRACOS são: costuras verticais aparentes,
  decote estruturado (coração, meia-taça, aro de sutiã) e tecido encorpado
  (sarja, alfaiataria, couro, cetim grosso, jacquard, jeans). Sinal fraco
  sozinho NÃO faz um corset: tomara que caia de decote coração com costuras é
  CROPPED ou TOP. A barra em V sozinha também não: o colete social termina em
  bico. Abotoado com botões na frente é COLETE, mesmo com barra em V. Com
  amarração na frente, é CORSET, nunca COLETE nem BLUSA: a amarração não é a
  abertura de um colete. Laço solto de amarrar (blusa de
  amarração) é BLUSA.
- frontOpening: preencha ANTES da categoria. true se a peça de cima abre na
  frente de cima a baixo: fileira de botões, zíper ou amarração de casaco
  (cardigã, jaqueta, camisa). Blusa fechada, suéter, moletom fechado ou só um
  botão na gola = false.
- corsetSigns: preencha ANTES de escolher a categoria. Os sinais FORTES de
  corset que você vê de fato na foto; na dúvida, deixe de fora. Lista vazia
  se não houver nenhum ou se não for peça de cima. Sem amarração, colchetes
  ou barbatanas, a categoria não pode ser CORSET.
- categoryIfNotCorset: a categoria da peça se ela não fosse um corset (para
  um corset de verdade, a mais parecida: CROPPED, BLUSA ou TOP).
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
- revealing: true se a peça mostra pele demais para um ambiente sério, como o
  trabalho: decote marcado (V fundo, abaixo do colo), costas abertas, frente
  única, ombro de fora, tomara que caia, alça fina, barriga de fora ou tecido
  transparente. Decote careca, gola alta, gola de camisa ou V discreto = false.
  Calça, short, saia e calçado = false.
- mini: true se for SAIA ou VESTIDO curto, que termina acima do meio da coxa
  (minissaia, vestido curto). Na altura do joelho, midi ou longo = false.
  Qualquer outra categoria = false.
- heel: só para SAPATO, SANDALIA e BOTA: true se o calçado tem salto de uns
  3 cm ou mais (scarpin, salto fino, salto bloco, anabela, meia pata, bota de
  salto). Rasteira, sapatilha, mocassim, coturno, bota de solado baixo e
  sapato social masculino (oxford, derby, de amarrar), cujo salto e' baixo e
  largo = false. Qualquer outra categoria (inclusive TENIS) = false.
- heavyCoat: só para JAQUETA e BLAZER: true se é um casaco pesado, de frio
  forte: puffer ou acolchoado (gomos estufados), parka, casaco forrado de pelo
  ou de lã grossa, sobretudo de lã. Jaqueta de couro, jeans, corta-vento,
  casaco de moletom, cardigã e casaco de tricô, de malha ou de soft = false.
  Qualquer outra categoria = false.
- tailoringSigns: preencha ANTES de tailored. Os sinais de corte de alfaiataria
  que você vê de fato na foto (só em CALCA, SHORT, SAIA, VESTIDO, BLAZER,
  COLETE e JAQUETA; nas outras, lista vazia):
  - PREGAS: pregas ou pences na frente, saindo do cós;
  - VINCO: vinco passado descendo pela frente da perna;
  - BOLSO_FACA: bolso inclinado embutido na costura do quadril, sem aba;
  - COS_COM_PASSANTES: cós reto e firme com passantes de cinto e fecho de
    zíper com botão ou colchete;
  - LAPELA: lapela de blazer ou de casaco.
- casualSigns: os sinais de peça casual que você vê: BOLSO_CARGO (bolsos
  grandes com aba nas laterais da perna), COS_DE_ELASTICO (cós de elástico ou
  de cordão), PUNHO (punho de elástico na barra, jogger), JEANS (denim,
  pesponto aparente, bolso de jeans), ESTAMPA_CASUAL (camuflado, tie-dye,
  estampa gráfica). Lista vazia se não houver.
- tailored: true se a peça tem corte de alfaiataria (calça social, pantalona
  ou wide leg de tecido plano com pregas e cós com passantes, blazer, colete
  social, saia lápis). Vale qualquer fibra: uma calça de alfaiataria de
  viscose, linho ou poliéster é tailored. Calça cargo, jogger, de malha, de
  moletom, legging e jeans = false.
- collar: true se a peça tem gola de camisa (colarinho dobrado): camisa, camisa
  polo, chemise, blusa com gola de camisa. Gola redonda, V, careca, alta ou
  capuz = false. Polo é CAMISETA com collar true.
- bootShaft: só para BOTA, a altura do cano, pela foto; null em qualquer outra
  categoria. Na dúvida entre dois, escolha o mais curto:
{describe(BOOT_SHAFTS)}
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
- material: o tecido (a fibra) mais provável pela aparência (espessura, brilho,
  textura, caimento). O corte de alfaiataria vai em tailored; aqui vai o
  tecido. Use null só se não der para ter ideia:
{describe(MATERIALS)}
- A primeira imagem é a peça inteira: as cores, a categoria e o formato vêm
  dela. A segunda é um detalhe ampliado do centro, só para ver o tecido
  (textura, brilho, paetê, renda, trama do jeans).
- primaryColor e secondaryColor: códigos do ColorADD: {", ".join(SYMBOLS)}.
  - A foto pode ter luz amarela de lâmpada: diga a cor real do tecido, como uma
    pessoa descreveria a peça (uma calça azul bebê sob luz amarela continua
    AZUL_CLARO). Ignore o fundo (cama, lençol, chão).
  - Rosa bebê e salmão = VERMELHO_CLARO; pink e rosa choque = ROXO_CLARO;
    bege, nude e creme = CASTANHO_CLARO; marrom = CASTANHO;
    vinho = VERMELHO_ESCURO; marinho = AZUL_ESCURO; off-white (branco
    quase puro, sem tom amarelado ou rosado) = BRANCO; não existe cinza médio.
    Calçado e couro nude ou creme puxam para o bege: se não é branco de
    verdade, é CASTANHO_CLARO.
  - primaryColor: a cor que ocupa a maior parte da peça.
  - secondaryColor: só se a peça tiver uma segunda cor bem visível (estampa,
    listra, xadrez, detalhe grande). Peça lisa = null. Não conte costura,
    etiqueta, botão ou zíper.
"""


# Sinais fortes de corset (lista da Sophia, 28/10/2026). Os fracos (costuras
# verticais, decote coracao, tecido encorpado) ficam so' no prompt: sozinhos,
# aparecem em qualquer tomara que caia.
CORSET_SIGNS = ("AMARRACAO", "COLCHETES", "BARBATANAS", "BARRA_EM_V")

# Sinais do corte de alfaiataria e da peca casual (10/11/2026). So' com o
# campo tailored, a calca wide leg de pregas da Sophia saia sem alfaiataria e
# a calca cargo camuflada saia com.
TAILORING_SIGNS = ("PREGAS", "VINCO", "BOLSO_FACA", "COS_COM_PASSANTES", "LAPELA")
CASUAL_SIGNS = ("BOLSO_CARGO", "COS_DE_ELASTICO", "PUNHO", "JEANS", "ESTAMPA_CASUAL")
# Um destes basta; COS_COM_PASSANTES e BOLSO_FACA tambem aparecem em calca
# casual de sarja e precisam de outro sinal junto.
TAILORING_STRONG = {"PREGAS", "VINCO", "LAPELA"}


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
                "frontOpening",
                "corsetSigns",
                "categoryIfNotCorset",
                "category",
                "pajama",
                "partyDetail",
                "revealing",
                "mini",
                "heel",
                "heavyCoat",
                "tailoringSigns",
                "casualSigns",
                "tailored",
                "collar",
                "bootShaft",
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
                # Os sinais vem antes da categoria: o modelo responde na ordem
                # do schema, e com a categoria primeiro ele decidia "corset" e
                # depois inventava o sinal.
                "frontOpening": {"type": "boolean"},
                "corsetSigns": {"type": "array", "items": {"type": "string", "enum": [*CORSET_SIGNS]}},
                "categoryIfNotCorset": _codigo({c: d for c, d in CATEGORIES.items() if c != "CORSET"}),
                "category": _codigo(CATEGORIES),
                "pajama": {"type": "boolean"},
                "partyDetail": {"type": "boolean"},
                "revealing": {"type": "boolean"},
                "mini": {"type": "boolean"},
                "heel": {"type": "boolean"},
                "heavyCoat": {"type": "boolean"},
                "tailoringSigns": {"type": "array", "items": {"type": "string", "enum": [*TAILORING_SIGNS]}},
                "casualSigns": {"type": "array", "items": {"type": "string", "enum": [*CASUAL_SIGNS]}},
                "tailored": {"type": "boolean"},
                "collar": {"type": "boolean"},
                "bootShaft": _codigo(BOOT_SHAFTS),
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
    # Sueter e' fechado na frente; com botoes ou ziper descendo pela frente,
    # e' cardiga (JAQUETA de trico). So' pelo prompt, o cardiga branco de
    # botoes da Sophia saia SUETER (10/11/2026).
    if category == "SUETER" and data.get("frontOpening") is True:
        category = "JAQUETA"
    # Corset so' com sinal forte (amarracao, colchetes ou barbatanas): o top
    # preto tomara que caia, de decote coracao e costuras, saia corset
    # (28/10/2026). A barra em V sozinha nao basta: o colete social tambem
    # termina em bico, e os coletes de alfaiataria viravam corset.
    sinais = set(data.get("corsetSigns") or []) - {"BARRA_EM_V"}
    if category == "CORSET" and not sinais:
        category = normalize_value(data.get("categoryIfNotCorset"), CATEGORIES) or "CROPPED"
        if category == "CORSET":
            category = "CROPPED"
    sleeve = normalize_value(data.get("sleeve"), SLEEVES)
    material = normalize_value(data.get("material"), MATERIALS)

    # Corset pelo tecido (lista da Sophia, 28/10/2026): couro, cetim e veludo
    # sao de balada, jantar e casamento; o de jeans, do dia a dia.
    if category == "CORSET" and data.get("pajama") is not True:
        if material in ("COURO", "CETIM", "VELUDO") and "FESTA" not in normalized_occasions:
            normalized_occasions.append("FESTA")
        if material == "JEANS" and "DIA_A_DIA" not in normalized_occasions:
            normalized_occasions.append("DIA_A_DIA")

    # Parte de cima de pijama sem manga e' regata (camiseta sem manga), mesmo
    # com renda ou decote: o modelo insistia em BLUSA.
    if data.get("pajama") is True and category == "BLUSA" and sleeve == "SEM_MANGA":
        category = "CAMISETA"
    # Decote e transparencia: o motor de looks tira a peca do trabalho. So'
    # vale para pecas de cima e vestido.
    revealing = data.get("revealing") is True
    if category in CATEGORIES_WITHOUT_SLEEVE:
        sleeve = None
        revealing = False
    if category == "COLETE":
        sleeve = "SEM_MANGA"
    # O corset quase sempre e' sem manga; o modelo as vezes deixava em branco.
    if category == "CORSET" and sleeve is None:
        sleeve = "SEM_MANGA"
    # Comprimento: so' saia e vestido. O motor tira a saia curta do trabalho.
    mini = data.get("mini") is True and category in ("SAIA", "VESTIDO")
    # Salto (05/11/2026): o motor tira o salto do passeio e da balada. So' nos
    # calcados que podem ter salto.
    heel = data.get("heel") is True and category in ("SAPATO", "SANDALIA", "BOTA")
    # Casaco pesado (10/11/2026): puffer, parka, sobretudo. O motor so' o usa
    # com 13 graus ou menos; a jaqueta de cetim acolchoada da Sophia entrou num
    # jantar com 16 a 19 graus.
    heavy_coat = data.get("heavyCoat") is True and category in ("JAQUETA", "BLAZER")
    # Cano: so' na bota. O motor de looks decide a ocasiao e o clima por ele.
    boot_shaft = normalize_value(data.get("bootShaft"), BOOT_SHAFTS) if category == "BOTA" else None

    style = normalize_value(data.get("style"), STYLES)
    # Alfaiataria e' o corte (10/11/2026): a calca de alfaiataria de viscose
    # saia "casual de viscose", e o motor nao sabia que era de trabalho. O
    # tecido "ALFAIATARIA" (fibra nao reconhecida) tambem conta como o corte.
    # Decide pelos sinais: um forte (pregas, vinco, lapela) ou dois quaisquer,
    # e nenhum sinal casual (bolso cargo, cos de elastico, jeans...).
    sinais_alfaiataria = set(data.get("tailoringSigns") or []) & set(TAILORING_SIGNS)
    sinais_casuais = set(data.get("casualSigns") or []) & set(CASUAL_SIGNS)
    if sinais_casuais and material == "ALFAIATARIA":
        # Tecido de alfaiataria numa calca cargo ou jogger nao faz sentido: a
        # fibra fica desconhecida.
        material = None
    tailored = (
        category in CATEGORIES_WITH_TAILORING
        and not sinais_casuais
        and (
            bool(sinais_alfaiataria & TAILORING_STRONG)
            or len(sinais_alfaiataria) >= 2
            or data.get("tailored") is True
            or material == "ALFAIATARIA"
        )
    )
    # Colarinho: a polo saia como camiseta basica e entrava no look de ficar
    # em casa. A camisa sempre tem colarinho.
    collar = category == "CAMISA" or (
        category in CATEGORIES_WITH_COLLAR and data.get("collar") is True
    )

    # Roupa de treino (10/11/2026): so' para atividade fisica. O modelo
    # marcava toda peca esportiva tambem como dia a dia, e a camiseta dry-fit
    # saia no look de shopping.
    if style == "ESPORTIVO" and data.get("pajama") is not True:
        normalized_occasions = [o for o in normalized_occasions if o not in ("DIA_A_DIA", "CASA")]
        if "ACADEMIA" not in normalized_occasions:
            normalized_occasions.insert(0, "ACADEMIA")

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
        "revealing": revealing,
        "mini": mini,
        "heel": heel,
        "heavyCoat": heavy_coat,
        "bootShaft": boot_shaft,
        "tailored": tailored,
        "collar": collar,
        "style": style,
        "pattern": normalize_value(data.get("pattern"), PATTERNS),
        "warmth": normalize_value(data.get("warmth"), WARMTH),
        "material": material,
        "occasions": normalized_occasions,
        # {colorName, colorAddSymbol, hex}, com o hex de referencia do simbolo.
        "primaryColor": primary_color,
        "secondaryColor": secondary_color,
    }
