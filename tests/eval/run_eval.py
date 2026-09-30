"""
Avalia o /analyze-clothing contra fotos rotuladas a mao.

Uso (na raiz do repo):
    python -m tests.eval.run_eval
    python -m tests.eval.run_eval --runs 3 --images tests/eval/images
    python -m tests.eval.run_eval --compare tests/eval/labels_sophia.csv

O labels.csv tem uma linha por foto. Campo vazio = nao avaliado. Em
"occasions", separe os valores com "|" (ex.: DIA_A_DIA|TRABALHO).
"""

import argparse
import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from src.clothing_analysis.taxonomy import (
    CATEGORIES,
    MATERIALS,
    OCCASIONS,
    PATTERNS,
    STYLES,
    WARMTH,
)

EVAL_DIR = Path(__file__).parent

SINGLE_FIELDS = {
    "category": CATEGORIES,
    "style": STYLES,
    "pattern": PATTERNS,
    "warmth": WARMTH,
    "material": MATERIALS,
}


def parse_occasions(value: str):
    return {item.strip() for item in value.split("|") if item.strip()}


def load_labels(path: Path):
    """Le o CSV e para com erro se algum valor nao existir no enum (typo)."""
    rows = []
    errors = []

    with open(path, newline="", encoding="utf-8") as file:
        for line, row in enumerate(csv.DictReader(file), start=2):
            if not (row.get("arquivo") or "").strip():
                continue

            label = {"arquivo": row["arquivo"].strip()}

            for field, allowed in SINGLE_FIELDS.items():
                value = (row.get(field) or "").strip().upper()
                if value and value not in allowed:
                    errors.append(f"linha {line}: {field}={value} nao existe")
                label[field] = value or None

            occasions = parse_occasions((row.get("occasions") or "").upper())
            for value in occasions - OCCASIONS.keys():
                errors.append(f"linha {line}: occasions={value} nao existe")
            label["occasions"] = occasions or None

            rows.append(label)

    if errors:
        sys.exit("Rotulos invalidos em " + str(path) + ":\n  " + "\n  ".join(errors))

    return rows


def jaccard(a: set, b: set):
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def majority(values):
    return Counter(values).most_common(1)[0][0]


def print_report(title: str, labels, predictions):
    """
    labels e predictions sao listas alinhadas de dicts com os mesmos campos.
    Imprime acerto por campo e as confusoes mais comuns.
    """
    print(f"\n{title}")
    print("-" * len(title))

    for field in SINGLE_FIELDS:
        pairs = [
            (label[field], pred.get(field))
            for label, pred in zip(labels, predictions)
            if label[field]
        ]
        if not pairs:
            print(f"{field:<10} sem rotulos")
            continue

        hits = sum(expected == got for expected, got in pairs)
        confusions = Counter(
            f"{expected}->{got}" for expected, got in pairs if expected != got
        ).most_common(3)

        line = f"{field:<10} {hits}/{len(pairs)} ({hits / len(pairs):.0%})"
        if confusions:
            line += "  erros: " + ", ".join(f"{c} x{n}" for c, n in confusions)
        print(line)

    occasion_pairs = [
        (label["occasions"], pred.get("occasions") or set())
        for label, pred in zip(labels, predictions)
        if label["occasions"]
    ]
    if occasion_pairs:
        scores = [jaccard(expected, got) for expected, got in occasion_pairs]
        exact = sum(expected == got for expected, got in occasion_pairs)
        print(
            f"{'occasions':<10} sobreposicao media {sum(scores) / len(scores):.0%}, "
            f"conjunto identico {exact}/{len(occasion_pairs)}"
        )


def compare_labelers(labels_a, labels_b):
    """Concordancia entre duas pessoas: o teto realista para a IA."""
    by_file = {row["arquivo"]: row for row in labels_b}
    common = [row for row in labels_a if row["arquivo"] in by_file]

    if not common:
        sys.exit("Os dois arquivos nao tem fotos em comum.")

    print_report(
        f"Concordancia entre rotuladores ({len(common)} fotos)",
        common,
        [by_file[row["arquivo"]] for row in common],
    )


def run(labels, images_dir: Path, runs: int):
    from src.clothing_analysis.analyze_clothing import analyze_clothing

    evaluated_labels = []
    predictions = []
    unstable = Counter()
    output_rows = []

    for label in labels:
        image_path = images_dir / label["arquivo"]
        if not image_path.exists():
            print(f"[pulando] {label['arquivo']} nao encontrado em {images_dir}")
            continue

        image_bytes = image_path.read_bytes()
        attempts = []

        for attempt in range(runs):
            try:
                attempts.append(analyze_clothing(image_bytes))
            except Exception as error:
                print(f"[erro] {label['arquivo']} (rodada {attempt + 1}): {error}")

        if not attempts:
            continue

        # Voto da maioria entre as rodadas; divergencia conta como instabilidade.
        prediction = {}
        for field in SINGLE_FIELDS:
            values = [result[field] for result in attempts]
            prediction[field] = majority(values)
            if len(set(values)) > 1:
                unstable[field] += 1

        occasion_sets = [frozenset(result["occasions"]) for result in attempts]
        prediction["occasions"] = set(majority(occasion_sets))
        if len(set(occasion_sets)) > 1:
            unstable["occasions"] += 1

        evaluated_labels.append(label)
        predictions.append(prediction)

        for index, result in enumerate(attempts, start=1):
            output_rows.append({
                "arquivo": label["arquivo"],
                "rodada": index,
                **{f"esperado_{f}": label[f] or "" for f in SINGLE_FIELDS},
                **{f"previsto_{f}": result[f] or "" for f in SINGLE_FIELDS},
                "esperado_occasions": "|".join(sorted(label["occasions"] or [])),
                "previsto_occasions": "|".join(sorted(result["occasions"])),
            })

        print(f"[ok] {label['arquivo']}")

    if not predictions:
        sys.exit("Nenhuma foto avaliada.")

    print_report(
        f"IA x rotulo ({len(predictions)} fotos, {runs} rodada(s) cada)",
        evaluated_labels,
        predictions,
    )

    if runs > 1:
        print("\nInstabilidade (fotos com resposta diferente entre rodadas):")
        for field in [*SINGLE_FIELDS, "occasions"]:
            print(f"{field:<10} {unstable[field]}/{len(predictions)}")

    results_dir = EVAL_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    output_path = results_dir / f"eval_{datetime.now():%Y%m%d_%H%M}.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\nDetalhes por foto: {output_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--labels", type=Path, default=EVAL_DIR / "labels.csv")
    parser.add_argument("--images", type=Path, default=EVAL_DIR / "images")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument(
        "--compare",
        type=Path,
        help="outro labels.csv, para medir a concordancia entre rotuladores",
    )
    args = parser.parse_args()

    labels = load_labels(args.labels)

    if args.compare:
        compare_labelers(labels, load_labels(args.compare))
    else:
        run(labels, args.images, args.runs)


if __name__ == "__main__":
    main()
