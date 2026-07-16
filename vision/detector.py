import os
from utils.image_utils import load_image, pdf_to_image
from vision.ocr import extract_text
from vision.rules import validate_cover
from vision.annotate import draw_annotations

# Process a book cover, validate it, and generate an annotated image
def process_cover(file_path):
    # Determine the uploaded file type
    ext = os.path.splitext(file_path)[1].lower()

    # Convert PDF to image, otherwise load the image directly
    if ext == ".pdf":
        image = pdf_to_image(file_path)
    else:
        image = load_image(file_path)

    # Extract text and bounding boxes using OCR
    ocr_results = extract_text(image)

    # Run all validation checks
    result = validate_cover(image, ocr_results)

    # Generate an annotated image highlighting validation issues
    base_name = os.path.splitext(file_path)[0]
    annotated_path = f"{base_name}_annotated.png"

    draw_annotations(
        image,
        ocr_results,
        result["badge_overlaps"],
        result["border_violations"],
        annotated_path
    )

    # Include the annotated image path in the response
    result["annotated_image_path"] = annotated_path

    return result