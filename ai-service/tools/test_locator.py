import cv2
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.plate_locator import find_plate

BASE_DIR = Path(__file__).resolve().parent.parent
PLATES_DIR = BASE_DIR / "samples" / "plates"
OUTPUT_DIR = BASE_DIR / "locator_debug"

OUTPUT_DIR.mkdir(exist_ok=True)

extensions = {".jpg", ".jpeg", ".png", ".bmp", ".jfif"}

images = sorted(
    file for file in PLATES_DIR.iterdir()
    if file.suffix.lower() in extensions
)

for image_path in images:

    img = cv2.imread(str(image_path))

    if img is None:
        print("Unable to load:", image_path.name)
        continue

    cropped = find_plate(img)

    output_path = OUTPUT_DIR / f"{image_path.stem}_crop.jpg"

    cv2.imwrite(str(output_path), cropped)

    print(
        image_path.name,
        "| Original:", img.shape,
        "| Crop:", cropped.shape
    )

print("\nAll crop images saved in:", OUTPUT_DIR)
