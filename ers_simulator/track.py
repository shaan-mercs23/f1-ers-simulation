"""
Formula 1 Circuit and Track Geometry Representation by Season Calendar
======================================================================
Models track curvature, corner radii, braking zones, DRS zones, elevation changes,
and sector divisions for all Grand Prix circuits across modern F1 seasons (2020-2025).
"""

from dataclasses import dataclass, field
import numpy as np
import math
from typing import List, Dict, Optional, Any


@dataclass
class TrackSector:
    """Sector definition."""
    number: int
    start_distance_m: float
    end_distance_m: float


@dataclass
class TrackSegment:
    """A geometric section of the track (straight or corner)."""
    length_m: float
    radius_m: float               # float('inf') or >= 10000 for straight
    corner_name: str = ""
    is_drs: bool = False
    elevation_change_m: float = 0.0
    sector: int = 1


@dataclass
class DiscretizedTrack:
    """Discretized spatial representation of the circuit."""
    distance_m: np.ndarray       # Shape (N,)
    radius_m: np.ndarray         # Shape (N,)
    curvature: np.ndarray        # Shape (N,) 1/R
    slope_rad: np.ndarray        # Shape (N,)
    elevation_m: np.ndarray      # Shape (N,)
    drs_active: np.ndarray       # Shape (N,) bool
    sector: np.ndarray           # Shape (N,) int
    corner_labels: List[str]     # Corner name at each index if any
    total_length_m: float
    dx: float


@dataclass
class Track:
    """High-level Track definition comprising consecutive track segments."""
    id: str
    name: str
    country: str
    total_length_m: float
    segments: List[TrackSegment]
    years: List[int]             # F1 World Championship seasons this circuit appeared in
    description: str = ""
    lap_record: str = ""
    typical_downforce: str = "Medium"  # Low, Medium, High, Maximum
    derate_sensitivity: str = "Medium" # Low, Medium, High, Extreme

    def discretize(self, dx: float = 2.0) -> DiscretizedTrack:
        """
        Discretize track into equidistant spatial steps dx (meters).
        Applies smooth transitions for curvature to simulate realistic racing lines.
        """
        seg_starts = []
        cum = 0.0
        for seg in self.segments:
            seg_starts.append(cum)
            cum += seg.length_m

        total_len = cum
        num_points = int(np.ceil(total_len / dx))
        s_points = np.linspace(0.0, total_len, num_points, endpoint=False)

        radius_arr = np.full(num_points, 100_000.0)
        drs_arr = np.zeros(num_points, dtype=bool)
        sector_arr = np.ones(num_points, dtype=int)
        slope_arr = np.zeros(num_points, dtype=float)
        labels: List[str] = [""] * num_points

        for i, s in enumerate(s_points):
            seg_idx = 0
            for idx, start_d in enumerate(seg_starts):
                if s >= start_d:
                    seg_idx = idx
                else:
                    break
            
            seg = self.segments[seg_idx]
            seg_start = seg_starts[seg_idx]
            local_pos = s - seg_start
            
            radius_arr[i] = seg.radius_m
            drs_arr[i] = seg.is_drs
            sector_arr[i] = seg.sector
            
            slope = seg.elevation_change_m / max(1e-3, seg.length_m)
            slope_arr[i] = math.atan(slope)
            
            if seg.corner_name and local_pos < (dx * 1.5):
                labels[i] = seg.corner_name

        raw_curv = 1.0 / np.clip(radius_arr, 15.0, 100_000.0)
        smoothed_curv = np.convolve(raw_curv, np.ones(7)/7.0, mode='same')
        smoothed_radius = 1.0 / np.clip(smoothed_curv, 1e-5, 1.0)

        elev = np.zeros(num_points)
        cum_elev = 0.0
        for i in range(num_points):
            cum_elev += slope_arr[i] * dx
            elev[i] = cum_elev

        return DiscretizedTrack(
            distance_m=s_points,
            radius_m=smoothed_radius,
            curvature=smoothed_curv,
            slope_rad=slope_arr,
            elevation_m=elev,
            drs_active=drs_arr,
            sector=sector_arr,
            corner_labels=labels,
            total_length_m=total_len,
            dx=dx
        )


# ---------------------------------------------------------------------------
# Track Construction Definitions
# ---------------------------------------------------------------------------

