"""
Unit tests for ERS Strategy Modes and Harvesting Rules.
"""

import unittest
from ers_simulator.ers_strategy import ERSStrategy, ERSMode


class TestERSStrategy(unittest.TestCase):
    def test_hotlap_mode_full_deployment(self):
        """Qualifying mode requests maximum 120 kW when throttle is 1.0."""
        pwr = ERSStrategy.calculate_deployment_demand(
            mode=ERSMode.HOTLAP_QUALI,
            speed_mps=50.0,
            throttle=1.0,
            is_drs_zone=False,
            corner_exit_progress=0.5,
            cumulative_deployed_j=500_000.0,
            current_soc=0.80
        )
        self.assertEqual(pwr, 120_000.0)

    def test_balanced_mode_cutoff_at_high_speed(self):
        """Balanced mode reduces power at high speed to prevent derate."""
        pwr_low = ERSStrategy.calculate_deployment_demand(
            mode=ERSMode.RACE_BALANCED,
            speed_mps=35.0, # ~126 km/h
            throttle=1.0,
            is_drs_zone=False,
            corner_exit_progress=0.3,
            cumulative_deployed_j=500_000.0,
            current_soc=0.80,
            cutoff_speed_kmh=290.0
        )
        pwr_high = ERSStrategy.calculate_deployment_demand(
            mode=ERSMode.RACE_BALANCED,
            speed_mps=85.0, # ~306 km/h (above cutoff)
            throttle=1.0,
            is_drs_zone=False,
            corner_exit_progress=1.0,
            cumulative_deployed_j=500_000.0,
            current_soc=0.80,
            cutoff_speed_kmh=290.0
        )
        self.assertGreater(pwr_low, pwr_high)
        self.assertLessEqual(pwr_high, 120_000.0 * 0.20)

    def test_overtake_mode_boosts_in_drs(self):
        """Overtake mode gives full power in DRS zone."""
        pwr_drs = ERSStrategy.calculate_deployment_demand(
            mode=ERSMode.OVERTAKE_PUSH,
            speed_mps=75.0,
            throttle=1.0,
            is_drs_zone=True,
            corner_exit_progress=1.0,
            cumulative_deployed_j=500_000.0,
            current_soc=0.80
        )
        pwr_no_drs = ERSStrategy.calculate_deployment_demand(
            mode=ERSMode.OVERTAKE_PUSH,
            speed_mps=75.0,
            throttle=1.0,
            is_drs_zone=False,
            corner_exit_progress=1.0,
            cumulative_deployed_j=500_000.0,
            current_soc=0.80
        )
        self.assertEqual(pwr_drs, 120_000.0)
        self.assertLess(pwr_no_drs, pwr_drs)

    def test_lift_and_coast_trigger(self):
        """Verify lift and coast throttle lift within distance window."""
        throttle_coast, is_coast = ERSStrategy.calculate_lift_and_coast(
            distance_to_braking_marker_m=25.0,
            lift_and_coast_window_m=40.0
        )
        self.assertTrue(is_coast)
        self.assertEqual(throttle_coast, 0.0)

        throttle_push, is_push = ERSStrategy.calculate_lift_and_coast(
            distance_to_braking_marker_m=80.0,
            lift_and_coast_window_m=40.0
        )
        self.assertFalse(is_push)
        self.assertEqual(throttle_push, 1.0)


if __name__ == "__main__":
    unittest.main()
