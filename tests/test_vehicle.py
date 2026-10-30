"""
Unit tests for F1 Vehicle, Power Unit, and Battery Dynamics.
"""

import unittest
import math
from ers_simulator.vehicle import F1Vehicle, F1PowerUnit, EnergyStore, Aerodynamics, EngineCharacteristics


class TestVehicleAndPowerUnit(unittest.TestCase):
    def setUp(self):
        self.vehicle = F1Vehicle()
        self.pu = self.vehicle.power_unit

    def test_ice_power_output(self):
        """Verify ICE power at low and high speeds under full throttle."""
        power_high, fuel_high = self.pu.ice.mechanical_power(speed_mps=80.0, throttle=1.0)
        self.assertAlmostEqual(power_high, 590_000.0, delta=1000.0)
        self.assertAlmostEqual(fuel_high, 100.0 / 3600.0, places=4)

        # Zero throttle gives zero power
        power_zero, _ = self.pu.ice.mechanical_power(speed_mps=80.0, throttle=0.0)
        self.assertEqual(power_zero, 0.0)

    def test_battery_discharge_and_soc(self):
        """Test battery discharge step and SoC reduction."""
        battery = EnergyStore(total_capacity_j=5_000_000.0, initial_soc=0.80)
        initial_energy = battery.current_energy_j
        
        # Discharge 100 kW for 1 second
        delivered_w, heat_loss_w = battery.step_discharge(100_000.0, dt=1.0)
        self.assertGreater(delivered_w, 0.0)
        self.assertGreater(heat_loss_w, 0.0)
        self.assertLess(battery.current_energy_j, initial_energy)
        self.assertLess(battery.soc, 0.80)

    def test_mgu_k_regulatory_limits(self):
        """Ensure MGU-K deployment does not exceed 120 kW and respects 4.0 MJ per lap cap."""
        self.pu.reset_lap(soc_override=0.85)

        # Request 150 kW (exceeding 120 kW FIA limit)
        _, k_mech_w, _, _ = self.pu.deploy_powertrain(
            speed_mps=60.0, throttle=1.0, k_request_w=150_000.0, dt=0.1
        )
        # Delivered mechanical power must not exceed 120 kW
        self.assertLessEqual(k_mech_w, 120_000.0 + 1e-5)

        # Simulate deploying until 4.0 MJ regulatory cap is exhausted from ES
        # With 120 kW purely from ES: 4.0 MJ / 120 kW = 33.3 seconds
        dt = 0.5
        clipping_occurred = False
        for _ in range(75):
            _, _, _, is_clipping = self.pu.deploy_powertrain(
                speed_mps=70.0, throttle=1.0, k_request_w=120_000.0, dt=dt, allow_direct_mguh=False
            )
            if is_clipping:
                clipping_occurred = True
                break

        self.assertTrue(clipping_occurred, "Power unit should enter clipping/derate after 4MJ ES limit")
        self.assertLessEqual(self.pu.lap_es_deployed_j, 4_000_000.0 + 5000.0)

    def test_mgu_k_harvest_regulatory_limit(self):
        """Verify MGU-K regen is capped at 120 kW and 2.0 MJ per lap into ES."""
        self.pu.reset_lap(soc_override=0.40)

        dt = 0.5
        for _ in range(50):
            self.pu.harvest_braking(brake_power_request_w=200_000.0, dt=dt)

        self.assertLessEqual(self.pu.lap_es_harvested_j, 2_000_000.0 + 5000.0)

    def test_aerodynamics_and_drs(self):
        """Check downforce and DRS drag reduction."""
        speed = 80.0 # ~288 km/h
        drag_normal = self.vehicle.aero.drag(speed, drs_active=False)
        drag_drs = self.vehicle.aero.drag(speed, drs_active=True)
        self.assertLess(drag_drs, drag_normal)
        self.assertAlmostEqual(drag_drs, drag_normal * 0.75, delta=1.0)


if __name__ == "__main__":
    unittest.main()
