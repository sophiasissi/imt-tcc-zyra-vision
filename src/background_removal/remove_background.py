"""
Remove o fundo da foto da peca, para o armario ficar mais bonito.

Modelo: U2-Net (rembg, `u2net`), rodando localmente com onnxruntime. Em 20/10/2026,
comparado nas fotos de tests/eval/images:
  - u2netp (5 MB): 0,22 s por foto, mas deixou parte do lencol na blusa tie-dye;
  - u2net (168 MB): 0,53 s por foto, recorte limpo em todas;
  - isnet-general-use: apagou a camiseta roxa e deixou o xadrez transparente;
  - birefnet-general-lite: pesado demais para rodar sem placa de video.

Por que nao a OpenAI: a edicao de imagem dela redesenha a foto e pode mudar a cor
da roupa, o pior erro possivel num app para daltonicos. O U2-Net so' decide o que
e' fundo; os pixels da peca saem identicos aos da foto.
"""

import io
import threading

import numpy as np
from PIL import Image

from src.image_io import open_srgb

MODELO = "u2net"

# No Mac, o onnxruntime tenta o CoreML primeiro, e abrir o modelo nele travou
# (0% de CPU por minutos). O servidor tambem nao tem acelerador: so' CPU.
_PROVEDORES = ["CPUExecutionProvider"]

# Lado maior da imagem recortada: suficiente para a peca ampliada no app, e a
# imagem sai com ~100 a 300 KB em WebP.
LADO_MAXIMO = 1600

# Pixel com opacidade abaixo disso conta como fundo ao medir a peca.
_OPACIDADE_MINIMA = 128

# Se a peca ocupar menos que isso da foto, o modelo nao achou nada.
FRACAO_MINIMA_DA_PECA = 0.03

# Folga ao redor da peca no recorte final, em fracao do lado maior.
_MARGEM = 0.04

_sessao = None
_trava = threading.Lock()


def _sessao_rembg():
    """Carrega o modelo uma vez so', na primeira foto (~0,3 s)."""
    global _sessao
    with _trava:
        if _sessao is None:
            from rembg import new_session

            _sessao = new_session(MODELO, providers=_PROVEDORES)
        return _sessao


def _reduzir(imagem: Image.Image) -> Image.Image:
    if max(imagem.size) <= LADO_MAXIMO:
        return imagem
    imagem = imagem.copy()
    imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
    return imagem


def _recortar_na_peca(recorte: Image.Image, alfa: np.ndarray) -> Image.Image:
    """Corta as bordas vazias, para a peca preencher o card do armario."""
    linhas = np.where(alfa.max(axis=1) >= _OPACIDADE_MINIMA)[0]
    colunas = np.where(alfa.max(axis=0) >= _OPACIDADE_MINIMA)[0]
    margem = int(max(recorte.size) * _MARGEM)
    largura, altura = recorte.size

    return recorte.crop(
        (
            max(0, colunas[0] - margem),
            max(0, linhas[0] - margem),
            min(largura, colunas[-1] + 1 + margem),
            min(altura, linhas[-1] + 1 + margem),
        )
    )


def remove_background(image_bytes: bytes) -> bytes:
    """
    Devolve a peca sem fundo, em WebP com transparencia.

    Levanta ValueError("Imagem inválida") se os bytes nao forem uma imagem, e
    ValueError("Não encontrei a peça na foto") se o recorte vier vazio (quem
    chama guarda a foto original).
    """
    from rembg import remove

    imagem = _reduzir(open_srgb(image_bytes))
    recorte = remove(imagem, session=_sessao_rembg(), post_process_mask=True)

    alfa = np.asarray(recorte.getchannel("A"))
    if (alfa >= _OPACIDADE_MINIMA).mean() < FRACAO_MINIMA_DA_PECA:
        raise ValueError("Não encontrei a peça na foto")

    saida = io.BytesIO()
    _recortar_na_peca(recorte, alfa).save(saida, format="WEBP", quality=90, method=4)
    return saida.getvalue()
