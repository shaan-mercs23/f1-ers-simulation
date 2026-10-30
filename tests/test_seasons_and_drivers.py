"""
Unit tests for Multi-Season Track Calendar and Complete Driver Roster.
"""

import unittest
from ers_simulator.track import list_seasons, list_circuits, get_circuit
from ers_simulator.driver import list_driver_presets, get_driver_preset, list_seasons_drivers
from ers_simulator.solver import LapSimulator


class TestSeasonsAndDrivers(unittest.TestCase):
    def test_seasons_list(self):
        """Verify seasons from 2020 to 2025 are available."""
        seasons = list_seasons()
        for yr in [2020, 2021, 2022, 2023, 2024, 2025]:
            self.assertIn(yr, seasons)

    def test_tracks_by_year(self):
        """Verify calendars have correct rounds and key tracks."""
        cal_2024 = list_circuits(year=2024)
        self.assertGreaterEqual(len(cal_2024), 14)
        
        # Check round numbering and presence of Monza
        track_ids_2024 = [t["id"] for t in cal_2024]
        self.assertIn("monza", track_ids_2024)
        self.assertIn("silverstone", track_ids_2024)
        self.assertIn("spa", track_ids_2024)
        self.assertIn("baku", track_ids_2024)
        self.assertIn("lasvegas", track_ids_2024)

    def test_complete_driver_grid_2024(self):
        """Verify all drivers from 2024 grid exist with team and traits."""
        drivers_2024 = list_driver_presets(year=2024)
        codes_2024 = {d["code"].lower() for d in drivers_2024}
        
        expected_drivers = [
            "ver", "per", "ham", "rus", "lec", "sai", "nor", "pia",
            "alo", "str", "gas", "oco", "alb", "col", "hul", "mag",
            "tsu", "ric", "bot", "zho"
        ]
        for exp in expected_drivers:
            self.assertIn(exp, codes_2024, f"Driver {exp} should be in 2024 grid")

    def test_driver_year_adaptation(self):
        """Verify driver adapts team and color depending on year (e.g. Hamilton / Sainz / Alonso)."""
        ham_2024 = get_driver_preset("ham", year=2024)
        self.assertEqual(ham_2024.team, "Mercedes")
        self.assertEqual(ham_2024.color, "#00D2BE")

        ham_2025 = get_driver_preset("ham", year=2025)
        self.assertEqual(ham_2025.team, "Ferrari")
        self.assertEqual(ham_2025.color, "#E80020")

        sai_2024 = get_driver_preset("sai", year=2024)
        self.assertEqual(sai_2024.team, "Ferrari")

        sai_2025 = get_driver_preset("sai", year=2025)
        self.assertEqual(sai_2025.team, "Williams")

    def test_simulate_different_tracks(self):
        """Simulate on diverse circuits: Baku (long straight) and Monaco (tight street)."""
        sim = LapSimulator()
        ver = get_driver_preset("ver")

        # Simulate Baku
        baku = get_circuit("baku")
        res_baku = sim.simulate(baku, ver, dx=4.0)
        self.assertGreater(res_baku.top_speed_kmh, 340.0)
        self.assertGreater(res_baku.lap_time_s, 85.0)
        self.assertLess(res_baku.lap_time_s, 110.0)

        # Simulate Monaco
        monaco = get_circuit("monaco")
        res_monaco = sim.simulate(monaco, ver, dx=4.0)
        self.assertLess(res_monaco.top_speed_kmh, 335.0)
        self.assertGreater(res_monaco.top_speed_kmh, 280.0)
        self.assertLess(res_monaco.lap_time_s, 85.0)

    def test_lap_times_change_by_year(self):
        """Verify that car weight and technical regulations cause lap times to vary across seasons."""
        sim = LapSimulator()
        monza = get_circuit("monza")
        
        # In 2020: 746kg lightweight car + peak bargeboards
        ver_2020 = get_driver_preset("ver", year=2020)
        res_2020 = sim.simulate(monza, ver_2020, year=2020, dx=4.0)

        # In 2022: 798kg heavy car + early ground effect reset (+46kg heavier)
        ver_2022 = get_driver_preset("ver", year=2022)
        res_2022 = sim.simulate(monza, ver_2022, year=2022, dx=4.0)

        # In 2024: 798kg mature ground effect refinement
        ver_2024 = get_driver_preset("ver", year=2024)
        res_2024 = sim.simulate(monza, ver_2024, year=2024, dx=4.0)

        # 2020 lightweight car must be faster than the 2022 early ground-effect reset
        self.assertLess(res_2020.lap_time_s, res_2022.lap_time_s)
        self.assertGreater(res_2022.lap_time_s - res_2020.lap_time_s, 1.5)

        # 2024 mature development must be faster than 2022 early ground effect
        self.assertLess(res_2024.lap_time_s, res_2022.lap_time_s)


if __name__ == "__main__":
    unittest.main()