def create_monza_circuit() -> Track:
    segments = [
        TrackSegment(950.0, 50000.0, "Pit Straight", is_drs=True, sector=1),
        TrackSegment(90.0, 35.0, "Variante del Rettifilo (T1)", sector=1),
        TrackSegment(85.0, 42.0, "Variante del Rettifilo (T2)", sector=1),
        TrackSegment(350.0, 2000.0, sector=1),
        TrackSegment(450.0, 380.0, "Curva Grande (T3)", sector=1),
        TrackSegment(380.0, 50000.0, is_drs=False, sector=1),
        TrackSegment(90.0, 55.0, "Variante della Roggia (T4)", sector=2),
        TrackSegment(85.0, 60.0, "Variante della Roggia (T5)", sector=2),
        TrackSegment(220.0, 50000.0, sector=2),
        TrackSegment(110.0, 95.0, "1st Lesmo (T6)", sector=2),
        TrackSegment(160.0, 50000.0, sector=2),
        TrackSegment(120.0, 85.0, "2nd Lesmo (T7)", sector=2),
        TrackSegment(680.0, 50000.0, "Curva del Serraglio", is_drs=True, sector=2),
        TrackSegment(95.0, 95.0, "Ascari Entry (T8)", sector=3),
        TrackSegment(90.0, 110.0, "Ascari Mid (T9)", sector=3),
        TrackSegment(110.0, 130.0, "Ascari Exit (T10)", sector=3),
        TrackSegment(960.0, 50000.0, "Rettifilo Posteriore", is_drs=False, sector=3),
        TrackSegment(340.0, 145.0, "Curva Parabolica (T11)", sector=3),
        TrackSegment(428.0, 50000.0, sector=3),
    ]
    return Track(
        id="monza",
        name="Autodromo Nazionale Monza",
        country="Italy",
        total_length_m=5793.0,
        segments=segments,
        years=[2020, 2021, 2022, 2023, 2024, 2025],
        description="High-speed power temple with long straights and violent braking zones. Key benchmark for ERS clipping and derating.",
        lap_record="1:21.046 (Rubens Barrichello, Ferrari, 2004)",
        typical_downforce="Low",
        derate_sensitivity="Extreme"
    )


def create_silverstone_circuit() -> Track:
    segments = [
        TrackSegment(450.0, 50000.0, "Hamilton Straight", is_drs=True, sector=1),
        TrackSegment(140.0, 280.0, "Abbey (T1)", sector=1),
        TrackSegment(180.0, 400.0, "Farm Curve (T2)", sector=1),
        TrackSegment(90.0, 45.0, "Village (T3)", sector=1),
        TrackSegment(110.0, 35.0, "The Loop (T4)", sector=1),
        TrackSegment(120.0, 130.0, "Aintree (T5)", sector=1),
        TrackSegment(750.0, 50000.0, "Wellington Straight", is_drs=True, sector=2),
        TrackSegment(160.0, 85.0, "Brooklands (T6)", sector=2),
        TrackSegment(220.0, 70.0, "Luffield (T7)", sector=2),
        TrackSegment(180.0, 260.0, "Woodcote (T8)", sector=2),
        TrackSegment(480.0, 50000.0, sector=2),
        TrackSegment(160.0, 240.0, "Copse (T9)", sector=2),
        TrackSegment(280.0, 50000.0, sector=2),
        TrackSegment(130.0, 220.0, "Maggotts (T10)", sector=3),
        TrackSegment(110.0, 140.0, "Becketts 1 (T11)", sector=3),
        TrackSegment(120.0, 100.0, "Becketts 2 (T12)", sector=3),
        TrackSegment(110.0, 150.0, "Chapel (T13)", sector=3),
        TrackSegment(780.0, 50000.0, "Hangar Straight", is_drs=True, sector=3),
        TrackSegment(160.0, 125.0, "Stowe (T15)", sector=3),
        TrackSegment(260.0, 50000.0, sector=3),
        TrackSegment(90.0, 45.0, "Vale (T16)", sector=3),
        TrackSegment(150.0, 80.0, "Club (T17/18)", sector=3),
        TrackSegment(541.0, 50000.0, sector=3),
    ]
    return Track(
        id="silverstone",
        name="Silverstone Circuit",
        country="Great Britain",
        total_length_m=5891.0,
        segments=segments,
        years=[2020, 2021, 2022, 2023, 2024, 2025],
        description="High-G lateral corners with heavy aero loading and massive continuous MGU-H energy harvesting.",
        lap_record="1:27.097 (Max Verstappen, Red Bull, 2020)",
        typical_downforce="Medium-High",
        derate_sensitivity="Medium"
    )


