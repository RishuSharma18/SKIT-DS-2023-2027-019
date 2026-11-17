import cv2
import numpy as np


class UnsupportedImageError(ValueError):
    pass


class InvalidImageError(ValueError):
    pass


_SIGNATURES = (
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"BM", "BMP"),
)


def decode_plate_image(contents):
    if not contents:
        raise InvalidImageError("Uploaded file is empty.")

    is_webp = len(contents) >= 12 and contents[:4] == b"RIFF" and contents[8:12] == b"WEBP"
    if not is_webp and not any(contents.startswith(signature) for signature, _ in _SIGNATURES):
        raise UnsupportedImageError("Unsupported image format. Upload a JPEG, PNG, WebP, or BMP image.")

    image = cv2.imdecode(np.frombuffer(contents, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise InvalidImageError("The uploaded image could not be decoded.")

    height, width = image.shape[:2]
    if width > 8000 or height > 8000 or width * height > 25_000_000:
        raise InvalidImageError("Image dimensions exceed the supported limit of 25 megapixels.")
    return image
