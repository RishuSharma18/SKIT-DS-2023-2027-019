
import re
import cv2
import easyocr
import numpy as np


class PlateReader:
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=False)

    def preprocess_image(self, image):
        # Convert image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Improve contrast
        gray = cv2.equalizeHist(gray)

        # Enlarge image for better OCR
        gray = cv2.resize(
            gray, None, fx=2, fy=2,
            interpolation=cv2.INTER_CUBIC
        )

        # Reduce noise
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        return gray

    
    def normalize(self, text):
        import re

        text = re.sub(r'[^A-Z0-9]', '', text.upper())

        # Match Indian Bharat Series plates, e.g. 22BH6517
        bh_match = re.search(r'\d{2}BH\d{4,5}', text)
        if bh_match:
            return bh_match.group(0)

        # Match regular Indian plates, e.g. RJ19UC7034 or TN09BY9726
        regular_match = re.search(
            r'(?:AN|AP|AR|AS|BR|CG|CH|DD|DL|DN|GA|GJ|HP|HR|JH|JK|KA|KL|'
            r'LA|LD|MH|ML|MN|MP|MZ|NL|OD|PB|PY|RJ|SK|TN|TR|TS|UK|UP|WB)'
            r'\d{1,2}[A-Z]{1,3}\d{1,4}',
            text
        )

        if regular_match:
            return regular_match.group(0)

        # Return cleaned OCR text if no plate pattern is found
        return text


        
    
    def read_plate(self, image_path):
        image = cv2.imread(str(image_path))

        if image is None:
            raise ValueError(f"Could not read image: {image_path}")

        # Preprocess image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        gray = cv2.resize(
            gray, None, fx=2, fy=2,
            interpolation=cv2.INTER_CUBIC
        )

        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # Create different image versions
        _, threshold = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        adaptive = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 5
        )

        images = [gray, threshold, adaptive]

        best_raw_text = ""
        best_plate = ""

        for processed in images:
            results = self.reader.readtext(
                processed,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            )

            raw_text = " ".join(
                result[1] for result in results
            )

            plate = self.normalize(raw_text)

            print("OCR:", raw_text)
            print("Normalized:", plate)

            # Select only a recognized plate pattern
            if re.fullmatch(
                r"\d{2}BH\d{4,5}|"
                r"(?:AN|AP|AR|AS|BR|CG|CH|DD|DL|DN|GA|GJ|HP|HR|JH|JK|KA|KL|"
                r"LA|LD|MH|ML|MN|MP|MZ|NL|OD|PB|PY|RJ|SK|TN|TR|TS|UK|UP|WB)"
                r"\d{1,2}[A-Z]{1,3}\d{1,4}",
                plate
            ):
                best_raw_text = raw_text
                best_plate = plate

        return {
            "raw_text": best_raw_text,
            "plate": best_plate
        }
