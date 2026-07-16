import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from vision.detector import process_cover

app = FastAPI()

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
        # Process the uploaded cover
        result = process_cover(temp_path)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to process cover image"
        )

    finally:
        # Remove the temporary file after processing
        os.remove(temp_path)

    # Return the validation report
    return {
        "isbn": isbn,
        "status": result["status"],
        "confidence": result["confidence"],
        "issues": result["issues"],
        "instructions": result["instructions"],
        "annotated_image_path": result["annotated_image_path"]
    }