"""
Formula 1 Vehicle, Aerodynamics, and Power Unit (ICE + MGU-K + MGU-H + Energy Store)
=====================================================================================
Accurate longitudinal vehicle dynamics, powertrain limits, and energy balance according
to FIA Formula 1 Technical Regulations.
"""

from dataclasses import dataclass, field
import math
from typing import Tuple, Dict, List, Optional, Any


@dataclass
class EngineCharacteristics:
    """Internal Combustion Engine (ICE) 1.6L V6 Turbocharged specifications."""
    peak_power_w: float = 590_000.0        # Peak mechanical power (~791 hp)
    max_fuel_flow_kg_h: float = 100.0      # FIA limit: 100 kg/h above 10,500 rpm
    fuel_lhv_j_kg: float = 44_000_000.0    # Lower heating value of F1 fuel (44 MJ/kg)
    thermal_efficiency: float = 0.50       # Peak thermal efficiency (~50%)
    idle_rpm: float = 4000.0
    max_rpm: float = 15000.0
    power_rpm_sweetspot: float = 12000.0

    def mechanical_power(self, speed_mps: float, throttle: float) -> Tuple[float, float]:
        """
        Calculate ICE mechanical power output and fuel consumption.
        
        Args:
            speed_mps: Vehicle forward velocity (m/s).
            throttle: Throttle position [0.0, 1.0].
            
        Returns:
            Tuple of (power_watts, fuel_flow_kg_per_sec).
        """
        if throttle <= 0.01 or speed_mps <= 1.0:
            return 0.0, 0.0005  # Minimal idle fuel
        
        # Effective speed ratio across 8-speed gearbox simulation
        # At very low speed (< 25 m/s), 1st/2nd gear traction & RPM ramp-up
        speed_factor = min(1.0, 0.45 + 0.55 * math.tanh(speed_mps / 20.0))
        
        # High-speed aerodynamic & 8th-gear rev limiter roll-off (terminal F1 speed ~355-365 km/h)
        # Above 90 m/s (~324 km/h), engine approaches 14,000+ rpm with increasing frictional loss
        if speed_mps > 88.0:
            overspeed_penalty = max(0.60, 1.0 - 0.015 * (speed_mps - 88.0) ** 1.3)
            speed_factor *= overspeed_penalty

        power = self.peak_power_w * throttle * speed_factor
        
        # Fuel flow limited by FIA 100 kg/h = 0.02778 kg/s
        fuel_flow = (self.max_fuel_flow_kg_h / 3600.0) * throttle * speed_factor
        return power, fuel_flow