def create_spa_circuit() -> Track:
    segments = [
        TrackSegment(350.0, 50000.0, "Start Straight", sector=1),
        TrackSegment(95.0, 28.0, "La Source (T1)", sector=1),
        TrackSegment(520.0, 50000.0, elevation_change_m=-18.0, sector=1),
        TrackSegment(140.0, 220.0, "Eau Rouge (T2)", elevation_change_m=12.0, sector=1),
        TrackSegment(130.0, 210.0, "Raidillon (T3/T4)", elevation_change_m=22.0, sector=1),
        TrackSegment(980.0, 50000.0, "Kemmel Straight", is_drs=True, elevation_change_m=5.0, sector=1),
        TrackSegment(95.0, 65.0, "Les Combes (T5)", sector=2),
        TrackSegment(90.0, 70.0, "Les Combes (T6)", sector=2),
        TrackSegment(110.0, 110.0, "Malmedy (T7)", sector=2),
        TrackSegment(320.0, 50000.0, elevation_change_m=-12.0, sector=2),
        TrackSegment(180.0, 55.0, "Bruxelles (T8)", sector=2),
        TrackSegment(110.0, 85.0, "T9", sector=2),
        TrackSegment(380.0, 50000.0, elevation_change_m=-15.0, sector=2),
        TrackSegment(240.0, 140.0, "Pouhon (T10/T11)", sector=2),
        TrackSegment(280.0, 50000.0, sector=2),
        TrackSegment(120.0, 75.0, "Fagnes (T12/T13)", sector=2),
        TrackSegment(210.0, 110.0, "Campus/Stavelot", sector=2),
        TrackSegment(180.0, 350.0, sector=3),
        TrackSegment(1250.0, 500.0, "Blanchimont (T17/T18)", is_drs=True, sector=3),
        TrackSegment(95.0, 32.0, "Bus Stop Chicane (T19/20)", sector=3),
        TrackSegment(369.0, 50000.0, is_drs=True, sector=3),
    ]
    return Track(
        id="spa",
        name="Circuit de Spa-Francorchamps",
        country="Belgium",
        total_length_m=7004.0,
        segments=segments,
        years=[2020, 2021, 2022, 2023, 2024, 2025],
        description="The ultimate roller-coaster. Huge elevation delta, iconic Raidillon, and immense Kemmel straight where ERS clipping costs up to 0.4s.",
        lap_record="1:46.286 (Valtteri Bottas, Mercedes, 2018)",
        typical_downforce="Medium-Low",
        derate_sensitivity="High"
    )


def create_monaco_circuit() -> Track:
    segments = [
        TrackSegment(300.0, 50000.0, "Main Straight", is_drs=True, sector=1),
        TrackSegment(80.0, 30.0, "Sainte Devote (T1)", sector=1),
        TrackSegment(380.0, 300.0, "Beau Rivage Uphill", elevation_change_m=20.0, sector=1),
        TrackSegment(90.0, 65.0, "Massenet (T2)", sector=1),
        TrackSegment(85.0, 55.0, "Casino Square (T3)", sector=1),
        TrackSegment(210.0, 50000.0, elevation_change_m=-14.0, sector=2),
        TrackSegment(80.0, 38.0, "Mirabeau Haute (T5)", sector=2),
        TrackSegment(85.0, 18.0, "Grand Hotel Hairpin (T6)", sector=2),
        TrackSegment(90.0, 32.0, "Mirabeau Bas (T7)", sector=2),
        TrackSegment(110.0, 42.0, "Portier (T8)", sector=2),
        TrackSegment(580.0, 450.0, "The Tunnel", sector=2),
        TrackSegment(95.0, 30.0, "Nouvelle Chicane (T10/11)", sector=3),
        TrackSegment(220.0, 50000.0, sector=3),
        TrackSegment(110.0, 85.0, "Tabac (T12)", sector=3),
        TrackSegment(160.0, 110.0, "Louis Chiron (T13/14)", sector=3),
        TrackSegment(140.0, 50.0, "Piscine Chicane (T15/16)", sector=3),
        TrackSegment(160.0, 28.0, "La Rascasse (T18)", sector=3),
        TrackSegment(110.0, 35.0, "Anthony Noghes (T19)", sector=3),
        TrackSegment(277.0, 50000.0, sector=3),
    ]
    return Track(
        id="monaco",
        name="Circuit de Monaco",
        country="Monaco",
        total_length_m=3337.0,
        segments=segments,
        years=[2021, 2022, 2023, 2024, 2025],
        description="Tight street circuit with frequent heavy braking and low top speeds. MGU-K harvesting dominates; battery rarely runs out.",
        lap_record="1:12.909 (Lewis Hamilton, Mercedes, 2021)",
        typical_downforce="Maximum",
        derate_sensitivity="Low"
    )


