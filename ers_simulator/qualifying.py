"""
Formula 1 Qualifying Simulation & Knockout Shootout Engine
==========================================================
Simulates authentic Formula 1 qualifying sessions with:
- Multi-session knockout structure (Q1, Q2, Q3) or shootout format for any number of drivers.
- Track evolution (+0.8% grip in Q2, +1.5% grip in Q3).
- Qualifying engine party modes (+8 kW in Q1, +10 kW in Q2, +12 kW in Q3).
- Low fuel mass configurations (3.8 kg in Q1, 3.5 kg in Q2, 3.2 kg in Q3).
- Softest compound tire lateral grip factor.
- Full ERS Hotlap attack deployment (100% deployment, zero lift & coast).
- Sector purple split detection, speed traps, and elimination brackets.
- Full high-frequency telemetry output for charting any number of drivers.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import numpy as np

from .track import Track, get_circuit
from .driver import DriverProfile, get_driver_preset, list_driver_presets
from .solver import LapSimulator, LapResult, format_lap_time
from .ers_strategy import ERSMode
from .telemetry import TelemetryComparison


@dataclass
class DriverQualiResult:
    """Individual driver qualifying classification and telemetry."""
    driver: DriverProfile
    position: int = 1
    q1_time_s: Optional[float] = None
    q1_str: str = "-"
    q2_time_s: Optional[float] = None
    q2_str: str = "-"
    q3_time_s: Optional[float] = None
    q3_str: str = "-"
    best_lap_s: float = 0.0
    best_lap_str: str = ""
    gap_to_pole_s: float = 0.0
    gap_to_pole_str: str = "+0.000s"
    eliminated_in: Optional[str] = None  # "Q1", "Q2", "Q3", or None (Pole)
    
    # Sector times (best flying lap)
    s1_s: float = 0.0
    s1_str: str = ""
    s2_s: float = 0.0
    s2_str: str = ""
    s3_s: float = 0.0
    s3_str: str = ""
    is_purple_s1: bool = False
    is_purple_s2: bool = False
    is_purple_s3: bool = False
    
    # ERS & Speed Trap Metrics
    top_speed_kmh: float = 0.0
    energy_deployed_mj: float = 0.0
    energy_harvested_mj: float = 0.0
    net_soc_delta_pct: float = 0.0
    derate_time_s: float = 0.0
    derate_pct: float = 0.0
    
    # Underlying telemetry object from the driver's fastest qualifying lap
    best_lap_result: Optional[LapResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.position,
            "position": self.position,
            "code": self.driver.short_code.upper(),
            "name": self.driver.name,
            "team": self.driver.team,
            "color": self.driver.color,
            "number": self.driver.number,
            "q1": self.q1_str,
            "q2": self.q2_str,
            "q3": self.q3_str,
            "best_lap": self.best_lap_str,
            "best_lap_s": round(self.best_lap_s, 3),
            "gap": self.gap_to_pole_str,
            "gap_s": round(self.gap_to_pole_s, 3),
            "eliminated": self.eliminated_in or ("POLE" if self.position == 1 else "Q3"),
            "s1": self.s1_str,
            "s2": self.s2_str,
            "s3": self.s3_str,
            "is_purple_s1": self.is_purple_s1,
            "is_purple_s2": self.is_purple_s2,
            "is_purple_s3": self.is_purple_s3,
            "top_speed": f"{self.top_speed_kmh:.1f} km/h",
            "top_speed_kmh": round(self.top_speed_kmh, 1),
            "energy_deployed_mj": round(self.energy_deployed_mj, 2),
            "energy_harvested_mj": round(self.energy_harvested_mj, 2),
            "net_soc_delta_pct": round(self.net_soc_delta_pct, 1),
            "derate_time_s": round(self.derate_time_s, 2),
            "derate_pct": round(self.derate_pct, 1),
        }


@dataclass
class QualifyingResult:
    """Full qualifying shootout session classification and comparison."""
    track_name: str
    track_length_m: float
    year: int
    num_drivers: int
    sessions_run: List[str]
    grid: List[DriverQualiResult]
    
    # Purple sectors and speed trap records
    purple_s1_s: float = 0.0
    purple_s1_driver: str = ""
    purple_s2_s: float = 0.0
    purple_s2_driver: str = ""
    purple_s3_s: float = 0.0
    purple_s3_driver: str = ""
    speed_trap_kmh: float = 0.0
    speed_trap_driver: str = ""
    
    # High-resolution telemetry comparison of fastest laps
    comparison: Optional[TelemetryComparison] = None

    @property
    def pole_driver(self) -> DriverQualiResult:
        return self.grid[0] if self.grid else None

    @property
    def pole_time_s(self) -> float:
        return self.grid[0].best_lap_s if self.grid else 0.0

    @property
    def pole_time_str(self) -> str:
        return self.grid[0].best_lap_str if self.grid else "0:00.000"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary for web dashboard and API."""
        base_dict = self.comparison.to_dict() if self.comparison else {}
        base_dict.update({
            "mode": "qualifying",
            "track_name": self.track_name,
            "track_length_m": self.track_length_m,
            "year": self.year,
            "num_drivers": self.num_drivers,
            "sessions_run": self.sessions_run,
            "pole_driver": self.pole_driver.driver.name if self.pole_driver else "",
            "pole_code": self.pole_driver.driver.short_code.upper() if self.pole_driver else "",
            "pole_time": self.pole_time_str,
            "purple_s1": {
                "time": format_lap_time(self.purple_s1_s),
                "seconds": round(self.purple_s1_s, 3),
                "driver": self.purple_s1_driver,
            },
            "purple_s2": {
                "time": format_lap_time(self.purple_s2_s),
                "seconds": round(self.purple_s2_s, 3),
                "driver": self.purple_s2_driver,
            },
            "purple_s3": {
                "time": format_lap_time(self.purple_s3_s),
                "seconds": round(self.purple_s3_s, 3),
                "driver": self.purple_s3_driver,
            },
            "speed_trap": {
                "kmh": round(self.speed_trap_kmh, 1),
                "driver": self.speed_trap_driver,
            },
            "grid": [r.to_dict() for r in self.grid],
            "leaderboard": [r.to_dict() for r in self.grid],
        })
        return base_dict

    def to_csv(self) -> str:
        """Export qualifying classification and telemetry to CSV string."""
        lines = [
            f"# FORMULA 1 QUALIFYING RESULTS - {self.track_name.upper()} ({self.year})",
            f"# Pole Position: {self.pole_driver.driver.name} ({self.pole_time_str})",
            f"# Purple Sectors: S1={format_lap_time(self.purple_s1_s)} ({self.purple_s1_driver}), "
            f"S2={format_lap_time(self.purple_s2_s)} ({self.purple_s2_driver}), "
            f"S3={format_lap_time(self.purple_s3_s)} ({self.purple_s3_driver})",
            f"# Speed Trap: {self.speed_trap_kmh:.1f} km/h ({self.speed_trap_driver})",
            "",
            "POS,DRIVER,CODE,TEAM,NUMBER,Q1,Q2,Q3,BEST_LAP,GAP_TO_POLE,ELIMINATED,S1,S2,S3,V_MAX_KMH,DEPLOY_MJ,HARVEST_MJ,NET_SOC_PCT,DERATE_S"
        ]
        for r in self.grid:
            lines.append(
                f"P{r.position},{r.driver.name},{r.driver.short_code.upper()},{r.driver.team},{r.driver.number},"
                f"{r.q1_str},{r.q2_str},{r.q3_str},{r.best_lap_str},{r.gap_to_pole_str},{r.eliminated_in or 'POLE'},"
                f"{r.s1_str},{r.s2_str},{r.s3_str},{r.top_speed_kmh:.1f},{r.energy_deployed_mj:.2f},"
                f"{r.energy_harvested_mj:.2f},{r.net_soc_delta_pct:+.1f},{r.derate_time_s:.2f}"
            )
        
        if self.comparison:
            lines.append("")
            lines.append("# HIGH FREQUENCY TELEMETRY")
            lines.append(self.comparison.to_csv())

        return "\n".join(lines)


