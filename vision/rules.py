from utils.image_utils import detect_blur
from config import CONFIDENCE_THRESHOLD

# --- Constants from the BookLeaf spec -------------------------------------

DPI = 300  # print-quality baseline, only used for the absolute resolution check
COVER_WIDTH_IN = 5
COVER_HEIGHT_IN = 8
COVER_WIDTH_MM = COVER_WIDTH_IN * 25.4
COVER_HEIGHT_MM = COVER_HEIGHT_IN * 25.4

# Safe area margins: 3mm on each side, 9mm from the bottom of the front cover
MARGIN_LEFT_MM = 3
MARGIN_RIGHT_MM = 3
MARGIN_TOP_MM = 3
MARGIN_BOTTOM_MM = 9

BADGE_HEIGHT_MM = 9  # bottom 9mm strip reserved for the award emblem, full width of the front cover

MIN_BLUR_VARIANCE = 100  # Laplacian variance threshold below which an image is considered blurry
BACK_COVER_EDGE_MARGIN_RATIO = 0.02  # 2% of back-cover width/height, used for the back-cover alignment check


def filter_low_confidence(ocr_results):
    """
    Raw OCR output includes noise: stray characters, artifacts picked up
    from thresholding. Without this filter, every image tends to trigger
    the same violations from noise alone, flattening the confidence score.
    """
    return [item for item in ocr_results if item["confidence"] >= CONFIDENCE_THRESHOLD]


def split_front_and_back(image_width, image_height):
    """
    Sample covers are supplied as a full wraparound spread (back | front).
    A single front-cover-only upload has an aspect ratio close to 5:8 (0.625).
    A spread is roughly twice as wide, so aspect ratio > 1.0 signals a spread.
    Assumption: no separate spine strip - the spread splits 50/50.
    """
    aspect_ratio = image_width / image_height

    if aspect_ratio > 1.0:
        # Wraparound spread: right half is the front cover, left half is the back cover.
        front_x_offset = image_width // 2
        front_width = image_width - front_x_offset
        back_region = {"x_min": 0, "y_min": 0, "x_max": front_x_offset, "y_max": image_height}
    else:
        # Single front-cover-only upload: the whole image is the front cover, no back cover to check.
        front_x_offset = 0
        front_width = image_width
        back_region = None

    front_region = {
        "x_min": front_x_offset,
        "y_min": 0,
        "x_max": front_x_offset + front_width,
        "y_max": image_height
    }

    return front_region, back_region


def get_expected_front_cover_dimensions():
    """
    Absolute print-quality floor - deliberately tied to real 300 DPI,
    since this check exists to catch genuinely low-quality/pixelated uploads.
    Ordinary web-sized test images will usually fall below this on purpose.
    """
    width_px = COVER_WIDTH_IN * DPI
    height_px = COVER_HEIGHT_IN * DPI
    return width_px, height_px


def get_safe_margins(front_region):
    """
    Margins as a proportion of the front cover's real physical size (mm),
    applied to whatever the actual pixel dimensions happen to be. This keeps
    placement checks correct regardless of the uploaded image's resolution -
    a fixed-DPI pixel margin would cover a wildly different fraction of the
    cover depending on how large the uploaded file actually is.
    """
    front_width = front_region["x_max"] - front_region["x_min"]
    front_height = front_region["y_max"] - front_region["y_min"]

    return {
        "left": int(front_width * (MARGIN_LEFT_MM / COVER_WIDTH_MM)),
        "right": int(front_width * (MARGIN_RIGHT_MM / COVER_WIDTH_MM)),
        "top": int(front_height * (MARGIN_TOP_MM / COVER_HEIGHT_MM)),
        "bottom": int(front_height * (MARGIN_BOTTOM_MM / COVER_HEIGHT_MM))
    }


def get_badge_area(front_region):
    """Full-width rectangle covering the bottom BADGE_HEIGHT_MM of the front cover."""
    front_height = front_region["y_max"] - front_region["y_min"]
    badge_height = int(front_height * (BADGE_HEIGHT_MM / COVER_HEIGHT_MM))
    return {
        "x_min": front_region["x_min"],
        "y_min": front_region["y_max"] - badge_height,
        "x_max": front_region["x_max"],
        "y_max": front_region["y_max"]
    }


def bbox_to_rect(bbox):
    """Convert a 4-point OCR bounding box into a simple min/max rectangle."""
    xs = [point[0] for point in bbox]
    ys = [point[1] for point in bbox]
    return {
        "x_min": min(xs),
        "y_min": min(ys),
        "x_max": max(xs),
        "y_max": max(ys)
    }


