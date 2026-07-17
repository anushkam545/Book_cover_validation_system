import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from vision.detector import process_cover
from config import BASE_URL

# outputs/ must exist before StaticFiles mounts it at startup
os.makedirs("outputs", exist_ok=True)

app = FastAPI()
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# Supported upload formats
ALLOWED_EXTENSIONS = {".pdf", ".png"}


# API endpoint to analyze a book cover
@app.post("/analyze")
def analyze(isbn: str = Form(...), file: UploadFile = File(...)):
    # Get the uploaded file extension
    suffix = os.path.splitext(file.filename)[1].lower()

    # Validate supported file types
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and PNG files are supported"
        )

    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    try:
        # Process the uploaded cover - isbn doubles as the output filename identifier
        result = process_cover(temp_path, isbn)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to process cover image"
        )

    finally:
        # Remove the temporary upload after processing (annotated output stays in outputs/)
        os.remove(temp_path)

    # Build a real, fetchable URL for the annotated image instead of a local path -
    # this is what actually goes into Airtable's "Visual annotations URL" field.
    annotated_filename = os.path.basename(result["annotated_image_path"])
    annotated_url = f"{BASE_URL}/outputs/{annotated_filename}"

    # Return the validation report
    return {
        "isbn": isbn,
        "status": result["status"],
        "confidence": result["confidence"],
        "issues": result["issues"],
        "instructions": result["instructions"],
        "annotated_image_url": annotated_url
    }