@dataclass
class EnergyStore:
    """
    Energy Store (ES / Battery Pack) model.
    Models capacity, State-of-Charge (SoC), internal resistance heating, and thermal state.
    """
    total_capacity_j: float = 5_000_000.0  # 5.0 MJ total battery capacity (~1.39 kWh)
    usable_capacity_j: float = 4_000_000.0 # 4.0 MJ usable window
    initial_soc: float = 0.85              # Initial State of Charge (85%)
    min_soc: float = 0.15                  # Safety lower limit (15%)
    max_soc: float = 0.95                  # Safety upper limit (95%)
    internal_resistance_ohm: float = 0.08  # Internal resistance
    nominal_voltage_v: float = 750.0       # DC bus voltage
    ambient_temp_c: float = 25.0           # Ambient temperature (°C)
    cell_thermal_mass_j_k: float = 18_000.0# Thermal mass
    cooling_coeff_w_k: float = 45.0        # Liquid cooling efficiency

    current_energy_j: float = field(init=False)
    soc: float = field(init=False)
    temperature_c: float = field(init=False)
    total_joules_lost_heat: float = field(init=False, default=0.0)

    def __post_init__(self):
        self.reset()

    def reset(self, soc_override: float = None):
        """Reset battery state."""
        self.soc = self.initial_soc if soc_override is None else soc_override
        self.current_energy_j = self.soc * self.total_capacity_j
        self.temperature_c = self.ambient_temp_c
        self.total_joules_lost_heat = 0.0

    def can_deploy(self) -> bool:
        """Check if battery has sufficient energy above minimum SoC."""
        return self.soc > self.min_soc

    def can_harvest(self) -> bool:
        """Check if battery has room below maximum SoC."""
        return self.soc < self.max_soc

    def step_discharge(self, electrical_watts: float, dt: float) -> Tuple[float, float]:
        """
        Discharge battery by electrical_watts for dt seconds.
        Accounts for I^2 * R ohmic losses and thermal rise.
        
        Returns:
            Tuple of (effective_delivered_watts, heat_loss_watts).
        """
        if electrical_watts <= 0.0 or not self.can_deploy():
            self._cool(dt)
            return 0.0, 0.0
        
        # Current = P / V
        current_a = electrical_watts / self.nominal_voltage_v
        i2r_loss = (current_a ** 2) * self.internal_resistance_ohm
        total_drain_watts = electrical_watts + i2r_loss
        joules_needed = total_drain_watts * dt

        # Cap by available usable energy
        available_joules = max(0.0, self.current_energy_j - (self.min_soc * self.total_capacity_j))
        if joules_needed > available_joules:
            ratio = available_joules / (joules_needed + 1e-9)
            electrical_watts *= ratio
            i2r_loss *= ratio
            joules_needed = available_joules

        self.current_energy_j = max(0.0, self.current_energy_j - joules_needed)
        self.soc = self.current_energy_j / self.total_capacity_j
        self.total_joules_lost_heat += i2r_loss * dt
        self._update_temp(i2r_loss, dt)

        return electrical_watts, i2r_loss

    def step_charge(self, electrical_watts: float, dt: float) -> Tuple[float, float]:
        """
        Charge battery by electrical_watts for dt seconds.
        
        Returns:
            Tuple of (effective_stored_watts, heat_loss_watts).
        """
        if electrical_watts <= 0.0 or not self.can_harvest():
            self._cool(dt)
            return 0.0, 0.0

        current_a = electrical_watts / self.nominal_voltage_v
        i2r_loss = (current_a ** 2) * self.internal_resistance_ohm
        net_charge_watts = max(0.0, electrical_watts - i2r_loss)
        joules_in = net_charge_watts * dt

        room_joules = max(0.0, (self.max_soc * self.total_capacity_j) - self.current_energy_j)
        if joules_in > room_joules:
            ratio = room_joules / (joules_in + 1e-9)
            joules_in = room_joules
            net_charge_watts *= ratio
            i2r_loss *= ratio

        self.current_energy_j = min(self.total_capacity_j, self.current_energy_j + joules_in)
        self.soc = self.current_energy_j / self.total_capacity_j
        self.total_joules_lost_heat += i2r_loss * dt
        self._update_temp(i2r_loss, dt)

        return net_charge_watts, i2r_loss

    def _update_temp(self, heat_loss_watts: float, dt: float):
        cooling_watts = self.cooling_coeff_w_k * (self.temperature_c - self.ambient_temp_c)
        net_heat = (heat_loss_watts - cooling_watts) * dt
        delta_t = net_heat / self.cell_thermal_mass_j_k
        self.temperature_c += delta_t

    def _cool(self, dt: float):
        cooling_watts = self.cooling_coeff_w_k * (self.temperature_c - self.ambient_temp_c)
        delta_t = -(cooling_watts * dt) / self.cell_thermal_mass_j_k
        self.temperature_c += delta_t


