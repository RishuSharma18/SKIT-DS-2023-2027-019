"""Map supported COCO vehicle classes to the parking system's categories."""

CLASS_NAMES = {
    2: "car (SUVs included)",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
CLASS_TO_CATEGORY = {
    2: "car",
    3: "bike",
    5: "heavy_vehicle",
    7: "heavy_vehicle",
}


def categorize(cls_id):
    """Map COCO vehicle classes without pretending it has a separate SUV class."""
    return CLASS_TO_CATEGORY.get(cls_id)
