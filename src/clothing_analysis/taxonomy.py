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
    # Corset separado (28/10/2026): com a amarracao na frente, saia como
    # colete, e o motor o punha por cima de outra blusa.
    "CORSET": (
        "corset, corpete ou bustie: peca de cima estruturada com pelo menos um sinal forte: amarracao "
        "com ilhoses ou passantes, fileira de colchetes, barbatanas ou barra em V (bico na frente)"
    ),
    "MOLETOM": (
        "blusa de moletom fechada na frente: malha grossa e felpuda por dentro (blusao, canguru, com "
        "capuz). Blusa fina de manga longa NAO e' moletom; malha de trico ou la e' SUETER"
    ),
    # Sueter separado do moletom (10/11/2026, pedido da Sophia): o sueter
    # listrado de trico dela estava salvo como "moletom preto".
    "SUETER": (
        "sueter, pulover ou blusa de frio de trico, croche ou la, fechada na frente (sem ziper nem "
        "botoes), de gola redonda, V ou alta. Aberto na frente com botoes e' JAQUETA (cardiga)"
    ),
    "JAQUETA": "jaqueta, casaco, cardiga, blusa de frio aberta na frente (ziper ou botoes), com manga, inclusive moletom com ziper, corta-vento",
    "BLAZER": "blazer, paleto",
    # Colete separado (23/10/2026): salvo como blusa ou jaqueta, entrava duas
    # vezes no mesmo look, um como peca de cima e outro como camada.
    "COLETE": "colete: peca SEM MANGA com abotoamento ou abertura na frente, de alfaiataria, trico, jeans, couro ou puffer, inclusive o colete social usado como blusa. Com amarracao de cordao na frente e' CORSET",
    "CALCA": "calca de qualquer tecido, legging, calca de pijama",
    "SHORT": "short, bermuda",
    "SAIA": "saia de qualquer comprimento",
    "VESTIDO": "vestido, macacao (vestido tem saia; o body e' fechado entre as pernas)",
    "TENIS": "tenis",
    # Calcados abertos separados do sapato (20/10/2026): chinelo saia como
    # sapato e entrava em look de festa e de trabalho.
    "SAPATO": "calcado fechado que termina abaixo do tornozelo: sapato social, sapatilha, mocassim, scarpin, oxford, salto fechado",
    # Bota separada do sapato (05/11/2026): a bota castanha de couro da Sophia
    # saia como sapato. O cano fica no campo BOOT_SHAFTS.
    "BOTA": "bota de qualquer cano: chelsea, coturno, bota western ou texana, bota de montaria, galocha, bota over the knee. Tenis de cano alto continua TENIS",
    "SANDALIA": "sandalia aberta com tiras: rasteira, sandalia de salto, papete, anabela aberta",
    "CHINELO": "chinelo de dedo, slide, chinelo de quarto, pantufa, babuche",
}

STYLES = {
    "CASUAL": "uso cotidiano descontraido",
    "SOCIAL": "formal, de escritorio",
    # Esportivo e' so' a roupa feita para treinar (10/11/2026): a camiseta
    # dry-fit da Nike da Sophia saia num look de shopping.
    "ESPORTIVO": (
        "roupa feita para treinar e suar: dry-fit, tecido tecnologico, legging e top de academia, "
        "short de corrida, tenis de corrida ou de treino. Tenis de passeio (couro, lona, retro) e "
        "moletom de marca para sair NAO sao esportivos"
    ),
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
    "ACADEMIA": "atividade fisica em que se sua: treino, corrida, caminhada, trilha, bike",
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
    # Alfaiataria e' o corte, nao a fibra (10/11/2026): o corte vai no campo
    # tailored. Aqui fica so' o tecido plano encorpado de alfaiataria cuja
    # fibra nao da para reconhecer pela foto.
    "ALFAIATARIA": "tecido plano encorpado de alfaiataria (crepe, gabardine, la fria, sarja social) quando a fibra nao e' reconhecivel",
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

# Altura do cano da bota (lista da Sophia, 05/11/2026). Nulo nas outras pecas.
BOOT_SHAFTS = {
    "CURTO": "ate' o tornozelo ou logo acima: chelsea, coturno baixo, bota de salto curta",
    "MEDIO": "no meio da canela, entre o tornozelo e o joelho: western, texana, coturno de cano medio",
    "LONGO": "logo abaixo do joelho, cobrindo a panturrilha: bota de montaria, bota social de cano alto",
    "ACIMA_DO_JOELHO": "over the knee: o cano passa do joelho e cobre parte da coxa",
}

# Pecas que podem ter corte de alfaiataria (vinco, cos estruturado, bolso faca).
CATEGORIES_WITH_TAILORING = {"CALCA", "SHORT", "SAIA", "VESTIDO", "BLAZER", "COLETE", "JAQUETA"}
# Pecas de cima que podem ter gola de camisa (colarinho): camisa, polo, chemise.
CATEGORIES_WITH_COLLAR = {"CAMISETA", "CAMISA", "BLUSA", "BODY", "CROPPED", "VESTIDO"}

CATEGORIES_WITHOUT_SLEEVE = {"CALCA", "SHORT", "SAIA", "TENIS", "SAPATO", "BOTA", "SANDALIA", "CHINELO"}


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
