
import cv2


def find_plate(img):
    """
    Detect a rectangular number plate.
    Use the original contour method as fallback.
    Return the original image if detection is unreliable.
    """

    if img is None or img.size == 0:
        return img

    height, width = img.shape[:2]

    # -----------------------------------
    # METHOD 1: Detect rectangular plate
    # -----------------------------------

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    filtered = cv2.bilateralFilter(
        gray, 9, 50, 50
    )

    edges = cv2.Canny(filtered, 50, 150)

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (5, 3)
    )

    edges = cv2.dilate(
        edges, kernel, iterations=1
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []

    for contour in contours:

        perimeter = cv2.arcLength(contour, True)

        if perimeter == 0:
            continue

        approx = cv2.approxPolyDP(
            contour,
            0.025 * perimeter,
            True
        )

        if len(approx) != 4:
            continue

        if not cv2.isContourConvex(approx):
            continue

        x, y, w, h = cv2.boundingRect(approx)

        area = w * h

        if area < width * height * 0.008:
            continue

        if area > width * height * 0.65:
            continue

        aspect_ratio = w / float(h)

        if not 1.8 <= aspect_ratio <= 6.5:
            continue

        rectangularity = cv2.contourArea(approx) / area

        if rectangularity < 0.55:
            continue

        score = (
            (area / (width * height))
            * rectangularity
            * (1 - 0.08 * abs(aspect_ratio - 4))
        )

        candidates.append(
            (score, x, y, w, h)
        )

    # Use the best rectangular candidate
    if candidates:

        candidates.sort(
            key=lambda item: item[0],
            reverse=True
        )

        _, x, y, w, h = candidates[0]

        margin_x = max(3, int(w * 0.025))
        margin_y = max(3, int(h * 0.12))

        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)

        x2 = min(width, x + w + margin_x)
        y2 = min(height, y + h + margin_y)

        crop = img[y1:y2, x1:x2]

        if crop.size > 0:
            return crop

    # -----------------------------------
    # METHOD 2: Existing contour fallback
    # -----------------------------------

    filtered = cv2.bilateralFilter(
        gray, 11, 17, 17
    )

    edges = cv2.Canny(filtered, 30, 200)

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE
    )

    fallback_candidates = []

    for contour in contours:

        x, y, w, h = cv2.boundingRect(contour)

        area = w * h

        if w < 60 or h < 15:
            continue

        if area < 1000 or area > width * height * 0.5:
            continue

        aspect_ratio = w / float(h)

        if 2.0 <= aspect_ratio <= 5.0:

            fallback_candidates.append(
                (area, x, y, w, h)
            )

    if not fallback_candidates:
        return img

    fallback_candidates.sort(reverse=True)

    _, x, y, w, h = fallback_candidates[0]

    # Avoid suspiciously small crops
    if h < max(50, int(height * 0.12)):
        return img

    margin_x = int(w * 0.05)
    margin_y = int(h * 0.15)

    x1 = max(0, x - margin_x)
    y1 = max(0, y - margin_y)

    x2 = min(width, x + w + margin_x)
    y2 = min(height, y + h + margin_y)

    crop = img[y1:y2, x1:x2]

    if crop is None or crop.size == 0:
        return img

    return crop