def create_redbullring_circuit() -> Track:
    segments = [
        TrackSegment(480.0, 50000.0, "Start/Finish Straight", is_drs=True, sector=1),
        TrackSegment(85.0, 42.0, "Niki Lauda Kurve (T1)", sector=1),
        TrackSegment(760.0, 50000.0, "Straight to T3", is_drs=True, elevation_change_m=18.0, sector=1),
        TrackSegment(80.0, 25.0, "Remus (T3 hairpin)", sector=2),
        TrackSegment(840.0, 50000.0, "Straight to T4", is_drs=True, elevation_change_m=-12.0, sector=2),
        TrackSegment(90.0, 48.0, "Schlossgold (T4)", sector=2),
        TrackSegment(350.0, 50000.0, sector=2),
        TrackSegment(120.0, 85.0, "T6 Left", sector=2),
        TrackSegment(240.0, 50000.0, sector=3),
        TrackSegment(110.0, 95.0, "Rindt (T9)", sector=3),
        TrackSegment(180.0, 50000.0, sector=3),
        TrackSegment(120.0, 105.0, "Red Bull Mobile (T10)", sector=3),
        TrackSegment(863.0, 50000.0, sector=3),
    ]
    return Track(
        id="redbullring",
        name="Red Bull Ring (Spielberg)",
        country="Austria",
        total_length_m=4318.0,
        segments=segments,
        years=[2020, 2021, 2022, 2023, 2024, 2025],
        description="High elevation changes and 3 consecutive DRS straights into heavy braking hairpins. Huge tactical deployment playground.",
        lap_record="1:05.619 (Carlos Sainz, McLaren, 2020)",
        typical_downforce="Medium",
        derate_sensitivity="Medium-High"
    )


def create_bahrain_circuit() -> Track:
    segments = [
        TrackSegment(900.0, 50000.0, "Main Straight", is_drs=True, sector=1),
        TrackSegment(85.0, 32.0, "Michael Schumacher Turn (T1)", sector=1),
        TrackSegment(120.0, 65.0, "T2 / T3 Exit", sector=1),
        TrackSegment(450.0, 50000.0, is_drs=True, sector=1),
        TrackSegment(90.0, 60.0, "T4 Outbrake", sector=1),
        TrackSegment(320.0, 50000.0, sector=2),
        TrackSegment(140.0, 95.0, "T5/6 Esses", sector=2),
        TrackSegment(110.0, 80.0, "T7", sector=2),
        TrackSegment(95.0, 35.0, "T8 Hairpin", sector=2),
        TrackSegment(280.0, 50000.0, sector=2),
        TrackSegment(120.0, 48.0, "T9/T10 Tricky Left", sector=2),
        TrackSegment(520.0, 50000.0, "Back Straight", is_drs=True, sector=2),
        TrackSegment(110.0, 120.0, "T11 Sweeper", sector=3),
        TrackSegment(130.0, 210.0, "T12 Flat Right", sector=3),
        TrackSegment(110.0, 85.0, "T13", sector=3),
        TrackSegment(380.0, 50000.0, sector=3),
        TrackSegment(110.0, 75.0, "T14/15 Final Corner", sector=3),
        TrackSegment(462.0, 50000.0, sector=3),
    ]
    return Track(
        id="bahrain",
        name="Bahrain International Circuit (Sakhir)",
        country="Bahrain",
        total_length_m=5412.0,
        segments=segments,
        years=[2020, 2021, 2022, 2023, 2024, 2025],
        description="Tire-degrading traction circuit with 4 DRS straights and punishing braking into Turn 1 and Turn 10.",
        lap_record="1:31.447 (Pedro de la Rosa, McLaren, 2005)",
        typical_downforce="Medium",
        derate_sensitivity="High"
    )


def create_jeddah_circuit() -> Track:
    segments = [
        TrackSegment(650.0, 50000.0, "Main Straight", is_drs=True, sector=1),
        TrackSegment(85.0, 40.0, "T1/2 Chicane", sector=1),
        TrackSegment(320.0, 500.0, sector=1),
        TrackSegment(180.0, 180.0, "T4/5 High-speed flick", sector=1),
        TrackSegment(450.0, 400.0, "T6-T10 Esses", sector=1),
        TrackSegment(280.0, 50000.0, is_drs=True, sector=2),
        TrackSegment(160.0, 95.0, "T13 Banked Hairpin", sector=2),
        TrackSegment(520.0, 600.0, "T14-T16 Blind Sweepers", sector=2),
        TrackSegment(380.0, 50000.0, sector=2),
        TrackSegment(140.0, 160.0, "T22/23 Chicane", sector=2),
        TrackSegment(920.0, 50000.0, "Back Straight (DRS 3)", is_drs=True, sector=3),
        TrackSegment(110.0, 45.0, "T27 Final Hairpin", sector=3),
        TrackSegment(979.0, 50000.0, is_drs=True, sector=3),
    ]
    return Track(
        id="jeddah",
        name="Jeddah Corniche Circuit",
        country="Saudi Arabia",
        total_length_m=6174.0,
        segments=segments,
        years=[2021, 2022, 2023, 2024, 2025],
        description="The fastest street circuit in motorsport history. Over 250 km/h average speed with blind barriers and relentless full throttle.",
        lap_record="1:30.734 (Lewis Hamilton, Mercedes, 2021)",
        typical_downforce="Low-Medium",
        derate_sensitivity="Extreme"
    )


