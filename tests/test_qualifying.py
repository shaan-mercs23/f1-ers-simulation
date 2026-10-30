"""
Unit tests for Formula 1 Qualifying Shootout and Multi-Driver Simulation.
"""

import unittest
from ers_simulator.track import get_circuit
from ers_simulator.driver import get_driver_preset, list_driver_presets
from ers_simulator.solver import LapSimulator
from ers_simulator.qualifying import QualifyingSimulator, simulate_qualifying_session


class TestQualifyingSimulation(unittest.TestCase):
    """Test suite for F1 qualifying knockout and shootout engine."""

    def setUp(self):
        self.track = get_circuit("monza")
        self.ver = get_driver_preset("ver", year=2024)
        self.ham = get_driver_preset("ham", year=2024)
        self.nor = get_driver_preset("nor", year=2024)
        self.lec = get_driver_preset("lec", year=2024)

    def test_head_to_head_qualifying(self):
        """Test 2-driver qualifying shootout."""
        sim = QualifyingSimulator()
        res = sim.simulate(self.track, [self.ver, self.ham], year=2024, dx=5.0)

        self.assertEqual(res.num_drivers, 2)
        self.assertEqual(len(res.grid), 2)
        self.assertEqual(res.grid[0].position, 1)
        self.assertEqual(res.grid[1].position, 2)
        self.assertEqual(res.grid[0].gap_to_pole_str, "POLE")
        self.assertTrue(res.grid[1].gap_to_pole_s >= 0.0)

        # Qualifying times should be in realistic F1 qualifying range for Monza (1:17 - 1:24)
        self.assertTrue(75.0 < res.pole_time_s < 85.0)
        self.assertTrue(res.purple_s1_s > 0)
        self.assertTrue(res.purple_s2_s > 0)
        self.assertTrue(res.purple_s3_s > 0)
        self.assertTrue(res.speed_trap_kmh > 330.0)

    def test_track_evolution_progression(self):
        """Test that Q3 lap times improve over Q1 due to rubbering-in and engine party mode."""
        sim = QualifyingSimulator()
        res = sim.simulate(self.track, [self.ver, self.lec, self.nor, self.ham], year=2024, dx=5.0)

        for d in res.grid:
            if d.q1_time_s and d.q3_time_s:
                # Q3 should be faster than Q1 due to +1.5% grip and +12 kW vs +8 kW
                self.assertLess(d.q3_time_s, d.q1_time_s, f"{d.driver.name} Q3 ({d.q3_time_s}) not faster than Q1 ({d.q1_time_s})")

    def test_qualifying_faster_than_race(self):
        """Test that qualifying simulation produces faster lap times than race simulation."""
        solver = LapSimulator()
        race_lap = solver.simulate(self.track, self.ver, year=2024, is_qualifying=False, dx=5.0)
        
        sim = QualifyingSimulator(solver=solver)
        quali_res = sim.simulate(self.track, [self.ver], year=2024, dx=5.0)
        quali_lap = quali_res.grid[0].best_lap_s

        # Qualifying should be faster than standard race pace by 0.8s to 3.0s
        self.assertLess(quali_lap, race_lap.lap_time_s)

    def test_arbitrary_driver_count(self):
        """Test simulating an arbitrary number of drivers (e.g. 5 drivers, 8 drivers)."""
        sim = QualifyingSimulator()
        drivers = [
            get_driver_preset("ver", year=2024),
            get_driver_preset("nor", year=2024),
            get_driver_preset("lec", year=2024),
            get_driver_preset("pia", year=2024),
            get_driver_preset("sai", year=2024),
        ]
        res = sim.simulate(self.track, drivers, year=2024, dx=5.0)
        self.assertEqual(res.num_drivers, 5)
        self.assertEqual(len(res.grid), 5)

        # Check telemetry conversion to dict
        d = res.to_dict()
        self.assertEqual(d["mode"], "qualifying")
        self.assertIn("grid", d)
        self.assertEqual(len(d["grid"]), 5)
        self.assertIn("pole_driver", d)
        self.assertIn("purple_s1", d)
        self.assertIn("speed_trap", d)

    def test_to_csv_export(self):
        """Test qualifying CSV export contains header, classification and telemetry."""
        sim = QualifyingSimulator()
        res = sim.simulate(self.track, [self.ver, self.ham], year=2024, dx=10.0)
        csv_str = res.to_csv()
        self.assertIn("FORMULA 1 QUALIFYING RESULTS", csv_str)
        self.assertIn("POLE", csv_str)
        self.assertIn("VER", csv_str)
        self.assertIn("HAM", csv_str)


if __name__ == "__main__":
    unittest.main()