def rects_overlap(rect_a, rect_b):
    """True if two rectangles intersect at all (even partially)."""
    return not (
        rect_a["x_max"] < rect_b["x_min"] or
        rect_a["x_min"] > rect_b["x_max"] or
        rect_a["y_max"] < rect_b["y_min"] or
        rect_a["y_min"] > rect_b["y_max"]
    )


def overlap_ratio(rect_a, rect_b):
    """Fraction of rect_a's area that overlaps with rect_b. 0 if no overlap.
    Used to scale the badge-overlap penalty by how bad the overlap actually is,
    rather than applying the same flat penalty to a 5% clip and a 90% clip."""
    x_overlap = max(0, min(rect_a["x_max"], rect_b["x_max"]) - max(rect_a["x_min"], rect_b["x_min"]))
    y_overlap = max(0, min(rect_a["y_max"], rect_b["y_max"]) - max(rect_a["y_min"], rect_b["y_min"]))
    intersection = x_overlap * y_overlap

    area_a = (rect_a["x_max"] - rect_a["x_min"]) * (rect_a["y_max"] - rect_a["y_min"])
    if area_a <= 0:
        return 0.0
    return intersection / area_a


def check_badge_overlap(ocr_results, front_region):
    """
    Critical check per the spec (95% accuracy required): does any detected
    text on the front cover overlap the reserved award badge strip?
    """
    badge_area = get_badge_area(front_region)
    overlaps = []
    ratios = []
    for item in ocr_results:
        text_rect = bbox_to_rect(item["bbox"])
        if not rects_overlap(text_rect, front_region):
            continue  # this text belongs to the back cover, not relevant here
        ratio = overlap_ratio(text_rect, badge_area)
        if ratio > 0:
            overlaps.append(item["text"])
            ratios.append(ratio)
    return overlaps, ratios


def check_border_spacing(ocr_results, front_region):
    """Flags front-cover text that encroaches into the 3mm/9mm safe margins."""
    margins = get_safe_margins(front_region)
    violations = []
    depths = []  # how far (in px) each violating text box crosses into the margin
    for item in ocr_results:
        rect = bbox_to_rect(item["bbox"])
        if not rects_overlap(rect, front_region):
            continue

        depth = 0
        if rect["x_min"] < front_region["x_min"] + margins["left"]:
            depth = max(depth, (front_region["x_min"] + margins["left"]) - rect["x_min"])
        if rect["x_max"] > front_region["x_max"] - margins["right"]:
            depth = max(depth, rect["x_max"] - (front_region["x_max"] - margins["right"]))
        if rect["y_min"] < front_region["y_min"] + margins["top"]:
            depth = max(depth, (front_region["y_min"] + margins["top"]) - rect["y_min"])
        if rect["y_max"] > front_region["y_max"] - margins["bottom"]:
            depth = max(depth, rect["y_max"] - (front_region["y_max"] - margins["bottom"]))

        if depth > 0:
            violations.append(item["text"])
            depths.append(depth)
    return violations, depths


def check_back_cover_alignment(ocr_results, back_region):
    """
    Additional detection requirement from the spec: back-cover text alignment.
    No exact numbers given in the spec for this one, so a 2% edge margin on
    the back cover is used as a reasonable working assumption.
    """
    if back_region is None:
        return []

    width = back_region["x_max"] - back_region["x_min"]
    height = back_region["y_max"] - back_region["y_min"]
    edge_margin_x = int(width * BACK_COVER_EDGE_MARGIN_RATIO)
    edge_margin_y = int(height * BACK_COVER_EDGE_MARGIN_RATIO)

    violations = []
    for item in ocr_results:
        rect = bbox_to_rect(item["bbox"])
        if not rects_overlap(rect, back_region):
            continue
        if (rect["x_min"] < back_region["x_min"] + edge_margin_x or
                rect["x_max"] > back_region["x_max"] - edge_margin_x or
                rect["y_min"] < back_region["y_min"] + edge_margin_y or
                rect["y_max"] > back_region["y_max"] - edge_margin_y):
            violations.append(item["text"])
    return violations


# --- Continuous, severity-weighted scoring functions -----------------------
# Each returns None if that check passed (no penalty), or a penalty amount
# that scales with how bad the issue actually is - this is what gives the
# confidence score real variance instead of a flat per-category deduction.