@dataclass
class F1PowerUnit:
    """
    Complete Formula 1 Hybrid Power Unit with ERS.
    - ICE (Internal Combustion Engine)
    - MGU-K (Kinetic Energy Recovery, 120 kW limit, 4MJ deploy cap, 2MJ harvest cap)
    - MGU-H (Heat Energy Recovery from Turbo, unlimited energy, direct DC feed to MGU-K)
    - Energy Store (ES Battery)
    """
    ice: EngineCharacteristics = field(default_factory=EngineCharacteristics)
    battery: EnergyStore = field(default_factory=EnergyStore)

    # FIA Regulatory Limits (per lap)
    mgu_k_max_power_w: float = 120_000.0      # 120 kW (~161 hp)
    mgu_k_max_deploy_lap_j: float = 4_000_000.0  # 4.0 MJ per lap from ES to MGU-K
    mgu_k_max_harvest_lap_j: float = 2_000_000.0 # 2.0 MJ per lap from MGU-K to ES
    
    # Efficiencies
    mgu_k_motor_eff: float = 0.96             # Electrical to mechanical
    mgu_k_gen_eff: float = 0.95               # Mechanical to electrical
    mgu_h_gen_eff: float = 0.92               # Exhaust enthalpy to electrical
    mgu_h_peak_power_w: float = 52_000.0      # Peak continuous harvest (~52 kW)

    # Lap Accumulators
    lap_es_deployed_j: float = field(init=False, default=0.0)
    lap_es_harvested_j: float = field(init=False, default=0.0)
    lap_mguh_harvested_j: float = field(init=False, default=0.0)
    lap_mguh_direct_to_k_j: float = field(init=False, default=0.0)
    derate_time_s: float = field(init=False, default=0.0)
    derate_distance_m: float = field(init=False, default=0.0)

    def __post_init__(self):
        self.reset_lap()

    def reset_lap(self, soc_override: float = None):
        """Reset per-lap regulatory tracking and battery."""
        self.lap_es_deployed_j = 0.0
        self.lap_es_harvested_j = 0.0
        self.lap_mguh_harvested_j = 0.0
        self.lap_mguh_direct_to_k_j = 0.0
        self.derate_time_s = 0.0
        self.derate_distance_m = 0.0
        if soc_override is not None:
            self.battery.reset(soc_override)

    def get_mguh_harvest(self, speed_mps: float, throttle: float) -> float:
        """
        Calculate MGU-H electrical power generated from exhaust gases.
        Depends on engine throttle load and exhaust enthalpy flow.
        """
        if throttle < 0.3 or speed_mps < 15.0:
            return 0.0
        
        # At full throttle and high vehicle speed, exhaust flow is maximal
        throttle_factor = (throttle - 0.3) / 0.7
        speed_factor = min(1.0, speed_mps / 65.0)
        power_w = self.mgu_h_peak_power_w * (throttle_factor ** 1.3) * speed_factor * self.mgu_h_gen_eff
        return power_w

    def deploy_powertrain(
        self,
        speed_mps: float,
        throttle: float,
        k_request_w: float,
        dt: float,
        allow_direct_mguh: bool = True
    ) -> Tuple[float, float, float, bool]:
        """
        Deploy ICE and MGU-K power.
        
        Args:
            speed_mps: Vehicle velocity (m/s).
            throttle: Throttle demand [0.0, 1.0].
            k_request_w: Requested MGU-K mechanical power (0 to 120 kW).
            dt: Time step (seconds).
            allow_direct_mguh: Whether direct MGU-H -> MGU-K DC bus feed is active.
            
        Returns:
            Tuple of:
                - ice_mech_w: Mechanical power from ICE.
                - mguk_mech_w: Mechanical power delivered by MGU-K.
                - mguh_gen_w: Electrical power generated by MGU-H.
                - is_clipping: True if MGU-K was restricted due to 4MJ limit or battery depletion (derate).
        """
        ice_mech_w, _ = self.ice.mechanical_power(speed_mps, throttle)
        mguh_gen_w = self.get_mguh_harvest(speed_mps, throttle)
        self.lap_mguh_harvested_j += mguh_gen_w * dt

        # Cap MGU-K demand to regulatory 120 kW
        k_request_w = max(0.0, min(self.mgu_k_max_power_w, k_request_w * throttle))
        
        # Check regulatory 4.0 MJ limit from ES
        remaining_es_budget_j = max(0.0, self.mgu_k_max_deploy_lap_j - self.lap_es_deployed_j)
        battery_ok = self.battery.can_deploy()

        is_clipping = False
        mguk_mech_w = 0.0

        if k_request_w > 0.0:
            # First pathway: Direct MGU-H feed (unlimited by 4MJ rule!)
            direct_h_power_w = 0.0
            if allow_direct_mguh and mguh_gen_w > 0.0:
                direct_h_power_w = min(k_request_w, mguh_gen_w)
                self.lap_mguh_direct_to_k_j += direct_h_power_w * dt

            needed_from_es_mech_w = k_request_w - direct_h_power_w

            if needed_from_es_mech_w > 0.0:
                needed_from_es_elec_w = needed_from_es_mech_w / self.mgu_k_motor_eff
                max_es_elec_from_budget_w = remaining_es_budget_j / (dt + 1e-9)

                if remaining_es_budget_j <= 0.0 or not battery_ok:
                    # Derate / Clipping! Car cannot draw power from ES
                    is_clipping = True
                    actual_es_elec_w = 0.0
                else:
                    target_es_elec_w = min(needed_from_es_elec_w, max_es_elec_from_budget_w)
                    actual_es_elec_w, _ = self.battery.step_discharge(target_es_elec_w, dt)
                    self.lap_es_deployed_j += actual_es_elec_w * dt

                    if actual_es_elec_w < needed_from_es_elec_w * 0.98:
                        is_clipping = True

                delivered_mech_from_es_w = actual_es_elec_w * self.mgu_k_motor_eff
            else:
                delivered_mech_from_es_w = 0.0

            mguk_mech_w = (direct_h_power_w * self.mgu_k_motor_eff) + delivered_mech_from_es_w
        else:
            # If not deploying direct MGU-H to K, send MGU-H energy to battery if possible
            if mguh_gen_w > 0.0:
                self.battery.step_charge(mguh_gen_w, dt)

        return ice_mech_w, mguk_mech_w, mguh_gen_w, is_clipping

    def harvest_braking(self, brake_power_request_w: float, dt: float) -> Tuple[float, float]:
        """
        Harvest kinetic energy via MGU-K during braking.
        
        Args:
            brake_power_request_w: Braking deceleration power requested (W).
            dt: Time step (seconds).
            
        Returns:
            Tuple of:
                - mguk_regen_mech_w: Mechanical braking power absorbed by MGU-K (up to 120 kW).
                - friction_brake_w: Remainder absorbed by hydraulic friction discs.
        """
        # MGU-K recovery capped at 120 kW
        target_k_regen_mech_w = min(self.mgu_k_max_power_w, brake_power_request_w)
        
        # Check regulatory 2.0 MJ harvest limit to ES per lap
        remaining_harvest_budget_j = max(0.0, self.mgu_k_max_harvest_lap_j - self.lap_es_harvested_j)

        if remaining_harvest_budget_j <= 0.0 or not self.battery.can_harvest():
            # Harvest cap hit or battery saturated -> all braking handled by friction brakes
            return 0.0, brake_power_request_w

        max_elec_from_budget_w = remaining_harvest_budget_j / (dt + 1e-9)
        k_elec_gen_w = min(target_k_regen_mech_w * self.mgu_k_gen_eff, max_elec_from_budget_w)

        stored_w, _ = self.battery.step_charge(k_elec_gen_w, dt)
        self.lap_es_harvested_j += stored_w * dt

        effective_regen_mech_w = stored_w / self.mgu_k_gen_eff
        friction_brake_w = max(0.0, brake_power_request_w - effective_regen_mech_w)

        return effective_regen_mech_w, friction_brake_w


