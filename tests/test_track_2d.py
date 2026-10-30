"""
Unit tests for 2D Circuit Geometry & On-Track Simulation engine.
"""

import unittest
from ers_simulator.track import get_circuit, list_circuits
from ers_simulator.track_2d import build_smooth_2d_track, TRACK_2D_ANCHORS


class TestTrack2D(unittest.TestCase):
    def test_all_15_circuits_have_anchors(self):
        """Verify that all 15 circuits have authentic 2D anchors."""
        circuits = list_circuits()
        for c in circuits:
            c_id = c["id"].lower()
            self.assertIn(c_id, TRACK_2D_ANCHORS, f"Missing 2D anchors for {c_id}")
            self.assertTrue(len(TRACK_2D_ANCHORS[c_id]) >= 10, f"Too few anchors for {c_id}")

    def test_smooth_track_generation(self):
        """Test smooth 2D track loop interpolation and bounds."""
        monza = get_circuit("monza")
        t2d = build_smooth_2d_track(monza, num_samples=500)

        self.assertEqual(t2d["track_id"], "monza")
        self.assertEqual(t2d["num_points"], 500)
        self.assertEqual(len(t2d["x"]), 500)
        self.assertEqual(len(t2d["y"]), 500)
        self.assertEqual(len(t2d["distances_m"]), 500)

        # Bounds should be well inside [0, 1000] canvas range
        self.assertTrue(min(t2d["x"]) >= 40.0)
        self.assertTrue(max(t2d["x"]) <= 960.0)
        self.assertTrue(min(t2d["y"]) >= 40.0)
        self.assertTrue(max(t2d["y"]) <= 960.0)

        # Corners should be extracted
        self.assertTrue(len(t2d["corners"]) >= 10)
        first_corner = t2d["corners"][0]
        self.assertIn("name", first_corner)
        self.assertIn("distance_m", first_corner)
        self.assertIn("x", first_corner)
        self.assertIn("y", first_corner)

        # DRS zones and sectors
        self.assertTrue(len(t2d["drs_zones"]) >= 1)
        self.assertEqual(len(t2d["sectors"]), 3)
        self.assertEqual(len(t2d["point_sectors"]), 500)
        self.assertEqual(len(t2d["point_drs"]), 500)

    def test_silverstone_and_spa(self):
        """Test smooth 2D track loops for Silverstone and Spa."""
        for c_id in ["silverstone", "spa", "monaco", "suzuka", "redbullring"]:
            c = get_circuit(c_id)
            t2d = build_smooth_2d_track(c, num_samples=300)
            self.assertEqual(len(t2d["x"]), 300)
            self.assertEqual(len(t2d["y"]), 300)
            self.assertTrue(len(t2d["drs_zones"]) >= 1)
            self.assertEqual(len(t2d["sectors"]), 3)


if __name__ == "__main__":
    unittest.main()
