# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ZYRA Vision is the computer-vision API for a TCC (undergraduate thesis) project focused on accessible fashion. It exposes a FastAPI service that inspects a photo of a clothing item and returns its dominant color (mapped to the ColorADD system, designed for colorblind users) and whether the image actually depicts clothing.

## Setup & commands

Python 3.9, dependencies pinned in `requirements.txt`. A `.venv` already exists in the repo root.

```bash
# activate the existing venv
source .venv/bin/activate

# install/update dependencies
pip install -r requirements.txt

# run the API with hot reload
uvicorn src.api.main:app --reload
```

There is no test suite, linter, or formatter configured in this repo yet.

`analyze_clothing.py` reads `OPENAI_API_KEY` via `python-dotenv` from a `.env` file (both `.env` and `.env.example` are currently empty placeholders — populate `.env` locally with a real key before exercising that module).

## Architecture

FastAPI app in `src/api/main.py` is a thin HTTP layer with two routes, each delegating straight to a module-level function and translating exceptions to `HTTPException(400)`:

- `POST /detect-color` → `src.color_detection.detect_color.detect_dominant_color`
- `POST /validate-clothing` → `src.clothing_analysis.validate_clothing.validate_clothing`

Both endpoints take a multipart `UploadFile`, read it into raw bytes, and pass the bytes straight through — no image is ever persisted to disk.

### Color detection (`src/color_detection/`)

Pure OpenCV/numpy pipeline, no ML model:

1. `detect_color.py` decodes the uploaded bytes with OpenCV, crops a small region around the image center (`crop_center`, default 20% of the shorter dimension) on the assumption that the garment fills the frame, and averages the RGB pixels in that crop.
2. `color_mapper.py` (`map_rgb_to_color`) turns that average RGB into a result:
   - Checks for near-neutral colors first (`detect_neutral_color`: low saturation → Preto/Cinza/Branco by brightness).
   - Checks a hand-tuned "beige/light brown" special case (`detect_special_cases`) that plain nearest-color matching handles poorly.
   - Otherwise finds the nearest reference color in `COLOR_REFERENCES` by CIE Lab distance (`rgb_to_lab` + `calculate_lab_distance` — Lab is used instead of raw RGB distance because it's closer to human perceptual difference), then applies a light/dark tone suffix (`apply_tone`) based on brightness.
   - Also computes a `warningCode` (`LOW_LIGHT`/`HIGH_LIGHT`/`None`) from brightness/saturation so the API can flag when the source photo's lighting likely makes the color reading unreliable.
   - Every result carries a `colorAddSymbol`, the tag used by the ColorADD system so colorblind users can identify colors by symbol rather than name.

### Clothing analysis (`src/clothing_analysis/`)

Two independent approaches to "does this image show clothing," only one of which is currently wired into the API:

- `validate_clothing.py` (wired to `/validate-clothing`): zero-shot classification via CLIP (`openai/clip-vit-base-patch32`, loaded once at import time). It scores the image against a fixed list of `LABELS` (clothing-ish vs. person/selfie-ish), then applies a heuristic on top of the raw softmax: if the best "person" score is high and not clearly beaten by the best "clothing" score, it overrides the top label and returns `isClothing: False, reason: "PERSON_DETECTED"` — this guards against a photo of someone wearing clothes being misread as a clean product-style clothing photo.
- `analyze_clothing.py` (not currently called from `main.py`): sends the image to OpenAI's `gpt-4o-mini` vision endpoint with a Portuguese system prompt asking for structured JSON (`isClothing`, `category`, `style`, `pattern`, `confidence`) using a fixed vocabulary for `category`/`style`. Requires `OPENAI_API_KEY`. Treat this as a richer, LLM-based classifier/tagger that a future endpoint would expose — check `main.py` before assuming it's live.

### Language convention

User-facing strings, JSON field values (color names, prompts), and some identifiers are in Portuguese (matching the target audience), while code identifiers (function/variable names) are in English. Keep new code consistent with this split.
