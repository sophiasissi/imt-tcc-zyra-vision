"""
Avalia a deteccao de cor com as fotos e o gabarito de tests/eval.

Roda local, sem OpenAI. Compara as duas leituras do /detect-color:

- mira: so o ponto central, como no loop da camera;
- peca: a cor que mais ocupa a peca e a segunda cor (a leitura do cadastro).

Para a cor principal, conta acerto exato (familia e tom) e de familia. Para a
secundaria, so nas fotos com gabarito de secundaria conta acerto; nas fotos sem
segunda cor no gabarito, conta falso positivo quando a leitura inventa uma.

    python -m tests.eval.avaliar_cor        # so a leitura de pixels, sem custo
    python -m tests.eval.avaliar_cor --ia   # tambem a analise da IA (paga)

Com --ia, mede a cor secundaria que a analise da peca devolve (a que o
cadastro usa) e, de brinde, o acerto de categoria: uma chamada por foto.
"""

import csv
import sys
from pathlib import Path

from src.color_detection.detect_color import (
    COLOR_SYMBOLS,
    color_family,
    detect_dominant_color,
    map_rgb_to_color,
    reference_rgb,
)

EVAL_DIR = Path(__file__).parent


def aceitos(valor: str) -> set[str]:
    """'VERDE|AZUL' -> {'COLORADD_VERDE', 'COLORADD_AZUL'}; vazio -> set()."""
    return {f"COLORADD_{v.strip()}" for v in valor.split("|") if v.strip()}


def main():
    # A cor de referencia de cada simbolo precisa ser lida como ele mesmo; senao
    # uma cor secundaria sem pixels na foto ganharia um hex de outra cor.
    erradas = [
        s for s in COLOR_SYMBOLS
        if map_rgb_to_color(reference_rgb(s))["colorAddSymbol"] != f"COLORADD_{s}"
    ]
    print(f"Cores de referencia lidas como outro simbolo: {erradas or 'nenhuma'}\n")

    with open(EVAL_DIR / "labels.csv", encoding="utf-8") as arquivo:
        linhas = [l for l in csv.DictReader(arquivo) if l["cor_principal"].strip()]

    total = len(linhas)
    exato = {"mira": 0, "peca": 0}
    familia = {"mira": 0, "peca": 0}
    sec_esperadas = sec_acertos = sec_sem_gabarito = sec_falsas = 0
    erros = []

    for linha in linhas:
        imagem = (EVAL_DIR / "images" / linha["arquivo"]).read_bytes()
        principal = aceitos(linha["cor_principal"])
        secundaria = aceitos(linha["cor_secundaria"])
        familias = {color_family(c) for c in principal}

        leituras = {area: detect_dominant_color(imagem, area) for area in ("mira", "peca")}

        for area, lida in leituras.items():
            exato[area] += lida["colorAddSymbol"] in principal
            familia[area] += color_family(lida["colorAddSymbol"]) in familias

        lida = leituras["peca"]
        sec = lida["secondary"]["colorAddSymbol"] if lida["secondary"] else None

        if secundaria:
            sec_esperadas += 1
            sec_acertos += sec in secundaria
        else:
            sec_sem_gabarito += 1
            sec_falsas += sec is not None

        if lida["colorAddSymbol"] not in principal or (sec not in secundaria if sec or secundaria else False):
            erros.append(
                f"  {linha['arquivo']:42} esperado {linha['cor_principal']}"
                f" + {linha['cor_secundaria'] or '-'} | leu {lida['colorAddSymbol'].removeprefix('COLORADD_')}"
                f" + {sec.removeprefix('COLORADD_') if sec else '-'}"
            )

    def pct(n, d):
        return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "-"

    print(f"Cor principal ({total} fotos)")
    for area in ("mira", "peca"):
        print(f"  {area}: exata {pct(exato[area], total)}, familia {pct(familia[area], total)}")

    print("\nCor secundaria (leitura da peca)")
    print(f"  acertou a segunda cor: {pct(sec_acertos, sec_esperadas)}")
    print(f"  inventou segunda cor em peca de uma cor so: {pct(sec_falsas, sec_sem_gabarito)}")

    if erros:
        print("\nDivergencias na leitura da peca:")
        print("\n".join(erros))

    if "--ia" in sys.argv:
        avaliar_ia(linhas)


def avaliar_ia(linhas):
    # Importado aqui: so carrega o cliente da OpenAI quando a avaliacao paga
    # foi pedida.
    from src.clothing_analysis.analyze_clothing import analyze_clothing

    esperadas = acertos = acertos_familia = sem_gabarito = falsas = 0
    cat_total = cat_acertos = 0
    relatorio = []

    for linha in linhas:
        resultado = analyze_clothing((EVAL_DIR / "images" / linha["arquivo"]).read_bytes())
        cor = resultado["secondaryColor"]
        sec = cor["colorAddSymbol"] if cor else None
        secundaria = aceitos(linha["cor_secundaria"])

        if secundaria:
            esperadas += 1
            acertos += sec in secundaria
            familias = {color_family(c) for c in secundaria}
            acertos_familia += bool(sec) and color_family(sec) in familias
        else:
            sem_gabarito += 1
            falsas += sec is not None

        if linha["category"]:
            cat_total += 1
            cat_acertos += resultado["category"] == linha["category"]

        relatorio.append(
            f"  {linha['arquivo']:42} gabarito {linha['category'] or '-'}"
            f" + {linha['cor_secundaria'] or '-'} | IA {resultado['category']}"
            f" {resultado['pattern']} + {sec.removeprefix('COLORADD_') if sec else '-'}"
        )

    print("\nCor secundaria (analise da IA)")
    print(
        f"  acertou a segunda cor: {pct(acertos, esperadas)}"
        f" (familia: {pct(acertos_familia, esperadas)})"
    )
    print(f"  inventou segunda cor em peca de uma cor so: {pct(falsas, sem_gabarito)}")
    print(f"\nCategoria (analise da IA): {pct(cat_acertos, cat_total)}")
    print("\n".join(relatorio))


def pct(n, d):
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "-"


if __name__ == "__main__":
    main()