def create_suzuka_circuit() -> Track:
    segments = [
        TrackSegment(600.0, 50000.0, "Main Straight", is_drs=True, sector=1),
        TrackSegment(140.0, 110.0, "T1/T2 First Curve", sector=1),
        TrackSegment(240.0, 160.0, "S-Curves Entry (T3)", sector=1),
        TrackSegment(220.0, 140.0, "S-Curves Mid (T4/5)", sector=1),
        TrackSegment(190.0, 130.0, "Dunlop Curve (T7)", sector=1),
        TrackSegment(320.0, 50000.0, sector=2),
        TrackSegment(90.0, 60.0, "Degner 1 (T8)", sector=2),
        TrackSegment(85.0, 38.0, "Degner 2 (T9)", sector=2),
        TrackSegment(350.0, 50000.0, "Under Bridge Straight", sector=2),
        TrackSegment(110.0, 35.0, "Hairpin (T11)", sector=2),
        TrackSegment(480.0, 500.0, "200R", sector=2),
        TrackSegment(220.0, 85.0, "Spoon Curve 1 (T13)", sector=2),
        TrackSegment(180.0, 95.0, "Spoon Curve 2 (T14)", sector=2),
        TrackSegment(950.0, 50000.0, "Crossover Back Straight", sector=3),
        TrackSegment(160.0, 240.0, "130R (T15 flat out)", sector=3),
        TrackSegment(95.0, 32.0, "Casio Triangle Chicane (T16/17)", sector=3),
        TrackSegment(377.0, 50000.0, sector=3),
    ]
    return Track(
        id="suzuka",
        name="Suzuka International Racing Course",
        country="Japan",
        total_length_m=5807.0,
        segments=segments,
        years=[2022, 2023, 2024, 2025],
        description="The ultimate driver's circuit. Figure-8 layout, punishing Esses, technical Degners, and the legendary 130R.",
        lap_record="1:30.983 (Lewis Hamilton, Mercedes, 2019)",
        typical_downforce="High",
        derate_sensitivity="Medium"
    )


def create_baku_circuit() -> Track:
    segments = [
        TrackSegment(900.0, 50000.0, "Main Pit Straight Exit", is_drs=True, sector=1),
        TrackSegment(90.0, 42.0, "T1 90-degree Left", sector=1),
        TrackSegment(320.0, 50000.0, is_drs=True, sector=1),
        TrackSegment(85.0, 40.0, "T2 90-degree Left", sector=1),
        TrackSegment(480.0, 50000.0, is_drs=True, sector=1),
        TrackSegment(90.0, 45.0, "T3 90-degree Left", sector=1),
        TrackSegment(180.0, 50000.0, sector=2),
        TrackSegment(85.0, 42.0, "T4 90-degree Right", sector=2),
        TrackSegment(240.0, 50000.0, sector=2),
        TrackSegment(90.0, 38.0, "T5/6 Chicane", sector=2),
        TrackSegment(160.0, 50000.0, sector=2),
        TrackSegment(95.0, 22.0, "Castle Section (T8-T10 narrowest point)", sector=2),
        TrackSegment(380.0, 250.0, "T11-T12 Descent", sector=2),
        TrackSegment(110.0, 65.0, "T15 Downhill Braking", sector=2),
        TrackSegment(110.0, 55.0, "T16 Final Real Corner", sector=3),
        TrackSegment(2200.0, 50000.0, "Monster 2.2km Full Throttle Blast (T17-20 flat)", is_drs=True, sector=3),
        TrackSegment(383.0, 50000.0, sector=3),
    ]
    return Track(
        id="baku",
        name="Baku City Circuit",
        country="Azerbaijan",
        total_length_m=6003.0,
        segments=segments,
        years=[2021, 2022, 2023, 2024, 2025],
        description="Extreme contrast: 7.6m narrow medieval castle section paired with the longest full-throttle straight in F1 (2.2 km). Immense derating battle.",
        lap_record="1:43.009 (Charles Leclerc, Ferrari, 2019)",
        typical_downforce="Low",
        derate_sensitivity="Extreme"
    )


def create_lasvegas_circuit() -> Track:
    segments = [
        TrackSegment(550.0, 50000.0, "Start Straight", sector=1),
        TrackSegment(95.0, 38.0, "T1-T2 Hairpin Complex", sector=1),
        TrackSegment(320.0, 50000.0, sector=1),
        TrackSegment(90.0, 42.0, "T3", sector=1),
        TrackSegment(420.0, 50000.0, "Koval Lane (DRS 1)", is_drs=True, sector=1),
        TrackSegment(110.0, 55.0, "T5 Sphere Chicane", sector=2),
        TrackSegment(140.0, 80.0, "T6-T9 Around Sphere", sector=2),
        TrackSegment(1850.0, 50000.0, "The Las Vegas Strip Blast (DRS 2)", is_drs=True, sector=2),
        TrackSegment(110.0, 48.0, "T14 Hard Braking", sector=3),
        TrackSegment(120.0, 55.0, "T15-T16 Left/Right", sector=3),
        TrackSegment(800.0, 50000.0, "Straight to Line", sector=3),
        TrackSegment(156.0, 50000.0, sector=3),
    ]
    return Track(
        id="lasvegas",
        name="Las Vegas Strip Circuit",
        country="United States",
        total_length_m=6201.0,
        segments=segments,
        years=[2023, 2024, 2025],
        description="Cold desert night conditions with a mammoth 1.9km blast down the iconic Las Vegas Strip reaching 355 km/h.",
        lap_record="1:35.490 (Oscar Piastri, McLaren, 2023)",
        typical_downforce="Low",
        derate_sensitivity="Extreme"
    )


