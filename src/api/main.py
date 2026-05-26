from fastapi import FastAPI, File, HTTPException, UploadFile

from src.color_detection.detect_color import detect_dominant_color

app = FastAPI(title="ZYRA Vision API")


@app.get("/")
def health_check():
    return {
        "message": "ZYRA Vision API funcionando"
    }


@app.post("/detect-color")
async def detect_color(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        result = detect_dominant_color(image_bytes)

        return result
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))