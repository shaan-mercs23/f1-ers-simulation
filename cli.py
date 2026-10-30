"""
Command-Line Interface (CLI) for F1 ERS Simulation and Driver Comparison
========================================================================
Usage:
    python cli.py compare --drivers ver,ham,alo,nor --track monza --year 2024
    python cli.py list-seasons
    python cli.py list-tracks --year 2024
    python cli.py list-drivers --year 2024
    python cli.py export-csv --drivers ver,ham --track spa --output spa_telemetry.csv
"""

import argparse
import sys
import os
from typing import List, Optional

from ers_simulator.track import get_circuit, list_circuits, list_seasons
from ers_simulator.driver import get_driver_preset, list_driver_presets, DriverProfile
from ers_simulator.ers_strategy import ERSMode
from ers_simulator.solver import LapSimulator, format_lap_time
from ers_simulator.telemetry import TelemetryComparison
from ers_simulator.qualifying import QualifyingSimulator, simulate_qualifying_session
from ers_simulator.report import generate_html_report, generate_matplotlib_script


def print_banner():
    banner = r"""
=============================================================================
 FORMULA 1 ENERGY RECOVERY SYSTEM (ERS) SIMULATOR & MULTI-DRIVER LAB
 Complete F1 Driver Database & Multi-Season Track Calendar (2020 - 2025+)
 1.6L V6 Turbo Hybrid | MGU-K (120 kW) | MGU-H Direct DC Feed | FIA 4MJ Limit
=============================================================================
"""
    print(banner)


def cmd_list_seasons(args):
    print("\n--- AVAILABLE FORMULA 1 CHAMPIONSHIP SEASONS ---")
    seasons = list_seasons()
    for yr in seasons:
        tracks = list_circuits(year=yr)
        drivers = list_driver_presets(year=yr)
        print(f"  • Season {yr}: {len(tracks)} Grand Prix circuits | {len(drivers)} competing drivers")
    print()


def cmd_list_tracks(args):
    year_str = f" ({args.year} CALENDAR)" if args.year else " (ALL SEASONS)"
    print(f"\n--- FORMULA 1 GRAND PRIX CIRCUITS{year_str} ---")
    circuits = list_circuits(year=args.year)
    for c in circuits:
        round_prefix = f"Round {c['round']:>2}: " if "round" in c else "         "
        print(f"  {round_prefix}{c['id'].upper():<12} | {c['name']:<40} | {c['length_m']:>5.0f} m | Downforce: {c['downforce']}")
        print(f"             Record: {c['lap_record']}")
        print(f"             {c['description']}\n")


def cmd_list_drivers(args):
    year_str = f" ({args.year} GRID)" if args.year else " (ALL SEASONS)"
    print(f"\n--- FORMULA 1 DRIVER DATABASE{year_str} ---")
    drivers = list_driver_presets(year=args.year)
    for d in drivers:
        num_str = f"#{d['number']:<2}" if d['number'] else "   "
        print(f"  • {d['code']:<4} | {num_str} {d['name']:<20} | {d['team']:<25} | {d['country']}")
        print(f"    Traits: Brake: {d['braking_offset_m']:+.1f}m | L&C: {d['lift_and_coast_m']:>2.0f}m | Throttle: {d['throttle_aggression']:.2f}x | Style: {d['notes']}\n")


def parse_ers_mode(mode_str: str) -> ERSMode:
    s = mode_str.lower().strip()
    for m in ERSMode:
        if s in m.value or m.value in s:
            return m
    return ERSMode.HOTLAP_QUALI


def resolve_drivers_list(drivers_arg: str, year: int = None) -> List[DriverProfile]:
    """Parse comma-separated driver list or resolve keywords 'all' / 'grid'."""
    raw = drivers_arg.lower().strip()
    if raw in ("all", "grid", "full"):
        presets = list_driver_presets(year=year)
        return [get_driver_preset(p["code"], year=year) for p in presets]
    
    codes = [c.strip().lower() for c in drivers_arg.split(",") if c.strip()]
    if not codes:
        codes = ["ver", "ham", "nor", "lec"]

    drivers = []
    for code in codes:
        try:
            drv = get_driver_preset(code, year=year)
            drivers.append(drv)
        except KeyError as e:
            print(f"Warning: {e}. Skipping.")
    return drivers