def create_interlagos_circuit() -> Track:
    segments = [
        TrackSegment(520.0, 50000.0, "Reta Oposta Exit", sector=1),
        TrackSegment(110.0, 55.0, "Senna 'S' Turn 1 (T1)", elevation_change_m=-6.0, sector=1),
        TrackSegment(95.0, 65.0, "Senna 'S' Turn 2 (T2)", elevation_change_m=-5.0, sector=1),
        TrackSegment(140.0, 110.0, "Curva do Sol (T3)", sector=1),
        TrackSegment(720.0, 50000.0, "Reta Oposta (DRS 1)", is_drs=True, sector=2),
        TrackSegment(95.0, 50.0, "Descida do Lago (T4)", sector=2),
        TrackSegment(110.0, 75.0, "Descida do Lago (T5)", sector=2),
        TrackSegment(280.0, 50000.0, sector=2),
        TrackSegment(120.0, 85.0, "Ferradura (T6/7)", sector=2),
        TrackSegment(90.0, 38.0, "Bico de Pato (T8)", sector=2),
        TrackSegment(110.0, 35.0, "Mergulho (T9)", sector=2),
        TrackSegment(130.0, 48.0, "Juncao (T10)", elevation_change_m=4.0, sector=3),
        TrackSegment(450.0, 500.0, "Subida dos Boxes (Steep Uphill)", elevation_change_m=16.0, is_drs=True, sector=3),
        TrackSegment(680.0, 50000.0, "Arquibancadas Straight", is_drs=True, sector=3),
        TrackSegment(649.0, 50000.0, sector=3),
    ]
    return Track(
        id="interlagos",
        name="Autodromo Jose Carlos Pace (Interlagos)",
        country="Brazil",
        total_length_m=4309.0,
        segments=segments,
        years=[2021, 2022, 2023, 2024, 2025],
        description="Anti-clockwise amphitheater with steep elevation, Senna S descent, and punishing uphill drag up Subida dos Boxes.",
        lap_record="1:10.540 (Valtteri Bottas, Mercedes, 2018)",
        typical_downforce="Medium",
        derate_sensitivity="Medium-High"
    )


def create_cota_circuit() -> Track:
    segments = [
        TrackSegment(480.0, 50000.0, "Main Straight Uphill", elevation_change_m=28.0, is_drs=True, sector=1),
        TrackSegment(85.0, 25.0, "Turn 1 Blind Crest Hairpin", sector=1),
        TrackSegment(220.0, 280.0, "Downhill run into Esses", elevation_change_m=-18.0, sector=1),
        TrackSegment(180.0, 180.0, "T3 Maggotts clone", sector=1),
        TrackSegment(160.0, 140.0, "T4 Becketts clone", sector=1),
        TrackSegment(170.0, 120.0, "T5 Chapel clone", sector=1),
        TrackSegment(180.0, 95.0, "T6-T9 Technical S", sector=1),
        TrackSegment(110.0, 55.0, "T11 Hairpin", sector=2),
        TrackSegment(1050.0, 50000.0, "Back Straight (DRS 2)", is_drs=True, sector=2),
        TrackSegment(95.0, 35.0, "T12 Heavy Braking 330->75 km/h", sector=3),
        TrackSegment(110.0, 60.0, "T13-T15 Stadium section", sector=3),
        TrackSegment(240.0, 130.0, "T16-T18 Triple Apex Carrousel", sector=3),
        TrackSegment(120.0, 75.0, "T19 Fast Sweeper", sector=3),
        TrackSegment(110.0, 48.0, "T20 Final Turn", sector=3),
        TrackSegment(203.0, 50000.0, sector=3),
    ]
    return Track(
        id="cota",
        name="Circuit of the Americas (COTA)",
        country="United States",
        total_length_m=5513.0,
        segments=segments,
        years=[2021, 2022, 2023, 2024, 2025],
        description="Massive 11% gradient climb into Turn 1, Silverstone-inspired Esses, and a 1km back straight.",
        lap_record="1:36.169 (Charles Leclerc, Ferrari, 2019)",
        typical_downforce="High",
        derate_sensitivity="High"
    )


