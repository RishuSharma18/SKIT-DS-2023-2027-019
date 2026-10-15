"""Vehicle category logic, shared by the pipeline and the tuning tools,
so what you tune in tools/detect_demo.py is exactly what the pipeline uses."""
from . import config

# COCO classes used by YOLOv8: 2=car, 3=motorcycle, 5=bus, 7=truck
CLASS_NAMES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
CLASS_TO_CATEGORY = {2: "car", 3: "bike", 5: "suv", 7: "suv"}


def area_ratio(box, frame_area):
    """Bounding-box area as a fraction of the whole frame."""
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1) / frame_area


def categorize(cls_id, box, frame_area):
    """YOLO/COCO has no SUV class: buses/trucks -> suv, big car boxes -> suv."""
    cat = CLASS_TO_CATEGORY.get(cls_id, "car")
    if cat == "car" and area_ratio(box, frame_area) > config.SUV_AREA_RATIO:
        cat = "suv"
    return cat
