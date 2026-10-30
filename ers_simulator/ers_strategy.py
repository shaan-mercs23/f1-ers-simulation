"""
Formula 1 ERS Harvesting and Deployment Strategies
===================================================
Models strategic energy management modes:
- HOTLAP_QUALI: Unrestricted 120 kW deployment until 4MJ cap or battery runs dry (clipping).
- RACE_BALANCED: Delta-zero energy deployment prioritizing corner exits below aerodynamic cutoff.
- OVERTAKE_PUSH: Tactical hoarding in twisty sectors with full blast on DRS passing straights.
- RECHARGE_HARVEST: Battery replenishment mode for in-laps or preparing for a push lap.
- OPTIMAL_DYNAMIC: Sensitivity-based Pontryagin energy distribution for maximum lap time gain.
"""

from enum import Enum
import math
from typing import Tuple


class ERSMode(str, Enum):
    HOTLAP_QUALI = "hotlap_quali"
    RACE_BALANCED = "race_balanced"
    OVERTAKE_PUSH = "overtake_push"
    RECHARGE_HARVEST = "recharge_harvest"
    OPTIMAL_DYNAMIC = "optimal_dynamic"


class ERSStrategy:
    """Calculates instantaneous MGU-K power demand based on driving state, track, and mode."""

    @staticmethod
    def calculate_deployment_demand(
        mode: ERSMode,
        speed_mps: float,
        throttle: float,
        is_drs_zone: bool,
        corner_exit_progress: float,  # [0.0, 1.0] 1.0 = fully straight
        cumulative_deployed_j: float,
        current_soc: float,
        cutoff_speed_kmh: float = 295.0,
        max_power_w: float = 120_000.0,
        max_lap_deploy_j: float = 4_000_000.0,
    ) -> float:
        """
        Calculate requested MGU-K mechanical deployment power (Watts).
        
        Args:
            mode: ERS deployment mode.
            speed_mps: Vehicle speed (m/s).
            throttle: Throttle position [0.0, 1.0].
            is_drs_zone: Whether car is in a DRS passing zone.
            corner_exit_progress: Progress out of corner towards next straight.
            cumulative_deployed_j: Total Joules deployed so far this lap.
            current_soc: Battery state of charge [0.0, 1.0].
            cutoff_speed_kmh: Speed above which balanced mode cuts deployment.
            max_power_w: Maximum MGU-K output (120 kW).
            max_lap_deploy_j: Regulatory 4.0 MJ limit.
            
        Returns:
            Requested MGU-K power in Watts.
        """
        if throttle <= 0.05 or current_soc <= 0.15 or cumulative_deployed_j >= max_lap_deploy_j:
            return 0.0

        speed_kmh = speed_mps * 3.6
        cutoff_mps = cutoff_speed_kmh / 3.6

        if mode == ERSMode.HOTLAP_QUALI:
            # Full 120 kW deployment on any throttle demand until 4MJ or empty
            return max_power_w * throttle

        elif mode == ERSMode.RACE_BALANCED:
            # High deployment at low speeds where delta-time impact is greatest (a = P/(m*v))
            # Taper off as car reaches top speed to conserve battery and eliminate derate
            if speed_mps < 45.0:  # < 162 km/h
                factor = 1.0
            elif speed_mps < cutoff_mps:
                # Smooth cosine decay down to 25% power
                progress = (speed_mps - 45.0) / max(1.0, (cutoff_mps - 45.0))
                factor = 0.25 + 0.75 * 0.5 * (1.0 + math.cos(math.pi * progress))
            else:
                # Above cutoff speed, only deploy direct MGU-H power (~20-30 kW) to prevent battery drain
                factor = 0.15
            return max_power_w * factor * throttle

        elif mode == ERSMode.OVERTAKE_PUSH:
            # In DRS or major overtaking zones, dump full 120 kW boost
            if is_drs_zone:
                return max_power_w * throttle
            # On corner exits leading to short straights, deploy moderate power
            if speed_mps < 50.0:
                return max_power_w * 0.70 * throttle
            # Conserve heavily elsewhere
            return max_power_w * 0.20 * throttle

        elif mode == ERSMode.RECHARGE_HARVEST:
            # Battery recharge lap: minimal deployment (only low speed traction support)
            if speed_mps < 40.0:
                return max_power_w * 0.35 * throttle
            return 0.0

        elif mode == ERSMode.OPTIMAL_DYNAMIC:
            # Pontryagin energy sensitivity allocation:
            # Benefit of extra power d(dt)/dE is proportional to 1 / (v^2)
            # Low speed = huge benefit; high speed = low benefit
            base_ratio = (30.0 / max(15.0, speed_mps)) ** 1.8
            factor = min(1.0, max(0.20, base_ratio))
            
            # If in DRS zone, maintain high top-end boost
            if is_drs_zone:
                factor = max(factor, 0.85)

            return max_power_w * factor * throttle

        return max_power_w * throttle

    @staticmethod
    def calculate_lift_and_coast(
        distance_to_braking_marker_m: float,
        lift_and_coast_window_m: float
    ) -> Tuple[float, bool]:
        """
        Determine throttle position and lift-and-coast flag.
        
        Returns:
            Tuple of (effective_throttle, is_coasting).
        """
        if lift_and_coast_window_m <= 1.0:
            return 1.0, False
        
        if 0.0 <= distance_to_braking_marker_m <= lift_and_coast_window_m:
            # Coasting: lift completely off throttle
            return 0.0, True
        
        return 1.0, False