@dataclass
class Aerodynamics:
    """Formula 1 Aerodynamic Model (Downforce and Drag with DRS)."""
    cla: float = 3.50                 # Lift coefficient * Reference Area (m^2)
    cda: float = 1.10                 # Drag coefficient * Reference Area (m^2)
    drs_drag_reduction: float = 0.25  # 25% drag reduction when DRS wing is open
    air_density: float = 1.205        # kg/m^3 at sea level, 20°C

    def downforce(self, speed_mps: float) -> float:
        """Calculate aerodynamic downforce (Newtons)."""
        return 0.5 * self.air_density * self.cla * (speed_mps ** 2)

    def drag(self, speed_mps: float, drs_active: bool = False) -> float:
        """Calculate aerodynamic drag (Newtons)."""
        effective_cda = self.cda * (1.0 - self.drs_drag_reduction) if drs_active else self.cda
        return 0.5 * self.air_density * effective_cda * (speed_mps ** 2)


@dataclass
class F1Vehicle:
    """Complete Formula 1 Car model including chassis, tires, aero, and power unit."""
    name: str = "Formula 1 2024-Spec"
    empty_mass_kg: float = 798.0         # FIA minimum weight (car + driver without fuel)
    fuel_mass_kg: float = 15.0           # Fuel mass (kg)
    mu_accel: float = 1.65               # Longitudinal traction coefficient
    mu_brake: float = 1.85               # Longitudinal braking friction coefficient
    mu_corner: float = 1.70              # Lateral cornering grip coefficient
    rolling_res_coeff: float = 0.015     # Rolling resistance coefficient Crr
    gravity: float = 9.80665             # m/s^2

    aero: Aerodynamics = field(default_factory=Aerodynamics)
    power_unit: F1PowerUnit = field(default_factory=F1PowerUnit)

    @property
    def total_mass_kg(self) -> float:
        """Total vehicle mass with fuel."""
        return self.empty_mass_kg + self.fuel_mass_kg

    def normal_force(self, speed_mps: float) -> float:
        """Total vertical force (gravity + downforce)."""
        return (self.total_mass_kg * self.gravity) + self.aero.downforce(speed_mps)

    def rolling_resistance(self, speed_mps: float) -> float:
        """Rolling resistance force (Newtons)."""
        return self.rolling_res_coeff * self.normal_force(speed_mps)

    def max_cornering_speed(self, radius_m: float, grip_factor: float = 1.0) -> float:
        """
        Calculate maximum apex speed allowed by lateral tire grip and downforce.
        Solves: M * v^2 / R <= mu * (M * g + 0.5 * rho * CLA * v^2)
        """
        if radius_m >= 10_000.0 or radius_m <= 0.0:
            return 101.5  # ~365.4 km/h realistic modern F1 terminal straight line ceiling
        
        effective_mu = self.mu_corner * grip_factor
        mass = self.total_mass_kg
        rho = self.aero.air_density
        cla = self.aero.cla

        denominator = (mass / radius_m) - (0.5 * rho * cla * effective_mu)
        if denominator <= 0.0:
            # Aero downforce exceeds centrifugal demand: flat out corner!
            return 100.0  # ~360 km/h max corner speed
        
        v_sq = (effective_mu * mass * self.gravity) / denominator
        return math.sqrt(max(0.0, v_sq))

    def max_traction_force(self, speed_mps: float) -> float:
        """Tire longitudinal traction limit (Newtons)."""
        return self.mu_accel * self.normal_force(speed_mps)

    def max_braking_force(self, speed_mps: float) -> float:
        """Tire longitudinal braking limit (Newtons)."""
        return self.mu_brake * self.normal_force(speed_mps)


