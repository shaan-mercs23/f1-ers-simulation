"""
Formula 1 Driver Database and Driving Style Characteristics by Season
====================================================================
Comprehensive database of every Formula 1 driver across the modern Turbo-Hybrid era
(2020-2025+), including season-by-season team mappings, telemetry parameters,
braking styles, Lift-and-Coast tendencies, and ERS tactical preferences.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from .ers_strategy import ERSMode


@dataclass
class DriverProfile:
    """Driver behavioral and tactical characteristics."""
    name: str
    short_code: str
    team: str
    color: str                      # Hex color code for UI / charts
    number: int = 0
    country: str = ""
    year: int = 2024                # Championship season year
    years: List[int] = field(default_factory=lambda: [2024])
    team_history: Dict[int, str] = field(default_factory=dict)
    color_history: Dict[int, str] = field(default_factory=dict)
    
    # Driving Dynamics & Style
    braking_offset_m: float = 0.0   # Negative = later braking, positive = earlier braking
    braking_aggression: float = 1.0 # Multiplier on deceleration build-up (0.8 - 1.25)
    lift_and_coast_m: float = 0.0   # Distance before braking where throttle lifts to coast & regen
    throttle_aggression: float = 1.0# Speed of throttle ramp out of apex (0.8 - 1.25)
    cornering_grip_factor: float = 1.0 # Multiplier on lateral grip (0.97 - 1.03)
    
    # ERS Strategy
    ers_mode: ERSMode = ERSMode.HOTLAP_QUALI
    initial_soc: float = 0.85       # Starting battery SoC (85%)
    cutoff_speed_kmh: float = 295.0 # Speed above which MGU-K de-rates in balanced modes
    
    # Custom Notes
    notes: str = ""

    def for_year(self, year: int) -> "DriverProfile":
        """Return a clone of this profile adapted to the given championship year."""
        cloned = self.copy_with(year=year)
        if year in self.team_history:
            cloned.team = self.team_history[year]
        if year in self.color_history:
            cloned.color = self.color_history[year]
        return cloned

    def copy_with(self, **kwargs) -> "DriverProfile":
        """Return a modified clone of this profile."""
        data = {
            "name": self.name,
            "short_code": self.short_code,
            "team": self.team,
            "color": self.color,
            "number": self.number,
            "country": self.country,
            "year": self.year,
            "years": list(self.years),
            "team_history": dict(self.team_history),
            "color_history": dict(self.color_history),
            "braking_offset_m": self.braking_offset_m,
            "braking_aggression": self.braking_aggression,
            "lift_and_coast_m": self.lift_and_coast_m,
            "throttle_aggression": self.throttle_aggression,
            "cornering_grip_factor": self.cornering_grip_factor,
            "ers_mode": self.ers_mode,
            "initial_soc": self.initial_soc,
            "cutoff_speed_kmh": self.cutoff_speed_kmh,
            "notes": self.notes,
        }
        data.update(kwargs)
        return DriverProfile(**data)


# ---------------------------------------------------------------------------
# Complete Driver Database (Modern Turbo-Hybrid Era)
# ---------------------------------------------------------------------------

_DRIVER_REGISTRY: Dict[str, DriverProfile] = {
    # ------------------ RED BULL RACING / VCARB ------------------
    "ver": DriverProfile(
        name="Max Verstappen", short_code="VER", team="Red Bull Racing", color="#3671C6",
        number=1, country="Netherlands", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={y: "Red Bull Racing" for y in [2020, 2021, 2022, 2023, 2024, 2025]},
        color_history={y: "#3671C6" for y in [2020, 2021, 2022, 2023, 2024, 2025]},
        braking_offset_m=-7.5, braking_aggression=1.18, lift_and_coast_m=0.0,
        throttle_aggression=1.16, cornering_grip_factor=1.025, ers_mode=ERSMode.HOTLAP_QUALI,
        initial_soc=0.88, cutoff_speed_kmh=315.0,
        notes="Ultra-aggressive late braking, rapid throttle snap, high traction exit."
    ),
    "per": DriverProfile(
        name="Sergio Perez", short_code="PER", team="Red Bull Racing", color="#1E5BC6",
        number=11, country="Mexico", years=[2020, 2021, 2022, 2023, 2024],
        team_history={2020: "Racing Point", 2021: "Red Bull Racing", 2022: "Red Bull Racing", 2023: "Red Bull Racing", 2024: "Red Bull Racing"},
        color_history={2020: "#F596C8", 2021: "#3671C6", 2022: "#3671C6", 2023: "#3671C6", 2024: "#1E5BC6"},
        braking_offset_m=-1.5, braking_aggression=1.03, lift_and_coast_m=20.0,
        throttle_aggression=1.04, cornering_grip_factor=1.012, ers_mode=ERSMode.RACE_BALANCED,
        notes="Master of tire management, smooth rear axle preservation, steady energy flow."
    ),
    "tsu": DriverProfile(
        name="Yuki Tsunoda", short_code="TSU", team="RB (VCARB)", color="#6692FF",
        number=22, country="Japan", years=[2021, 2022, 2023, 2024, 2025],
        team_history={2021: "AlphaTauri", 2022: "AlphaTauri", 2023: "AlphaTauri", 2024: "RB (VCARB)", 2025: "RB (VCARB)"},
        color_history={2021: "#4E7C9B", 2022: "#4E7C9B", 2023: "#4E7C9B", 2024: "#6692FF", 2025: "#6692FF"},
        braking_offset_m=-4.5, braking_aggression=1.12, lift_and_coast_m=5.0,
        throttle_aggression=1.11, cornering_grip_factor=1.015, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Sharp initial steering bite, commits hard into mid-speed corners."
    ),
    "ric": DriverProfile(
        name="Daniel Ricciardo", short_code="RIC", team="RB / McLaren / Renault", color="#2B4562",
        number=3, country="Australia", years=[2020, 2021, 2022, 2023, 2024],
        team_history={2020: "Renault", 2021: "McLaren", 2022: "McLaren", 2023: "AlphaTauri", 2024: "RB (VCARB)"},
        color_history={2020: "#FFF500", 2021: "#FF8000", 2022: "#FF8000", 2023: "#4E7C9B", 2024: "#6692FF"},
        braking_offset_m=-6.0, braking_aggression=1.15, lift_and_coast_m=10.0,
        throttle_aggression=1.09, cornering_grip_factor=1.016, ers_mode=ERSMode.OVERTAKE_PUSH,
        notes="Iconic late-braking divebomb specialist with deep trail-braking."
    ),
    "law": DriverProfile(
        name="Liam Lawson", short_code="LAW", team="RB / Red Bull", color="#5C88EE",
        number=30, country="New Zealand", years=[2023, 2024, 2025],
        team_history={2023: "AlphaTauri", 2024: "RB (VCARB)", 2025: "Red Bull / RB"},
        color_history={2023: "#4E7C9B", 2024: "#6692FF", 2025: "#3671C6"},
        braking_offset_m=-4.0, braking_aggression=1.10, lift_and_coast_m=8.0,
        throttle_aggression=1.10, cornering_grip_factor=1.015, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Aggressive combative wheel-to-wheel racer with assertive braking."
    ),

    # ------------------ SCUDERIA FERRARI ------------------
    "lec": DriverProfile(
        name="Charles Leclerc", short_code="LEC", team="Ferrari", color="#E80020",
        number=16, country="Monaco", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={y: "Ferrari" for y in [2020, 2021, 2022, 2023, 2024, 2025]},
        color_history={y: "#E80020" for y in [2020, 2021, 2022, 2023, 2024, 2025]},
        braking_offset_m=-6.8, braking_aggression=1.16, lift_and_coast_m=0.0,
        throttle_aggression=1.14, cornering_grip_factor=1.024, ers_mode=ERSMode.HOTLAP_QUALI,
        initial_soc=0.90, cutoff_speed_kmh=310.0,
        notes="Qualifying speed maestro; dances on the knife-edge of rear axle rotation."
    ),
    "sai": DriverProfile(
        name="Carlos Sainz", short_code="SAI", team="Ferrari / Williams", color="#DC0000",
        number=55, country="Spain", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={2020: "McLaren", 2021: "Ferrari", 2022: "Ferrari", 2023: "Ferrari", 2024: "Ferrari", 2025: "Williams"},
        color_history={2020: "#FF8000", 2021: "#E80020", 2022: "#E80020", 2023: "#E80020", 2024: "#DC0000", 2025: "#00A0DE"},
        braking_offset_m=-3.8, braking_aggression=1.08, lift_and_coast_m=12.0,
        throttle_aggression=1.08, cornering_grip_factor=1.018, ers_mode=ERSMode.RACE_BALANCED,
        notes="Tactical, cerebral approach with high corner-entry stability."
    ),
    "bea": DriverProfile(
        name="Oliver Bearman", short_code="BEA", team="Haas / Ferrari", color="#B02A30",
        number=38, country="Great Britain", years=[2024, 2025],
        team_history={2024: "Ferrari / Haas", 2025: "Haas"},
        color_history={2024: "#E80020", 2025: "#B6BABD"},
        braking_offset_m=-4.0, braking_aggression=1.11, lift_and_coast_m=5.0,
        throttle_aggression=1.10, cornering_grip_factor=1.016, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Fearless high-speed corner commitment, excellent throttle modulation."
    ),

    # ------------------ MERCEDES-AMG PETRONAS ------------------
    "ham": DriverProfile(
        name="Lewis Hamilton", short_code="HAM", team="Mercedes / Ferrari", color="#00D2BE",
        number=44, country="Great Britain", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={2020: "Mercedes", 2021: "Mercedes", 2022: "Mercedes", 2023: "Mercedes", 2024: "Mercedes", 2025: "Ferrari"},
        color_history={2020: "#00D2BE", 2021: "#00D2BE", 2022: "#00D2BE", 2023: "#00D2BE", 2024: "#00D2BE", 2025: "#E80020"},
        braking_offset_m=-2.0, braking_aggression=1.06, lift_and_coast_m=12.0,
        throttle_aggression=1.05, cornering_grip_factor=1.022, ers_mode=ERSMode.RACE_BALANCED,
        initial_soc=0.85, cutoff_speed_kmh=290.0,
        notes="Exquisite trail-braking into apex, carries immense roll speed, balanced energy conservation."
    ),
    "rus": DriverProfile(
        name="George Russell", short_code="RUS", team="Mercedes", color="#24F4D6",
        number=63, country="Great Britain", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={2020: "Williams / Mercedes", 2021: "Williams", 2022: "Mercedes", 2023: "Mercedes", 2024: "Mercedes", 2025: "Mercedes"},
        color_history={2020: "#0082FA", 2021: "#0082FA", 2022: "#00D2BE", 2023: "#00D2BE", 2024: "#24F4D6", 2025: "#00D2BE"},
        braking_offset_m=-5.0, braking_aggression=1.12, lift_and_coast_m=6.0,
        throttle_aggression=1.11, cornering_grip_factor=1.019, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="High-energy qualifying approach with aggressive apex entry."
    ),
    "ant": DriverProfile(
        name="Kimi Antonelli", short_code="ANT", team="Mercedes", color="#00C4B4",
        number=12, country="Italy", years=[2025],
        team_history={2025: "Mercedes"},
        color_history={2025: "#00D2BE"},
        braking_offset_m=-4.5, braking_aggression=1.12, lift_and_coast_m=6.0,
        throttle_aggression=1.12, cornering_grip_factor=1.018, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Prodigious teenage talent; rapid throttle pick-up and agile direction change."
    ),

    # ------------------ MCLAREN F1 TEAM ------------------
    "nor": DriverProfile(
        name="Lando Norris", short_code="NOR", team="McLaren", color="#FF8000",
        number=4, country="Great Britain", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={y: "McLaren" for y in [2020, 2021, 2022, 2023, 2024, 2025]},
        color_history={y: "#FF8000" for y in [2020, 2021, 2022, 2023, 2024, 2025]},
        braking_offset_m=-3.5, braking_aggression=1.08, lift_and_coast_m=8.0,
        throttle_aggression=1.08, cornering_grip_factor=1.020, ers_mode=ERSMode.OPTIMAL_DYNAMIC,
        initial_soc=0.85, cutoff_speed_kmh=298.0,
        notes="Clean flowing driving style with optimal Pontryagin energy distribution."
    ),
    "pia": DriverProfile(
        name="Oscar Piastri", short_code="PIA", team="McLaren", color="#FF9E1B",
        number=81, country="Australia", years=[2023, 2024, 2025],
        team_history={2023: "McLaren", 2024: "McLaren", 2025: "McLaren"},
        color_history={2023: "#FF8000", 2024: "#FF9E1B", 2025: "#FF8000"},
        braking_offset_m=-3.2, braking_aggression=1.07, lift_and_coast_m=10.0,
        throttle_aggression=1.08, cornering_grip_factor=1.018, ers_mode=ERSMode.RACE_BALANCED,
        notes="Remarkably calm telemetry inputs with steady battery SoC equilibrium."
    ),

    # ------------------ ASTON MARTIN ARAMCO ------------------
    "alo": DriverProfile(
        name="Fernando Alonso", short_code="ALO", team="Aston Martin / Alpine", color="#229971",
        number=14, country="Spain", years=[2021, 2022, 2023, 2024, 2025],
        team_history={2021: "Alpine", 2022: "Alpine", 2023: "Aston Martin", 2024: "Aston Martin", 2025: "Aston Martin"},
        color_history={2021: "#0090FF", 2022: "#0090FF", 2023: "#229971", 2024: "#229971", 2025: "#229971"},
        braking_offset_m=-4.0, braking_aggression=1.12, lift_and_coast_m=35.0,
        throttle_aggression=1.20, cornering_grip_factor=1.017, ers_mode=ERSMode.OVERTAKE_PUSH,
        initial_soc=0.82, cutoff_speed_kmh=320.0,
        notes="Tactical battery hoarder; uses heavy Lift & Coast then unleashes full boost on passing straights."
    ),
    "str": DriverProfile(
        name="Lance Stroll", short_code="STR", team="Aston Martin", color="#1F7D5C",
        number=18, country="Canada", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={2020: "Racing Point", 2021: "Aston Martin", 2022: "Aston Martin", 2023: "Aston Martin", 2024: "Aston Martin", 2025: "Aston Martin"},
        color_history={2020: "#F596C8", 2021: "#229971", 2022: "#229971", 2023: "#229971", 2024: "#1F7D5C", 2025: "#229971"},
        braking_offset_m=-2.0, braking_aggression=1.04, lift_and_coast_m=15.0,
        throttle_aggression=1.06, cornering_grip_factor=1.011, ers_mode=ERSMode.RACE_BALANCED,
        notes="Strong straight-line traction focus with early upshifts."
    ),
    "vet": DriverProfile(
        name="Sebastian Vettel", short_code="VET", team="Aston Martin / Ferrari", color="#00594F",
        number=5, country="Germany", years=[2020, 2021, 2022],
        team_history={2020: "Ferrari", 2021: "Aston Martin", 2022: "Aston Martin"},
        color_history={2020: "#DC0000", 2021: "#229971", 2022: "#229971"},
        braking_offset_m=-3.0, braking_aggression=1.08, lift_and_coast_m=14.0,
        throttle_aggression=1.12, cornering_grip_factor=1.018, ers_mode=ERSMode.OPTIMAL_DYNAMIC,
        notes="Rear-planted driving style; uses engine braking and MGU-K regen to rotate the chassis."
    ),

    # ------------------ ALPINE F1 TEAM ------------------
    "gas": DriverProfile(
        name="Pierre Gasly", short_code="GAS", team="Alpine / AlphaTauri", color="#FF87BC",
        number=10, country="France", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={2020: "AlphaTauri", 2021: "AlphaTauri", 2022: "AlphaTauri", 2023: "Alpine", 2024: "Alpine", 2025: "Alpine"},
        color_history={2020: "#4E7C9B", 2021: "#4E7C9B", 2022: "#4E7C9B", 2023: "#0090FF", 2024: "#FF87BC", 2025: "#0090FF"},
        braking_offset_m=-4.0, braking_aggression=1.10, lift_and_coast_m=8.0,
        throttle_aggression=1.10, cornering_grip_factor=1.015, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="High mid-corner momentum carrier with punchy qualifying laps."
    ),
    "oco": DriverProfile(
        name="Esteban Ocon", short_code="OCO", team="Haas / Alpine", color="#0090FF",
        number=31, country="France", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={2020: "Renault", 2021: "Alpine", 2022: "Alpine", 2023: "Alpine", 2024: "Alpine", 2025: "Haas"},
        color_history={2020: "#FFF500", 2021: "#0090FF", 2022: "#0090FF", 2023: "#0090FF", 2024: "#0090FF", 2025: "#B6BABD"},
        braking_offset_m=-3.5, braking_aggression=1.09, lift_and_coast_m=12.0,
        throttle_aggression=1.07, cornering_grip_factor=1.014, ers_mode=ERSMode.OVERTAKE_PUSH,
        notes="Stubborn defensive racer; places car perfectly and hoards battery to defend straights."
    ),
    "doo": DriverProfile(
        name="Jack Doohan", short_code="DOO", team="Alpine", color="#0084E6",
        number=7, country="Australia", years=[2025],
        team_history={2025: "Alpine"},
        color_history={2025: "#0090FF"},
        braking_offset_m=-3.5, braking_aggression=1.09, lift_and_coast_m=7.0,
        throttle_aggression=1.09, cornering_grip_factor=1.014, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Sharp throttle response and aggressive corner exit commitment."
    ),

    # ------------------ WILLIAMS RACING ------------------
    "alb": DriverProfile(
        name="Alexander Albon", short_code="ALB", team="Williams / Red Bull", color="#00A0DE",
        number=23, country="Thailand", years=[2020, 2022, 2023, 2024, 2025],
        team_history={2020: "Red Bull Racing", 2022: "Williams", 2023: "Williams", 2024: "Williams", 2025: "Williams"},
        color_history={2020: "#3671C6", 2022: "#0082FA", 2023: "#0082FA", 2024: "#00A0DE", 2025: "#00A0DE"},
        braking_offset_m=-4.2, braking_aggression=1.11, lift_and_coast_m=8.0,
        throttle_aggression=1.11, cornering_grip_factor=1.016, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Extracts supreme straight-line top speed; outstanding defensive positioning."
    ),
    "col": DriverProfile(
        name="Franco Colapinto", short_code="COL", team="Williams", color="#0080FF",
        number=43, country="Argentina", years=[2024, 2025],
        team_history={2024: "Williams", 2025: "Williams / Alpine"},
        color_history={2024: "#00A0DE", 2025: "#00A0DE"},
        braking_offset_m=-4.0, braking_aggression=1.10, lift_and_coast_m=6.0,
        throttle_aggression=1.12, cornering_grip_factor=1.015, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="High natural car control; fearless throttle commitment on street circuits."
    ),
    "sar": DriverProfile(
        name="Logan Sargeant", short_code="SAR", team="Williams", color="#32B5E8",
        number=2, country="United States", years=[2023, 2024],
        team_history={2023: "Williams", 2024: "Williams"},
        color_history={2023: "#0082FA", 2024: "#00A0DE"},
        braking_offset_m=-2.0, braking_aggression=1.04, lift_and_coast_m=10.0,
        throttle_aggression=1.05, cornering_grip_factor=1.008, ers_mode=ERSMode.RACE_BALANCED,
        notes="Steady progressive braking with moderate cornering loading."
    ),
    "lat": DriverProfile(
        name="Nicholas Latifi", short_code="LAT", team="Williams", color="#041E42",
        number=6, country="Canada", years=[2020, 2021, 2022],
        team_history={2020: "Williams", 2021: "Williams", 2022: "Williams"},
        color_history={2020: "#0082FA", 2021: "#0082FA", 2022: "#0082FA"},
        braking_offset_m=-0.5, braking_aggression=1.00, lift_and_coast_m=15.0,
        throttle_aggression=1.02, cornering_grip_factor=1.005, ers_mode=ERSMode.RACE_BALANCED,
        notes="Conservative braking points and steady exit throttle."
    ),

    # ------------------ STAKE F1 TEAM SAUBER / AUDI ------------------
    "hul": DriverProfile(
        name="Nico Hulkenberg", short_code="HUL", team="Sauber / Haas", color="#52E252",
        number=27, country="Germany", years=[2020, 2022, 2023, 2024, 2025],
        team_history={2020: "Racing Point", 2022: "Aston Martin", 2023: "Haas", 2024: "Haas", 2025: "Sauber / Audi"},
        color_history={2020: "#F596C8", 2022: "#229971", 2023: "#B6BABD", 2024: "#B6BABD", 2025: "#52E252"},
        braking_offset_m=-5.5, braking_aggression=1.14, lift_and_coast_m=4.0,
        throttle_aggression=1.12, cornering_grip_factor=1.018, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Qualifying beast; extracts 100% of tire grip on single flying laps."
    ),
    "bot": DriverProfile(
        name="Valtteri Bottas", short_code="BOT", team="Sauber / Mercedes", color="#00E700",
        number=77, country="Finland", years=[2020, 2021, 2022, 2023, 2024, 2025],
        team_history={2020: "Mercedes", 2021: "Mercedes", 2022: "Alfa Romeo", 2023: "Alfa Romeo", 2024: "Sauber", 2025: "Sauber / Mercedes"},
        color_history={2020: "#00D2BE", 2021: "#00D2BE", 2022: "#900000", 2023: "#C92D4B", 2024: "#52E252", 2025: "#52E252"},
        braking_offset_m=-3.8, braking_aggression=1.09, lift_and_coast_m=10.0,
        throttle_aggression=1.08, cornering_grip_factor=1.019, ers_mode=ERSMode.RACE_BALANCED,
        notes="Pure precision on single laps with smooth, geometric corner arcs."
    ),
    "zho": DriverProfile(
        name="Zhou Guanyu", short_code="ZHO", team="Sauber / Alfa Romeo", color="#00C800",
        number=24, country="China", years=[2022, 2023, 2024, 2025],
        team_history={2022: "Alfa Romeo", 2023: "Alfa Romeo", 2024: "Sauber", 2025: "Sauber / Ferrari"},
        color_history={2022: "#900000", 2023: "#C92D4B", 2024: "#52E252", 2025: "#52E252"},
        braking_offset_m=-2.5, braking_aggression=1.05, lift_and_coast_m=12.0,
        throttle_aggression=1.05, cornering_grip_factor=1.011, ers_mode=ERSMode.RACE_BALANCED,
        notes="Consistent, smooth steering inputs preserving battery and tires."
    ),
    "bor": DriverProfile(
        name="Gabriel Bortoleto", short_code="BOR", team="Sauber / Audi", color="#46D246",
        number=5, country="Brazil", years=[2025],
        team_history={2025: "Sauber / Audi"},
        color_history={2025: "#52E252"},
        braking_offset_m=-4.0, braking_aggression=1.10, lift_and_coast_m=6.0,
        throttle_aggression=1.10, cornering_grip_factor=1.015, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="F2 & F3 champion with mature racecraft and rapid tire warm-up technique."
    ),

    # ------------------ MONEYGRAM HAAS F1 TEAM ------------------
    "mag": DriverProfile(
        name="Kevin Magnussen", short_code="MAG", team="Haas", color="#B6BABD",
        number=20, country="Denmark", years=[2020, 2022, 2023, 2024],
        team_history={2020: "Haas", 2022: "Haas", 2023: "Haas", 2024: "Haas"},
        color_history={2020: "#787878", 2022: "#FFFFFF", 2023: "#B6BABD", 2024: "#B6BABD"},
        braking_offset_m=-5.0, braking_aggression=1.14, lift_and_coast_m=8.0,
        throttle_aggression=1.13, cornering_grip_factor=1.014, ers_mode=ERSMode.OVERTAKE_PUSH,
        notes="Aggressive wheel-to-wheel combatant with violent braking bites."
    ),
    "msc": DriverProfile(
        name="Mick Schumacher", short_code="MSC", team="Haas", color="#E60000",
        number=47, country="Germany", years=[2021, 2022],
        team_history={2021: "Haas", 2022: "Haas"},
        color_history={2021: "#FFFFFF", 2022: "#FFFFFF"},
        braking_offset_m=-2.5, braking_aggression=1.05, lift_and_coast_m=12.0,
        throttle_aggression=1.06, cornering_grip_factor=1.010, ers_mode=ERSMode.RACE_BALANCED,
        notes="Progressive input buildup with methodical lap time improvement."
    ),

    # ------------------ LEGENDARY TURBO-HYBRID DRIVERS ------------------
    "rai": DriverProfile(
        name="Kimi Raikkonen", short_code="RAI", team="Alfa Romeo / Ferrari", color="#900000",
        number=7, country="Finland", years=[2020, 2021],
        team_history={2020: "Alfa Romeo", 2021: "Alfa Romeo"},
        color_history={2020: "#900000", 2021: "#900000"},
        braking_offset_m=-3.0, braking_aggression=1.08, lift_and_coast_m=18.0,
        throttle_aggression=1.07, cornering_grip_factor=1.018, ers_mode=ERSMode.RACE_BALANCED,
        notes="The Iceman. Supreme front-end sensitivity, master of kinetic energy preservation."
    ),
    "gio": DriverProfile(
        name="Antonio Giovinazzi", short_code="GIO", team="Alfa Romeo", color="#800000",
        number=99, country="Italy", years=[2020, 2021],
        team_history={2020: "Alfa Romeo", 2021: "Alfa Romeo"},
        color_history={2020: "#900000", 2021: "#900000"},
        braking_offset_m=-2.5, braking_aggression=1.06, lift_and_coast_m=10.0,
        throttle_aggression=1.06, cornering_grip_factor=1.011, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Strong single-lap qualifying pace on low fuel."
    ),
    "dev": DriverProfile(
        name="Nyck de Vries", short_code="DEV", team="AlphaTauri / Williams", color="#2B4562",
        number=21, country="Netherlands", years=[2022, 2023],
        team_history={2022: "Williams", 2023: "AlphaTauri"},
        color_history={2022: "#0082FA", 2023: "#4E7C9B"},
        braking_offset_m=-2.0, braking_aggression=1.05, lift_and_coast_m=10.0,
        throttle_aggression=1.06, cornering_grip_factor=1.010, ers_mode=ERSMode.RACE_BALANCED,
        notes="Formula E world champion with deep EV powertrain energy management knowledge."
    ),
    "kvy": DriverProfile(
        name="Daniil Kvyat", short_code="KVY", team="AlphaTauri", color="#3E5C76",
        number=26, country="Russia", years=[2020],
        team_history={2020: "AlphaTauri"},
        color_history={2020: "#4E7C9B"},
        braking_offset_m=-4.5, braking_aggression=1.12, lift_and_coast_m=8.0,
        throttle_aggression=1.10, cornering_grip_factor=1.014, ers_mode=ERSMode.OVERTAKE_PUSH,
        notes="The Torpedo; aggressive apex turn-in and strong braking power."
    ),
    "gro": DriverProfile(
        name="Romain Grosjean", short_code="GRO", team="Haas", color="#5C6068",
        number=8, country="France", years=[2020],
        team_history={2020: "Haas"},
        color_history={2020: "#787878"},
        braking_offset_m=-4.0, braking_aggression=1.11, lift_and_coast_m=6.0,
        throttle_aggression=1.11, cornering_grip_factor=1.015, ers_mode=ERSMode.HOTLAP_QUALI,
        notes="Tremendous raw speed and apex commitment when confident in front-end grip."
    ),
}


def list_seasons_drivers() -> List[int]:
    """List all available seasons across driver careers."""
    years = set()
    for d in _DRIVER_REGISTRY.values():
        years.update(d.years)
    return sorted(list(years), reverse=True)


def get_driver_preset(short_code_or_name: str, year: Optional[int] = None) -> DriverProfile:
    """
    Retrieve driver profile by short code or name, optionally adapted for a specific year.
    """
    query = short_code_or_name.lower().strip()
    target_drv: Optional[DriverProfile] = None

    if query in _DRIVER_REGISTRY:
        target_drv = _DRIVER_REGISTRY[query]
    else:
        for code, p in _DRIVER_REGISTRY.items():
            if query == p.short_code.lower() or query in p.name.lower():
                target_drv = p
                break

    if target_drv is None:
        raise KeyError(f"Driver '{short_code_or_name}' not found. Available: {list(_DRIVER_REGISTRY.keys())}")

    if year is not None:
        return target_drv.for_year(year)
    return target_drv.copy_with()


def list_driver_presets(year: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    List driver profiles, optionally filtered by World Championship season year.
    """
    results = []
    for p in _DRIVER_REGISTRY.values():
        if year is not None and year not in p.years:
            continue
        
        drv = p.for_year(year) if year is not None else p
        results.append({
            "code": drv.short_code,
            "name": drv.name,
            "number": drv.number,
            "country": drv.country,
            "team": drv.team,
            "color": drv.color,
            "years": drv.years,
            "ers_mode": drv.ers_mode.value,
            "notes": drv.notes,
            "braking_offset_m": drv.braking_offset_m,
            "lift_and_coast_m": drv.lift_and_coast_m,
            "throttle_aggression": drv.throttle_aggression,
            "cornering_grip_factor": drv.cornering_grip_factor,
        })
    
    # Sort alphabetically by driver name
    return sorted(results, key=lambda x: x["name"])
