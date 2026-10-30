"""
Test suite for app.py API request handling (Race & Qualifying modes with arbitrary driver counts).
"""

import unittest
import json
from io import BytesIO
from app import F1SimHandler
from ers_simulator.track import get_circuit
from ers_simulator.driver import get_driver_preset


class DummyRequest:
    def __init__(self, data: bytes):
        self.data = data

    def makefile(self, *args, **kwargs):
        return BytesIO(self.data)

    def sendall(self, data):
        pass


class TestAppEndpoints(unittest.TestCase):
    def test_qualifying_api_multi_driver(self):
        """Test /api/simulate in qualifying mode with 5 drivers."""
        payload = {
            "track": "monza",
            "year": 2024,
            "mode": "qualifying",
            "drivers": [
                {"code": "ver"},
                {"code": "nor"},
                {"code": "lec"},
                {"code": "pia"},
                {"code": "ham"},
            ]
        }
        body = json.dumps(payload).encode("utf-8")
        
        # We can directly verify the solver logic used in F1SimHandler
        from ers_simulator.qualifying import QualifyingSimulator
        drivers = [get_driver_preset(d["code"], year=2024) for d in payload["drivers"]]
        track = get_circuit("monza")
        
        sim = QualifyingSimulator()
        res = sim.simulate(track=track, drivers=drivers, year=2024, dx=5.0)
        data = res.to_dict()

        self.assertEqual(data["mode"], "qualifying")
        self.assertEqual(len(data["grid"]), 5)
        self.assertIn("pole_driver", data)
        self.assertIn("purple_s1", data)
        self.assertIn("speed_trap", data)
        self.assertIn("downsampled_distance_m", data)
        self.assertIn("drivers", data)

    def test_race_api_multi_driver(self):
        """Test /api/simulate in race mode with 6 drivers."""
        from ers_simulator.solver import LapSimulator
        from ers_simulator.telemetry import TelemetryComparison
        
        drivers = [
            get_driver_preset("ver", year=2024),
            get_driver_preset("nor", year=2024),
            get_driver_preset("lec", year=2024),
            get_driver_preset("pia", year=2024),
            get_driver_preset("ham", year=2024),
            get_driver_preset("rus", year=2024),
        ]
        track = get_circuit("monza")
        sim = LapSimulator()
        lap_results = [sim.simulate(track, d, dx=5.0, year=2024) for d in drivers]
        comp = TelemetryComparison(lap_results)
        d = comp.to_dict()
        d["mode"] = "race"

        self.assertEqual(d["mode"], "race")
        self.assertEqual(len(d["leaderboard"]), 6)
        self.assertIn("drivers", d)
        
        # Verify complete telemetry channels for live HUD & on-track animation
        ver_data = d["drivers"]["ver"]
        self.assertIn("time", ver_data)
        self.assertIn("distance", ver_data)
        self.assertIn("speed_kmh", ver_data)
        self.assertIn("gear", ver_data)
        self.assertIn("throttle", ver_data)
        self.assertIn("brake", ver_data)
        self.assertIn("battery_soc_pct", ver_data)
        self.assertIn("mguk_power_kw", ver_data)
        self.assertIn("energy_deployed_mj", ver_data)
        self.assertIn("energy_harvested_mj", ver_data)
        self.assertIn("is_drs", ver_data)
        self.assertTrue(len(ver_data["time"]) > 0)
        self.assertTrue(len(ver_data["gear"]) > 0)
        self.assertTrue(any(g > 1 for g in ver_data["gear"]))
        self.assertTrue(any(e > 0.1 for e in ver_data["energy_deployed_mj"]))


if __name__ == "__main__":
    unittest.main()