def cmd_compare(args):
    track_key = args.track.lower()
    try:
        track = get_circuit(track_key)
    except KeyError as e:
        print(f"Error: {e}")
        sys.exit(1)

    drivers = resolve_drivers_list(args.drivers, year=args.year)
    if args.strategy:
        strategy_mode = parse_ers_mode(args.strategy)
        for drv in drivers:
            drv.ers_mode = strategy_mode

    if not drivers:
        print("Error: No valid drivers specified.")
        sys.exit(1)

    print_banner()
    year_info = f" [Season {args.year}]" if args.year else ""
    print(f"Circuit: {track.name}{year_info} ({track.total_length_m:,.0f} m)")
    print(f"Simulating {len(drivers)} drivers at spatial resolution dx = {args.dx}m...\n")

    sim = LapSimulator()
    results = []
    for drv in drivers:
        res = sim.simulate(track, drv, dx=args.dx, year=args.year)
        results.append(res)

    comparison = TelemetryComparison(results)

    # Print Leaderboard Table
    print(f"{'POS':<4} | {'DRIVER':<20} | {'TEAM':<20} | {'LAP TIME':<9} | {'GAP':<9} | {'V_MAX':<7} | {'DEPLOY':<8} | {'HARVEST':<8} | {'NET ΔSoC':<8} | {'DERATE':<9}")
    print("-" * 135)
    for row in comparison.leaderboards:
        derate_txt = f"{row.derate_time_s:.1f}s ({row.derate_pct:.1f}%)" if row.derate_time_s > 0 else "None"
        net_soc = f"{row.net_battery_delta_soc_pct:+.1f}%"
        print(f"P{row.rank:<3} | {row.driver_name:<20} | {row.team:<20} | {row.lap_time_str:<9} | {row.gap_to_leader_str:<9} | {row.top_speed_kmh:>5.1f} | {row.energy_deployed_mj:>5.2f} MJ | {row.total_energy_harvested_mj:>5.2f} MJ | {net_soc:>8} | {derate_txt:<9}")
    print("-" * 135)

    # Print Sector Times
    print("\n--- SECTOR SPLIT BREAKDOWN ---")
    print(f"{'DRIVER':<20} | {'SECTOR 1':<12} | {'SECTOR 2':<12} | {'SECTOR 3':<12} | {'TOTAL':<10}")
    print("-" * 74)
    for row in comparison.leaderboards:
        print(f"{row.driver_name:<20} | {row.sectors[1].sector_time_str:<12} | {row.sectors[2].sector_time_str:<12} | {row.sectors[3].sector_time_str:<12} | {row.lap_time_str:<10}")
    print("-" * 74)

    # HTML Report Generation
    if args.html_report:
        path = generate_html_report(comparison, args.html_report)
        print(f"\n[✓] Generated interactive HTML report: {os.path.abspath(path)}")

    # CSV Export
    if args.csv_output:
        csv_data = comparison.to_csv()
        with open(args.csv_output, "w", encoding="utf-8") as f:
            f.write(csv_data)
        print(f"[✓] Exported telemetry CSV: {os.path.abspath(args.csv_output)}")

    # Matplotlib script
    if args.generate_plot_script:
        import json
        with open("telemetry_data.json", "w", encoding="utf-8") as f:
            json.dump(comparison.to_dict(), f, indent=2)
        generate_matplotlib_script(comparison, "plot_telemetry.py")
        print("[✓] Generated standalone Matplotlib script: plot_telemetry.py")


