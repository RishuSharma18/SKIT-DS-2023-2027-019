import unittest

import numpy as np

from app.detection import frame_tiles, suppress_duplicate_detections, tile_count


class TiledDetectionTests(unittest.TestCase):
    def test_large_4k_frame_uses_four_overlapping_tiles(self):
        frame = np.zeros((2160, 3840, 3), dtype=np.uint8)
        tiles = frame_tiles(frame)
        self.assertEqual(tile_count(3840, 2160), 4)
        self.assertEqual(len(tiles), 4)
        self.assertTrue(all(tile.shape[:2] == (1188, 2112) for tile, _, _ in tiles))
        self.assertEqual([(x, y) for _, x, y in tiles], [(0, 0), (1728, 0), (0, 972), (1728, 972)])

    def test_1080p_frame_uses_overlapping_horizontal_tiles(self):
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        tiles = frame_tiles(frame)
        self.assertEqual(tile_count(1920, 1080), 2)
        self.assertEqual(len(tiles), 2)
        self.assertTrue(all(tile.shape[:2] == (1080, 1056) for tile, _, _ in tiles))

    def test_class_wise_nms_removes_tile_duplicates_without_merging_nearby_cars(self):
        detections = np.array([
            [100, 100, 200, 200, 0.90, 2],
            [105, 105, 205, 205, 0.80, 2],
            [155, 100, 255, 200, 0.70, 2],
            [100, 100, 200, 200, 0.85, 3],
        ], dtype=np.float32)
        result = suppress_duplicate_detections(detections, iou_threshold=0.65)
        self.assertEqual(len(result), 3)
        self.assertEqual(sum(result[:, 5] == 2), 2)
        self.assertEqual(sum(result[:, 5] == 3), 1)

    def test_nms_accepts_no_detections(self):
        result = suppress_duplicate_detections(np.empty((0, 6), dtype=np.float32))
        self.assertEqual(result.shape, (0, 6))


if __name__ == "__main__":
    unittest.main()
