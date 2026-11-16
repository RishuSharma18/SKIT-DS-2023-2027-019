"""Map supported COCO vehicle classes to the parking system's categories."""

CLASS_NAMES = {2: "car (SUVs included)", 3: "motorcycle"}
CLASS_TO_CATEGORY = {2: "car", 3: "bike"}


def categorize(cls_id):
    """Keep COCO cars as cars; it has no reliable, separate SUV class."""
    return CLASS_TO_CATEGORY.get(cls_id)
