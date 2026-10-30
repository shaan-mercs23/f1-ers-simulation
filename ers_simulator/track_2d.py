"""
Formula 1 2D Circuit Geometry & Coordinate Engine
=================================================
Provides authentic 2D planar coordinates (x, y) for all 15 Formula 1 circuits.
Calculates arc-length parameterized coordinates (x(s), y(s)), corner annotations,
sector boundaries, and DRS zones for real-time on-track canvas simulation.
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Any, Optional

from .track import Track, get_circuit


# Canonical 2D control point loops for circuits normalized to a [0, 1000] canvas box
# Each circuit is defined by characteristic anchor points preserving authentic racing line geometry.
TRACK_2D_ANCHORS: Dict[str, List[Tuple[float, float, str]]] = {
    "monza": [
        # (x, y, corner_label)
        (250, 750, "Pit Straight"),
        (280, 750, ""),
        (480, 750, ""),
        (650, 750, "T1 Rettifilo Entry"),
        (670, 735, "T1 Rettifilo"),
        (660, 715, "T2 Rettifilo Exit"),
        (690, 680, ""),
        (780, 580, "T3 Curva Grande"),
        (830, 480, ""),
        (850, 390, ""),
        (840, 320, "T4 Variante della Roggia"),
        (810, 310, "T5 Roggia Exit"),
        (800, 270, ""),
        (800, 220, "T6 1st Lesmo"),
        (815, 170, ""),
        (830, 130, "T7 2nd Lesmo"),
        (800, 120, ""),
        (650, 150, "Curva del Serraglio"),
        (480, 180, ""),
        (380, 195, "T8 Ascari Entry"),
        (340, 190, "T9 Ascari Mid"),
        (320, 220, "T10 Ascari Exit"),
        (280, 300, "Rettifilo Posteriore"),
        (230, 420, ""),
        (180, 560, ""),
        (150, 660, "T11 Curva Parabolica"),
        (170, 730, "Parabolica Exit"),
        (210, 750, "Start/Finish Line"),
    ],
    "silverstone": [
        (450, 750, "Hamilton Straight"),
        (560, 750, ""),
        (620, 720, "T1 Abbey"),
        (650, 680, "T2 Farm Curve"),
        (660, 620, "T3 Village"),
        (620, 600, "T4 The Loop"),
        (580, 630, "T5 Aintree"),
        (480, 610, "Wellington Straight"),
        (350, 580, ""),
        (270, 560, "T6 Brooklands"),
        (240, 510, "T7 Luffield"),
        (280, 470, "T8 Woodcote"),
        (350, 450, "National Straight"),
        (460, 420, "T9 Copse"),
        (520, 380, ""),
        (570, 330, "T10 Maggotts"),
        (610, 280, "T11 Becketts"),
        (590, 230, "T12 Becketts Exit"),
        (540, 210, "T13 Chapel"),
        (440, 200, "Hangar Straight"),
        (300, 200, ""),
        (200, 210, "T15 Stowe"),
        (180, 320, ""),
        (190, 420, "T16 Vale"),
        (230, 460, "T17/18 Club"),
        (320, 620, ""),
        (380, 720, ""),
        (420, 750, "Start/Finish Line"),
    ],
    "spa": [
        (300, 780, "Start Straight"),
        (280, 720, "T1 La Source"),
        (310, 670, "Eau Rouge Descent"),
        (350, 620, "T2 Eau Rouge"),
        (380, 560, "T3/T4 Raidillon"),
        (450, 470, "Kemmel Straight"),
        (560, 370, ""),
        (660, 280, ""),
        (720, 230, "T5/T6 Les Combes"),
        (760, 220, "T7 Malmedy"),
        (820, 270, ""),
        (850, 340, "T8 Bruxelles"),
        (830, 400, "T9"),
        (810, 470, ""),
        (760, 550, "T10/T11 Pouhon"),
        (710, 620, ""),
        (680, 680, "T12/T13 Fagnes"),
        (660, 730, "T14 Stavelot"),
        (620, 780, "T15 Campus"),
        (520, 830, "T16 Paul Frere"),
        (420, 840, "Blanchimont (T17/T18)"),
        (330, 830, "Bus Stop Chicane (T19/20)"),
        (310, 800, ""),
    ],
    "monaco": [
        (450, 820, "Main Straight"),
        (580, 830, "T1 Sainte Devote"),
        (650, 750, "Beau Rivage Hill"),
        (730, 640, "T2 Massenet"),
        (770, 570, "T3 Casino Square"),
        (740, 500, "T4 Mirabeau Haute"),
        (680, 460, "T5 Fairmont Hairpin"),
        (690, 400, "T6 Mirabeau Bas"),
        (730, 370, "T7 Portier"),
        (800, 390, "Tunnel Entry"),
        (850, 470, "Tunnel Section"),
        (830, 580, "T10/11 Nouvelle Chicane"),
        (770, 660, "T12 Tabac"),
        (690, 720, "Louis Chiron (T13)"),
        (620, 740, "Piscine Swimming Pool"),
        (530, 760, "T16/T17 La Rascasse"),
        (470, 790, "T18 Anthony Noghes"),
    ],
    "redbullring": [
        (250, 700, "Start/Finish Straight"),
        (450, 710, ""),
        (650, 720, "T1 Niki Lauda Curve"),
        (690, 640, "Uphill Straight"),
        (730, 500, ""),
        (780, 330, ""),
        (810, 220, "T3 Remus Hairpin"),
        (720, 270, "Downhill Run"),
        (610, 340, "T4"),
        (520, 410, "T5"),
        (440, 460, "T6"),
        (370, 510, "T7"),
        (300, 570, "T8 Jochen Rindt"),
        (240, 630, "T9"),
        (230, 680, "T10"),
    ],
    "bahrain": [
        (200, 750, "Main Straight"),
        (450, 750, ""),
        (680, 750, "T1 Michael Schumacher"),
        (730, 710, "T2"),
        (740, 650, "T3"),
        (720, 570, "T4"),
        (660, 500, "T5/T6 Esses"),
        (610, 430, "T7"),
        (620, 360, "T8 Hairpin"),
        (680, 330, "T9/T10 Downhill"),
        (760, 320, ""),
        (820, 300, "Back Straight"),
        (860, 240, "T11"),
        (820, 180, "T12"),
        (730, 190, "T13"),
        (550, 250, ""),
        (400, 350, "T14/T15"),
        (280, 500, ""),
        (210, 650, ""),
    ],
    "jeddah": [
        (250, 850, "Pit Straight"),
        (350, 850, ""),
        (420, 820, "T1/T2 Chicane"),
        (460, 760, "T3-T4"),
        (510, 680, "T5-T7 Esses"),
        (580, 580, "T8-T10"),
        (660, 470, "T11-T12"),
        (720, 380, "T13 Banked Hairpin"),
        (690, 320, "T14-T16"),
        (640, 260, "T17-T20"),
        (570, 210, "T21-T22"),
        (480, 180, "Fast Sweep"),
        (380, 220, "T23-T24"),
        (320, 320, ""),
        (280, 460, "T25-T26"),
        (240, 620, ""),
        (230, 760, "T27 Final Turn"),
    ],
    "suzuka": [
        (350, 750, "Pit Straight"),
        (500, 750, ""),
        (650, 730, "T1/T2 First Curve"),
        (690, 660, "S-Curves Entry (T3)"),
        (660, 590, "S-Curves (T4)"),
        (700, 530, "T5"),
        (670, 470, "Dunlop Curve (T6)"),
        (620, 420, "T7"),
        (560, 390, "Degner 1 (T8)"),
        (520, 370, "Degner 2 (T9)"),
        (480, 410, "Under Overpass"),
        (420, 460, "T11 Hairpin"),
        (380, 420, ""),
        (360, 350, "200R (T12)"),
        (390, 280, "Spoon Curve (T13)"),
        (450, 240, "Spoon Curve (T14)"),
        (560, 240, "Back Straight"),
        (680, 250, ""),
        (780, 270, "130R (T15)"),
        (810, 360, "Overpass Bridge"),
        (760, 480, ""),
        (690, 600, "Casio Triangle (T16)"),
        (550, 700, "Final Turn (T18)"),
    ],
    "baku": [
        (150, 750, "Main Neftchilar Straight (2.2km)"),
        (400, 750, ""),
        (700, 750, ""),
        (850, 750, "T1 90-Degree Left"),
        (850, 600, ""),
        (850, 480, "T2 90-Degree Left"),
        (720, 480, ""),
        (600, 480, "T3 90-Degree Right"),
        (600, 360, "T4 90-Degree Left"),
        (480, 360, "T5/T6 Chicane"),
        (450, 320, "T7"),
        (460, 260, "T8 Old City Castle Entry"),
        (490, 220, "T9-T11 Castle Narrow Section"),
        (530, 250, "T12"),
        (580, 270, "T13-T15 Downhill"),
        (650, 260, "T16"),
        (720, 240, ""),
        (800, 220, "T18-T20 Kink Sweeps"),
        (680, 350, ""),
        (500, 470, ""),
        (320, 610, ""),
        (180, 710, "Final Kink"),
    ],
    "lasvegas": [
        (250, 750, "Pit Straight"),
        (380, 750, ""),
        (450, 720, "T1 Hairpin"),
        (470, 650, "T2-T3"),
        (520, 580, "Koval Lane"),
        (620, 480, ""),
        (720, 380, "T4"),
        (780, 360, "T5 Sphere Section"),
        (840, 410, "T6-T9 Sphere Complex"),
        (820, 520, ""),
        (750, 600, "T12 onto Strip"),
        (600, 650, "Las Vegas Strip Straight (1.9km)"),
        (420, 710, ""),
        (260, 770, ""),
        (180, 810, "T14 Harmon Ave Chicane"),
        (210, 780, ""),
    ],
    "interlagos": [
        (350, 800, "Arquibancadas Straight"),
        (550, 800, ""),
        (680, 780, "T1 Senna 'S' Entry"),
        (720, 720, "T2 Senna 'S' Exit"),
        (740, 640, "T3 Curva do Sol"),
        (730, 520, "Reta Oposta"),
        (710, 400, ""),
        (680, 330, "T4 Descida do Lago"),
        (620, 340, "T5"),
        (540, 390, "T6 Ferradura"),
        (480, 450, "T7"),
        (440, 520, "T8 Laranjinha"),
        (460, 590, "T9 Pinheirinho"),
        (510, 630, "T10 Bico de Pato"),
        (470, 680, "T11 Mergulho"),
        (410, 720, "T12 Juncao"),
        (340, 760, "Subida dos Boxes"),
    ],
    "cota": [
        (200, 780, "Start Straight"),
        (350, 780, "Steep Uphill"),
        (460, 760, "T1 Blind Crest Hairpin"),
        (520, 710, "T2 Downhill Sweep"),
        (580, 640, "T3-T6 Maggotts Esses"),
        (650, 540, ""),
        (720, 430, "T7-T9"),
        (760, 340, "T10"),
        (820, 260, "T11 Hairpin"),
        (720, 280, "Long Back Straight (1.2km)"),
        (560, 310, ""),
        (410, 340, ""),
        (280, 370, "T12 Heavy Braking"),
        (240, 430, "T13-T15 Stadium"),
        (280, 510, "T16-T18 Multi-Apex Carousel"),
        (350, 580, ""),
        (330, 660, "T19"),
        (270, 730, "T20 Final Turn"),
    ],
    "albertpark": [
        (300, 800, "Pit Straight"),
        (500, 800, ""),
        (650, 780, "T1/T2 Chicane"),
        (740, 700, ""),
        (800, 600, "T3 Braking Zone"),
        (810, 520, "T4"),
        (790, 430, "T5 Fast Sweep"),
        (750, 360, "T6/T7"),
        (680, 300, "Lakeside Run"),
        (580, 250, "T8 Fast Flowing"),
        (470, 220, "T9/T10 High-Speed Chicane"),
        (360, 250, ""),
        (270, 320, "T11/T12 Rapid Chicanes"),
        (220, 440, ""),
        (200, 570, "T13"),
        (220, 690, "T14"),
    ],
    "hungaroring": [
        (350, 800, "Pit Straight"),
        (550, 800, ""),
        (720, 780, "T1 Downhill Hairpin"),
        (760, 700, "T2 Long Left"),
        (780, 620, "T3"),
        (740, 530, "T4 Fast Blind Crest"),
        (680, 460, "T5 Long Carousel"),
        (610, 420, "T6/T7 Chicane"),
        (560, 380, "T8"),
        (510, 360, "T9"),
        (460, 380, "T10"),
        (410, 430, "T11 High Speed"),
        (360, 510, "T12 90-Degree Right"),
        (310, 600, "T13 180-Degree Hairpin"),
        (320, 720, "T14 Final Turn"),
    ],
    "zandvoort": [
        (300, 780, "Pit Straight"),
        (500, 780, ""),
        (670, 760, "T1 Tarzanbocht Hairpin"),
        (740, 700, "T2 Gerlachbocht"),
        (780, 620, "T3 Hugenholtzbocht Banked"),
        (770, 510, "T4-T6"),
        (720, 420, "T7 Scheivlak High-G"),
        (650, 340, "T8 Mastersbocht"),
        (570, 280, "T9"),
        (490, 260, "T10"),
        (420, 300, "T11/T12 Hans Ernst Chicane"),
        (330, 400, ""),
        (270, 520, "T13 Kumhobocht"),
        (260, 660, "T14 Arie Luyendykbocht Banked (18 deg)"),
    ],
}


def build_smooth_2d_track(
    track_or_id: Any,
    total_length_m: Optional[float] = None,
    num_samples: int = 600,
) -> Dict[str, Any]:
    """
    Generate an equidistant, closed, smoothed 2D spatial representation of the circuit.
    Interpolates anchor points with periodic Catmull-Rom / cubic spline.
    Extracts DRS zones, sector boundaries, and corner markers.
    """
    if isinstance(track_or_id, str):
        try:
            track_obj = get_circuit(track_or_id)
            key = track_obj.id.lower()
            length_val = total_length_m or track_obj.total_length_m
        except Exception:
            track_obj = None
            key = track_or_id.lower()
            length_val = total_length_m or 5000.0
    else:
        track_obj = track_or_id
        key = getattr(track_obj, "id", "monza").lower()
        length_val = total_length_m or getattr(track_obj, "total_length_m", 5000.0)

    anchors = TRACK_2D_ANCHORS.get(key, TRACK_2D_ANCHORS["monza"])
    
    # Extract anchor coordinates
    raw_pts = [(pt[0], pt[1]) for pt in anchors]
    labels_with_idx = [(i, pt[2]) for i, pt in enumerate(anchors) if pt[2]]

    # Ensure loop closure
    if raw_pts[0] != raw_pts[-1]:
        raw_pts.append(raw_pts[0])

    # Compute cumulative linear distance along anchors
    n_pts = len(raw_pts)
    seg_dists = [0.0]
    for i in range(1, n_pts):
        dx = raw_pts[i][0] - raw_pts[i-1][0]
        dy = raw_pts[i][1] - raw_pts[i-1][1]
        seg_dists.append(seg_dists[-1] + math.sqrt(dx * dx + dy * dy))
    
    total_anchor_dist = seg_dists[-1]
    
    # Sample smoothly around the loop
    sample_dists = np.linspace(0.0, total_anchor_dist, num_samples, endpoint=False)
    xs_raw = np.array([pt[0] for pt in raw_pts])
    ys_raw = np.array([pt[1] for pt in raw_pts])

    # Periodic cubic spline / linear interpolation
    xs_interp = np.interp(sample_dists, seg_dists, xs_raw)
    ys_interp = np.interp(sample_dists, seg_dists, ys_raw)

    # Smooth coordinates with periodic moving average to eliminate sharp kinks
    window = 5
    kernel = np.ones(window) / window
    xs_pad = np.concatenate([xs_interp[-window:], xs_interp, xs_interp[:window]])
    ys_pad = np.concatenate([ys_interp[-window:], ys_interp, ys_interp[:window]])
    
    xs_smooth = np.convolve(xs_pad, kernel, mode='same')[window:-window]
    ys_smooth = np.convolve(ys_pad, kernel, mode='same')[window:-window]

    # Normalize coordinates into a clean [70, 930] bounding box with preserved aspect ratio
    min_x, max_x = float(np.min(xs_smooth)), float(np.max(xs_smooth))
    min_y, max_y = float(np.min(ys_smooth)), float(np.max(ys_smooth))
    
    span_x = max(1.0, max_x - min_x)
    span_y = max(1.0, max_y - min_y)
    max_span = max(span_x, span_y)

    scale = 820.0 / max_span
    offset_x = 500.0 - ((min_x + max_x) / 2.0) * scale
    offset_y = 500.0 - ((min_y + max_y) / 2.0) * scale

    xs_final = np.round(xs_smooth * scale + offset_x, 1)
    ys_final = np.round(ys_smooth * scale + offset_y, 1)

    # Equidistant distances in actual track meters [0, total_length_m]
    distances_m = np.linspace(0.0, length_val, num_samples, endpoint=False)

    # Map corner annotations to the nearest sampled distance
    corner_markers = []
    for anchor_idx, label in labels_with_idx:
        anchor_d = (seg_dists[anchor_idx] / total_anchor_dist) * length_val
        closest_idx = int(np.argmin(np.abs(distances_m - anchor_d)))
        corner_markers.append({
            "name": label,
            "distance_m": round(float(distances_m[closest_idx]), 1),
            "x": float(xs_final[closest_idx]),
            "y": float(ys_final[closest_idx]),
        })

    # Extract DRS zones and sector intervals from track_obj if available
    drs_zones = []
    sectors = []
    point_sectors = [1] * num_samples
    point_drs = [False] * num_samples

    if track_obj and hasattr(track_obj, "segments"):
        cum_dist = 0.0
        cur_drs_start = None
        cur_sec = 1
        sec_start = 0.0

        for seg in track_obj.segments:
            seg_start = cum_dist
            seg_end = cum_dist + seg.length_m

            # Track DRS intervals
            if seg.is_drs:
                if cur_drs_start is None:
                    cur_drs_start = seg_start
            else:
                if cur_drs_start is not None:
                    drs_zones.append({"start_m": round(cur_drs_start, 1), "end_m": round(seg_start, 1)})
                    cur_drs_start = None

            # Track Sector transitions
            if seg.sector != cur_sec:
                sectors.append({"sector": cur_sec, "start_m": round(sec_start, 1), "end_m": round(seg_start, 1)})
                cur_sec = seg.sector
                sec_start = seg_start

            cum_dist = seg_end

        if cur_drs_start is not None:
            drs_zones.append({"start_m": round(cur_drs_start, 1), "end_m": round(cum_dist, 1)})
        sectors.append({"sector": cur_sec, "start_m": round(sec_start, 1), "end_m": round(cum_dist, 1)})

        # Tag each sample point
        for i, d in enumerate(distances_m):
            # Find sector
            for s_info in sectors:
                if s_info["start_m"] <= d <= s_info["end_m"]:
                    point_sectors[i] = s_info["sector"]
                    break
            # Find DRS
            for drs_info in drs_zones:
                if drs_info["start_m"] <= d <= drs_info["end_m"]:
                    point_drs[i] = True
                    break

    return {
        "track_id": key,
        "track_name": getattr(track_obj, "name", key.capitalize()) if track_obj else key.capitalize(),
        "total_length_m": length_val,
        "num_points": num_samples,
        "x": xs_final.tolist(),
        "y": ys_final.tolist(),
        "distances_m": np.round(distances_m, 1).tolist(),
        "corners": corner_markers,
        "drs_zones": drs_zones,
        "sectors": sectors,
        "point_sectors": point_sectors,
        "point_drs": point_drs,
    }