@dataclass
class SeasonRegulations:
    """FIA Technical Regulations specifications for a given Formula 1 season."""
    year: int
    empty_mass_kg: float
    cla: float
    cda: float
    mu_corner: float
    mu_accel: float
    mu_brake: float
    drs_reduction: float
    base_ice_power_w: float
    notes: str = ""


_SEASON_REGULATIONS: Dict[int, SeasonRegulations] = {
    2020: SeasonRegulations(
        year=2020, empty_mass_kg=746.0, cla=4.15, cda=1.24, mu_corner=1.76, mu_accel=1.68, mu_brake=1.88,
        drs_reduction=0.28, base_ice_power_w=595_000.0,
        notes="Peak high-downforce generation with 746kg lightweight chassis and complex bargeboards."
    ),
    2021: SeasonRegulations(
        year=2021, empty_mass_kg=752.0, cla=3.78, cda=1.20, mu_corner=1.73, mu_accel=1.66, mu_brake=1.86,
        drs_reduction=0.27, base_ice_power_w=595_000.0,
        notes="FIA floor cuts reduced downforce by ~10% with 752kg minimum weight."
    ),
    2022: SeasonRegulations(
        year=2022, empty_mass_kg=798.0, cla=3.35, cda=1.14, mu_corner=1.67, mu_accel=1.63, mu_brake=1.82,
        drs_reduction=0.25, base_ice_power_w=585_000.0,
        notes="Ground effect Venturi reset: +46kg heavier, 18-inch wheels, E10 fuel, initial porpoising."
    ),
    2023: SeasonRegulations(
        year=2023, empty_mass_kg=798.0, cla=3.55, cda=1.12, mu_corner=1.70, mu_accel=1.65, mu_brake=1.84,
        drs_reduction=0.26, base_ice_power_w=590_000.0,
        notes="Floor edges raised 15mm; teams regained underfloor load and refined aero."
    ),
    2024: SeasonRegulations(
        year=2024, empty_mass_kg=798.0, cla=3.70, cda=1.10, mu_corner=1.71, mu_accel=1.66, mu_brake=1.85,
        drs_reduction=0.27, base_ice_power_w=595_000.0,
        notes="Mature ground effect development approaching 2020 peak cornering speeds."
    ),
    2025: SeasonRegulations(
        year=2025, empty_mass_kg=798.0, cla=3.78, cda=1.09, mu_corner=1.72, mu_accel=1.67, mu_brake=1.86,
        drs_reduction=0.27, base_ice_power_w=598_000.0,
        notes="Pinnacle of the 2022-2025 ground effect technical regulatory cycle."
    ),
}

