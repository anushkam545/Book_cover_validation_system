import cv2
import numpy as np

# Draw OCR annotations and highlight validation issues
def draw_annotations(image, ocr_results, badge_overlap_texts, border_violation_texts, output_path):
    annotated = image.copy()

    # Convert to sets for faster membership checks
    badge_overlap_texts = set(badge_overlap_texts)
    border_violation_texts = set(border_violation_texts)

    for item in ocr_results:
        bbox = np.array(item["bbox"], dtype=np.int32)
        text = item["text"]

        # Choose annotation color based on validation result
        if text in badge_overlap_texts:
            color = (0, 0, 255)      # Red - overlaps reserved badge area
        elif text in border_violation_texts:
            color = (0, 255, 255)    # Yellow - too close to cover border
        else:
            color = (0, 255, 0)      # Green - valid text

        # Draw the OCR bounding box
        cv2.polylines(
            annotated,
            [bbox],
            isClosed=True,
            color=color,
            thickness=2
        )

    # Save the annotated image
    cv2.imwrite(output_path, annotated)

    return output_path