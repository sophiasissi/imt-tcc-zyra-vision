# Avaliação do `/analyze-clothing`

Mede se a IA acerta categoria, estilo, estampa, aquecimento, material e ocasiões.

## Como montar o conjunto

1. Tire ~40 fotos de peças reais do jeito que o usuário tiraria no app (cabide, cama, chão, luz de casa). Varie as categorias.
2. Coloque as fotos em `tests/eval/images/`.
3. Preencha o `labels.csv`, uma linha por foto, com os códigos de `src/clothing_analysis/taxonomy.py`:

```csv
arquivo,category,style,pattern,warmth,material,occasions
camisa-azul.jpg,CAMISA,SOCIAL,LISO,MEDIO,,TRABALHO|FESTA
calca-jeans.jpg,CALCA,CASUAL,LISO,MEDIO,JEANS,DIA_A_DIA
```

Campo vazio não é avaliado. Em `occasions`, separe os valores com `|`.

O `labels.csv` também tem a cor real de cada peça, usada para avaliar a detecção de cor:

- `cor_real`: a cor como quem conhece a peça descreveria, em texto livre;
- `cor_principal` e `cor_secundaria`: a mesma cor em código ColorADD (ex.: `VERDE_CLARO`, `AZUL_ESCURO`, `PRETO`). Quando mais de uma resposta é aceitável, separe com `|` (ex.: `VERDE|AZUL`). Rosa é `VERMELHO_CLARO`; bege é `CASTANHO_CLARO`.

Edite o arquivo como CSV. Uma planilha salva como `.numbers` ou `.xlsx` não é lida pelo script.

## Como rodar

Na raiz do repo, com o `.venv` ativo e o `OPENAI_API_KEY` no `.env`:

```bash
python -m tests.eval.run_eval            # 3 rodadas por foto
python -m tests.eval.run_eval --runs 1   # mais rápido
```

O resultado mostra o acerto por campo, os erros mais comuns e quantas fotos mudaram de resposta entre as rodadas. Os detalhes de cada foto ficam em `tests/eval/results/`.

## Avaliação da cor

Sem OpenAI e sem custo. Compara a leitura da mira (loop da câmera) com a leitura da peça (cadastro) e mede a cor secundária:

```bash
python -m tests.eval.avaliar_cor
python -m tests.eval.avaliar_cor --ia   # inclui a cor secundária da análise da IA (paga, uma chamada por foto)
```

## Concordância entre rotuladores

Estilo e ocasião são subjetivos. Para saber o teto realista, cada pessoa rotula num arquivo separado e compara:

```bash
python -m tests.eval.run_eval --labels tests/eval/labels.csv --compare tests/eval/labels_sophia.csv
```