def cmd_qualify(args):
    """Execute F1 Qualifying Knockout / Shootout Simulation."""
    track_key = args.track.lower()
    try:
        track = get_circuit(track_key)
    except KeyError as e:
        print(f"Error: {e}")
        sys.exit(1)

    drivers = resolve_drivers_list(args.drivers, year=args.year)
    if not drivers:
        print("Error: No valid drivers specified.")
        sys.exit(1)

    print_banner()
    year_val = args.year or 2024
    print(f"╔═══════════════════════════════════════════════════════════════════════════════════════╗")
    print(f"║ FORMULA 1 OFFICIAL QUALIFYING SHOOTOUT — {track.name.upper()} ({year_val})")
    print(f"║ Competing Drivers: {len(drivers)} | Format: Knockout Sessions (Q1, Q2, Q3 Shootout)")
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════════╝\n")

    sim = QualifyingSimulator()
    quali_res = sim.simulate(track=track, drivers=drivers, year=year_val, dx=args.dx)

    # Header Highlights
    print(f"🏁 POLE POSITION: {quali_res.pole_driver.driver.name.upper()} ({quali_res.pole_driver.driver.team}) — {quali_res.pole_time_str}")
    print(f"💜 PURPLE SECTORS:")
    print(f"   • Sector 1: {quali_res.purple_s1_driver} ({format_lap_time(quali_res.purple_s1_s)})")
    print(f"   • Sector 2: {quali_res.purple_s2_driver} ({format_lap_time(quali_res.purple_s2_s)})")
    print(f"   • Sector 3: {quali_res.purple_s3_driver} ({format_lap_time(quali_res.purple_s3_s)})")
    print(f"⚡ SPEED TRAP RECORD: {quali_res.speed_trap_driver} — {quali_res.speed_trap_kmh:.1f} km/h\n")

    # Grid Classification Table
    print(f"{'POS':<4} | {'DRIVER':<20} | {'TEAM':<20} | {'Q1':<9} | {'Q2':<9} | {'Q3':<9} | {'GAP TO POLE':<11} | {'STATUS':<6} | {'V_MAX':<7}")
    print("=" * 115)

    last_status = None
    for r in quali_res.grid:
        # Separation lines for Q2 / Q1 eliminations
        cur_status = r.eliminated_in or "Q3"
        if last_status is not None and last_status != cur_status and cur_status in ("Q2", "Q1"):
            print("-" * 115 + f" [ELIMINATION CUTOFF - {last_status}]")
        last_status = cur_status

        status_tag = r.eliminated_in if r.eliminated_in else ("POLE" if r.position == 1 else "Q3")
        print(f"P{r.position:<3} | {r.driver.name:<20} | {r.driver.team:<20} | {r.q1_str:<9} | {r.q2_str:<9} | {r.q3_str:<9} | {r.gap_to_pole_str:<11} | {status_tag:<6} | {r.top_speed_kmh:>5.1f}")

    print("=" * 115)

    # Sector splits
    print("\n--- QUALIFYING SECTOR SPLIT BREAKDOWN ---")
    print(f"{'POS':<4} | {'DRIVER':<20} | {'SECTOR 1':<12} | {'SECTOR 2':<12} | {'SECTOR 3':<12} | {'BEST LAP':<10}")
    print("-" * 75)
    for r in quali_res.grid:
        p_s1 = " 💜" if r.is_purple_s1 else ""
        p_s2 = " 💜" if r.is_purple_s2 else ""
        p_s3 = " 💜" if r.is_purple_s3 else ""
        print(f"P{r.position:<3} | {r.driver.name:<20} | {r.s1_str + p_s1:<12} | {r.s2_str + p_s2:<12} | {r.s3_str + p_s3:<12} | {r.best_lap_str:<10}")
    print("-" * 75)

    # CSV Export
    if args.csv_output:
        csv_data = quali_res.to_csv()
        with open(args.csv_output, "w", encoding="utf-8") as f:
            f.write(csv_data)
        print(f"\n[✓] Exported qualifying CSV: {os.path.abspath(args.csv_output)}")

    # HTML Report Generation
    if args.html_report and quali_res.comparison:
        path = generate_html_report(quali_res.comparison, args.html_report)
        print(f"\n[✓] Generated interactive qualifying HTML report: {os.path.abspath(path)}")



