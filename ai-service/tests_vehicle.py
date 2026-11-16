import unittest
from pathlib import Path

from app import config
from app.slots import SlotMap
from app.vehicle import categorize


class VehicleCategoryTests(unittest.TestCase):
    def test_coco_cars_including_suvs_use_car_category(self):
        self.assertEqual(categorize(2), "car")

    def test_motorcycles_use_bike_category(self):
        self.assertEqual(categorize(3), "bike")

    def test_bus_and_truck_are_not_mislabeled_as_suv(self):
        self.assertEqual(categorize(5), "heavy_vehicle")
        self.assertEqual(categorize(7), "heavy_vehicle")
        self.assertEqual(config.VEHICLE_CLASSES, [2, 3, 5, 7])

    def test_sample_slot_map_contains_five_car_bays(self):
        slots = SlotMap(Path(__file__).parent / "config" / "slots.json")
        self.assertEqual(len(slots.slots), 5)
        self.assertEqual(slots.locate((2097, 1238), "car")["slotId"], "A-04")
        self.assertIsNone(slots.locate((2097, 1238), "bike"))


if __name__ == "__main__":
    unittest.main()
