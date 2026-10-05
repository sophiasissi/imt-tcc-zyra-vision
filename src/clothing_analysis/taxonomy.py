import unicodedata

# Fonte da verdade dos valores de peca. Os enums do Prisma no back
# (Categoria, Estilo, Estampa, Ocasiao, Aquecimento, Material) devem ter
# exatamente estes codigos. A descricao de cada um vai para o prompt do
# analyze_clothing, entao ela tambem define a fronteira entre valores vizinhos.
#
# Base das categorias, estampas e materiais: ontologia Fashionpedia (Jia et
# al., ECCV 2020) e Google Product Taxonomy. Base de estilos e ocasioes: os
# codigos de vestimenta do Emily Post Institute (casual, business casual,
# black tie). Bolsa, mochila, bone e chapeu ficam de fora: nao sao cadastraveis.

CATEGORIES = {
    "CAMISETA": "camiseta, t-shirt, baby look, blusinha de malha com manga, cropped com manga",
    "POLO": "camisa polo: malha com gola e poucos botoes so no alto da frente",
    "REGATA": "regata, top sem manga, blusinha de alca, cropped sem manga",
    "CAMISA": "camisa com botoes na frente toda, social ou casual, e blusa de tecido plano (bata, blusa de seda)",
    "MOLETOM": "moletom com ou sem capuz, blusa de frio fechada, sueter, pulover de trico",
    "CARDIGA": "cardiga: blusa de malha ou trico aberta na frente, com botoes ou sem fecho",
    "JAQUETA": "jaqueta curta, ate o quadril: jeans, couro, bomber, corta-vento, puffer curta, blusa de frio com ziper",
    "CASACO": "casaco longo, abaixo do quadril: sobretudo, trench coat, parka, casacao",
    "BLAZER": "blazer, paleto",
    "COLETE": "colete sem manga, de alfaiataria, puffer ou de trico",
    "CALCA": "calca de qualquer tecido, legging, jogger",
    "SHORT": "short, bermuda",
    "SAIA": "saia de qualquer comprimento, short-saia",
    "VESTIDO": "vestido de qualquer comprimento",
    "MACACAO": "macacao, macaquinho, jardineira: peca unica de cima e de baixo com pernas",
    "TENIS": "tenis",
    "SAPATO": "calcado fechado que nao e tenis nem bota: sapato social, mocassim, sapatilha, scarpin",
    "BOTA": "bota e botina, de cano curto ou longo",
    "SANDALIA": "calcado aberto: sandalia, rasteira, chinelo, tamanco, sandalia de salto",
}

STYLES = {
    "CASUAL": "uso cotidiano descontraido",
    "ESPORTE_FINO": "meio-termo entre casual e social (business casual): calca de alfaiataria ou chino, camisa ou polo, blazer sem gravata",
    "SOCIAL": "formal de escritorio: terno, tailleur, camisa social com gravata",
    "ESPORTIVO": "pratica esportiva",
    "STREETWEAR": "urbano, oversized, estampas graficas",
    "ELEGANTE": "sofisticado, para eventos e noite",
    "BASICO": "peca coringa, sem elementos marcantes",
}

PATTERNS = {
    "LISO": "uma cor so, sem estampa",
    "LISTRADO": "listras",
    "XADREZ": "xadrez",
    "FLORAL": "flores ou folhagens",
    "POA": "bolinhas (poa)",
    "ANIMAL_PRINT": "pele de animal: onca, leopardo, zebra, cobra",
    "LOGO": "peca lisa com logo ou escrita em destaque",
    "ESTAMPADO": "qualquer outra estampa: geometrica, abstrata, grafica, camuflada, paisley",
}

OCCASIONS = {
    "DIA_A_DIA": "rotina, faculdade, passeio",
    "TRABALHO": "escritorio, reuniao",
    "FESTA": "aniversario, balada, show, confraternizacao",
    "EVENTO_FORMAL": "casamento, formatura, jantar formal, evento de gala, teatro",
    "ACADEMIA": "treino, corrida",
    "PRAIA": "praia, piscina, calor",
    "CASA": "ficar em casa, dormir",
}

WARMTH = {
    "LEVE": "fresca, para calor (regata, linho, short, vestido leve, sandalia)",
    "MEDIO": "meia-estacao (camiseta, camisa, calca jeans, tenis)",
    "QUENTE": "para frio (moletom, trico, casaco, bota)",
}

# So materiais que da para reconhecer pela foto e que o usuario usa para se
# referir a peca ("minha calca jeans", "bota de camurca"). Algodao, poliester,
# linho etc. so se confirmam pela etiqueta e ficam null.
MATERIALS = {
    "JEANS": "jeans, denim",
    "COURO": "couro ou couro sintetico, liso ou texturizado",
    "VERNIZ": "couro envernizado, com brilho espelhado",
    "CAMURCA": "camurca, suede, nobuck",
    "TRICO": "trico ou croche com o ponto visivel",
    "PELO": "pelo sintetico, pelucia, teddy, shearling",
    "PAETE": "paete ou lantejoula cobrindo a peca",
}


def normalize_value(value, allowed: dict):
    """
    Converte a resposta da IA para um valor do enum ("tênis" -> "TENIS",
    "dia-a-dia" -> "DIA_A_DIA"). Devolve None se nao estiver na lista, para
    nunca gravar um valor que o back nao conhece.
    """
    if not isinstance(value, str):
        return None

    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    key = ascii_value.strip().upper().replace("-", "_").replace(" ", "_")

    return key if key in allowed else None


def describe(allowed: dict) -> str:
    return "\n".join(f"  - {key}: {hint}" for key, hint in allowed.items())
