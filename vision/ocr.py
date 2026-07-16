import easyocr

reader = easyocr.Reader(['en'], gpu=False)

def extract_text(image):
    results = reader.readtext(image)
    extracted = []
    for bbox, text, confidence in results:
        extracted.append({
            "text": text,
            "confidence": confidence,
            "bbox": bbox
        })
    return extracted