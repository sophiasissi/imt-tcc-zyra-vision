# Avaliação do `/analyze-clothing`

Mede se a IA acerta categoria, estilo, estampa, aquecimento e ocasiões.

## Como montar o conjunto

1. Tire ~40 fotos de peças reais do jeito que o usuário tiraria no app (cabide, cama, chão, luz de casa). Varie as categorias.
2. Coloque as fotos em `tests/eval/images/`.
3. Preencha o `labels.csv`, uma linha por foto, com os códigos de `src/clothing_analysis/taxonomy.py`:

```csv
arquivo,category,style,pattern,warmth,occasions
camisa-azul.jpg,CAMISA,SOCIAL,LISO,MEDIO,TRABALHO|FESTA
```

Campo vazio não é avaliado. Em `occasions`, separe os valores com `|`.

## Como rodar

Na raiz do repo, com o `.venv` ativo e o `OPENAI_API_KEY` no `.env`:

```bash
python -m tests.eval.run_eval            # 3 rodadas por foto
python -m tests.eval.run_eval --runs 1   # mais rápido
```

O resultado mostra o acerto por campo, os erros mais comuns e quantas fotos mudaram de resposta entre as rodadas. Os detalhes de cada foto ficam em `tests/eval/results/`.

## Concordância entre rotuladores

Estilo e ocasião são subjetivos. Para saber o teto realista, cada pessoa rotula num arquivo separado e compara:

```bash
python -m tests.eval.run_eval --labels tests/eval/labels.csv --compare tests/eval/labels_sophia.csv
```
