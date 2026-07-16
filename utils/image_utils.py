import fitz
import cv2
import numpy as np

# Load an image from the given file path
def load_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Unable to load image: {image_path}")
    return image

# Convert a PDF page into an OpenCV image
def pdf_to_image(pdf_path, page_number=0):
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    pix = page.get_pixmap()

    # Convert PyMuPDF pixmap to NumPy array
    img_array = np.frombuffer(
        pix.samples, dtype=np.uint8
    ).reshape(pix.height, pix.width, pix.n)

    # Convert image to OpenCV BGR format
    if pix.n == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    doc.close()
    return img_array

# Resize image while maintaining the original aspect ratio
def resize_image(image, target_width):
    height, width = image.shape[:2]
    ratio = target_width / width
    target_height = int(height * ratio)
    return cv2.resize(image, (target_width, target_height))

# Return image dimensions as (width, height)
def get_dimensions(image):
    height, width = image.shape[:2]
    return width, height

# Calculate blur score using Laplacian variance
# Higher value = sharper image
def detect_blur(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

# Check whether image meets minimum resolution requirements
def is_resolution_valid(image, min_width, min_height):
    width, height = get_dimensions(image)
    return width >= min_width and height >= min_height

