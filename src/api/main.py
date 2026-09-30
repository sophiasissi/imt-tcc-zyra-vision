import logging

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.clothing_analysis.analyze_clothing import analyze_clothing
from src.clothing_analysis.validate_clothing import validate_clothing
from src.color_detection.detect_color import detect_dominant_color

logger = logging.getLogger(__name__)

app = FastAPI(title="ZYRA Vision API")

# NOTA SOBRE `def` EM VEZ DE `async def`
#
# Tudo o que estes endpoints fazem e' bloqueante: CLIP e torch, OpenCV e o
# cliente da OpenAI sao sincronos. Declarados como `async def`, eles rodariam
# dentro do laco de eventos e o prenderiam -- o servidor pararia de atender
# QUALQUER outra requisicao ate' terminar.
#
# Com a analise da peca levando de 5 a 16 segundos, o loop da camera (que le a
# cor a cada 800ms) estouraria o tempo enquanto um cadastro estivesse em curso.
#
# Declarados como `def` comum, o FastAPI executa cada um numa thread do pool e
# o laco de eventos continua livre para atender as demais chamadas.


@app.get("/")
def health_check():
    return {"message": "ZYRA Vision API funcionando"}


@app.post("/detect-color")
def detect_color(file: UploadFile = File(...)):
    try:
        image_bytes = file.file.read()

        return detect_dominant_color(image_bytes)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/validate-clothing")
def validate_clothing_endpoint(file: UploadFile = File(...)):
    try:
        image_bytes = file.file.read()

        return validate_clothing(image_bytes)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.post("/analyze-clothing")
def analyze_clothing_endpoint(file: UploadFile = File(...)):
    """
    Descreve a peca com a OpenAI usando os codigos de taxonomy.py.

    E' a unica chamada paga do servico, por isso so' e' usada quando a pessoa
    toca em "Cadastrar nova peca" -- nunca ao tirar a foto. A foto ja' passou
    pelo /validate-clothing antes de chegar aqui.
    """
    image_bytes = file.file.read()

    try:
        return analyze_clothing(image_bytes)
    except ValueError as error:
        # Imagem ilegivel ou resposta da IA fora do formato.
        raise HTTPException(status_code=400, detail=str(error))
    except Exception as error:
        # OpenAI fora do ar, chave ausente, limite de uso.
        logger.exception("Falha ao analisar as caracteristicas da peca: %s", error)
        raise HTTPException(
            status_code=503,
            detail="Nao foi possivel analisar a peca agora.",
        )
