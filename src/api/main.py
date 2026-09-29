from fastapi import FastAPI, File, HTTPException, UploadFile
from src.clothing_analysis.analyze_clothing import analyze_clothing
from src.clothing_analysis.validate_clothing import validate_clothing
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
    
@app.post("/validate-clothing")
async def validate_clothing_endpoint(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        result = validate_clothing(image_bytes)

        return result
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))

@app.post("/analyze-clothing")
async def analyze_clothing_endpoint(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        result = analyze_clothing(image_bytes)

        return result
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))