def create_albertpark_circuit() -> Track:
    segments = [
        TrackSegment(480.0, 50000.0, "Main Straight", is_drs=True, sector=1),
        TrackSegment(90.0, 45.0, "T1/T2 Chicane", sector=1),
        TrackSegment(380.0, 50000.0, is_drs=True, sector=1),
        TrackSegment(85.0, 38.0, "T3 Braking zone", sector=1),
        TrackSegment(95.0, 55.0, "T4", sector=1),
        TrackSegment(350.0, 50000.0, sector=2),
        TrackSegment(110.0, 75.0, "T6 Fast Right", sector=2),
        TrackSegment(720.0, 50000.0, "Lakeside Fast Curve (DRS 3)", is_drs=True, sector=2),
        TrackSegment(140.0, 110.0, "T9/T10 High-speed chicane 240km/h", sector=2),
        TrackSegment(420.0, 50000.0, sector=3),
        TrackSegment(110.0, 60.0, "T11 Sweeper", sector=3),
        TrackSegment(95.0, 42.0, "T13", sector=3),
        TrackSegment(110.0, 55.0, "T14 Final Corner", sector=3),
        TrackSegment(2083.0, 50000.0, sector=3),
    ]
    return Track(
        id="albertpark",
        name="Albert Park Circuit (Melbourne)",
        country="Australia",
        total_length_m=5278.0,
        segments=segments,
        years=[2022, 2023, 2024, 2025],
        description="Fast semi-street parkland track with 4 DRS zones and ultra-high-speed sweepers.",
        lap_record="1:19.813 (Charles Leclerc, Ferrari, 2024)",
        typical_downforce="Medium",
        derate_sensitivity="High"
    )


def create_hungaroring_circuit() -> Track:
    segments = [
        TrackSegment(780.0, 50000.0, "Main Straight", is_drs=True, sector=1),
        TrackSegment(90.0, 40.0, "T1 Downhill Hairpin", sector=1),
        TrackSegment(320.0, 50000.0, is_drs=True, sector=1),
        TrackSegment(95.0, 48.0, "T2 Downhill Off-camber Left", sector=1),
        TrackSegment(110.0, 95.0, "T3 Fast Right", sector=1),
        TrackSegment(380.0, 50000.0, sector=2),
        TrackSegment(120.0, 110.0, "T4 Fast Blind Left", sector=2),
        TrackSegment(160.0, 65.0, "T5 Long Right", sector=2),
        TrackSegment(90.0, 38.0, "T6/T7 Chicane", sector=2),
        TrackSegment(220.0, 50000.0, sector=2),
        TrackSegment(120.0, 75.0, "T8-T11 Flowing Infield", sector=2),
        TrackSegment(110.0, 55.0, "T12 90-degree Right", sector=3),
        TrackSegment(130.0, 45.0, "T13 Long Left", sector=3),
        TrackSegment(140.0, 52.0, "T14 Final Long Corner", sector=3),
        TrackSegment(1506.0, 50000.0, sector=3),
    ]
    return Track(
        id="hungaroring",
        name="Hungaroring (Budapest)",
        country="Hungary",
        total_length_m=4381.0,
        segments=segments,
        years=[2020, 2021, 2022, 2023, 2024, 2025],
        description="Monaco without walls. Relentless medium-speed corners testing mechanical grip and MGU-K corner exit punch.",
        lap_record="1:16.627 (Lewis Hamilton, Mercedes, 2020)",
        typical_downforce="High",
        derate_sensitivity="Low-Medium"
    )


def create_zandvoort_circuit() -> Track:
    segments = [
        TrackSegment(580.0, 50000.0, "Main Straight", is_drs=True, sector=1),
        TrackSegment(95.0, 32.0, "Tarzan Bocht (T1 180 deg)", sector=1),
        TrackSegment(280.0, 50000.0, sector=1),
        TrackSegment(110.0, 85.0, "Gerlachbocht (T2)", sector=1),
        TrackSegment(140.0, 60.0, "Hugenholtzbocht (T3 19 deg banking!)", sector=1),
        TrackSegment(480.0, 50000.0, sector=2),
        TrackSegment(120.0, 140.0, "Slotemaker (T6)", sector=2),
        TrackSegment(160.0, 110.0, "Scheivlak (T7 240km/h downhill)", sector=2),
        TrackSegment(110.0, 75.0, "Mastersbocht (T8)", sector=2),
        TrackSegment(180.0, 50000.0, sector=2),
        TrackSegment(110.0, 45.0, "T9-T10 Infield hairpin", sector=2),
        TrackSegment(240.0, 50000.0, sector=3),
        TrackSegment(95.0, 42.0, "Hans Ernst Bocht (T11/12)", sector=3),
        TrackSegment(180.0, 50000.0, sector=3),
        TrackSegment(120.0, 95.0, "Kumhobocht (T13)", sector=3),
        TrackSegment(220.0, 120.0, "Arie Luyendyk Bocht (T14 18 deg banking DRS)", is_drs=True, sector=3),
        TrackSegment(1039.0, 50000.0, sector=3),
    ]
    return Track(
        id="zandvoort",
        name="Circuit Zandvoort",
        country="Netherlands",
        total_length_m=4259.0,
        segments=segments,
        years=[2021, 2022, 2023, 2024, 2025],
        description="Dramatic seaside sand dunes featuring steep 18-degree Indianapolis-style banked corners.",
        lap_record="1:11.097 (Lewis Hamilton, Mercedes, 2021)",
        typical_downforce="High",
        derate_sensitivity="Medium"
    )


