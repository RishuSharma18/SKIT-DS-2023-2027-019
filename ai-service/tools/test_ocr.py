import time
from pathlib import Path
import sys

import cv2

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.plate_reader import PlateReader
from app.plate_locator import find_plate


PLATES_DIR = BASE_DIR / "samples" / "plates"


EXPECTED_PLATES = {
    "image1.jfif": "RJ14CV0002",
    "images2.jfif": "22BH6517A",
    "images3.jfif": "WB06F5977",
    "images4.jfif": "MP33C3370",
    "images5.jfif": "MH47BP8265",
    "images6.jfif": "HR26DQ5551",
    "images7.jfif": "WB06F5977",
    "images8.jfif": "MH47BP8265",
    "images9.jfif": "CH01DD0001",
    "images10.jfif": "KA01MN9787",
    "images11.jfif": "LL8888888",
    "images12.jfif": "WB06F5977",
    "images13.jfif": "JR0012",
    "images14.jfif": "TN37CF4902",
    "images15.jfif": "XX88XY8888",
    "images16.jfif": "KA99EQ11316",
    "images17.jfif": "21BH2211Y",
    "images18.jfif": "DL26CA1111",
    "images19.jfif": "MH40BP4231",
    "images20.png": "WB03MF4477",
    "images21.jfif": "RJ20CF3184",
    "images22.jfif": "GJ31AE0305",
    "images23.jfif": "RJ31CA3320"
}





def recognize_image(reader, image, image_path):
    if image is None or image.size == 0:
        return ""

    import re

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Increase image size for small number plates
    height, width = gray.shape

    if width < 800:
        scale = 800 / width
        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    # Improve contrast
    gray = cv2.bilateralFilter(gray, 5, 35, 35)

    gray = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    ).apply(gray)

    # OCR
    results = reader.reader.readtext(
        gray,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        detail=1,
        paragraph=False,
        batch_size=1
    )

    if not results:
        return ""

    candidates = []

    for result in results:

        text = result[1].upper()
        confidence = result[2]

        # Remove unwanted characters
        text = re.sub(r"[^A-Z0-9]", "", text)

        if confidence < 0.15:
            continue

        # Reject very short text
        if len(text) < 5:
            continue

        candidates.append((text, confidence))

    if not candidates:
        return ""

    # Prefer the longest meaningful detection
    candidates.sort(
        key=lambda item: (
            len(item[0]),
            item[1]
        ),
        reverse=True
    )

    return candidates[0][0]


def main():

    if not PLATES_DIR.exists():
        print("Please create the samples/plates folder.")
        return

    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".jfif"}

    images = sorted([
        file for file in PLATES_DIR.iterdir()
        if file.suffix.lower() in extensions
    ])

    if not images:
        print("No images found in samples/plates/")
        return

    reader = PlateReader()

    correct = 0
    total = 0
    total_processing_time = 0

    print("\n========== FAST OCR TEST (WITH LOCATOR) ==========")

    for image_path in images:

        expected = EXPECTED_PLATES.get(image_path.name)

        if not expected:
            continue

        print("\n--------------------------------")
        print("Image:", image_path.name)

        img = cv2.imread(str(image_path))

        if img is None:
            print("Unable to load image.")
            continue

        total += 1
        start_time = time.perf_counter()

        try:
            # Detect and crop number plate
            cropped_img = find_plate(img)

            if cropped_img is None or cropped_img.size == 0:
                cropped_img = img

            # Run OCR only once
            predicted = recognize_image(
                reader, cropped_img, image_path
            )

            elapsed = time.perf_counter() - start_time
            total_processing_time += elapsed

            print("Expected:", expected)
            print("Predicted:", predicted)
            print(f"Processing time: {elapsed:.2f} seconds")

            if predicted == expected:
                correct += 1
                print("Result: CORRECT")
            else:
                print("Result: INCORRECT")

        except Exception as error:
            print("OCR Error:", error)

    print("\n========== FINAL RESULTS ==========")

    if total > 0:
        accuracy = (correct / total) * 100
        average_time = total_processing_time / total

        print(f"Correct: {correct}/{total}")
        print(f"Accuracy: {accuracy:.2f}%")
        print(f"Total processing time: {total_processing_time:.2f} seconds")
        print(f"Average time per image: {average_time:.2f} seconds")

    else:
        print("No images could be evaluated.")

    print("==================================")


if __name__ == "__main__":
    main()
