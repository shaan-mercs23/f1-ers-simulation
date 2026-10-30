"""
Unit tests for Lap Simulator and Multi-Driver Comparison.
"""

import unittest
from ers_simulator.track import get_circuit
from ers_simulator.driver import get_driver_preset
from ers_simulator.solver import LapSimulator
from ers_simulator.telemetry import TelemetryComparison


class TestLapSimulator(unittest.TestCase):
    def setUp(self):
        self.simulator = LapSimulator()
        self.monza = get_circuit("monza")
        self.ver = get_driver_preset("ver")
        self.ham = get_driver_preset("ham")

    def test_single_driver_simulation(self):
        """Simulate single lap on Monza and verify physical plausibility."""
        result = self.simulator.simulate(self.monza, self.ver, dx=4.0)

        # Monza lap time should be realistically around 78 to 86 seconds
        self.assertGreater(result.lap_time_s, 70.0)
        self.assertLess(result.lap_time_s, 95.0)

        # Top speed at Monza should reach 330 - 365 km/h
        self.assertGreater(result.top_speed_kmh, 325.0)
        self.assertLess(result.top_speed_kmh, 375.0)

        # Energy deployed must not exceed 4.0 MJ regulatory limit
        self.assertLessEqual(result.energy_deployed_mj, 4.005)

        # Energy harvested from MGU-K must not exceed 2.0 MJ
        self.assertLessEqual(result.energy_harvested_k_mj, 2.005)

        # Telemetry arrays must be populated and equal length
        self.assertEqual(len(result.distance), len(result.speed_kmh))
        self.assertEqual(len(result.time), len(result.battery_soc))

    def test_multi_driver_comparison(self):
        """Compare two drivers and verify delta time and leaderboard generation."""
        res_ver = self.simulator.simulate(self.monza, self.ver, dx=4.0)
        res_ham = self.simulator.simulate(self.monza, self.ham, dx=4.0)

        comparison = TelemetryComparison([res_ver, res_ham])
        self.assertEqual(len(comparison.leaderboards), 2)
        
        # Fastest driver should have gap = 0.0
        fastest = comparison.leaderboards[0]
        self.assertEqual(fastest.gap_to_leader_s, 0.0)
        self.assertEqual(fastest.gap_to_leader_str, "Leader")

        # Delta time trace exists
        self.assertIn("VER", comparison.delta_times)
        self.assertIn("HAM", comparison.delta_times)

        # Telemetry export dictionary
        dict_data = comparison.to_dict()
        self.assertEqual(dict_data["track_name"], self.monza.name)
        self.assertIn("VER", dict_data["drivers"])
        self.assertIn("HAM", dict_data["drivers"])

        # CSV export should contain rows
        csv_str = comparison.to_csv()
        self.assertIn("Distance_m", csv_str)
        self.assertIn("VER_Speed_kmh", csv_str)
        self.assertIn("HAM_Delta_s", csv_str)


if __name__ == "__main__":
    unittest.main()