# Team relative performance factors by year: (downforce_mult, power_mult, drag_mult)
_TEAM_YEAR_PERFORMANCE: Dict[str, Dict[int, Tuple[float, float, float]]] = {
    "red bull": {
        2020: (0.985, 0.980, 0.99),
        2021: (1.015, 1.005, 0.98),
        2022: (1.020, 1.010, 0.96),
        2023: (1.035, 1.020, 0.94), # Dominant RB19
        2024: (1.020, 1.010, 0.96),
        2025: (1.015, 1.010, 0.96),
    },
    "mercedes": {
        2020: (1.040, 1.025, 1.00), # Legendary W11
        2021: (1.015, 1.015, 0.99),
        2022: (0.965, 0.995, 1.04), # W13 porpoising & high drag
        2023: (0.985, 1.000, 1.01),
        2024: (1.010, 1.005, 0.98),
        2025: (1.010, 1.005, 0.98),
    },
    "ferrari": {
        2020: (0.960, 0.935, 1.03), # SF1000 engine power deficit
        2021: (0.990, 0.980, 1.00),
        2022: (1.025, 1.015, 1.00), # F1-75 rapid low-speed cornering
        2023: (0.995, 1.010, 0.98),
        2024: (1.020, 1.010, 0.97),
        2025: (1.022, 1.015, 0.97),
    },
    "mclaren": {
        2020: (0.980, 0.985, 0.99),
        2021: (0.990, 1.005, 0.97),
        2022: (0.970, 0.990, 1.01),
        2023: (1.005, 1.000, 0.99),
        2024: (1.030, 1.010, 0.96), # MCL38 champion car
        2025: (1.030, 1.010, 0.96),
    },
    "aston martin": {
        2020: (1.005, 1.010, 0.99), # Racing Point "Pink Mercedes"
        2021: (0.970, 0.995, 1.01),
        2022: (0.960, 0.990, 1.02),
        2023: (1.015, 1.000, 1.01), # Alonso early season surge
        2024: (0.985, 0.995, 1.00),
        2025: (0.990, 1.000, 1.00),
    },
    "alpine": {
        2020: (0.980, 0.985, 0.98), # Renault
        2021: (0.975, 0.985, 0.99),
        2022: (0.985, 0.995, 0.99),
        2023: (0.970, 0.980, 1.00),
        2024: (0.965, 0.975, 1.00),
        2025: (0.970, 0.980, 1.00),
    },
    "williams": {
        2020: (0.930, 1.000, 1.02),
        2021: (0.945, 1.000, 1.00),
        2022: (0.940, 0.990, 0.97),
        2023: (0.950, 0.995, 0.96), # Low drag straight-line rocket
        2024: (0.960, 0.995, 0.97),
        2025: (0.970, 1.000, 0.97),
    },
    "sauber": {
        2020: (0.935, 0.935, 1.02), # Alfa Romeo
        2021: (0.950, 0.980, 1.01),
        2022: (0.975, 1.010, 1.00),
        2023: (0.955, 0.990, 1.01),
        2024: (0.950, 0.990, 1.01),
        2025: (0.960, 0.995, 1.00),
    },
    "haas": {
        2020: (0.930, 0.935, 1.02),
        2021: (0.910, 0.970, 1.03), # No development season
        2022: (0.970, 1.010, 1.01),
        2023: (0.960, 0.995, 1.01),
        2024: (0.975, 1.000, 0.99),
        2025: (0.975, 1.000, 0.99),
    },
    "rb": {
        2020: (0.975, 0.980, 0.99), # AlphaTauri
        2021: (0.985, 1.005, 0.99),
        2022: (0.955, 0.990, 1.01),
        2023: (0.960, 1.000, 1.01),
        2024: (0.975, 1.005, 0.99),
        2025: (0.980, 1.005, 0.99),
    },
}


