import unicodedata

# Fonte da verdade dos valores de peca. Os enums do Prisma no back
# (Categoria, Estilo, Estampa, Ocasiao) devem ter exatamente estes valores.
# A descricao de cada um vai para o prompt do analyze_clothing.

CATEGORIES = {
    "CAMISETA": "camiseta, t-shirt, polo, regata, blusinha feminina, cropped, top",
    "CAMISA": "camisa de botao, social ou casual",
    "MOLETOM": "moletom, blusa de frio, sueter, trico, cardiga",
    "JAQUETA": "jaqueta, casaco, blusa de frio com ziper, corta-vento, jaqueta jeans ou de couro",
    "BLAZER": "blazer, paleto",
    "CALCA": "calca de qualquer tecido, legging",
    "SHORT": "short, bermuda",
    "SAIA": "saia de qualquer comprimento",
    "VESTIDO": "vestido, macacao",
    "TENIS": "tenis",
    "SAPATO": "sapato, sandalia, bota, chinelo, salto",
    "BOLSA": "bolsa, mochila",
}

STYLES = {
    "CASUAL": "uso cotidiano descontraido",
    "SOCIAL": "formal, de escritorio",
    "ESPORTIVO": "pratica esportiva",
    "STREETWEAR": "urbano, oversized, estampas graficas",
    "ELEGANTE": "sofisticado, para eventos",
    "BASICO": "peca coringa, sem elementos marcantes",
}

PATTERNS = {
    "LISO": "uma cor so, sem estampa",
    "ESTAMPADO": "estampa floral, animal, geometrica ou grafica",
    "LISTRADO": "listras",
    "XADREZ": "xadrez",
    "LOGO": "peca lisa com logo ou escrita em destaque",
}

OCCASIONS = {
    "DIA_A_DIA": "rotina, faculdade, passeio",
    "TRABALHO": "escritorio, reuniao",
    "FESTA": "festa, balada, casamento, evento",
    "ACADEMIA": "treino, corrida",
    "PRAIA": "praia, piscina, calor",
    "CASA": "ficar em casa, dormir",
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