# Catalog mapping of all Grand Prix circuits
_ALL_CIRCUITS: Dict[str, Track] = {
    "monza": create_monza_circuit(),
    "silverstone": create_silverstone_circuit(),
    "spa": create_spa_circuit(),
    "monaco": create_monaco_circuit(),
    "redbullring": create_redbullring_circuit(),
    "bahrain": create_bahrain_circuit(),
    "jeddah": create_jeddah_circuit(),
    "suzuka": create_suzuka_circuit(),
    "baku": create_baku_circuit(),
    "lasvegas": create_lasvegas_circuit(),
    "interlagos": create_interlagos_circuit(),
    "cota": create_cota_circuit(),
    "albertpark": create_albertpark_circuit(),
    "hungaroring": create_hungaroring_circuit(),
    "zandvoort": create_zandvoort_circuit(),
}

# Grand Prix calendar round order by year
_CALENDAR_BY_YEAR: Dict[int, List[str]] = {
    2025: [
        "albertpark", "jeddah", "bahrain", "suzuka", "monaco", "monza", 
        "redbullring", "silverstone", "spa", "zandvoort", "baku", 
        "cota", "interlagos", "lasvegas"
    ],
    2024: [
        "bahrain", "jeddah", "albertpark", "suzuka", "monaco", "redbullring",
        "silverstone", "hungaroring", "spa", "zandvoort", "monza",
        "baku", "cota", "interlagos", "lasvegas"
    ],
    2023: [
        "bahrain", "jeddah", "albertpark", "monaco", "redbullring",
        "silverstone", "hungaroring", "spa", "zandvoort", "monza",
        "suzuka", "cota", "interlagos", "lasvegas"
    ],
    2022: [
        "bahrain", "jeddah", "albertpark", "monaco", "baku", "silverstone",
        "redbullring", "hungaroring", "spa", "zandvoort", "monza",
        "suzuka", "cota", "interlagos"
    ],
    2021: [
        "bahrain", "monaco", "baku", "redbullring", "silverstone",
        "hungaroring", "spa", "zandvoort", "monza", "cota",
        "interlagos", "jeddah"
    ],
    2020: [
        "redbullring", "hungaroring", "silverstone", "spa", "monza", "bahrain"
    ],
}


def list_seasons() -> List[int]:
    """List available F1 seasons/years."""
    return sorted(list(_CALENDAR_BY_YEAR.keys()), reverse=True)


def get_circuit(name_or_id: str) -> Track:
    """Retrieve track by ID or case-insensitive search."""
    clean = name_or_id.lower().replace(" ", "").replace("_", "").replace("-", "")
    for trk_id, trk in _ALL_CIRCUITS.items():
        if trk_id in clean or clean in trk_id:
            return trk
        if clean in trk.name.lower().replace(" ", ""):
            return trk
    raise KeyError(f"Circuit '{name_or_id}' not found. Available: {list(_ALL_CIRCUITS.keys())}")


def list_circuits(year: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    List circuits, optionally filtered by World Championship season year.
    Returns ordered calendar if year is provided.
    """
    if year is not None and year in _CALENDAR_BY_YEAR:
        ordered_ids = _CALENDAR_BY_YEAR[year]
        results = []
        for round_num, trk_id in enumerate(ordered_ids, start=1):
            if trk_id in _ALL_CIRCUITS:
                trk = _ALL_CIRCUITS[trk_id]
                results.append({
                    "round": round_num,
                    "id": trk.id,
                    "name": trk.name,
                    "country": trk.country,
                    "length_m": trk.total_length_m,
                    "year": year,
                    "downforce": trk.typical_downforce,
                    "derate_sensitivity": trk.derate_sensitivity,
                    "lap_record": trk.lap_record,
                    "description": trk.description,
                })
        return results

    # Return all unique circuits across all seasons
    return [
        {
            "id": trk.id,
            "name": trk.name,
            "country": trk.country,
            "length_m": trk.total_length_m,
            "years": trk.years,
            "downforce": trk.typical_downforce,
            "derate_sensitivity": trk.derate_sensitivity,
            "lap_record": trk.lap_record,
            "description": trk.description,
        }
        for trk in _ALL_CIRCUITS.values()
    ]
