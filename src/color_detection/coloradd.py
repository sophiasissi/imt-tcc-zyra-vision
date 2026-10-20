# Os 27 simbolos oficiais do ColorADD (manual de normas graficas, 1.3), com o
# nome mostrado ao usuario e a cor de referencia de cada um. A referencia e' a
# barra da tabela oficial (04A3 Codigo ColorADD B.png), a mesma da tela do
# ColorADD no app (ColorAddScreen.tsx).
#
# Serve para a cor que vem da analise da peca: o GPT devolve so' o codigo, e a
# cor de referencia entra como hex quando nao ha uma cor medida na foto.
SYMBOLS = {
    "AZUL": ("Azul", "#024299"),
    "VERDE": ("Verde", "#01A87C"),
    "AMARELO": ("Amarelo", "#FDDE05"),
    "LARANJA": ("Laranja", "#FF5913"),
    "VERMELHO": ("Vermelho", "#FD062F"),
    "ROXO": ("Roxo", "#9A017F"),
    "CASTANHO": ("Castanho", "#B96003"),
    "BRANCO": ("Branco", "#FFFFFF"),
    "PRETO": ("Preto", "#000000"),
    "CINZA_CLARO": ("Cinza Claro", "#B0B1B6"),
    "CINZA_ESCURO": ("Cinza Escuro", "#45454D"),
    "DOURADO": ("Dourado", "#B08842"),
    "PRATEADO": ("Prateado", "#7B7A76"),
    "AZUL_CLARO": ("Azul Claro", "#039CED"),
    "VERDE_CLARO": ("Verde Claro", "#7CC64D"),
    "AMARELO_CLARO": ("Amarelo Claro", "#FEF97A"),
    "LARANJA_CLARO": ("Laranja Claro", "#FBCA69"),
    "VERMELHO_CLARO": ("Vermelho Claro", "#FFB8BC"),
    "ROXO_CLARO": ("Roxo Claro", "#EF6EB0"),
    "CASTANHO_CLARO": ("Castanho Claro", "#FFC675"),
    "AZUL_ESCURO": ("Azul Escuro", "#0A013B"),
    "VERDE_ESCURO": ("Verde Escuro", "#005311"),
    "AMARELO_ESCURO": ("Amarelo Escuro", "#FDB800"),
    "LARANJA_ESCURO": ("Laranja Escuro", "#F36609"),
    "VERMELHO_ESCURO": ("Vermelho Escuro", "#910009"),
    "ROXO_ESCURO": ("Roxo Escuro", "#50003E"),
    "CASTANHO_ESCURO": ("Castanho Escuro", "#5E2403"),
}


def symbol_color(code):
    """
    "azul claro", "AZUL_CLARO" ou "COLORADD_AZUL_CLARO" -> a cor no formato do
    /detect-color ({colorName, colorAddSymbol, hex}). None se nao for um dos 27.
    """
    if not isinstance(code, str):
        return None

    key = code.strip().upper().replace("COLORADD_", "").replace("-", "_").replace(" ", "_")

    if key not in SYMBOLS:
        return None

    name, hex_code = SYMBOLS[key]

    return {"colorName": name, "colorAddSymbol": f"COLORADD_{key}", "hex": hex_code}
