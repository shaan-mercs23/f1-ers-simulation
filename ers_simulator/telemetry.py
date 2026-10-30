"""
Telemetry Analysis, Driver Comparison, and Data Export
======================================================
Computes time delta profiles, sector split differences, speed trap telemetry,
energy balance comparisons, and exports to CSV and JSON formats.
"""

from dataclasses import dataclass
import csv
import io
import json
import numpy as np
from typing import List, Dict, Any, Optional

from .solver import LapResult, format_lap_time


@dataclass
class SectorAnalysis:
    """Detailed sector comparison for a single driver."""
    sector_id: int
    sector_time_s: float
    sector_time_str: str
    gap_to_best_s: float
    energy_deployed_mj: float
    energy_harvested_mj: float


@dataclass
class DriverSummary:
    """Consolidated summary for driver comparison leaderboard."""
    rank: int
    driver_name: str
    short_code: str
    team: str
    color: str
    lap_time_s: float
    lap_time_str: str
    gap_to_leader_s: float
    gap_to_leader_str: str
    top_speed_kmh: float
    min_speed_kmh: float
    avg_speed_kmh: float
    energy_deployed_mj: float
    energy_harvested_k_mj: float
    energy_harvested_h_mj: float
    total_energy_harvested_mj: float
    net_battery_delta_soc_pct: float
    final_battery_soc: float
    derate_time_s: float
    derate_distance_m: float
    derate_pct: float
    fuel_consumed_kg: float
    ers_mode: str
    sectors: Dict[int, SectorAnalysis]


