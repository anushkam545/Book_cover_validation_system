from utils.image_utils import get_dimensions, detect_blur, is_resolution_valid

# Cover specifications
DPI = 300
COVER_WIDTH_IN = 5
COVER_HEIGHT_IN = 8

# Safe margins (in millimeters)
MARGIN_LEFT_MM = 3
MARGIN_RIGHT_MM = 3
MARGIN_TOP_MM = 3
MARGIN_BOTTOM_MM = 9

# Reserved badge area dimensions
BADGE_WIDTH_MM = 20
BADGE_HEIGHT_MM = 20

# Minimum acceptable blur score
MIN_BLUR_VARIANCE = 100

# Convert millimeters to pixels
def mm_to_px(mm):
    return int((mm / 25.4) * DPI)

# Return the expected cover dimensions in pixels
def get_expected_dimensions():
    width_px = COVER_WIDTH_IN * DPI
    height_px = COVER_HEIGHT_IN * DPI
    return width_px, height_px

# Return safe margins in pixels
def get_safe_margins():
    return {
        "left": mm_to_px(MARGIN_LEFT_MM),
        "right": mm_to_px(MARGIN_RIGHT_MM),
        "top": mm_to_px(MARGIN_TOP_MM),
        "bottom": mm_to_px(MARGIN_BOTTOM_MM)
    }

# Define the reserved badge area (bottom-right corner)
def get_badge_area(image_width, image_height):
    badge_width = mm_to_px(BADGE_WIDTH_MM)
    badge_height = mm_to_px(BADGE_HEIGHT_MM)

    return {
        "x_min": image_width - badge_width,
        "y_min": image_height - badge_height,
        "x_max": image_width,
        "y_max": image_height
    }

# Convert an OCR polygon into a rectangular bounding box
def bbox_to_rect(bbox):
    xs = [point[0] for point in bbox]
    ys = [point[1] for point in bbox]

    return {
        "x_min": min(xs),
        "y_min": min(ys),
        "x_max": max(xs),
        "y_max": max(ys)
    }

# Check whether two rectangles overlap
def rects_overlap(rect_a, rect_b):
    return not (
        rect_a["x_max"] < rect_b["x_min"] or
        rect_a["x_min"] > rect_b["x_max"] or
        rect_a["y_max"] < rect_b["y_min"] or
        rect_a["y_min"] > rect_b["y_max"]
    )

# Find text overlapping the reserved badge area
def check_badge_overlap(ocr_results, image_width, image_height):
    badge_area = get_badge_area(image_width, image_height)
    overlaps = set()

    for item in ocr_results:
        text_rect = bbox_to_rect(item["bbox"])

        if rects_overlap(text_rect, badge_area):
            overlaps.add(item["text"])

    return list(overlaps)

# Find text violating the safe border margins
def check_border_spacing(ocr_results, image_width, image_height):
    margins = get_safe_margins()
    violations = set()

    for item in ocr_results:
        rect = bbox_to_rect(item["bbox"])

        if rect["x_min"] < margins["left"]:
            violations.add(item["text"])

        if rect["x_max"] > image_width - margins["right"]:
            violations.add(item["text"])

        if rect["y_min"] < margins["top"]:
            violations.add(item["text"])

        if rect["y_max"] > image_height - margins["bottom"]:
            violations.add(item["text"])

    return list(violations)

# Run all validation checks and generate the final report
def validate_cover(image, ocr_results):
    issues = []
    instructions = []

    image_width, image_height = get_dimensions(image)

    confidence = 95

    # Resolution validation
    if not is_resolution_valid(image, *get_expected_dimensions()):
        issues.append("Resolution below required cover size")
        instructions.append("Increase image resolution to match 5x8 inch cover at 300 DPI")
        confidence -= 20

    # Blur validation
    blur_score = detect_blur(image)
    if blur_score < MIN_BLUR_VARIANCE:
        issues.append("Image is too blurry")
        instructions.append("Upload a sharper, higher quality image")
        confidence -= 20

    # Reserved badge area validation
    badge_overlaps = check_badge_overlap(
        ocr_results,
        image_width,
        image_height
    )

    if badge_overlaps:
        issues.append("Text overlaps reserved badge area")
        instructions.append("Move text away from the bottom-right badge zone")
        confidence -= 15

    # Safe margin validation
    border_violations = check_border_spacing(
        ocr_results,
        image_width,
        image_height
    )

    if border_violations:
        issues.append("Text too close to cover edges")
        instructions.append("Increase spacing between text and cover borders")
        confidence -= 15

    confidence = max(50, confidence)

    status = "PASS" if not issues else "REVIEW NEEDED"

    return {
        "status": status,
        "confidence": confidence,
        "issues": issues,
        "instructions": instructions,
        "badge_overlaps": badge_overlaps,
        "border_violations": border_violations
    }