def score_resolution(front_region):
    front_width = front_region["x_max"] - front_region["x_min"]
    front_height = front_region["y_max"] - front_region["y_min"]
    expected_width, expected_height = get_expected_front_cover_dimensions()

    actual_area = front_width * front_height
    expected_area = expected_width * expected_height

    if actual_area >= expected_area:
        return None  # valid, no penalty

    shortfall = 1 - (actual_area / expected_area)
    penalty = round(min(25, shortfall * 40), 1)
    return penalty


def score_blur(blur_score):
    if blur_score >= MIN_BLUR_VARIANCE:
        return None
    deficit_ratio = max(0.0, (MIN_BLUR_VARIANCE - blur_score) / MIN_BLUR_VARIANCE)
    penalty = round(min(20, deficit_ratio * 30), 1)
    return penalty


def score_badge_overlap(ratios):
    # Critical issue per the spec - base penalty starts high (22) and scales
    # up further with how much of the text actually sits inside the badge zone.
    if not ratios:
        return None
    worst_ratio = max(ratios)
    penalty = round(min(40, 22 + worst_ratio * 18), 1)
    return penalty


def score_border_spacing(depths, front_region):
    # Penalty scales with how far (as a fraction of front cover width) the
    # worst violation crosses into the margin - a 1px nudge over the line
    # shouldn't cost the same as text buried deep in the margin.
    if not depths:
        return None
    front_width = front_region["x_max"] - front_region["x_min"]
    total_depth_ratio = sum(depths) / front_width
    penalty = round(min(20, 6 + total_depth_ratio * 400), 1)
    return penalty


def score_back_cover(violation_count):
    if violation_count == 0:
        return None
    penalty = round(min(10, 4 + violation_count * 2), 1)
    return penalty


def validate_cover(image, ocr_results):
    """
    Main entry point - runs every check, accumulates a weighted penalty,
    and returns a PASS/REVIEW NEEDED verdict with a 20-98 confidence score.
    """
    ocr_results = filter_low_confidence(ocr_results)

    issues = []
    instructions = []
    total_penalty = 0.0

    image_height, image_width = image.shape[:2]
    front_region, back_region = split_front_and_back(image_width, image_height)

    # 1. Print-quality resolution floor (front cover only)
    resolution_penalty = score_resolution(front_region)
    if resolution_penalty is not None:
        issues.append("❌ Resolution below required cover size [MODERATE]")
        instructions.append("Increase image resolution to match 5x8 inch front cover at 300 DPI")
        total_penalty += resolution_penalty

    # 2. Sharpness / blur check (whole image)
    blur_score = detect_blur(image)
    blur_penalty = score_blur(blur_score)
    if blur_penalty is not None:
        issues.append("❌ Image is too blurry [MODERATE]")
        instructions.append("Upload a sharper, higher quality image")
        total_penalty += blur_penalty

    # 3. Critical check: text overlapping the award badge zone
    badge_overlaps, badge_ratios = check_badge_overlap(ocr_results, front_region)
    badge_penalty = score_badge_overlap(badge_ratios)
    if badge_penalty is not None:
        issues.append("❌ Text overlaps reserved award badge area [CRITICAL]")
        instructions.append("Move author name/text away from the bottom 9mm badge zone on the front cover")
        total_penalty += badge_penalty

    # 4. Text-to-border spacing (front cover safe margins)
    border_violations, border_depths = check_border_spacing(ocr_results, front_region)
    border_penalty = score_border_spacing(border_depths, front_region)
    if border_penalty is not None:
        issues.append("❌ Text too close to front cover edges [MINOR]")
        instructions.append("Increase spacing between text and front cover borders (3mm safe margin)")
        total_penalty += border_penalty

    # 5. Back cover text alignment
    back_cover_violations = check_back_cover_alignment(ocr_results, back_region)
    back_penalty = score_back_cover(len(back_cover_violations))
    if back_penalty is not None:
        issues.append("❌ Back cover text alignment issue [MINOR]")
        instructions.append("Realign back cover text away from its edges")
        total_penalty += back_penalty

    # Two-tier status per the spec: PASS only if every check cleared.
    status = "PASS" if not issues else "REVIEW NEEDED"
    confidence = round(max(20, min(98, 98 - total_penalty)))

    return {
        "status": status,
        "confidence": confidence,
        "issues": issues,
        "instructions": instructions,
        "badge_overlaps": badge_overlaps,
        "border_violations": border_violations
    }
