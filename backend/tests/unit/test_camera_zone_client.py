import unittest

class TestPointInPolygonGeometry(unittest.TestCase):
    """Unit tests for ray-casting algorithm to determine vehicle occupancy."""

    @staticmethod
    def point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
        inside = False
        n = len(polygon)
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def test_point_inside_slot(self):
        polygon = [[100, 100], [200, 100], [200, 200], [100, 200]]
        self.assertTrue(self.point_in_polygon(150, 150, polygon))
        self.assertTrue(self.point_in_polygon(120, 180, polygon))

    def test_point_outside_slot(self):
        polygon = [[100, 100], [200, 100], [200, 200], [100, 200]]
        self.assertFalse(self.point_in_polygon(50, 150, polygon))
        self.assertFalse(self.point_in_polygon(250, 150, polygon))
        self.assertFalse(self.point_in_polygon(150, 50, polygon))
        self.assertFalse(self.point_in_polygon(150, 250, polygon))

if __name__ == "__main__":
    unittest.main()
