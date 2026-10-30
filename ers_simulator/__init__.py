"""
Formula 1 Energy Recovery System (ERS) Modelling & Driver Lap Time Simulator
=============================================================================
A comprehensive quasi-steady-state simulation framework for modelling:
- Internal Combustion Engine (ICE) + Fuel Flow Limits
- MGU-K (Kinetic Energy Recovery & Deployment, 120 kW / 4MJ / 2MJ FIA limits)
- MGU-H (Heat Energy Recovery from Turbo & Direct DC Feed to MGU-K)
- Energy Store (ES / Battery Pack) SoC, voltage, thermal dynamics & degradation
- Vehicle Aerodynamics (Downforce, Drag, DRS)
- Driver Profiles (Braking aggression, Lift & Coast, Throttle aggression, Grip)
- Realistic F1 Tracks (Monza, Silverstone, Monaco, Spa-Francorchamps, Red Bull Ring)
- Comprehensive multi-driver lap time and telemetry comparison
"""

__version__ = "1.0.0"

from .vehicle import F1PowerUnit, F1Vehicle, Aerodynamics, EnergyStore, EngineCharacteristics
from .track import Track, TrackSector, get_circuit, list_circuits, list_seasons
from .driver import DriverProfile, get_driver_preset, list_driver_presets, list_seasons_drivers
from .ers_strategy import ERSStrategy, ERSMode
from .solver import LapSimulator, LapResult
from .telemetry import TelemetryComparison, SectorAnalysis
from .qualifying import QualifyingSimulator, QualifyingResult, DriverQualiResult, simulate_qualifying_session
from .track_2d import build_smooth_2d_track

__all__ = [
    "F1PowerUnit",
    "F1Vehicle",
    "Aerodynamics",
    "EnergyStore",
    "EngineCharacteristics",
    "Track",
    "TrackSector",
    "get_circuit",
    "list_circuits",
    "list_seasons",
    "DriverProfile",
    "get_driver_preset",
    "list_driver_presets",
    "list_seasons_drivers",
    "ERSStrategy",
    "ERSMode",
    "LapSimulator",
    "LapResult",
    "TelemetryComparison",
    "SectorAnalysis",
    "QualifyingSimulator",
    "QualifyingResult",
    "DriverQualiResult",
    "simulate_qualifying_session",
    "build_smooth_2d_track",
]