def get_season_regulations(year: Optional[int] = None) -> SeasonRegulations:
    """Retrieve FIA technical regulations for a given championship year."""
    if year is None or year not in _SEASON_REGULATIONS:
        return _SEASON_REGULATIONS[2024]
    return _SEASON_REGULATIONS[year]


def create_f1_vehicle(year: Optional[int] = None, team: Optional[str] = None) -> F1Vehicle:
    """
    Factory creating an F1Vehicle configured for a specific season year and constructor team.
    Applies regulatory weight, downforce, tire grip, and team-specific performance packages.
    """
    target_year = year if year in _SEASON_REGULATIONS else 2024
    regs = get_season_regulations(target_year)

    # Base season vehicle specs
    mass = regs.empty_mass_kg
    cla = regs.cla
    cda = regs.cda
    mu_corner = regs.mu_corner
    mu_accel = regs.mu_accel
    mu_brake = regs.mu_brake
    drs_red = regs.drs_reduction
    ice_pwr = regs.base_ice_power_w

    # Apply team-specific aero and power multipliers if known
    if team:
        clean_team = team.lower()
        matched_pkg = None
        for key, year_map in _TEAM_YEAR_PERFORMANCE.items():
            if key in clean_team or clean_team in key:
                if target_year in year_map:
                    matched_pkg = year_map[target_year]
                    break
        
        if matched_pkg:
            df_mult, pwr_mult, drag_mult = matched_pkg
            cla *= df_mult
            ice_pwr *= pwr_mult
            cda *= drag_mult

    aero = Aerodynamics(cla=cla, cda=cda, drs_drag_reduction=drs_red)
    engine = EngineCharacteristics(peak_power_w=ice_pwr)
    pu = F1PowerUnit(ice=engine)

    vehicle_name = f"F1 {target_year}-Spec"
    if team:
        vehicle_name += f" ({team})"

    return F1Vehicle(
        name=vehicle_name,
        empty_mass_kg=mass,
        fuel_mass_kg=15.0,
        mu_accel=mu_accel,
        mu_brake=mu_brake,
        mu_corner=mu_corner,
        aero=aero,
        power_unit=pu
    )