class TelemetryComparison:
    """Compares multiple driver lap simulations across speed, delta time, and energy metrics."""

    def __init__(self, results: List[LapResult], reference_driver_code: Optional[str] = None):
        if not results:
            raise ValueError("TelemetryComparison requires at least one LapResult.")
        
        # Sort results by lap time ascending (fastest first)
        self.results = sorted(results, key=lambda r: r.lap_time_s)
        
        # Set reference driver
        if reference_driver_code:
            ref_candidates = [r for r in self.results if r.driver.short_code.lower() == reference_driver_code.lower()]
            self.reference = ref_candidates[0] if ref_candidates else self.results[0]
        else:
            self.reference = self.results[0]

        self.track_name = self.results[0].track_name
        self.distance = self.results[0].distance
        self.leaderboards: List[DriverSummary] = []
        self.delta_times: Dict[str, np.ndarray] = {}
        self._build_comparison()

    def _build_comparison(self):
        """Construct leaderboard and calculate delta time traces."""
        best_lap_s = self.results[0].lap_time_s
        ref_time_series = np.interp(self.distance, self.reference.distance, self.reference.time)

        # Sector bests
        best_sectors = {1: float("inf"), 2: float("inf"), 3: float("inf")}
        for res in self.results:
            for sec_id, t in res.sector_times.items():
                if t < best_sectors[sec_id]:
                    best_sectors[sec_id] = t

        for rank, res in enumerate(self.results, start=1):
            gap_s = res.lap_time_s - best_lap_s
            gap_str = "Leader" if rank == 1 else f"+{gap_s:0.3f}s"

            # Interpolate time onto common distance grid for clean delta time
            res_time_series = np.interp(self.distance, res.distance, res.time)
            delta_trace = res_time_series - ref_time_series
            self.delta_times[res.driver.short_code] = delta_trace

            # Compute sector breakdown
            sec_dict: Dict[int, SectorAnalysis] = {}
            for sec_id in [1, 2, 3]:
                sec_t = res.sector_times.get(sec_id, 0.0)
                sec_gap = sec_t - best_sectors[sec_id]
                
                # Calculate energy in this sector
                sec_mask = (res.sector == sec_id)
                sec_deploy = 0.0
                sec_harv = 0.0
                if np.any(sec_mask):
                    deploy_diff = res.cumulative_deployed_mj[sec_mask]
                    if len(deploy_diff) > 1:
                        sec_deploy = float(deploy_diff[-1] - deploy_diff[0])
                    harv_diff = res.cumulative_harvested_mj[sec_mask]
                    if len(harv_diff) > 1:
                        sec_harv = float(harv_diff[-1] - harv_diff[0])

                sec_dict[sec_id] = SectorAnalysis(
                    sector_id=sec_id,
                    sector_time_s=sec_t,
                    sector_time_str=format_lap_time(sec_t),
                    gap_to_best_s=sec_gap,
                    energy_deployed_mj=max(0.0, sec_deploy),
                    energy_harvested_mj=max(0.0, sec_harv),
                )

            summary = DriverSummary(
                rank=rank,
                driver_name=res.driver.name,
                short_code=res.driver.short_code,
                team=res.driver.team,
                color=res.driver.color,
                lap_time_s=res.lap_time_s,
                lap_time_str=res.lap_time_str,
                gap_to_leader_s=gap_s,
                gap_to_leader_str=gap_str,
                top_speed_kmh=round(res.top_speed_kmh, 1),
                min_speed_kmh=round(res.min_speed_kmh, 1),
                avg_speed_kmh=round(res.avg_speed_kmh, 1),
                energy_deployed_mj=round(res.energy_deployed_mj, 3),
                energy_harvested_k_mj=round(res.energy_harvested_k_mj, 3),
                energy_harvested_h_mj=round(res.energy_harvested_h_mj, 3),
                total_energy_harvested_mj=round(res.total_energy_harvested_mj, 3),
                net_battery_delta_soc_pct=round(res.net_battery_delta_soc_pct, 1),
                final_battery_soc=round(res.final_battery_soc, 3),
                derate_time_s=round(res.derate_time_s, 2),
                derate_distance_m=round(res.derate_distance_m, 1),
                derate_pct=round(res.derate_pct_lap, 1),
                fuel_consumed_kg=round(res.fuel_consumed_kg, 2),
                ers_mode=res.driver.ers_mode.value,
                sectors=sec_dict,
            )
            self.leaderboards.append(summary)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire comparison to JSON-serializable dictionary."""
        data = {
            "track_name": self.track_name,
            "track_length_m": float(self.reference.track_length_m),
            "reference_driver": self.reference.driver.short_code,
            "leaderboard": [],
            "distance_m": [round(float(d), 1) for d in self.distance],
            "corner_labels": self.reference.corner_labels,
            "drivers": {}
        }

        for s in self.leaderboards:
            data["leaderboard"].append({
                "rank": s.rank,
                "name": s.driver_name,
                "code": s.short_code,
                "team": s.team,
                "color": s.color,
                "lap_time": s.lap_time_str,
                "gap": s.gap_to_leader_str,
                "top_speed": s.top_speed_kmh,
                "avg_speed": s.avg_speed_kmh,
                "energy_deployed_mj": s.energy_deployed_mj,
                "energy_harvested_mj": s.total_energy_harvested_mj,
                "net_soc_delta_pct": s.net_battery_delta_soc_pct,
                "final_soc": round(s.final_battery_soc * 100, 1),
                "derate_time_s": s.derate_time_s,
                "derate_pct": s.derate_pct,
                "ers_mode": s.ers_mode,
                "s1": s.sectors[1].sector_time_str,
                "s2": s.sectors[2].sector_time_str,
                "s3": s.sectors[3].sector_time_str,
            })

        # Downsample for web/json transport if length > 1200
        step = max(1, len(self.distance) // 800)
        downsampled_dist = [round(float(self.distance[i]), 1) for i in range(0, len(self.distance), step)]
        data["downsampled_distance_m"] = downsampled_dist

        for res in self.results:
            code_lower = res.driver.short_code.lower()
            code_upper = res.driver.short_code.upper()
            delta_tr = self.delta_times[res.driver.short_code]
            
            drv_payload = {
                "name": res.driver.name,
                "team": res.driver.team,
                "color": res.driver.color,
                "number": res.driver.number,
                "time": [round(float(res.time[i]), 3) for i in range(0, len(res.time), step)],
                "distance": [round(float(res.distance[i]), 1) for i in range(0, len(res.distance), step)],
                "speed_kmh": [round(float(res.speed_kmh[i]), 1) for i in range(0, len(res.speed_kmh), step)],
                "gear": [int(res.gear[i]) for i in range(0, len(res.gear), step)],
                "throttle": [round(float(res.throttle[i]), 2) for i in range(0, len(res.throttle), step)],
                "brake": [round(float(res.brake[i]), 2) for i in range(0, len(res.brake), step)],
                "delta_time_s": [round(float(delta_tr[i]), 3) for i in range(0, len(delta_tr), step)],
                "battery_soc_pct": [round(float(res.battery_soc[i] * 100.0), 1) for i in range(0, len(res.battery_soc), step)],
                "mguk_power_kw": [round(float(res.mguk_power_kw[i]), 1) for i in range(0, len(res.mguk_power_kw), step)],
                "mguh_power_kw": [round(float(res.mguh_power_kw[i]), 1) for i in range(0, len(res.mguh_power_kw), step)],
                "energy_deployed_mj": [round(float(res.cumulative_deployed_mj[i]), 3) for i in range(0, len(res.cumulative_deployed_mj), step)],
                "energy_harvested_mj": [round(float(res.cumulative_harvested_mj[i]), 3) for i in range(0, len(res.cumulative_harvested_mj), step)],
                "is_clipping": [bool(res.is_clipping[i]) for i in range(0, len(res.is_clipping), step)],
                "is_drs": [bool(res.is_drs[i]) for i in range(0, len(res.is_drs), step)],
                "accel_g": [round(float(res.accel_g[i]), 2) for i in range(0, len(res.accel_g), step)],
                "lateral_g": [round(float(res.lateral_g[i]), 2) for i in range(0, len(res.lateral_g), step)],
            }
            # Provide under both lowercase and uppercase for robust frontend lookup
            data["drivers"][code_lower] = drv_payload
            data["drivers"][code_upper] = drv_payload

        return data

    def to_csv(self) -> str:
        """Export telemetry traces into a CSV table."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = ["Distance_m", "Corner"]
        for res in self.results:
            code = res.driver.short_code
            headers.extend([
                f"{code}_Speed_kmh",
                f"{code}_Throttle",
                f"{code}_Brake",
                f"{code}_Delta_s",
                f"{code}_SoC_pct",
                f"{code}_MGUK_kW",
                f"{code}_MGUH_kW",
                f"{code}_Clipping",
            ])
        writer.writerow(headers)

        for i in range(len(self.distance)):
            row = [f"{self.distance[i]:.1f}", self.reference.corner_labels[i]]
            for res in self.results:
                code = res.driver.short_code
                delta_val = self.delta_times[code][i]
                row.extend([
                    f"{res.speed_kmh[i]:.1f}",
                    f"{res.throttle[i]:.2f}",
                    f"{res.brake[i]:.2f}",
                    f"{delta_val:+.3f}",
                    f"{res.battery_soc[i]*100.0:.1f}",
                    f"{res.mguk_power_kw[i]:.1f}",
                    f"{res.mguh_power_kw[i]:.1f}",
                    "1" if res.is_clipping[i] else "0",
                ])
            writer.writerow(row)

        return output.getvalue()
