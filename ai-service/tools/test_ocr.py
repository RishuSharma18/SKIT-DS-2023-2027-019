
from pathlib import Path
import sys

# Import PlateReader from ai-service folder
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from plate_reader import PlateReader

PLATES_DIR = BASE_DIR / "samples" / "plates"

# Add the correct plate number for each image
EXPECTED_PLATES = {
    "plate1.jfif": "22BH6517A",
    "plate2.jfif": "HR88B8888",
    "plate3.jfif": "TN09BY9726",
    "plate4.jfif": "RJ19UC7034",
    "plate5.jfif": "22BH6517A",
    "plate6.jfif": "0d02DL3332",
    "plate8.jfif": "GJ05RY4612"
}


def main():
    if not PLATES_DIR.exists():
        print("Please create the samples/plates folder.")
        return

    extensions = {".jpg", ".jpeg", ".png", ".bmp", ".jfif"}

    images = [
        file for file in PLATES_DIR.iterdir()
        if file.suffix.lower() in extensions
    ]

    if not images:
        print("No images found in samples/plates/")
        return

    reader = PlateReader()
    correct = 0
    total = 0

    for image in sorted(images):
        print("\nImage:", image.name)

        try:
            result = reader.read_plate(image)

            print("Raw text:", result["raw_text"])
            print("Final plate:", result["plate"])

            expected = EXPECTED_PLATES.get(image.name)

            if expected:
                total += 1
                expected = reader.normalize(expected)

                if result["plate"] == expected:
                    correct += 1
                    print("Status: CORRECT")
                else:
                    print("Expected plate:", expected)
                    print("Status: INCORRECT")

        except Exception as error:
            print("Error:", error)

    if total > 0:
        accuracy = (correct / total) * 100
        print("\nAccuracy:", round(accuracy, 2), "%")
        print("Correct:", correct, "/", total)
    else:
        print("\nAccuracy cannot be calculated yet.")
        print("Add correct plate numbers to EXPECTED_PLATES.")


if __name__ == "__main__":
    main()
