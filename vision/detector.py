import os
from utils.image_utils import load_image, pdf_to_image
from vision.ocr import extract_text
from vision.rules import validate_cover
from vision.annotate import draw_annotations

# Directory where annotated images are saved
OUTPUT_DIR = "outputs"

# Process a book cover, validate it, and generate an annotated image

def process_cover(file_path, identifier):
    """
    Complete processing pipeline for a single book cover.

    Steps:
    1. Load the uploaded image or convert the first PDF page to an image.
    2. Run OCR to detect text and bounding boxes.
    3. Validate the cover against BookLeaf publishing rules.
    4. Generate an annotated image highlighting detected issues.
    5. Return validation results along with the annotation path.

    The identifier (typically an ISBN) is used as the output filename
    so each processed submission can be traced easily.
    """

    # Determine uploaded file type
    ext = os.path.splitext(file_path)[1].lower()

    # Convert PDF to image or load raster image directly
    if ext == ".pdf":
        image = pdf_to_image(file_path)
    else:
        image = load_image(file_path)

    # Detect all visible text using OCR
    ocr_results = extract_text(image)

    # Validate cover against all publishing rules
    result = validate_cover(image, ocr_results)

    # Create output directory if it does not already exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save annotation using the submission identifier
    annotated_path = os.path.join(
        OUTPUT_DIR,
        f"{identifier}_annotated.png"
    )

    # Draw OCR boxes and highlight validation issues
    draw_annotations(
        image,
        ocr_results,
        result["badge_overlaps"],
        result["border_violations"],
        annotated_path
    )

    # Include annotated image path in the response
    result["annotated_image_path"] = annotated_path

    return result