def main():
    parser = argparse.ArgumentParser(
        description="F1 ERS Harvesting & Deployment Simulation and Driver Comparison Suite"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: qualify
    p_quali = subparsers.add_parser("qualify", help="Run F1 Qualifying Shootout (Q1, Q2, Q3) for any number of drivers")
    p_quali.add_argument("--drivers", "-d", type=str, default="all", help="Comma-separated driver codes or 'all' for full grid (e.g. all, ver,nor,lec,pia,ham,rus,sai)")
    p_quali.add_argument("--track", "-t", type=str, default="monza", help="Circuit name: monza, silverstone, spa, monaco, redbullring, etc.")
    p_quali.add_argument("--year", "-y", type=int, default=2024, help="Championship year (2020-2025)")
    p_quali.add_argument("--dx", type=float, default=2.0, help="Spatial discretization step in meters")
    p_quali.add_argument("--html-report", type=str, default=None, help="Save interactive qualifying HTML report")
    p_quali.add_argument("--csv-output", "-o", type=str, default=None, help="Save qualifying results to CSV")

    # Command: compare
    p_comp = subparsers.add_parser("compare", help="Compare multiple drivers on a circuit")
    p_comp.add_argument("--drivers", "-d", type=str, default="ver,ham,alo,nor", help="Comma-separated driver codes (e.g. ver,ham,alo,nor,lec,pia,sai,rus,col,tsu)")
    p_comp.add_argument("--track", "-t", type=str, default="monza", help="Circuit name: monza, silverstone, spa, monaco, redbullring, bahrain, jeddah, suzuka, baku, lasvegas, interlagos, cota, albertpark, hungaroring, zandvoort")
    p_comp.add_argument("--year", "-y", type=int, default=None, help="Championship year (2020-2025) to map driver teams and liveries")
    p_comp.add_argument("--strategy", "-s", type=str, default=None, help="Override ERS strategy: hotlap_quali, race_balanced, overtake_push, recharge_harvest, optimal_dynamic")
    p_comp.add_argument("--dx", type=float, default=2.0, help="Spatial discretization step in meters (default: 2.0m)")
    p_comp.add_argument("--html-report", type=str, default=None, help="File path to save interactive HTML report (e.g. report.html)")
    p_comp.add_argument("--csv-output", "-o", type=str, default=None, help="File path to export telemetry CSV")
    p_comp.add_argument("--generate-plot-script", action="store_true", help="Generate plot_telemetry.py Matplotlib script")

    # Command: list-seasons
    subparsers.add_parser("list-seasons", help="List all championship seasons")

    # Command: list-tracks
    p_trks = subparsers.add_parser("list-tracks", help="List F1 circuits divided by season year")
    p_trks.add_argument("--year", "-y", type=int, default=None, help="Filter by championship year (2020-2025)")

    # Command: list-drivers
    p_drvs = subparsers.add_parser("list-drivers", help="List all drivers divided by season year")
    p_drvs.add_argument("--year", "-y", type=int, default=None, help="Filter by championship year (2020-2025)")

    # Command: export-csv
    p_csv = subparsers.add_parser("export-csv", help="Export lap telemetry directly to CSV")
    p_csv.add_argument("--drivers", "-d", type=str, default="ver,ham", help="Comma-separated driver codes")
    p_csv.add_argument("--track", "-t", type=str, default="monza", help="Circuit name")
    p_csv.add_argument("--year", "-y", type=int, default=None, help="Championship year")
    p_csv.add_argument("--output", "-o", type=str, default="telemetry_export.csv", help="Output CSV path")
    p_csv.add_argument("--dx", type=float, default=2.0, help="Spatial discretization step in meters")

    args = parser.parse_args()

    if args.command == "list-seasons":
        cmd_list_seasons(args)
    elif args.command == "list-tracks":
        cmd_list_tracks(args)
    elif args.command == "list-drivers":
        cmd_list_drivers(args)
    elif args.command == "export-csv":
        args.strategy = None
        args.html_report = None
        args.csv_output = args.output
        args.generate_plot_script = False
        cmd_compare(args)
    elif args.command == "qualify":
        cmd_qualify(args)
    elif args.command == "compare":
        cmd_compare(args)
    else:
        # Default behavior: run Monza comparison
        args.drivers = "ver,ham,nor,lec"
        args.track = "monza"
        args.year = 2024
        args.strategy = None
        args.dx = 2.0
        args.html_report = "monza_comparison_report.html"
        args.csv_output = None
        args.generate_plot_script = False
        cmd_compare(args)


if __name__ == "__main__":
    main()
