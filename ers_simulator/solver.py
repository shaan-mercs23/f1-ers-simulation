"""
Formula 1 Quasi-Steady-State Lap Time & ERS Energy Solver
=========================================================
Two-pass forward-backward numerical integration engine:
1. Apex lateral grip & downforce envelope calculation.
2. Backward integration of braking deceleration limits (including driver offset & lift-and-coast).
3. Forward integration of powertrain tractive forces, ERS battery dynamics,
   clipping detection, exhaust heat recovery, and cyclic boundary convergence.
"""

from dataclasses import dataclass, field
import math
import numpy as np
from typing import List, Dict, Optional, Tuple

from .vehicle import F1Vehicle, create_f1_vehicle
from .track import Track, DiscretizedTrack
from .driver import DriverProfile
from .ers_strategy import ERSStrategy, ERSMode


@dataclass
class TelemetryFrame:
    """Instantaneous vehicle state at distance s."""
    distance_m: float
    time_s: float
    speed_kmh: float
    speed_mps: float
    throttle: float
    brake: float
    gear: int
    accel_g: float
    lateral_g: float
    ice_power_kw: float
    mguk_power_kw: float
    mguh_power_kw: float
    battery_soc: float
    battery_temp_c: float
    energy_deployed_mj: float
    energy_harvested_mj: float
    is_clipping: bool
    is_drs: bool
    is_coasting: bool
    sector: int
    corner_label: str


@dataclass
class LapResult:
    """Comprehensive output of a simulated lap."""
    driver: DriverProfile
    track_name: str
    track_length_m: float
    lap_time_s: float
    lap_time_str: str
    sector_times: Dict[int, float]
    top_speed_kmh: float
    min_speed_kmh: float
    avg_speed_kmh: float
    
    # ERS Energy Balance
    energy_deployed_mj: float
    energy_harvested_k_mj: float
    energy_harvested_h_mj: float
    total_energy_harvested_mj: float
    net_battery_delta_soc_pct: float
    final_battery_soc: float
    derate_time_s: float
    derate_distance_m: float
    derate_pct_lap: float
    fuel_consumed_kg: float
    
    # Telemetry Series (numpy arrays for fast analytics & graphing)
    distance: np.ndarray
    time: np.ndarray
    speed_kmh: np.ndarray
    throttle: np.ndarray
    brake: np.ndarray
    gear: np.ndarray
    accel_g: np.ndarray
    lateral_g: np.ndarray
    ice_power_kw: np.ndarray
    mguk_power_kw: np.ndarray
    mguh_power_kw: np.ndarray
    battery_soc: np.ndarray
    battery_temp_c: np.ndarray
    cumulative_deployed_mj: np.ndarray
    cumulative_harvested_mj: np.ndarray
    is_clipping: np.ndarray
    is_drs: np.ndarray
    sector: np.ndarray
    corner_labels: List[str]


def format_lap_time(seconds: float) -> str:
    """Format seconds into M:SS.mmm format."""
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes}:{rem_seconds:06.3f}"


def estimate_gear(speed_kmh: float) -> int:
    """Estimate F1 8-speed seamless gearbox gear from speed."""
    if speed_kmh < 95.0:
        return 1
    elif speed_kmh < 135.0:
        return 2
    elif speed_kmh < 175.0:
        return 3
    elif speed_kmh < 215.0:
        return 4
    elif speed_kmh < 255.0:
        return 5
    elif speed_kmh < 290.0:
        return 6
    elif speed_kmh < 325.0:
        return 7
    else:
        return 8


