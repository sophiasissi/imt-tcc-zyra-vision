# w2c_nomes.npy

Tabela usada por `color_mapper.match_family` para dar o nome básico da cor.

## Origem

Modelo de nomes de cor de:

> J. van de Weijer, C. Schmid, J. Verbeek e D. Larlus. **Learning Color Names for Real-World Applications.** *IEEE Transactions on Image Processing*, 18(7), 2009.

O modelo foi aprendido a partir de imagens reais da web. Para cada cor do sRGB, numa grade 32×32×32, ele dá a probabilidade de cada um dos 11 nomes básicos: preto, azul, marrom, cinza, verde, laranja, rosa, roxo, vermelho, branco e amarelo.

O arquivo original dos autores é o `w2c.mat` (matriz 32768×11, de 2009). Usamos a cópia publicada em <https://github.com/hailsham/Animal-Recongniton/blob/master/w2c.mat> (SHA-256 começando por `97b1f0ecd0fbecd1`).

## O que este arquivo guarda

Só o índice do nome mais provável de cada cor (`uint8`, 32768 posições, 32 KB), na ordem acima. A posição de uma cor RGB é:

```
(R // 8) + 32 * (G // 8) + 1024 * (B // 8)
```

## Como gerar de novo

```python
import numpy as np, scipy.io

w2c = scipy.io.loadmat("w2c.mat")["w2c"]
np.save("w2c_nomes.npy", w2c.argmax(axis=1).astype(np.uint8))
```

O `scipy` só é necessário para essa conversão. O serviço em si usa apenas o `numpy`.

## Por que trocamos os limiares por esta tabela

Avaliação de 04/10/2026 com 39 fotos de peças reais (`tests/eval/labels.csv`), simulando a mira da câmera:

| Método | Família certa | Cor exata (com tom) |
|---|---|---|
| Limiares anteriores (croma < 12 = neutro, matiz mais próximo) | 21/39 (54%) | 17/39 (44%) |
| Tabela de van de Weijer + regras de tom atuais | 25/39 (64%) | 19/39 (49%) |

Também testamos treinar um classificador nosso na Fashion Product Images (29 mil peças). No melhor caso, ele acertou 21/39 (54%), então não superou a tabela.