class QualifyingSimulator:
    """
    Simulates authentic Formula 1 qualifying sessions.
    Supports any number of drivers (from 1 to full 20+ grid).
    """

    def __init__(self, solver: Optional[LapSimulator] = None):
        self.solver = solver or LapSimulator()

    def simulate(
        self,
        track: Track,
        drivers: List[DriverProfile],
        year: Optional[int] = None,
        dx: float = 2.0,
    ) -> QualifyingResult:
        """
        Run qualifying simulation for any number of drivers.
        
        Session Breakdown:
        - If >= 16 drivers: Standard F1 3-stage Knockout (Q1: eliminate 5, Q2: eliminate 5, Q3: top 10).
        - If 11-15 drivers: 2-stage Knockout (Q1: all run, Q2/Q3: top 10 shootout).
        - If <= 10 drivers: Full 3-phase shootout evolution for all participating drivers.
        """
        if not drivers:
            raise ValueError("Qualifying requires at least 1 driver.")

        sim_year = year if year is not None else getattr(drivers[0], "year", 2024)
        n = len(drivers)

        # Determine session structure based on driver count
        if n >= 16:
            # Standard F1 grid knockout
            q1_elim_count = 5
            q2_elim_count = 5
            sessions = ["Q1", "Q2", "Q3"]
        elif n >= 11:
            q1_elim_count = n - 10
            q2_elim_count = 0
            sessions = ["Q1", "Q2", "Q3"]
        else:
            # 1 to 10 drivers: All drivers participate in the session shootout
            q1_elim_count = 0
            q2_elim_count = 0
            sessions = ["Q1", "Q2", "Q3"] if n > 1 else ["Q1", "Q2", "Q3"]

        # Track results dictionary: code -> DriverQualiResult
        quali_map: Dict[str, DriverQualiResult] = {}
        for d in drivers:
            code = d.short_code.lower()
            d_year = d.for_year(sim_year)
            quali_map[code] = DriverQualiResult(driver=d_year)

        # -------------------------------------------------------------
        # Phase 1: Q1 Session (All drivers run)
        # Fuel: 3.8 kg, Party mode: +8 kW, Tire compound: 1.025 (green track: x1.000)
        # -------------------------------------------------------------
        q1_results: List[Tuple[DriverProfile, LapResult]] = []
        for d in drivers:
            code = d.short_code.lower()
            d_prof = quali_map[code].driver
            res = self.solver.simulate(
                track=track,
                driver=d_prof,
                dx=dx,
                year=sim_year,
                fuel_kg=3.8,
                tire_grip_mult=1.025 * 1.000,
                ice_power_boost_w=8_000.0,
                is_qualifying=True,
            )
            quali_map[code].q1_time_s = res.lap_time_s
            quali_map[code].q1_str = format_lap_time(res.lap_time_s)
            quali_map[code].best_lap_s = res.lap_time_s
            quali_map[code].best_lap_str = quali_map[code].q1_str
            quali_map[code].best_lap_result = res
            self._update_telemetry_metrics(quali_map[code], res)
            q1_results.append((d_prof, res))

        # Sort Q1 by lap time
        q1_results.sort(key=lambda item: item[1].lap_time_s)

        # Q1 Eliminations
        q1_advancing: List[DriverProfile] = []
        if q1_elim_count > 0 and len(q1_results) > 10:
            cutoff = len(q1_results) - q1_elim_count
            q1_advancing = [item[0] for item in q1_results[:cutoff]]
            for item in q1_results[cutoff:]:
                c = item[0].short_code.lower()
                quali_map[c].eliminated_in = "Q1"
        else:
            q1_advancing = [item[0] for item in q1_results]

        # -------------------------------------------------------------
        # Phase 2: Q2 Session (Advancing drivers run)
        # Fuel: 3.5 kg, Party mode: +10 kW, Track rubber-in: x1.008 grip (+0.8%)
        # -------------------------------------------------------------
        q2_results: List[Tuple[DriverProfile, LapResult]] = []
        for d_prof in q1_advancing:
            code = d_prof.short_code.lower()
            res = self.solver.simulate(
                track=track,
                driver=d_prof,
                dx=dx,
                year=sim_year,
                fuel_kg=3.5,
                tire_grip_mult=1.025 * 1.008,
                ice_power_boost_w=10_000.0,
                is_qualifying=True,
            )
            quali_map[code].q2_time_s = res.lap_time_s
            quali_map[code].q2_str = format_lap_time(res.lap_time_s)
            if res.lap_time_s < quali_map[code].best_lap_s:
                quali_map[code].best_lap_s = res.lap_time_s
                quali_map[code].best_lap_str = quali_map[code].q2_str
                quali_map[code].best_lap_result = res
                self._update_telemetry_metrics(quali_map[code], res)
            q2_results.append((d_prof, res))

        # Sort Q2 by lap time
        q2_results.sort(key=lambda item: item[1].lap_time_s)

        # Q2 Eliminations
        q2_advancing: List[DriverProfile] = []
        if q2_elim_count > 0 and len(q2_results) > 10:
            cutoff = len(q2_results) - q2_elim_count
            q2_advancing = [item[0] for item in q2_results[:cutoff]]
            for item in q2_results[cutoff:]:
                c = item[0].short_code.lower()
                quali_map[c].eliminated_in = "Q2"
        else:
            q2_advancing = [item[0] for item in q2_results]

        # -------------------------------------------------------------
        # Phase 3: Q3 Pole Shootout (Top 10 or remaining drivers run)
        # Fuel: 3.2 kg, Maximum Party Mode: +12 kW, Track Rubber-in: x1.015 grip (+1.5%)
        # -------------------------------------------------------------
        q3_results: List[Tuple[DriverProfile, LapResult]] = []
        for d_prof in q2_advancing:
            code = d_prof.short_code.lower()
            res = self.solver.simulate(
                track=track,
                driver=d_prof,
                dx=dx,
                year=sim_year,
                fuel_kg=3.2,
                tire_grip_mult=1.025 * 1.015,
                ice_power_boost_w=12_000.0,
                is_qualifying=True,
            )
            quali_map[code].q3_time_s = res.lap_time_s
            quali_map[code].q3_str = format_lap_time(res.lap_time_s)
            if res.lap_time_s < quali_map[code].best_lap_s:
                quali_map[code].best_lap_s = res.lap_time_s
                quali_map[code].best_lap_str = quali_map[code].q3_str
                quali_map[code].best_lap_result = res
                self._update_telemetry_metrics(quali_map[code], res)
            q3_results.append((d_prof, res))

        # -------------------------------------------------------------
        # Phase 4: Final Grid Classification & Ordering
        # Official F1 rules:
        # - Q3 participants sorted by Q3 times (P1 to P10)
        # - Q2 eliminated drivers sorted by Q2 times (P11 to P15)
        # - Q1 eliminated drivers sorted by Q1 times (P16 to P20)
        # -------------------------------------------------------------
        final_grid_drivers: List[DriverQualiResult] = []

        # Sort Q3 participants
        q3_drivers = [quali_map[item[0].short_code.lower()] for item in q3_results]
        q3_drivers.sort(key=lambda r: (r.q3_time_s if r.q3_time_s is not None else 9999.0))
        final_grid_drivers.extend(q3_drivers)

        # Sort Q2 eliminated
        q2_eliminated = [
            quali_map[c] for c in quali_map
            if quali_map[c].eliminated_in == "Q2" and quali_map[c] not in final_grid_drivers
        ]
        q2_eliminated.sort(key=lambda r: (r.q2_time_s if r.q2_time_s is not None else 9999.0))
        final_grid_drivers.extend(q2_eliminated)

        # Sort Q1 eliminated
        q1_eliminated = [
            quali_map[c] for c in quali_map
            if quali_map[c].eliminated_in == "Q1" and quali_map[c] not in final_grid_drivers
        ]
        q1_eliminated.sort(key=lambda r: (r.q1_time_s if r.q1_time_s is not None else 9999.0))
        final_grid_drivers.extend(q1_eliminated)

        # Any remaining drivers (fallback)
        for c, r in quali_map.items():
            if r not in final_grid_drivers:
                final_grid_drivers.append(r)

        # If no elimination format was active (e.g. <= 10 drivers), sort by best overall lap time
        if q1_elim_count == 0 and q2_elim_count == 0:
            final_grid_drivers.sort(key=lambda r: r.best_lap_s)

        # Calculate pole time and gaps
        pole_time = final_grid_drivers[0].best_lap_s if final_grid_drivers else 0.0

        for rank, r in enumerate(final_grid_drivers, start=1):
            r.position = rank
            gap = r.best_lap_s - pole_time
            r.gap_to_pole_s = max(0.0, gap)
            r.gap_to_pole_str = "POLE" if rank == 1 else f"+{gap:06.3f}s"
            if rank == 1:
                r.eliminated_in = "POLE"

        # Determine Purple Sectors and Overall Speed Trap
        best_s1 = 9999.0
        best_s1_drv = ""
        best_s2 = 9999.0
        best_s2_drv = ""
        best_s3 = 9999.0
        best_s3_drv = ""
        top_speed_val = 0.0
        top_speed_drv = ""

        for r in final_grid_drivers:
            if r.s1_s > 0 and r.s1_s < best_s1:
                best_s1 = r.s1_s
                best_s1_drv = r.driver.short_code.upper()
            if r.s2_s > 0 and r.s2_s < best_s2:
                best_s2 = r.s2_s
                best_s2_drv = r.driver.short_code.upper()
            if r.s3_s > 0 and r.s3_s < best_s3:
                best_s3 = r.s3_s
                best_s3_drv = r.driver.short_code.upper()
            if r.top_speed_kmh > top_speed_val:
                top_speed_val = r.top_speed_kmh
                top_speed_drv = r.driver.short_code.upper()

        # Mark purple sectors on individual drivers
        for r in final_grid_drivers:
            if abs(r.s1_s - best_s1) < 0.001:
                r.is_purple_s1 = True
            if abs(r.s2_s - best_s2) < 0.001:
                r.is_purple_s2 = True
            if abs(r.s3_s - best_s3) < 0.001:
                r.is_purple_s3 = True

        # Build TelemetryComparison for telemetry charts
        lap_results = [r.best_lap_result for r in final_grid_drivers if r.best_lap_result is not None]
        comp = TelemetryComparison(lap_results) if lap_results else None

        return QualifyingResult(
            track_name=track.name,
            track_length_m=track.total_length_m,
            year=sim_year,
            num_drivers=len(final_grid_drivers),
            sessions_run=sessions,
            grid=final_grid_drivers,
            purple_s1_s=best_s1 if best_s1 < 9999.0 else 0.0,
            purple_s1_driver=best_s1_drv,
            purple_s2_s=best_s2 if best_s2 < 9999.0 else 0.0,
            purple_s2_driver=best_s2_drv,
            purple_s3_s=best_s3 if best_s3 < 9999.0 else 0.0,
            purple_s3_driver=best_s3_drv,
            speed_trap_kmh=top_speed_val,
            speed_trap_driver=top_speed_drv,
            comparison=comp,
        )

    def _update_telemetry_metrics(self, q_res: DriverQualiResult, lap: LapResult):
        """Update driver qualifying metrics from their latest best LapResult."""
        q_res.top_speed_kmh = lap.top_speed_kmh
        q_res.energy_deployed_mj = lap.energy_deployed_mj
        q_res.energy_harvested_mj = lap.total_energy_harvested_mj
        q_res.net_soc_delta_pct = lap.net_battery_delta_soc_pct
        q_res.derate_time_s = lap.derate_time_s
        q_res.derate_pct = lap.derate_pct_lap
        
        # Sector splits
        s1 = lap.sector_times.get(1, 0.0)
        s2 = lap.sector_times.get(2, 0.0)
        s3 = lap.sector_times.get(3, 0.0)
        q_res.s1_s = s1
        q_res.s2_s = s2
        q_res.s3_s = s3
        q_res.s1_str = format_lap_time(s1)
        q_res.s2_str = format_lap_time(s2)
        q_res.s3_str = format_lap_time(s3)


def simulate_qualifying_session(
    track_name: str,
    drivers: List[DriverProfile],
    year: Optional[int] = None,
    dx: float = 2.0,
) -> QualifyingResult:
    """Convenience helper to run qualifying simulation."""
    track = get_circuit(track_name)
    sim = QualifyingSimulator()
    return sim.simulate(track=track, drivers=drivers, year=year, dx=dx)