class LapSimulator:
    """Numerical solver for F1 lap simulation and ERS energy flow."""

    def __init__(self, vehicle: Optional[F1Vehicle] = None):
        self.vehicle_override = vehicle
        self.vehicle = vehicle or F1Vehicle()

    def simulate(
        self,
        track: Track,
        driver: DriverProfile,
        dx: float = 2.0,
        initial_soc_override: Optional[float] = None,
        year: Optional[int] = None,
        fuel_kg: Optional[float] = None,
        tire_grip_mult: float = 1.0,
        ice_power_boost_w: float = 0.0,
        is_qualifying: bool = False,
    ) -> LapResult:
        """
        Execute full lap simulation for given track and driver profile.
        Adapts vehicle mass, aerodynamics, and engine power to the specified year and team.
        Supports qualifying mode (low fuel, engine party mode, soft tire compound).
        """
        sim_year = year if year is not None else getattr(driver, "year", 2024)
        vehicle = self.vehicle_override or create_f1_vehicle(year=sim_year, team=driver.team)

        # Apply qualifying physical overrides if active
        if is_qualifying:
            # Qualifying fuel: ~3.5 kg (out-lap + flying lap + sample)
            vehicle.fuel_mass_kg = fuel_kg if fuel_kg is not None else 3.5
            # Party mode engine boost: +12 kW (~16 hp)
            vehicle.power_unit.ice.peak_power_w += (ice_power_boost_w if ice_power_boost_w != 0.0 else 12_000.0)
            # Softest Pirelli slick compound: +2.5% lateral grip
            effective_grip_mult = tire_grip_mult if tire_grip_mult != 1.0 else 1.025
            # In qualifying, driver runs 100% hotlap deployment and zero lift & coast
            active_driver = driver.copy_with(ers_mode=ERSMode.HOTLAP_QUALI, lift_and_coast_m=0.0)
        else:
            if fuel_kg is not None:
                vehicle.fuel_mass_kg = fuel_kg
            if ice_power_boost_w != 0.0:
                vehicle.power_unit.ice.peak_power_w += ice_power_boost_w
            effective_grip_mult = tire_grip_mult
            active_driver = driver

        disc_track = track.discretize(dx=dx)
        N = len(disc_track.distance_m)
        dist = disc_track.distance_m
        radius = disc_track.radius_m
        drs = disc_track.drs_active
        slope = disc_track.slope_rad
        sector = disc_track.sector
        labels = disc_track.corner_labels

        soc_start = initial_soc_override if initial_soc_override is not None else active_driver.initial_soc
        vehicle.power_unit.reset_lap(soc_override=soc_start)

        # -------------------------------------------------------------------
        # Step 1: Compute Corner Apex Maximum Speed Envelope
        # -------------------------------------------------------------------
        total_grip_factor = active_driver.cornering_grip_factor * effective_grip_mult
        v_apex = np.zeros(N)
        for i in range(N):
            v_apex[i] = vehicle.max_cornering_speed(radius[i], total_grip_factor)

        # -------------------------------------------------------------------
        # Step 2: Backward Pass (Braking limits into corners)
        # -------------------------------------------------------------------
        v_backward = np.copy(v_apex)

        # Run 2 passes to ensure cyclic continuity across start/finish straight
        for _ in range(2):
            for i in range(N - 1, -1, -1):
                next_i = (i + 1) % N
                v_next = v_backward[next_i]
                
                # Deceleration force at v_next
                f_aero_drag = vehicle.aero.drag(v_next, drs_active=drs[i])
                f_tire_brake = active_driver.braking_aggression * vehicle.max_braking_force(v_next)
                f_rr = vehicle.rolling_resistance(v_next)
                f_gravity = vehicle.total_mass_kg * vehicle.gravity * math.sin(slope[i])

                f_decel_total = f_tire_brake + f_aero_drag + f_rr + f_gravity
                a_decel = max(1.0, f_decel_total / vehicle.total_mass_kg)

                # v_prev^2 = v_next^2 + 2 * a * dx
                v_cand = math.sqrt(v_next ** 2 + 2.0 * a_decel * dx)

                # Apply braking offset modifier
                if active_driver.braking_offset_m < 0:
                    v_cand *= (1.0 + min(0.04, abs(active_driver.braking_offset_m) * 0.003))

                v_backward[i] = min(v_backward[i], v_cand)

        # -------------------------------------------------------------------
        # Step 3: Forward Pass (Powertrain, ERS deployment & telemetry)
        # -------------------------------------------------------------------
        # Identify braking markers for Lift & Coast lookahead
        is_approaching_braking = np.zeros(N, dtype=bool)
        dist_to_brake = np.full(N, 9999.0)
        
        # Scan forward to find hard braking points (where v_backward drops sharply)
        for i in range(N):
            lookahead_dist = 0.0
            for k in range(1, int(150.0 / dx)):
                check_i = (i + k) % N
                lookahead_dist += dx
                if v_backward[check_i] < (v_backward[i] - 15.0): # Hard braking ahead
                    dist_to_brake[i] = lookahead_dist
                    if lookahead_dist <= active_driver.lift_and_coast_m:
                        is_approaching_braking[i] = True
                    break

        # Arrays for storing telemetry
        v_final = np.zeros(N)
        t_final = np.zeros(N)
        throttle_arr = np.zeros(N)
        brake_arr = np.zeros(N)
        ice_pwr_arr = np.zeros(N)
        mguk_pwr_arr = np.zeros(N)
        mguh_pwr_arr = np.zeros(N)
        soc_arr = np.zeros(N)
        temp_arr = np.zeros(N)
        clipping_arr = np.zeros(N, dtype=bool)
        coasting_arr = np.zeros(N, dtype=bool)
        accel_g_arr = np.zeros(N)
        lat_g_arr = np.zeros(N)
        gear_arr = np.zeros(N, dtype=int)
        cum_deploy_arr = np.zeros(N)
        cum_harv_arr = np.zeros(N)

        # -------------------------------------------------------------------
        # Step 2b: Cyclic Convergence of Start/Finish Crossing Speed
        # -------------------------------------------------------------------
        # Find the slowest corner apex on the circuit where speed is physically apex-bound
        slowest_idx = int(np.argmin(v_apex))
        v_cycle = np.copy(v_backward)
        v_curr_est = v_apex[slowest_idx]

        # Integrate forward from slowest apex around to the start/finish line
        for step in range(N):
            idx = (slowest_idx + step) % N
            next_idx = (idx + 1) % N
            v_mps_est = max(10.0, v_curr_est)
            
            # Approximate net tractive acceleration
            f_tract = min((vehicle.power_unit.ice.peak_power_w + 100_000.0) / v_mps_est, vehicle.max_traction_force(v_mps_est))
            f_drag = vehicle.aero.drag(v_mps_est, drs_active=drs[idx])
            f_rr = vehicle.rolling_resistance(v_mps_est)
            a_net_est = max(0.1, (f_tract - f_drag - f_rr) / vehicle.total_mass_kg)
            
            v_next_est = math.sqrt(v_mps_est ** 2 + 2.0 * a_net_est * dx)
            v_curr_est = min(v_backward[next_idx], v_next_est)

        # Initial speed at start/finish line is now physically bounded by the final corner exit
        curr_v = min(v_backward[0], v_curr_est)
        curr_t = 0.0
        total_fuel_kg = 0.0

        for i in range(N):
            v_mps = max(10.0, curr_v)
            v_final[i] = v_mps
            t_final[i] = curr_t
            speed_kmh = v_mps * 3.6
            gear_arr[i] = estimate_gear(speed_kmh)

            # Lateral G-force: a_lat = v^2 / R
            r = radius[i]
            lat_g = (v_mps ** 2) / (r * vehicle.gravity) if r < 10000.0 else 0.0
            lat_g_arr[i] = min(6.0, lat_g)

            # Is the vehicle speed limited by corner/braking envelope?
            is_braking_zone = (v_mps >= (v_backward[i] - 0.5)) and (i < N - 1) and (v_backward[(i+1)%N] < v_backward[i])
            is_coasting = is_approaching_braking[i] and not is_braking_zone
            coasting_arr[i] = is_coasting

            # Time increment for this distance segment dx
            # Average velocity across segment
            dt = dx / v_mps

            if is_braking_zone:
                # ----------------- Braking Phase -----------------
                throttle = 0.0
                throttle_arr[i] = 0.0
                
                # Required braking deceleration
                v_target = v_backward[(i + 1) % N]
                req_decel = max(0.0, (v_mps ** 2 - v_target ** 2) / (2.0 * dx))
                req_brake_force = req_decel * vehicle.total_mass_kg
                req_brake_power = req_brake_force * v_mps

                # Regenerative braking via MGU-K
                k_regen_w, friction_w = vehicle.power_unit.harvest_braking(req_brake_power, dt)
                
                mguk_pwr_arr[i] = - (k_regen_w / 1000.0) # Negative indicates regen
                mguh_pwr_arr[i] = 0.0
                ice_pwr_arr[i] = 0.0
                clipping_arr[i] = False
                
                brake_fraction = min(1.0, req_brake_force / max(1.0, vehicle.max_braking_force(v_mps)))
                brake_arr[i] = brake_fraction
                accel_g_arr[i] = - (req_decel / vehicle.gravity)
                
                curr_v = max(10.0, v_target)

            elif is_coasting:
                # ----------------- Lift & Coast Phase -----------------
                # Throttle lifted to 0%, mild MGU-K regen (up to 35 kW) to harvest free energy
                throttle_arr[i] = 0.0
                brake_arr[i] = 0.0
                ice_pwr_arr[i] = 0.0
                
                mild_regen_demand_w = 35_000.0
                k_regen_w, _ = vehicle.power_unit.harvest_braking(mild_regen_demand_w, dt)
                mguk_pwr_arr[i] = - (k_regen_w / 1000.0)
                mguh_pwr_arr[i] = 0.0
                clipping_arr[i] = False

                # Deceleration under aero drag + light regen + rolling resistance
                f_drag = vehicle.aero.drag(v_mps, drs_active=drs[i])
                f_rr = vehicle.rolling_resistance(v_mps)
                f_regen = k_regen_w / v_mps
                f_net_decel = f_drag + f_rr + f_regen
                a_decel = f_net_decel / vehicle.total_mass_kg

                accel_g_arr[i] = - (a_decel / vehicle.gravity)
                next_v_sq = max(10.0 ** 2, v_mps ** 2 - 2.0 * a_decel * dx)
                curr_v = min(v_backward[(i + 1) % N], math.sqrt(next_v_sq))

            else:
                # ----------------- Acceleration Phase -----------------
                brake_arr[i] = 0.0
                # Corner exit throttle modulation based on driver throttle aggression
                # If speed is low, throttle ramps smoothly
                throttle_mult = min(1.0, 0.70 + 0.30 * active_driver.throttle_aggression * (v_mps / 45.0))
                throttle = min(1.0, throttle_mult)
                throttle_arr[i] = throttle

                # Compute ERS MGU-K demand
                k_request_w = ERSStrategy.calculate_deployment_demand(
                    mode=active_driver.ers_mode,
                    speed_mps=v_mps,
                    throttle=throttle,
                    is_drs_zone=drs[i],
                    corner_exit_progress=min(1.0, v_mps / 65.0),
                    cumulative_deployed_j=vehicle.power_unit.lap_es_deployed_j,
                    current_soc=vehicle.power_unit.battery.soc,
                    cutoff_speed_kmh=active_driver.cutoff_speed_kmh,
                    max_power_w=vehicle.power_unit.mgu_k_max_power_w,
                    max_lap_deploy_j=vehicle.power_unit.mgu_k_max_deploy_lap_j,
                )

                ice_w, k_w, h_w, is_clipping = vehicle.power_unit.deploy_powertrain(
                    speed_mps=v_mps,
                    throttle=throttle,
                    k_request_w=k_request_w,
                    dt=dt,
                    allow_direct_mguh=True
                )

                ice_pwr_arr[i] = ice_w / 1000.0
                mguk_pwr_arr[i] = k_w / 1000.0
                mguh_pwr_arr[i] = h_w / 1000.0
                clipping_arr[i] = is_clipping

                if is_clipping:
                    vehicle.power_unit.derate_time_s += dt
                    vehicle.power_unit.derate_distance_m += dx

                # Fuel tracking
                _, fuel_rate = vehicle.power_unit.ice.mechanical_power(v_mps, throttle)
                total_fuel_kg += fuel_rate * dt

                # Tractive force at wheels: F = P / v
                p_total = ice_w + k_w
                f_traction_raw = p_total / v_mps
                f_traction_limit = vehicle.max_traction_force(v_mps)
                f_traction = min(f_traction_raw, f_traction_limit)

                # Resistances
                f_drag = vehicle.aero.drag(v_mps, drs_active=drs[i])
                f_rr = vehicle.rolling_resistance(v_mps)
                f_gravity = vehicle.total_mass_kg * vehicle.gravity * math.sin(slope[i])

                f_net = f_traction - f_drag - f_rr - f_gravity
                a_net = f_net / vehicle.total_mass_kg
                accel_g_arr[i] = a_net / vehicle.gravity

                next_v_sq = max(10.0 ** 2, v_mps ** 2 + 2.0 * a_net * dx)
                next_v = math.sqrt(next_v_sq)

                # Cap by backward envelope
                curr_v = min(v_backward[(i + 1) % N], next_v)

            # Record state
            soc_arr[i] = vehicle.power_unit.battery.soc
            temp_arr[i] = vehicle.power_unit.battery.temperature_c
            cum_deploy_arr[i] = vehicle.power_unit.lap_es_deployed_j / 1_000_000.0
            cum_harv_arr[i] = (vehicle.power_unit.lap_es_harvested_j + vehicle.power_unit.lap_mguh_harvested_j) / 1_000_000.0

            curr_t += dt

        # Sector Times Calculation
        sector_times: Dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0}
        for i in range(N):
            sec = sector[i]
            dt_step = (t_final[i+1] - t_final[i]) if i < N - 1 else (curr_t - t_final[i])
            sector_times[sec] = sector_times.get(sec, 0.0) + dt_step

        lap_time_s = curr_t
        top_speed_kmh = float(np.max(v_final * 3.6))
        min_speed_kmh = float(np.min(v_final * 3.6))
        avg_speed_kmh = float((disc_track.total_length_m / lap_time_s) * 3.6)

        pu = vehicle.power_unit
        net_delta_soc = (pu.battery.soc - soc_start) * 100.0
        derate_pct = (pu.derate_time_s / lap_time_s) * 100.0 if lap_time_s > 0 else 0.0

        return LapResult(
            driver=active_driver,
            track_name=track.name,
            track_length_m=disc_track.total_length_m,
            lap_time_s=lap_time_s,
            lap_time_str=format_lap_time(lap_time_s),
            sector_times=sector_times,
            top_speed_kmh=top_speed_kmh,
            min_speed_kmh=min_speed_kmh,
            avg_speed_kmh=avg_speed_kmh,
            energy_deployed_mj=pu.lap_es_deployed_j / 1_000_000.0,
            energy_harvested_k_mj=pu.lap_es_harvested_j / 1_000_000.0,
            energy_harvested_h_mj=pu.lap_mguh_harvested_j / 1_000_000.0,
            total_energy_harvested_mj=(pu.lap_es_harvested_j + pu.lap_mguh_harvested_j) / 1_000_000.0,
            net_battery_delta_soc_pct=net_delta_soc,
            final_battery_soc=pu.battery.soc,
            derate_time_s=pu.derate_time_s,
            derate_distance_m=pu.derate_distance_m,
            derate_pct_lap=derate_pct,
            fuel_consumed_kg=total_fuel_kg,
            distance=dist,
            time=t_final,
            speed_kmh=v_final * 3.6,
            throttle=throttle_arr,
            brake=brake_arr,
            gear=gear_arr,
            accel_g=accel_g_arr,
            lateral_g=lat_g_arr,
            ice_power_kw=ice_pwr_arr,
            mguk_power_kw=mguk_pwr_arr,
            mguh_power_kw=mguh_pwr_arr,
            battery_soc=soc_arr,
            battery_temp_c=temp_arr,
            cumulative_deployed_mj=cum_deploy_arr,
            cumulative_harvested_mj=cum_harv_arr,
            is_clipping=clipping_arr,
            is_drs=drs,
            sector=sector,
            corner_labels=labels
        )
