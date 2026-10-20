import unicodedata

# Fonte da verdade dos valores de peca. Os enums do Prisma no back
# (Categoria, Estilo, Estampa, Ocasiao, Aquecimento, Material, Manga) devem ter
# exatamente estes valores. A descricao de cada um vai para o prompt do
# analyze_clothing.

# As pecas de cima seguem as definicoes da Sophia (19/10/2026): camiseta e' a
# malha em T sem botao; camisa tem colarinho e botoes; blusa e' o termo amplo
# para o resto; cropped termina acima do umbigo e o top logo abaixo do busto.
# Uma blusa fina de manga longa NAO e' moletom: moletom e' a peca grossa e
# felpuda por dentro.
CATEGORIES = {
    "CAMISETA": "camiseta em T de malha, sem botoes, gola redonda ou V, de qualquer manga; polo; regata (inclusive de alcinha e de pijama)",
    "CAMISA": "camisa com colarinho, punhos e botoes de cima a baixo, social ou casual",
    "BLUSA": (
        "blusa que nao e' camiseta basica: decote trabalhado (V profundo, quadrado, ombro a ombro), "
        "recorte, amarracao, babado, manga bufante, tecido fluido ou acetinado, blusa fina e justa de "
        "manga longa (segunda pele)"
    ),
    "CROPPED": "peca de cima curta que termina acima do umbigo (mais comprida que um top), de qualquer manga, inclusive tomara que caia",
    "TOP": "top justo que so cobre o busto e termina logo abaixo dele: top de academia, top de bojo, faixa estreita",
    "BODY": "body: peca de cima inteirica, fechada entre as pernas, como um maio com ou sem manga",
    "MOLETOM": (
        "blusa de frio grossa e fechada na frente: moletom felpudo por dentro (blusao, canguru, com "
        "capuz), sueter, trico. Blusa fina de manga longa NAO e' moletom"
    ),
    "JAQUETA": "jaqueta, casaco, cardiga, blusa de frio aberta na frente (ziper ou botoes), inclusive moletom com ziper, corta-vento",
    "BLAZER": "blazer, paleto",
    "CALCA": "calca de qualquer tecido, legging, calca de pijama",
    "SHORT": "short, bermuda",
    "SAIA": "saia de qualquer comprimento",
    "VESTIDO": "vestido, macacao (vestido tem saia; o body e' fechado entre as pernas)",
    "TENIS": "tenis",
    "SAPATO": "sapato, sandalia, bota, chinelo, salto",
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
    "CASA": "ficar em casa, dormir; pijama",
}

WARMTH = {
    "LEVE": "fresca, para calor (regata, linho, short, vestido leve, sandalia)",
    "MEDIO": "meia-estacao (camiseta, camisa, calca jeans, tenis)",
    "QUENTE": "para frio (moletom, trico, casaco, bota)",
}

# Tecido da peca, pelo nome que as pessoas usam ("calca de moletom", "pijama de
# soft"). A foto nao mostra a etiqueta: a IA escolhe pela aparencia. Quando a
# etiqueta mistura fibras (ex.: 89% poliamida e 11% elastano), vale a de maior
# proporcao, que e' a ordem em que a etiqueta lista as fibras.
MATERIALS = {
    "JEANS": "jeans, denim",
    "COURO": "couro ou couro sintetico",
    "MOLETOM": "moletom: malha grossa e felpuda por dentro (blusao, calca de moletom)",
    "MALHA": "malha de algodao comum, de camiseta (malha penteada, ribana, canelado)",
    "POLIAMIDA": (
        "malha lisa, fina e justa com elastano, de toque gelado: \"geladinho\", suplex, segunda pele, "
        "roupa de academia, body"
    ),
    "TRICO": "trico, croche, la, fio grosso",
    "SOFT": "soft, fleece, plush ou pelucia: tecido de pelinho macio (pijama, manta)",
    "LINHO": "linho",
    "ALFAIATARIA": "tecido de alfaiataria: calca social, blazer, terno, sarja e gabardine",
    "CETIM": "cetim, seda, tecido acetinado e brilhante",
    "VISCOSE": "viscose ou tecido leve, fluido e fosco que cai solto",
    "VELUDO": "veludo, veludo cotele, plush liso e brilhante",
}

# Manga das pecas de cima, do body e do vestido. Calca, short, saia e
# calcados ficam sem manga (null).
SLEEVES = {
    "SEM_MANGA": "regata, alcinha, tomara que caia",
    "CURTA": "manga curta ou ate' o cotovelo",
    "LONGA": "manga ate' o punho ou 3/4",
}

CATEGORIES_WITHOUT_SLEEVE = {"CALCA", "SHORT", "SAIA", "TENIS", "SAPATO"}


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
