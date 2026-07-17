import fitz
import cv2
import numpy as np

def load_image(image_path):
    """Load a PNG (or any raster image) from disk as a BGR OpenCV array."""
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Unable to load image: {image_path}")
    return image

def pdf_to_image(pdf_path, page_number=0):
    """Render a single PDF page to a BGR OpenCV image array (default: first page)."""
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    matrix = fitz.Matrix(4, 4)   
    pix = page.get_pixmap(matrix=matrix)

    # fitz gives raw RGB(A) bytes - reshape into a proper image array first
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

    # OpenCV expects BGR, not RGB(A), so convert based on whether alpha is present
    if pix.n == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    doc.close()
    return img_array


def resize_image(image, target_width):
    """Resize while preserving aspect ratio, scaled to a given target width."""
    height, width = image.shape[:2]
    ratio = target_width / width
    target_height = int(height * ratio)
    return cv2.resize(image, (target_width, target_height))


def preprocess_for_ocr(image):
    """
    Grayscale + adaptive threshold, used only for the OCR pass (not for
    annotation or rule checks, which still use the original full-color image).
    No resize step here on purpose: resizing would shift OCR's bounding box
    coordinates out of sync with the original image used everywhere else in
    the pipeline, and re-scaling every box back would add complexity this
    project doesn't need.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    threshold = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 15
    )
    return threshold


def detect_blur(image):
    """
    Laplacian variance as a sharpness proxy: a blurry image has fewer sharp
    edges, so its Laplacian response has lower variance. Compared against
    MIN_BLUR_VARIANCE in rules.py.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()
