"""
Formula 1 ERS Interactive Web Dashboard & Multi-Driver Comparison Lab
=====================================================================
Features:
- Track calendar selection divided by Championship Year (2020 - 2025+)
- Complete driver database across all modern F1 seasons with team livery colors
- Simulation Modes under Dropdown:
  1. 🏎️ On-Track Simulation (Live 2D Circuit Race & Telemetry Replay)
  2. ⚡ Qualifying Shootout (Q1, Q2, Q3 Knockout Grid)
  3. ▶ Race Simulation (Race Pace & Strategy)
- Start with NO drivers pre-selected (user chooses who to simulate)
- Instant 2D circuit map preview on track selection
- Real-time animated 2D circuit map with moving car markers, dynamic intervals, and DRS zones
- Live Driver Cockpit HUD: Digital speedometer, active gear shifts (1-8), throttle/brake bars,
  battery SoC, MGU-K deploy/regen power, and cumulative energy deployed/harvested
- Interactive playback controls: Play/Pause, Rewind, Speed (0.5x, 1x, 2x, 4x, 8x), and Lap Scrubber
- Synchronized multi-pane high-frequency telemetry charts with interactive legend toggling
"""

import http.server
import json
import socketserver
import urllib.parse
import sys
import os

from ers_simulator.track import get_circuit, list_circuits, list_seasons
from ers_simulator.driver import get_driver_preset, list_driver_presets, list_seasons_drivers, DriverProfile
from ers_simulator.ers_strategy import ERSMode
from ers_simulator.solver import LapSimulator
from ers_simulator.qualifying import QualifyingSimulator, simulate_qualifying_session
from ers_simulator.track_2d import build_smooth_2d_track
from ers_simulator.telemetry import TelemetryComparison


HTML_INDEX = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>F1 ERS Harvesting & Multi-Driver Lab</title>
<style>
  :root {
    --bg-dark: #080a0f;
    --panel-bg: #11141c;
    --card-bg: #181c26;
    --border: #262c3d;
    --accent: #e10600;
    --accent-glow: rgba(225, 6, 0, 0.4);
    --ontrack-accent: #00d26a;
    --ontrack-glow: rgba(0, 210, 106, 0.4);
    --quali-accent: #8b5cf6;
    --quali-glow: rgba(139, 92, 246, 0.4);
    --green: #00d26a;
    --purple: #d946ef;
    --yellow: #ffb703;
    --gold: #ffd700;
    --blue: #00b4d8;
    --text-main: #f0f3f8;
    --text-muted: #848e9f;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: var(--bg-dark); color: var(--text-main); font-size: 13px; display: flex; flex-direction: column; min-height: 100vh; }
  
  /* Top Nav */
  header {
    background: var(--panel-bg);
    border-bottom: 2px solid var(--accent);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 100;
    flex-wrap: wrap;
    gap: 10px;
  }
  .brand { display: flex; align-items: center; gap: 10px; }
  .logo-badge { background: var(--accent); color: #fff; font-weight: 900; padding: 4px 8px; border-radius: 4px; font-size: 0.85rem; letter-spacing: 1px; }
  .brand h1 { font-size: 1.15rem; font-weight: 800; letter-spacing: -0.5px; }

  .filter-controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  select, button, input { background: var(--card-bg); color: var(--text-main); border: 1px solid var(--border); border-radius: 6px; padding: 6px 10px; font-size: 0.82rem; }
  select:focus, button:focus, input:focus { outline: none; border-color: var(--accent); }
  button { cursor: pointer; font-weight: 600; transition: all 0.2s; }
  button.primary { background: var(--accent); border-color: var(--accent); color: white; }
  button.primary:hover { background: #ff1a14; box-shadow: 0 0 10px var(--accent-glow); }
  button.ontrack-btn { background: #059669; border-color: #10b981; color: white; }
  button.ontrack-btn:hover { background: #10b981; box-shadow: 0 0 10px var(--ontrack-glow); }
  button.quali-btn { background: #7c3aed; border-color: #8b5cf6; color: white; }
  button.quali-btn:hover { background: #6d28d9; box-shadow: 0 0 10px var(--quali-glow); }
  button.secondary { background: transparent; border-color: var(--border); }
  button.secondary:hover { background: var(--card-bg); }

  /* Main Layout */
  .main-layout { display: flex; flex: 1; overflow: hidden; }
  .sidebar { width: 380px; min-width: 320px; background: var(--panel-bg); border-right: 1px solid var(--border); padding: 14px; overflow-y: auto; height: calc(100vh - 54px); }
  .content { flex: 1; padding: 18px 24px; overflow-y: auto; height: calc(100vh - 54px); }

  .section-title { font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
  
  /* Quick Preset Pills */
  .preset-pills { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 10px; }
  .pill { background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border); border-radius: 12px; padding: 3px 8px; font-size: 0.74rem; cursor: pointer; color: var(--text-muted); transition: all 0.15s; }
  .pill:hover { background: rgba(255, 255, 255, 0.14); color: #fff; border-color: #555; }
  .pill.highlight { background: rgba(0, 210, 106, 0.15); border-color: rgba(0, 210, 106, 0.4); color: #86efac; }
  .pill.quali-pill { background: rgba(139, 92, 246, 0.15); border-color: rgba(139, 92, 246, 0.4); color: #c4b5fd; }

  /* Selection Counter & Batch Action */
  .batch-actions { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 0.75rem; }
  .link-btn { background: none; border: none; color: var(--blue); padding: 0; cursor: pointer; text-decoration: underline; font-size: 0.75rem; }
  .link-btn:hover { color: #fff; }

  /* Search & Filter Bar in Sidebar */
  .search-box { width: 100%; margin-bottom: 10px; padding: 6px 10px; }

  /* Driver Cards in Sidebar */
  .driver-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin-bottom: 6px; transition: border-color 0.2s, background 0.2s; }
  .driver-card:hover { border-color: #3b4459; }
  .driver-card.active-driver { border-left: 3px solid var(--accent); background: rgba(255, 255, 255, 0.02); }
  .driver-header { display: flex; justify-content: space-between; align-items: center; }
  .driver-label { display: flex; align-items: center; gap: 8px; font-weight: 700; cursor: pointer; flex: 1; }
  .driver-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
  .driver-details-toggle { font-size: 0.72rem; color: var(--blue); cursor: pointer; text-decoration: underline; margin-left: 6px; }
  .driver-settings { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 0.78rem; display: none; }
  .driver-settings.show { display: block; }
  .slider-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
  .slider-row label { color: var(--text-muted); }
  .slider-row input[type="range"] { width: 95px; }

  /* Dashboard Cards */
  .card { background: var(--panel-bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin-bottom: 16px; }
  .card h2 { font-size: 0.95rem; font-weight: 700; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }

  /* ========================================================= */
  /* ON-TRACK 2D SIMULATION ARENA STYLES                       */
  /* ========================================================= */
  .ontrack-arena {
    display: grid;
    grid-template-columns: 1fr 340px;
    gap: 16px;
    margin-bottom: 18px;
  }
  @media (max-width: 1100px) {
    .ontrack-arena { grid-template-columns: 1fr; }
  }
  .track-canvas-card {
    background: #090c13;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    position: relative;
    display: flex;
    flex-direction: column;
  }
  .track-canvas-container {
    position: relative;
    width: 100%;
    height: 480px;
    background: radial-gradient(circle at center, #111624 0%, #07090f 100%);
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #1a2234;
  }
  #canvasTrack2D { width: 100%; height: 100%; display: block; }

  /* Playback Controls Toolbar */
  .playback-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
    padding: 8px 12px;
    background: var(--panel-bg);
    border-radius: 6px;
    border: 1px solid var(--border);
    flex-wrap: wrap;
  }
  .playback-btn {
    background: var(--card-bg);
    border: 1px solid var(--border);
    color: #fff;
    padding: 5px 10px;
    border-radius: 5px;
    font-size: 0.8rem;
    font-weight: 700;
  }
  .playback-btn:hover { background: #262f45; border-color: #4b587a; }
  .speed-group { display: flex; gap: 3px; align-items: center; margin-left: 6px; }
  .speed-pill {
    padding: 3px 7px;
    border-radius: 4px;
    background: rgba(255,255,255,0.06);
    border: 1px solid transparent;
    font-size: 0.72rem;
    color: var(--text-muted);
    cursor: pointer;
  }
  .speed-pill:hover { color: #fff; }
  .speed-pill.active { background: #00d26a; color: #000; font-weight: 800; }
  .scrubber-slider { flex: 1; min-width: 140px; cursor: pointer; }
  .time-dist-readout { font-family: monospace; font-size: 0.75rem; color: #cbd5e1; }

  /* Live Timing Tower & Cockpit HUD Sidebar */
  .live-hud-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .timing-tower-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    max-height: 230px;
    overflow-y: auto;
  }
  .timing-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 5px 6px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .timing-row:hover { background: rgba(255,255,255,0.05); }
  .timing-row.active-hud { background: rgba(0, 210, 106, 0.12); border-left: 3px solid #00d26a; }

  /* Cockpit HUD Card */
  .cockpit-hud-card {
    background: linear-gradient(145deg, #121622 0%, #0d1017 100%);
    border: 1px solid #2a344a;
    border-radius: 8px;
    padding: 12px;
    position: relative;
  }
  .hud-driver-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  .hud-gauges-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  .gauge-box {
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 6px;
    padding: 6px 8px;
    text-align: center;
  }
  .gauge-box.full-width { grid-column: span 2; }
  .gauge-label { font-size: 0.68rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 2px; }
  .gauge-value { font-family: monospace; font-size: 1.15rem; font-weight: 900; color: #fff; }
  .gear-val { font-size: 1.6rem; color: #00d26a; }
  .drs-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 900;
    letter-spacing: 0.5px;
  }
  .drs-on { background: #00d26a; color: #000; box-shadow: 0 0 8px rgba(0,210,106,0.6); }
  .drs-off { background: rgba(255,255,255,0.08); color: var(--text-muted); }
  
  /* Pedal & Energy Bars */
  .pedal-bar-bg { width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; margin-top: 4px; }
  .pedal-bar-fill { height: 100%; transition: width 0.05s linear; }

  /* Qualifying Highlights Banner */
  .quali-banner {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 14px;
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.12) 0%, rgba(24, 28, 38, 0.8) 100%);
    border: 1px solid rgba(139, 92, 246, 0.35);
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 16px;
  }
  .pole-box { display: flex; flex-direction: column; justify-content: center; border-right: 1px solid rgba(255, 255, 255, 0.1); padding-right: 14px; }
  .pole-tag { display: inline-block; background: linear-gradient(135deg, #ffd700, #ff9100); color: #000; font-weight: 900; font-size: 0.72rem; letter-spacing: 0.8px; padding: 2px 7px; border-radius: 4px; width: fit-content; margin-bottom: 5px; }
  .pole-name { font-size: 1.25rem; font-weight: 800; color: #fff; letter-spacing: -0.3px; }
  .pole-team { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px; }
  .pole-time { font-family: monospace; font-size: 1.15rem; font-weight: 800; color: #ffd700; }

  .quali-stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; align-items: center; }
  .stat-card { background: rgba(0, 0, 0, 0.25); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 8px 10px; }
  .stat-card .stat-label { font-size: 0.7rem; font-weight: 700; color: var(--text-muted); margin-bottom: 3px; display: block; }
  .stat-card .stat-val { font-family: monospace; font-size: 0.95rem; font-weight: 700; color: #fff; }
  .stat-card .stat-driver { font-size: 0.72rem; color: var(--purple); margin-left: 4px; }

  /* Leaderboard */
  .table-responsive { width: 100%; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; white-space: nowrap; }
  th { text-align: left; padding: 7px 9px; color: var(--text-muted); border-bottom: 2px solid var(--border); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
  td { padding: 7px 9px; border-bottom: 1px solid var(--border); }
  tr:hover { background: rgba(255, 255, 255, 0.025); }
  .pole-row { background: rgba(255, 215, 0, 0.04) !important; border-left: 3px solid #ffd700; }
  .purple-sector { color: var(--purple); font-weight: 700; font-family: monospace; }
  .green-sector { color: var(--green); font-family: monospace; }
  .derate-tag { background: rgba(225,6,0,0.25); color: #ff6b6b; padding: 1px 5px; border-radius: 4px; font-weight: bold; font-size: 0.72rem; }
  
  /* Status Badges */
  .badge-pole { background: #ffd700; color: #000; font-weight: 900; padding: 1px 6px; border-radius: 3px; font-size: 0.7rem; }
  .badge-q3 { background: rgba(0, 210, 106, 0.15); color: #00d26a; border: 1px solid rgba(0, 210, 106, 0.4); padding: 1px 5px; border-radius: 3px; font-size: 0.7rem; font-weight: 700; }
  .badge-q2 { background: rgba(255, 183, 3, 0.15); color: #ffb703; border: 1px solid rgba(255, 183, 3, 0.4); padding: 1px 5px; border-radius: 3px; font-size: 0.7rem; font-weight: 700; }
  .badge-q1 { background: rgba(225, 6, 0, 0.15); color: #ff6b6b; border: 1px solid rgba(225, 6, 0, 0.4); padding: 1px 5px; border-radius: 3px; font-size: 0.7rem; font-weight: 700; }

  /* Charts */
  .chart-container { position: relative; width: 100%; height: 180px; margin-bottom: 12px; background: #0b0e14; border-radius: 6px; padding: 6px; border: 1px solid #1a202c; }
  canvas { width: 100%; height: 100%; display: block; }
  .chart-title-tag { position: absolute; top: 8px; left: 12px; font-size: 0.78rem; font-weight: 700; color: #a0aec0; pointer-events: none; }
  .hover-stats { position: absolute; top: 8px; right: 12px; font-family: monospace; font-size: 0.73rem; color: #fff; pointer-events: none; }

  /* Interactive Legend */
  .legend-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; font-size: 0.75rem; }
  .legend-item { display: flex; align-items: center; gap: 5px; background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border); border-radius: 10px; padding: 2px 7px; cursor: pointer; user-select: none; transition: all 0.15s; }
  .legend-item:hover { background: rgba(255, 255, 255, 0.09); }
  .legend-item.dimmed { opacity: 0.35; text-decoration: line-through; }
  .legend-bar { width: 10px; height: 3px; border-radius: 2px; }

  /* Loading Spinner */
  .loading-spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 0.8s linear infinite; margin-right: 6px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<header>
  <div class="brand">
    <span class="logo-badge">F1 ERS</span>
    <h1>Multi-Driver Energy Harvesting & Deployment Lab</h1>
  </div>
  <div class="filter-controls">
    <label for="seasonSelect" style="color: var(--text-muted); font-size: 0.8rem;">YEAR:</label>
    <select id="seasonSelect" onchange="onSeasonChanged()">
      <option value="2024" selected>2024 Season</option>
      <option value="2025">2025 Season</option>
      <option value="2023">2023 Season</option>
      <option value="2022">2022 Season</option>
      <option value="2021">2021 Season</option>
      <option value="2020">2020 Season</option>
      <option value="all">All Tracks / Seasons</option>
    </select>

    <label for="trackSelect" style="color: var(--text-muted); font-size: 0.8rem; margin-left: 6px;">CIRCUIT:</label>
    <select id="trackSelect" onchange="onTrackChanged()"></select>

    <!-- SIMULATION MODE DROPDOWN -->
    <label for="simModeSelect" style="color: var(--text-muted); font-size: 0.8rem; margin-left: 6px;">SIMULATE:</label>
    <select id="simModeSelect" onchange="onSimModeChanged()" style="font-weight: 700; border-color: #00d26a;">
      <option value="ontrack" selected>🏎️ On-Track Simulation (Live 2D Circuit Race & Telemetry)</option>
      <option value="qualifying">⚡ Qualifying Shootout (Q1/Q2/Q3 Knockout Grid)</option>
      <option value="race">▶ Race Simulation (Race Pace & Strategy)</option>
    </select>

    <button id="btnSimOnTrack" class="ontrack-btn" onclick="setSimModeAndRun('ontrack')">🏎️ On-Track Sim</button>
    <button id="btnSimQuali" class="quali-btn" onclick="setSimModeAndRun('qualifying')">⚡ Quali Sim</button>
    <button id="btnSimRace" class="secondary" onclick="setSimModeAndRun('race')">▶ Race Sim</button>
    <button class="secondary" onclick="exportCSV()">Export CSV</button>
  </div>
</header>

<div class="main-layout">
  <!-- Left Control Sidebar -->
  <aside class="sidebar">
    <div class="section-title">
      <span>Driver Grid Selection</span>
      <span id="selectedCount" style="color: var(--accent); font-weight: 700;">0 of 0 Selected</span>
    </div>

    <!-- Quick Presets -->
    <div class="preset-pills">
      <span class="pill highlight" onclick="applyPreset('all')">Full Grid (All Drivers)</span>
      <span class="pill quali-pill" onclick="applyPreset('quali')">Top 10 Quali</span>
      <span class="pill" onclick="applyPreset('top4')">Top 4</span>
      <span class="pill" onclick="applyPreset('teammates')">Teammate Duels</span>
      <span class="pill" onclick="applyPreset('clear')">Clear</span>
    </div>

    <!-- Batch actions -->
    <div class="batch-actions">
      <span>Choose <strong>any number of drivers</strong>:</span>
      <div>
        <button class="link-btn" onclick="applyPreset('all')">Select All</button> |
        <button class="link-btn" onclick="applyPreset('clear')">Clear</button>
      </div>
    </div>

    <!-- Filter input -->
    <input type="text" id="driverSearch" class="search-box" placeholder="🔍 Filter by driver name, code, or team..." oninput="filterDrivers()">

    <!-- Drivers List Container -->
    <div id="driverListContainer"></div>
  </aside>

  <!-- Right Content Area -->
  <main class="content">

    <!-- ========================================================= -->
    <!-- ON-TRACK 2D CIRCUIT SIMULATION ARENA                      -->
    <!-- ========================================================= -->
    <div id="onTrackArena" class="ontrack-arena">
      <!-- 2D Canvas & Controls -->
      <div class="track-canvas-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <div>
            <strong style="color: #00d26a; font-size: 0.95rem;">🏎️ Live On-Track Circuit Simulation</strong>
            <span id="onTrackMeta" style="color: var(--text-muted); font-size: 0.78rem; margin-left: 8px;"></span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">
            Cars on Track: <strong id="onTrackCarCount" style="color: #00d26a;">0</strong>
          </div>
        </div>

        <div class="track-canvas-container">
          <canvas id="canvasTrack2D"></canvas>
        </div>

        <!-- Playback toolbar -->
        <div class="playback-toolbar">
          <button id="btnPlayPause" class="playback-btn" onclick="togglePlayPause()">⏸ Pause</button>
          <button class="playback-btn" onclick="restartPlayback()">↺ Restart</button>

          <div class="speed-group">
            <span class="speed-pill" onclick="setSpeed(0.5, this)">0.5x</span>
            <span class="speed-pill active" onclick="setSpeed(1.0, this)">1x</span>
            <span class="speed-pill" onclick="setSpeed(2.0, this)">2x</span>
            <span class="speed-pill" onclick="setSpeed(4.0, this)">4x</span>
            <span class="speed-pill" onclick="setSpeed(8.0, this)">8x</span>
          </div>

          <input type="range" id="lapScrubber" class="scrubber-slider" min="0" max="100" step="0.1" value="0" oninput="onScrubLap(this.value)">

          <div class="time-dist-readout">
            <span id="txtLapTime">0:00.000</span> / <span id="txtLapTotal">0:00.000</span>
            (<span id="txtLapDist">0 m</span>)
          </div>
        </div>
      </div>

      <!-- Live Timing Tower & Cockpit HUD -->
      <div class="live-hud-panel">
        <!-- Live Timing Tower -->
        <div class="timing-tower-card">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; display: flex; justify-content: space-between;">
            <span>Live Timing Tower</span>
            <span>Speed / Gap</span>
          </div>
          <div id="liveTimingTower"></div>
        </div>

        <!-- Cockpit HUD Card -->
        <div class="cockpit-hud-card">
          <div class="hud-driver-header">
            <div>
              <span id="hudDriverDot" class="driver-dot" style="background-color: #64748b; margin-right: 5px;"></span>
              <strong id="hudDriverName">No Driver Selected</strong>
              <span id="hudDriverTeam" style="font-size: 0.7rem; color: var(--text-muted); display: block;">Select drivers in sidebar</span>
            </div>
            <div>
              <select id="hudDriverSelect" style="font-size: 0.72rem; padding: 2px 4px;" onchange="onSelectHudDriver(this.value)"></select>
            </div>
          </div>

          <div class="hud-gauges-grid">
            <div class="gauge-box">
              <div class="gauge-label">Ground Speed</div>
              <div class="gauge-value" id="hudSpeed">0 <span style="font-size: 0.7rem; font-weight: normal;">km/h</span></div>
            </div>
            <div class="gauge-box">
              <div class="gauge-label">Active Gear</div>
              <div class="gauge-value gear-val" id="hudGear">N</div>
            </div>

            <!-- Throttle & Brake -->
            <div class="gauge-box full-width" style="text-align: left;">
              <div style="display: flex; justify-content: space-between; font-size: 0.7rem;">
                <span style="color: #00d26a; font-weight: 700;">THROTTLE: <span id="hudThrottleVal">0%</span></span>
                <span style="color: #ff6b6b; font-weight: 700;">BRAKE: <span id="hudBrakeVal">0%</span></span>
              </div>
              <div class="pedal-bar-bg">
                <div id="hudThrottleBar" class="pedal-bar-fill" style="width: 0%; background: #00d26a;"></div>
              </div>
              <div class="pedal-bar-bg" style="margin-top: 3px;">
                <div id="hudBrakeBar" class="pedal-bar-fill" style="width: 0%; background: #ff6b6b;"></div>
              </div>
            </div>

            <!-- Energy Deployed & Harvested (Dynamic HUD) -->
            <div class="gauge-box full-width" style="text-align: left;">
              <div style="display: flex; justify-content: space-between; font-size: 0.7rem; margin-bottom: 2px;">
                <span style="color: #38bdf8; font-weight: 700;">ENERGY DEPLOYED: <span id="hudDeployVal">0.00 MJ</span></span>
                <span style="color: var(--text-muted);">FIA 4.0 MJ Limit</span>
              </div>
              <div class="pedal-bar-bg">
                <div id="hudDeployBar" class="pedal-bar-fill" style="width: 0%; background: #38bdf8;"></div>
              </div>
              <div style="display: flex; justify-content: space-between; font-size: 0.7rem; margin-top: 5px;">
                <span style="color: #4ade80;">HARVESTED: <strong id="hudHarvestVal">0.00 MJ</strong></span>
                <span style="color: #fbbf24;">MGU-H: <strong id="hudMguhVal">0 kW</strong></span>
              </div>
            </div>

            <!-- Battery SoC -->
            <div class="gauge-box">
              <div class="gauge-label">Battery SoC</div>
              <div class="gauge-value" id="hudSoc" style="color: #38bdf8;">85.0%</div>
            </div>

            <!-- MGU-K Power -->
            <div class="gauge-box">
              <div class="gauge-label">MGU-K Power</div>
              <div class="gauge-value" id="hudMguk" style="color: #fbbf24; font-size: 0.95rem;">0 kW</div>
            </div>

            <!-- DRS Status -->
            <div class="gauge-box full-width" style="display: flex; justify-content: space-between; align-items: center;">
              <span class="gauge-label" style="margin: 0;">Aero DRS Wing</span>
              <span id="hudDrsBadge" class="drs-badge drs-off">DRS CLOSED</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Qualifying Highlights Banner (Rendered in Qualifying mode) -->
    <div id="qualiBanner" class="quali-banner" style="display: none;">
      <div class="pole-box">
        <span class="pole-tag">🏁 POLE POSITION</span>
        <div class="pole-name" id="bannerPoleDriver">-</div>
        <div class="pole-team" id="bannerPoleTeam">-</div>
        <div class="pole-time" id="bannerPoleTime">-</div>
      </div>
      <div class="quali-stats-grid">
        <div class="stat-card">
          <span class="stat-label">💜 PURPLE SECTOR 1</span>
          <span class="stat-val" id="bannerPurpleS1">-</span>
          <span class="stat-driver" id="bannerPurpleS1Driver"></span>
        </div>
        <div class="stat-card">
          <span class="stat-label">💜 PURPLE SECTOR 2</span>
          <span class="stat-val" id="bannerPurpleS2">-</span>
          <span class="stat-driver" id="bannerPurpleS2Driver"></span>
        </div>
        <div class="stat-card">
          <span class="stat-label">💜 PURPLE SECTOR 3</span>
          <span class="stat-val" id="bannerPurpleS3">-</span>
          <span class="stat-driver" id="bannerPurpleS3Driver"></span>
        </div>
        <div class="stat-card">
          <span class="stat-label">⚡ TOP SPEED TRAP</span>
          <span class="stat-val" id="bannerSpeedTrap">-</span>
          <span class="stat-driver" id="bannerSpeedTrapDriver"></span>
        </div>
      </div>
    </div>

    <!-- Leaderboard -->
    <div class="card">
      <h2>
        <span id="leaderboardTitle">Driver Classification & Telemetry Audit</span>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span id="simStatus" style="font-size: 0.8rem; color: var(--text-muted); font-weight: normal;"></span>
          <span id="circuitMeta" style="font-size: 0.8rem; color: var(--text-muted); font-weight: normal;"></span>
        </div>
      </h2>
      <div class="table-responsive">
        <table>
          <thead id="leaderboardHead"></thead>
          <tbody id="leaderboardBody">
            <tr>
              <td colspan="15" style="text-align: center; color: var(--text-muted); padding: 30px;">
                Select one or more drivers from the sidebar (or click a Preset) to run simulation.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Telemetry Charts -->
    <div class="card">
      <h2>
        <span>High-Resolution Telemetry Comparison</span>
        <span style="font-size: 0.72rem; color: var(--text-muted); font-weight: normal;">Click driver pill to toggle trace visibility</span>
      </h2>
      <div class="legend-row" id="telemetryLegend"></div>

      <!-- Speed -->
      <div class="chart-container">
        <div class="chart-title-tag">Velocity Profile (km/h)</div>
        <div class="hover-stats" id="hover-speed"></div>
        <canvas id="canvasSpeed"></canvas>
      </div>

      <!-- Delta-t -->
      <div class="chart-container">
        <div class="chart-title-tag">Time Delta vs Reference Driver (&Delta;t seconds &bull; Positive = Slower)</div>
        <div class="hover-stats" id="hover-delta"></div>
        <canvas id="canvasDelta"></canvas>
      </div>

      <!-- Battery SoC -->
      <div class="chart-container">
        <div class="chart-title-tag">Battery State of Charge (% SoC)</div>
        <div class="hover-stats" id="hover-soc"></div>
        <canvas id="canvasSoC"></canvas>
      </div>

      <!-- MGU-K Power -->
      <div class="chart-container">
        <div class="chart-title-tag">MGU-K Power (kW &bull; Positive = 120kW Deploy, Negative = Regen Braking)</div>
        <div class="hover-stats" id="hover-mguk"></div>
        <canvas id="canvasMguk"></canvas>
      </div>

      <!-- Cumulative Energy Deployed -->
      <div class="chart-container">
        <div class="chart-title-tag">Cumulative Energy Deployed from Battery (MJ &bull; FIA 4.0 MJ Limit)</div>
        <div class="hover-stats" id="hover-deploy"></div>
        <canvas id="canvasDeploy"></canvas>
      </div>
    </div>

  </main>
</div>

<script>
let currentData = null;
let currentTrack2D = null;
let allDriversList = [];
let allTracksList = [];
let activeDriversMap = {};
let hiddenOnChart = {};
let hoverDistIndex = -1;
let isSimulating = false;

// On-Track Animation Engine Variables
let animFrameId = null;
let isPlaying = true;
let playbackSpeed = 1.0;
let simTime = 0.0;
let lastTimestamp = 0;
let maxLapTime = 80.0;
let focusedDriverCode = "";

async function initData() {
  await loadTracksForSeason();
  await loadDriversForSeason();
  
  // DON'T start with any drivers selected (let the user select them!)
  Object.values(activeDriversMap).forEach(d => d.active = false);
  updateSelectedCount();

  // Load and render 2D Track Preview immediately for the selected circuit
  const initialTrack = document.getElementById('trackSelect').value || 'monza';
  await loadTrackPreview(initialTrack);
}

async function onSeasonChanged() {
  await loadTracksForSeason();
  await loadDriversForSeason();
  const trackId = document.getElementById('trackSelect').value;
  const activeCount = Object.values(activeDriversMap).filter(d => d.active).length;
  if (activeCount > 0) {
    runSimulation();
  } else {
    await loadTrackPreview(trackId);
  }
}

async function onTrackChanged() {
  const activeCount = Object.values(activeDriversMap).filter(d => d.active).length;
  const trackId = document.getElementById('trackSelect').value;
  if (activeCount > 0) {
    runSimulation();
  } else {
    await loadTrackPreview(trackId);
  }
}

async function loadTrackPreview(trackId) {
  try {
    const res = await fetch(`/api/track-2d?track=${trackId}`);
    const t2d = await res.json();
    currentTrack2D = t2d;
    document.getElementById('onTrackMeta').innerText = `${t2d.track_name} • ${t2d.total_length_m.toLocaleString()} m`;
    document.getElementById('circuitMeta').innerText = `${t2d.track_name} (${t2d.total_length_m.toLocaleString()} m)`;
    document.getElementById('onTrackCarCount').innerText = "0";
    document.getElementById('txtLapTotal').innerText = "-";
    document.getElementById('txtLapTime').innerText = "0:00.000";
    document.getElementById('txtLapDist').innerText = "0 m";
    
    render2DTrackCanvas(currentTrack2D, []);
    renderTimingTowerEmpty();
  } catch (err) {
    console.error("Failed to load track preview:", err);
  }
}

function renderTimingTowerEmpty() {
  const container = document.getElementById('liveTimingTower');
  if (container) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--text-muted); padding: 30px 10px; font-size: 0.78rem;">
        <div style="font-size: 1.5rem; margin-bottom: 6px;">🏎️</div>
        <strong style="color: #cbd5e1;">Circuit Ready</strong>
        <div style="color: #64748b; font-size: 0.72rem; margin-top: 4px;">Select drivers in the sidebar or click a preset to launch simulation.</div>
      </div>
    `;
  }
}

function onSimModeChanged() {
  const activeCount = Object.values(activeDriversMap).filter(d => d.active).length;
  if (activeCount === 0) return;

  const mode = document.getElementById('simModeSelect').value;
  if (currentData) {
    if ((mode === 'qualifying' && currentData.mode !== 'qualifying') ||
        (mode !== 'qualifying' && currentData.mode === 'qualifying')) {
      runSimulation();
      return;
    }
    renderAll();
  } else {
    runSimulation();
  }
}

function setSimModeAndRun(mode) {
  document.getElementById('simModeSelect').value = mode;
  onSimModeChanged();
}

async function loadTracksForSeason() {
  const yr = document.getElementById('seasonSelect').value;
  const url = yr === 'all' ? '/api/tracks' : `/api/tracks?year=${yr}`;
  const res = await fetch(url);
  allTracksList = await res.json();

  const sel = document.getElementById('trackSelect');
  sel.innerHTML = allTracksList.map(t => {
    const roundTxt = t.round ? `Rd ${t.round}: ` : '';
    return `<option value="${t.id}">${roundTxt}${t.name} (${t.country})</option>`;
  }).join('');
}

async function loadDriversForSeason() {
  const yr = document.getElementById('seasonSelect').value;
  const url = yr === 'all' ? '/api/drivers' : `/api/drivers?year=${yr}`;
  const res = await fetch(url);
  allDriversList = await res.json();

  const prevMap = activeDriversMap;
  activeDriversMap = {};

  allDriversList.forEach(d => {
    const code = d.code.toLowerCase();
    const existing = prevMap[code];
    activeDriversMap[code] = {
      code: code,
      name: d.name,
      team: d.team,
      color: d.color,
      number: d.number,
      active: existing ? existing.active : false,
      strategy: existing ? existing.strategy : d.ers_mode,
      brakeOffset: existing ? existing.brakeOffset : d.braking_offset_m,
      liftCoast: existing ? existing.liftCoast : d.lift_and_coast_m,
      throttle: existing ? existing.throttle : d.throttle_aggression,
      grip: existing ? existing.grip : d.cornering_grip_factor,
      showSettings: false
    };
  });

  renderDriverCards();
}

function renderDriverCards() {
  const container = document.getElementById('driverListContainer');
  const query = document.getElementById('driverSearch').value.toLowerCase();

  const filtered = allDriversList.filter(d => 
    d.name.toLowerCase().includes(query) || 
    d.team.toLowerCase().includes(query) || 
    d.code.toLowerCase().includes(query)
  );

  container.innerHTML = filtered.map(d => {
    const code = d.code.toLowerCase();
    const st = activeDriversMap[code];
    const numStr = d.number ? `#${d.number}` : '';
    return `
      <div class="driver-card ${st.active ? 'active-driver' : ''}" id="card_${code}">
        <div class="driver-header">
          <label class="driver-label">
            <input type="checkbox" ${st.active ? 'checked' : ''} onchange="toggleDriver('${code}', this.checked)">
            <span class="driver-dot" style="background-color: ${st.color};"></span>
            <span>${st.name} <span style="font-size: 0.72rem; color: var(--text-muted);">${numStr} (${st.code.toUpperCase()})</span></span>
          </label>
          <span class="driver-details-toggle" onclick="toggleSettings('${code}')">Tune</span>
        </div>
        <div style="font-size: 0.72rem; color: var(--text-muted); margin-left: 26px; margin-top: 2px;">
          ${st.team}
        </div>
        <div class="driver-settings ${st.showSettings ? 'show' : ''}" id="settings_${code}">
          <div class="slider-row">
            <label>Strategy</label>
            <select style="padding: 1px 4px; font-size: 0.72rem;" onchange="activeDriversMap['${code}'].strategy = this.value; if(activeDriversMap['${code}'].active) runSimulation();">
              <option value="hotlap_quali" ${st.strategy === 'hotlap_quali' ? 'selected' : ''}>Hotlap Quali</option>
              <option value="race_balanced" ${st.strategy === 'race_balanced' ? 'selected' : ''}>Race Balanced</option>
              <option value="overtake_push" ${st.strategy === 'overtake_push' ? 'selected' : ''}>Overtake Push</option>
              <option value="optimal_dynamic" ${st.strategy === 'optimal_dynamic' ? 'selected' : ''}>Optimal Dynamic</option>
              <option value="recharge_harvest" ${st.strategy === 'recharge_harvest' ? 'selected' : ''}>Recharge Harvest</option>
            </select>
          </div>
          <div class="slider-row">
            <label>Braking Offset</label>
            <div>
              <input type="range" min="-15" max="10" step="0.5" value="${st.brakeOffset}" oninput="document.getElementById('lbl_bo_${code}').innerText = this.value + 'm'; activeDriversMap['${code}'].brakeOffset = parseFloat(this.value);" onchange="if(activeDriversMap['${code}'].active) runSimulation();">
              <span id="lbl_bo_${code}" style="font-family: monospace; width: 32px; display: inline-block; text-align: right;">${st.brakeOffset}m</span>
            </div>
          </div>
          <div class="slider-row">
            <label>Lift & Coast</label>
            <div>
              <input type="range" min="0" max="80" step="5" value="${st.liftCoast}" oninput="document.getElementById('lbl_lc_${code}').innerText = this.value + 'm'; activeDriversMap['${code}'].liftCoast = parseFloat(this.value);" onchange="if(activeDriversMap['${code}'].active) runSimulation();">
              <span id="lbl_lc_${code}" style="font-family: monospace; width: 32px; display: inline-block; text-align: right;">${st.liftCoast}m</span>
            </div>
          </div>
          <div class="slider-row">
            <label>Exit Throttle</label>
            <div>
              <input type="range" min="0.8" max="1.3" step="0.02" value="${st.throttle}" oninput="document.getElementById('lbl_th_${code}').innerText = this.value + 'x'; activeDriversMap['${code}'].throttle = parseFloat(this.value);" onchange="if(activeDriversMap['${code}'].active) runSimulation();">
              <span id="lbl_th_${code}" style="font-family: monospace; width: 32px; display: inline-block; text-align: right;">${st.throttle}x</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function filterDrivers() {
  renderDriverCards();
}

function toggleDriver(code, active) {
  if (activeDriversMap[code]) {
    activeDriversMap[code].active = active;
  }
  updateSelectedCount();
  renderDriverCards();

  const activeCount = Object.values(activeDriversMap).filter(d => d.active).length;
  if (activeCount > 0) {
    runSimulation();
  } else {
    currentData = null;
    const trackId = document.getElementById('trackSelect').value;
    loadTrackPreview(trackId);
    document.getElementById('leaderboardBody').innerHTML = '<tr><td colspan="15" style="text-align: center; color: var(--text-muted); padding: 30px;">Select one or more drivers from the sidebar to view leaderboard.</td></tr>';
    document.getElementById('qualiBanner').style.display = 'none';
  }
}

function toggleSettings(code) {
  if (activeDriversMap[code]) {
    activeDriversMap[code].showSettings = !activeDriversMap[code].showSettings;
    const el = document.getElementById(`settings_${code}`);
    if (el) el.classList.toggle('show');
  }
}

function updateSelectedCount() {
  const activeCount = Object.values(activeDriversMap).filter(d => d.active).length;
  const totalCount = Object.values(activeDriversMap).length;
  document.getElementById('selectedCount').innerText = `${activeCount} of ${totalCount} Selected`;
}

function applyPreset(type) {
  Object.values(activeDriversMap).forEach(d => d.active = false);

  if (type === 'all') {
    Object.values(activeDriversMap).forEach(d => d.active = true);
  } else if (type === 'top4') {
    ['ver', 'ham', 'nor', 'lec'].forEach(c => { if (activeDriversMap[c]) activeDriversMap[c].active = true; });
  } else if (type === 'teammates') {
    ['nor', 'pia', 'ver', 'per', 'lec', 'sai', 'ham', 'rus'].forEach(c => { if (activeDriversMap[c]) activeDriversMap[c].active = true; });
  } else if (type === 'quali') {
    ['ver', 'nor', 'lec', 'pia', 'sai', 'ham', 'rus', 'per', 'alo', 'hul'].forEach(c => { if (activeDriversMap[c]) activeDriversMap[c].active = true; });
  }

  updateSelectedCount();
  renderDriverCards();

  const activeCount = Object.values(activeDriversMap).filter(d => d.active).length;
  if (activeCount > 0) {
    runSimulation();
  } else {
    currentData = null;
    const trackId = document.getElementById('trackSelect').value;
    loadTrackPreview(trackId);
  }
}

async function runSimulation() {
  if (isSimulating) return;
  const track = document.getElementById('trackSelect').value;
  const activeList = Object.values(activeDriversMap).filter(d => d.active);
  const mode = document.getElementById('simModeSelect').value;

  if (activeList.length === 0) {
    currentData = null;
    await loadTrackPreview(track);
    return;
  }

  isSimulating = true;
  document.getElementById('simStatus').innerHTML = `<span class="loading-spinner"></span>Simulating ${activeList.length} drivers (${mode})...`;

  const payload = {
    track: track,
    year: parseInt(document.getElementById('seasonSelect').value) || null,
    mode: mode,
    drivers: activeList.map(d => ({
      code: d.code,
      strategy: d.strategy,
      braking_offset_m: d.brakeOffset,
      lift_and_coast_m: d.liftCoast,
      throttle_aggression: d.throttle,
      cornering_grip_factor: d.grip
    }))
  };

  try {
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    currentData = await res.json();
    if (currentData.track_2d) {
      currentTrack2D = currentData.track_2d;
    }
    initOnTrackSimulation();
    renderAll();
  } catch (err) {
    console.error("Simulation failed:", err);
  } finally {
    isSimulating = false;
    document.getElementById('simStatus').innerText = '';
  }
}

function renderAll() {
  if (!currentData) return;
  const mode = document.getElementById('simModeSelect').value;
  document.getElementById('circuitMeta').innerText = `${currentData.track_name} (${currentData.track_length_m.toLocaleString()} m)`;
  
  if (mode === 'qualifying') {
    renderQualifyingView();
  } else {
    renderRaceView();
  }

  renderLegends();
  renderCharts();
}

function renderQualifyingView() {
  const banner = document.getElementById('qualiBanner');
  banner.style.display = 'grid';
  document.getElementById('leaderboardTitle').innerText = 'Official F1 Qualifying Shootout (Q1, Q2, Q3 Knockout Grid)';

  if (currentData.pole_driver) {
    document.getElementById('bannerPoleDriver').innerText = currentData.pole_driver;
    document.getElementById('bannerPoleTime').innerText = currentData.pole_time;
    const poleRow = currentData.grid && currentData.grid[0];
    document.getElementById('bannerPoleTeam').innerText = poleRow ? poleRow.team : '';
  }

  if (currentData.purple_s1) {
    document.getElementById('bannerPurpleS1').innerText = currentData.purple_s1.time;
    document.getElementById('bannerPurpleS1Driver').innerText = `(${currentData.purple_s1.driver})`;
  }
  if (currentData.purple_s2) {
    document.getElementById('bannerPurpleS2').innerText = currentData.purple_s2.time;
    document.getElementById('bannerPurpleS2Driver').innerText = `(${currentData.purple_s2.driver})`;
  }
  if (currentData.purple_s3) {
    document.getElementById('bannerPurpleS3').innerText = currentData.purple_s3.time;
    document.getElementById('bannerPurpleS3Driver').innerText = `(${currentData.purple_s3.driver})`;
  }
  if (currentData.speed_trap) {
    document.getElementById('bannerSpeedTrap').innerText = `${currentData.speed_trap.kmh} km/h`;
    document.getElementById('bannerSpeedTrapDriver').innerText = `(${currentData.speed_trap.driver})`;
  }

  // Header
  document.getElementById('leaderboardHead').innerHTML = `
    <tr>
      <th>Pos</th>
      <th>Driver</th>
      <th>Team</th>
      <th>Q1</th>
      <th>Q2</th>
      <th>Q3</th>
      <th>Best Lap</th>
      <th>Gap to Pole</th>
      <th>Status</th>
      <th>S1</th>
      <th>S2</th>
      <th>S3</th>
      <th>V_Max</th>
      <th>Deploy</th>
      <th>Harvest</th>
      <th>Net &Delta;SoC</th>
    </tr>
  `;

  const tbody = document.getElementById('leaderboardBody');
  const grid = currentData.grid || [];

  tbody.innerHTML = grid.map(r => {
    const isPole = r.position === 1;
    const badgeClass = r.eliminated === 'POLE' ? 'badge-pole' :
                       r.eliminated === 'Q3' ? 'badge-q3' :
                       r.eliminated === 'Q2' ? 'badge-q2' : 'badge-q1';

    return `
      <tr class="${isPole ? 'pole-row' : ''}">
        <td><strong>P${r.position}</strong></td>
        <td>
          <span class="driver-dot" style="background-color: ${r.color}; margin-right: 6px;"></span>
          <strong>${r.name}</strong> <span style="color: var(--text-muted); font-size: 0.72rem;">(${r.code})</span>
        </td>
        <td style="color: var(--text-muted); font-size: 0.75rem;">${r.team || ''}</td>
        <td style="font-family: monospace; color: ${r.q1 !== '-' ? '#fff' : 'var(--text-muted)'};">${r.q1}</td>
        <td style="font-family: monospace; color: ${r.q2 !== '-' ? '#fff' : 'var(--text-muted)'};">${r.q2}</td>
        <td style="font-family: monospace; color: ${r.q3 !== '-' ? '#fff' : 'var(--text-muted)'};">${r.q3}</td>
        <td style="font-family: monospace; font-size: 0.9rem; font-weight: 700; color: ${isPole ? '#ffd700' : '#fff'};">${r.best_lap}</td>
        <td style="font-family: monospace; color: ${isPole ? 'var(--green)' : '#ff6b6b'}; font-weight: bold;">${r.gap}</td>
        <td><span class="${badgeClass}">${r.eliminated}</span></td>
        <td class="${r.is_purple_s1 ? 'purple-sector' : 'green-sector'}">${r.s1}${r.is_purple_s1 ? ' 💜' : ''}</td>
        <td class="${r.is_purple_s2 ? 'purple-sector' : 'green-sector'}">${r.s2}${r.is_purple_s2 ? ' 💜' : ''}</td>
        <td class="${r.is_purple_s3 ? 'purple-sector' : 'green-sector'}">${r.s3}${r.is_purple_s3 ? ' 💜' : ''}</td>
        <td><strong>${r.top_speed}</strong></td>
        <td>${r.energy_deployed_mj.toFixed(2)} MJ</td>
        <td>${r.energy_harvested_mj.toFixed(2)} MJ</td>
        <td style="color: ${r.net_soc_delta_pct >= 0 ? 'var(--green)' : '#ff6b6b'}; font-weight: bold;">
          ${r.net_soc_delta_pct > 0 ? '+' : ''}${r.net_soc_delta_pct.toFixed(1)}%
        </td>
      </tr>
    `;
  }).join('');
}

function renderRaceView() {
  document.getElementById('qualiBanner').style.display = 'none';
  document.getElementById('leaderboardTitle').innerText = 'Driver Telemetry Leaderboard & ERS Energy Audit (Race Pace)';

  document.getElementById('leaderboardHead').innerHTML = `
    <tr>
      <th>Pos</th>
      <th>Driver</th>
      <th>Team</th>
      <th>Strategy</th>
      <th>Lap Time</th>
      <th>Gap</th>
      <th>S1</th>
      <th>S2</th>
      <th>S3</th>
      <th>V_Max</th>
      <th>Deploy</th>
      <th>Harvest</th>
      <th>Net &Delta;SoC</th>
      <th>Derate</th>
    </tr>
  `;

  const tbody = document.getElementById('leaderboardBody');
  const board = currentData.leaderboard || [];

  let bestS1 = "9:99.999", bestS2 = "9:99.999", bestS3 = "9:99.999";
  board.forEach(r => {
    if (r.s1 && r.s1 < bestS1) bestS1 = r.s1;
    if (r.s2 && r.s2 < bestS2) bestS2 = r.s2;
    if (r.s3 && r.s3 < bestS3) bestS3 = r.s3;
  });

  tbody.innerHTML = board.map(r => `
    <tr>
      <td><strong>P${r.rank}</strong></td>
      <td>
        <span class="driver-dot" style="background-color: ${r.color}; margin-right: 6px;"></span>
        <strong>${r.name}</strong> <span style="color: var(--text-muted); font-size: 0.72rem;">(${r.code})</span>
      </td>
      <td style="color: var(--text-muted); font-size: 0.75rem;">${r.team || ''}</td>
      <td style="color: var(--blue); font-size: 0.75rem; text-transform: uppercase;">${(r.ers_mode || 'hotlap_quali').replace('_', ' ')}</td>
      <td style="font-family: monospace; font-size: 0.9rem; font-weight: 700;">${r.lap_time}</td>
      <td style="font-family: monospace; color: ${r.rank === 1 ? 'var(--green)' : '#ff6b6b'}; font-weight: bold;">${r.gap}</td>
      <td class="${r.s1 === bestS1 ? 'purple-sector' : 'green-sector'}">${r.s1}${r.s1 === bestS1 ? ' 💜' : ''}</td>
      <td class="${r.s2 === bestS2 ? 'purple-sector' : 'green-sector'}">${r.s2}${r.s2 === bestS2 ? ' 💜' : ''}</td>
      <td class="${r.s3 === bestS3 ? 'purple-sector' : 'green-sector'}">${r.s3}${r.s3 === bestS3 ? ' 💜' : ''}</td>
      <td><strong>${r.top_speed}</strong></td>
      <td>${r.energy_deployed_mj.toFixed(2)} MJ</td>
      <td>${r.energy_harvested_mj.toFixed(2)} MJ</td>
      <td style="color: ${r.net_soc_delta_pct >= 0 ? 'var(--green)' : '#ff6b6b'}; font-weight: bold;">
        ${r.net_soc_delta_pct > 0 ? '+' : ''}${r.net_soc_delta_pct.toFixed(1)}%
      </td>
      <td>
        ${r.derate_time_s > 0 ? `<span class="derate-tag">${r.derate_time_s.toFixed(1)}s (${r.derate_pct.toFixed(1)}%)</span>` : '<span style="color: var(--green); font-size: 0.75rem;">Clean</span>'}
      </td>
    </tr>
  `).join('');
}

function renderLegends() {
  const container = document.getElementById('telemetryLegend');
  const board = currentData.grid || currentData.leaderboard || [];

  container.innerHTML = board.map(d => {
    const isDimmed = hiddenOnChart[d.code.toLowerCase()] || hiddenOnChart[d.code.toUpperCase()];
    return `
      <div class="legend-item ${isDimmed ? 'dimmed' : ''}" onclick="toggleTraceVisibility('${d.code}')" title="Click to toggle on telemetry charts">
        <span class="legend-bar" style="background: ${d.color};"></span>
        <span>${d.name} (${d.code})</span>
      </div>
    `;
  }).join('');
}

function toggleTraceVisibility(code) {
  const cLower = code.toLowerCase();
  hiddenOnChart[cLower] = !hiddenOnChart[cLower];
  hiddenOnChart[code.toUpperCase()] = hiddenOnChart[cLower];
  renderLegends();
  renderCharts();
}

function renderCharts() {
  drawCanvas('canvasSpeed', d => d.speed_kmh, null, false);
  drawCanvas('canvasDelta', d => d.delta_time_s, null, true);
  drawCanvas('canvasSoC', d => d.battery_soc_pct, [0, 100], false);
  drawCanvas('canvasMguk', d => d.mguk_power_kw, [-130, 130], true);
  drawCanvas('canvasDeploy', d => d.energy_deployed_mj, [0, 4.5], false, 4.0);
}

function drawCanvas(canvasId, getter, yRange, drawZero = false, drawLimit = null) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !currentData || !currentData.drivers) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width, h = rect.height;
  const padL = 45, padR = 15, padT = 12, padB = 18;
  const plotW = w - padL - padR, plotH = h - padT - padB;

  const dists = currentData.downsampled_distance_m;
  if (!dists || dists.length === 0) return;
  const maxDist = dists[dists.length - 1];

  let minY = yRange ? yRange[0] : Infinity;
  let maxY = yRange ? yRange[1] : -Infinity;

  const seenCodes = new Set();
  const driversToDraw = [];

  for (const rawCode in currentData.drivers) {
    const cLower = rawCode.toLowerCase();
    if (seenCodes.has(cLower)) continue;
    seenCodes.add(cLower);
    if (hiddenOnChart[cLower]) continue;
    driversToDraw.push({ code: cLower, drv: currentData.drivers[rawCode] });
  }

  if (!yRange) {
    for (const item of driversToDraw) {
      const vals = getter(item.drv);
      if (!vals) continue;
      for (const v of vals) {
        if (v < minY) minY = v;
        if (v > maxY) maxY = v;
      }
    }
    if (minY === Infinity || maxY === -Infinity) {
      minY = 0; maxY = 100;
    }
    const margin = (maxY - minY) * 0.1 || 1;
    minY -= margin;
    maxY += margin;
  }

  // Grid lines
  ctx.strokeStyle = '#181e2b';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const yVal = minY + (i / 4) * (maxY - minY);
    const py = padT + plotH - (i / 4) * plotH;
    ctx.beginPath();
    ctx.moveTo(padL, py);
    ctx.lineTo(padL + plotW, py);
    ctx.stroke();

    ctx.fillStyle = '#656e82';
    ctx.font = '9px monospace';
    ctx.textAlign = 'right';
    ctx.fillText(yVal.toFixed(1), padL - 5, py + 3);
  }

  // Zero line
  if (drawZero && minY < 0 && maxY > 0) {
    const pyZero = padT + plotH - ((0 - minY) / (maxY - minY)) * plotH;
    ctx.strokeStyle = '#394155';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(padL, pyZero);
    ctx.lineTo(padL + plotW, pyZero);
    ctx.stroke();
  }

  // Regulatory limit line
  if (drawLimit !== null) {
    const pyLim = padT + plotH - ((drawLimit - minY) / (maxY - minY)) * plotH;
    ctx.strokeStyle = '#e10600';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padL, pyLim);
    ctx.lineTo(padL + plotW, pyLim);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#ff6b6b';
    ctx.fillText('FIA 4.0 MJ Limit', padL + plotW - 75, pyLim - 3);
  }

  // Traces
  for (const item of driversToDraw) {
    const drv = item.drv;
    const vals = getter(drv);
    if (!vals || vals.length === 0) continue;
    ctx.strokeStyle = drv.color;
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    for (let i = 0; i < dists.length; i++) {
      const px = padL + (dists[i] / maxDist) * plotW;
      const py = padT + plotH - ((vals[i] - minY) / (maxY - minY)) * plotH;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }

  // Crosshair
  if (hoverDistIndex >= 0 && hoverDistIndex < dists.length) {
    const px = padL + (dists[hoverDistIndex] / maxDist) * plotW;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(px, padT);
    ctx.lineTo(px, padT + plotH);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

function setupHoverEvents() {
  ['canvasSpeed', 'canvasDelta', 'canvasSoC', 'canvasMguk', 'canvasDeploy'].forEach(id => {
    const canvas = document.getElementById(id);
    canvas.addEventListener('mousemove', e => {
      if (!currentData || !currentData.downsampled_distance_m) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left - 45;
      const plotW = rect.width - 60;
      if (x < 0 || x > plotW) return;
      
      const frac = x / plotW;
      const dists = currentData.downsampled_distance_m;
      hoverDistIndex = Math.min(dists.length - 1, Math.max(0, Math.round(frac * (dists.length - 1))));
      updateHoverStats();
      renderCharts();
    });
    canvas.addEventListener('mouseleave', () => {
      hoverDistIndex = -1;
      clearHoverStats();
      renderCharts();
    });
  });
}

function updateHoverStats() {
  if (!currentData || hoverDistIndex < 0 || !currentData.drivers) return;
  const dist = currentData.downsampled_distance_m[hoverDistIndex];

  const update = (elId, getter, unit) => {
    const el = document.getElementById(elId);
    if (!el) return;
    const items = [];
    const seen = new Set();
    for (const rawCode in currentData.drivers) {
      const c = rawCode.toLowerCase();
      if (seen.has(c)) continue;
      seen.add(c);
      if (hiddenOnChart[c]) continue;
      const drv = currentData.drivers[rawCode];
      const val = getter(drv)[hoverDistIndex];
      items.push(`<span style="color: ${drv.color}; font-weight: bold;">${c.toUpperCase()}: ${val}${unit}</span>`);
    }
    el.innerHTML = `s=${dist}m | ` + items.join(' | ');
  };

  update('hover-speed', d => d.speed_kmh, ' km/h');
  update('hover-delta', d => d.delta_time_s, 's');
  update('hover-soc', d => d.battery_soc_pct, '%');
  update('hover-mguk', d => d.mguk_power_kw, ' kW');
  update('hover-deploy', d => d.energy_deployed_mj, ' MJ');
}

function clearHoverStats() {
  ['hover-speed', 'hover-delta', 'hover-soc', 'hover-mguk', 'hover-deploy'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '';
  });
}

function exportCSV() {
  const track = document.getElementById('trackSelect').value;
  const yr = document.getElementById('seasonSelect').value;
  const mode = document.getElementById('simModeSelect').value;
  window.open(`/api/export-csv?track=${track}&year=${yr}&mode=${mode}`, '_blank');
}


// =========================================================
// ON-TRACK 2D SIMULATION ANIMATION ENGINE
// =========================================================

function initOnTrackSimulation() {
  if (!currentData) return;

  const seen = new Set();
  const driversList = [];
  for (const rawCode in currentData.drivers) {
    const c = rawCode.toLowerCase();
    if (!seen.has(c)) {
      seen.add(c);
      driversList.push(c);
    }
  }

  document.getElementById('onTrackCarCount').innerText = driversList.length;
  document.getElementById('onTrackMeta').innerText = `${currentData.track_name} • ${currentData.track_length_m.toLocaleString()} m`;

  maxLapTime = 0.0;
  driversList.forEach(code => {
    const d = currentData.drivers[code];
    if (d && d.time && d.time.length > 0) {
      const totalT = d.time[d.time.length - 1];
      if (totalT > maxLapTime) maxLapTime = totalT;
    }
  });

  if (maxLapTime === 0.0) maxLapTime = 80.0;
  document.getElementById('txtLapTotal').innerText = formatSeconds(maxLapTime);

  // Populate HUD driver select
  const hudSelect = document.getElementById('hudDriverSelect');
  hudSelect.innerHTML = driversList.map(code => {
    const d = currentData.drivers[code];
    return `<option value="${code}" ${code === focusedDriverCode ? 'selected' : ''}>${code.toUpperCase()} (${d.name})</option>`;
  }).join('');

  if ((!focusedDriverCode || !currentData.drivers[focusedDriverCode]) && driversList.length > 0) {
    focusedDriverCode = driversList[0];
    hudSelect.value = focusedDriverCode;
  }

  simTime = 0.0;
  lastTimestamp = performance.now();

  if (!animFrameId) {
    animFrameId = requestAnimationFrame(onTrackAnimLoop);
  }
}

function onTrackAnimLoop(timestamp) {
  const dt = (timestamp - lastTimestamp) / 1000.0;
  lastTimestamp = timestamp;

  const track2d = currentTrack2D || (currentData && currentData.track_2d);

  if (isPlaying && currentData && track2d) {
    simTime += (dt * playbackSpeed);
    if (simTime >= maxLapTime) {
      simTime = 0.0; // Loop lap
    }
    updateOnTrackState();
  }

  animFrameId = requestAnimationFrame(onTrackAnimLoop);
}

function togglePlayPause() {
  isPlaying = !isPlaying;
  document.getElementById('btnPlayPause').innerText = isPlaying ? "⏸ Pause" : "▶ Play";
}

function restartPlayback() {
  simTime = 0.0;
  updateOnTrackState();
}

function setSpeed(spd, elem) {
  playbackSpeed = spd;
  document.querySelectorAll('.speed-pill').forEach(el => el.classList.remove('active'));
  if (elem) elem.classList.add('active');
}

function onScrubLap(pct) {
  simTime = (parseFloat(pct) / 100.0) * maxLapTime;
  updateOnTrackState();
}

function onSelectHudDriver(code) {
  focusedDriverCode = code.toLowerCase();
  document.getElementById('hudDriverSelect').value = focusedDriverCode;
  updateOnTrackState();
}

function estimateGearFromSpeed(spd) {
  if (spd < 95.0) return 1;
  if (spd < 135.0) return 2;
  if (spd < 175.0) return 3;
  if (spd < 215.0) return 4;
  if (spd < 255.0) return 5;
  if (spd < 290.0) return 6;
  if (spd < 325.0) return 7;
  return 8;
}

function updateOnTrackState() {
  const track2d = currentTrack2D || (currentData && currentData.track_2d);
  if (!track2d) return;

  const pct = maxLapTime > 0 ? (simTime / maxLapTime) * 100.0 : 0.0;
  document.getElementById('lapScrubber').value = pct.toFixed(1);
  document.getElementById('txtLapTime').innerText = formatSeconds(simTime);

  const totalTrackLen = currentData ? currentData.track_length_m : track2d.total_length_m;
  const livePositions = [];

  if (currentData && currentData.drivers) {
    const seen = new Set();
    for (const rawCode in currentData.drivers) {
      const code = rawCode.toLowerCase();
      if (seen.has(code)) continue;
      seen.add(code);

      const drv = currentData.drivers[code];
      const state = interpolateDriverState(drv, simTime, totalTrackLen);
      if (!state) continue;
      
      const coord = interpolate2DTrackCoord(track2d, state.distance_m, totalTrackLen);
      state.x = coord.x;
      state.y = coord.y;
      state.heading = coord.heading;
      state.code = code;
      state.name = drv.name || code.toUpperCase();
      state.color = drv.color || '#fff';
      state.team = drv.team || '';
      state.number = drv.number || '';
      livePositions.push(state);
    }
  }

  // Sort by distance covered to establish running order
  livePositions.sort((a, b) => b.distance_m - a.distance_m);

  if (livePositions.length > 0) {
    document.getElementById('txtLapDist').innerText = `${Math.round(livePositions[0].distance_m).toLocaleString()} m`;
  }

  // Render 2D Circuit Canvas
  render2DTrackCanvas(track2d, livePositions);

  // Render Timing Tower & Cockpit HUD
  if (livePositions.length > 0) {
    renderLiveTimingTower(livePositions);
    const focusedState = livePositions.find(p => p.code === focusedDriverCode) || livePositions[0];
    if (focusedState) {
      updateCockpitHudState(focusedState);
    }
  } else {
    renderTimingTowerEmpty();
  }
}

function interpolateDriverState(drv, t, totalTrackLen) {
  if (!drv) return null;
  const times = drv.time;
  const dists = drv.distance || (currentData && currentData.downsampled_distance_m);

  if (!times || times.length === 0 || !dists || dists.length === 0) {
    return {
      distance_m: 0,
      speed_kmh: 0,
      throttle: 0,
      brake: 0,
      gear: 1,
      battery_soc_pct: 85.0,
      mguk_power_kw: 0,
      mguh_power_kw: 0,
      energy_deployed_mj: 0.0,
      energy_harvested_mj: 0.0,
      is_drs: false
    };
  }

  const n = times.length;

  if (t <= times[0]) {
    const spd = drv.speed_kmh ? drv.speed_kmh[0] : 0;
    return {
      distance_m: dists[0],
      speed_kmh: spd,
      throttle: drv.throttle ? drv.throttle[0] : 0,
      brake: drv.brake ? drv.brake[0] : 0,
      gear: (drv.gear && drv.gear[0]) ? drv.gear[0] : estimateGearFromSpeed(spd),
      battery_soc_pct: drv.battery_soc_pct ? drv.battery_soc_pct[0] : 85.0,
      mguk_power_kw: drv.mguk_power_kw ? drv.mguk_power_kw[0] : 0,
      mguh_power_kw: drv.mguh_power_kw ? drv.mguh_power_kw[0] : 0,
      energy_deployed_mj: drv.energy_deployed_mj ? drv.energy_deployed_mj[0] : 0.0,
      energy_harvested_mj: drv.energy_harvested_mj ? drv.energy_harvested_mj[0] : 0.0,
      is_drs: drv.is_drs ? drv.is_drs[0] : false
    };
  }
  if (t >= times[n - 1]) {
    const lastIdx = n - 1;
    const spd = drv.speed_kmh ? drv.speed_kmh[lastIdx] : 0;
    return {
      distance_m: dists[lastIdx],
      speed_kmh: spd,
      throttle: drv.throttle ? drv.throttle[lastIdx] : 0,
      brake: drv.brake ? drv.brake[lastIdx] : 0,
      gear: (drv.gear && drv.gear[lastIdx]) ? drv.gear[lastIdx] : estimateGearFromSpeed(spd),
      battery_soc_pct: drv.battery_soc_pct ? drv.battery_soc_pct[lastIdx] : 75.0,
      mguk_power_kw: drv.mguk_power_kw ? drv.mguk_power_kw[lastIdx] : 0,
      mguh_power_kw: drv.mguh_power_kw ? drv.mguh_power_kw[lastIdx] : 0,
      energy_deployed_mj: drv.energy_deployed_mj ? drv.energy_deployed_mj[lastIdx] : 0.0,
      energy_harvested_mj: drv.energy_harvested_mj ? drv.energy_harvested_mj[lastIdx] : 0.0,
      is_drs: drv.is_drs ? drv.is_drs[lastIdx] : false
    };
  }

  // Binary search for time interval
  let low = 0, high = n - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (times[mid] < t) low = mid + 1;
    else high = mid - 1;
  }

  const i = Math.max(1, low);
  const t0 = times[i - 1], t1 = times[i];
  const frac = (t - t0) / Math.max(1e-4, t1 - t0);

  const lerp = (arr) => {
    if (!arr || arr.length === 0) return 0.0;
    const v0 = arr[Math.max(0, i - 1)] || 0;
    const v1 = arr[Math.min(arr.length - 1, i)] || 0;
    return v0 + frac * (v1 - v0);
  };

  const currentSpeed = Math.round(lerp(drv.speed_kmh));
  const currentGear = (drv.gear && drv.gear.length > i) ? drv.gear[i] : estimateGearFromSpeed(currentSpeed);

  return {
    distance_m: lerp(dists),
    speed_kmh: currentSpeed,
    throttle: Math.max(0, Math.min(1, lerp(drv.throttle))),
    brake: Math.max(0, Math.min(1, lerp(drv.brake))),
    gear: currentGear,
    battery_soc_pct: lerp(drv.battery_soc_pct),
    mguk_power_kw: Math.round(lerp(drv.mguk_power_kw)),
    mguh_power_kw: Math.round(lerp(drv.mguh_power_kw)),
    energy_deployed_mj: lerp(drv.energy_deployed_mj),
    energy_harvested_mj: lerp(drv.energy_harvested_mj),
    is_drs: drv.is_drs ? Boolean(drv.is_drs[i]) : false
  };
}

function interpolate2DTrackCoord(track2d, dist_m, totalLen) {
  const distances = track2d.distances_m;
  const xs = track2d.x;
  const ys = track2d.y;
  const n = distances.length;

  const normD = (dist_m % totalLen + totalLen) % totalLen;
  
  let i = 0;
  for (let k = 0; k < n - 1; k++) {
    if (normD >= distances[k] && normD <= distances[k + 1]) {
      i = k;
      break;
    }
  }

  const nextI = (i + 1) % n;
  const d0 = distances[i], d1 = (nextI === 0 ? totalLen : distances[nextI]);
  const frac = (normD - d0) / Math.max(1e-4, d1 - d0);

  const x = xs[i] + frac * (xs[nextI] - xs[i]);
  const y = ys[i] + frac * (ys[nextI] - ys[i]);
  const heading = Math.atan2(ys[nextI] - ys[i], xs[nextI] - xs[i]);

  return { x, y, heading };
}

function render2DTrackCanvas(track2d, livePositions) {
  const canvas = document.getElementById('canvasTrack2D');
  if (!canvas || !track2d) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return;

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width, h = rect.height;
  const pad = 40;
  const mapX = x => pad + (x / 1000.0) * (w - 2 * pad);
  const mapY = y => pad + (y / 1000.0) * (h - 2 * pad);

  ctx.clearRect(0, 0, w, h);

  const xs = track2d.x || [];
  const ys = track2d.y || [];
  const n = xs.length;
  if (n === 0) return;

  // 1. Draw outer asphalt ribbon
  ctx.strokeStyle = '#1e2638';
  ctx.lineWidth = 14;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const px = mapX(xs[i]), py = mapY(ys[i]);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.stroke();

  // 2. Draw inner racing line with Sector Colors and DRS glow
  const pSectors = track2d.point_sectors || [];
  const pDrs = track2d.point_drs || [];

  for (let i = 0; i < n; i++) {
    const nextI = (i + 1) % n;
    const px0 = mapX(xs[i]), py0 = mapY(ys[i]);
    const px1 = mapX(xs[nextI]), py1 = mapY(ys[nextI]);

    ctx.lineWidth = 4;
    if (pDrs[i]) {
      ctx.strokeStyle = '#00d26a'; // Glowing DRS zone
      ctx.shadowColor = '#00d26a';
      ctx.shadowBlur = 6;
    } else {
      ctx.shadowBlur = 0;
      const sec = pSectors[i] || 1;
      ctx.strokeStyle = sec === 1 ? '#00b4d8' : sec === 2 ? '#ffb703' : '#d946ef';
    }

    ctx.beginPath();
    ctx.moveTo(px0, py0);
    ctx.lineTo(px1, py1);
    ctx.stroke();
  }
  ctx.shadowBlur = 0; // reset

  // 3. Draw Start/Finish Line
  if (n > 0) {
    const sfx = mapX(xs[0]), sfy = mapY(ys[0]);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(sfx, sfy, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#fff';
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 9px monospace';
    ctx.fillText('FINISH 🏁', sfx + 8, sfy - 6);
  }

  // 4. Draw Corner Annotations
  const corners = track2d.corners || [];
  ctx.fillStyle = '#848e9f';
  ctx.font = '8px sans-serif';
  corners.forEach(c => {
    if (c.name) {
      const cx = mapX(c.x), cy = mapY(c.y);
      ctx.fillText(c.name, cx + 4, cy - 4);
    }
  });

  // 5. If 0 drivers active, display clean preview label
  if (!livePositions || livePositions.length === 0) {
    ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
    ctx.fillRect(w / 2 - 160, h / 2 - 22, 320, 44);
    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 1;
    ctx.strokeRect(w / 2 - 160, h / 2 - 22, 320, 44);

    ctx.fillStyle = '#22c55e';
    ctx.font = 'bold 12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`🏎️ ${track2d.track_name || 'Circuit'} Ready`, w / 2, h / 2 - 2);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px sans-serif';
    ctx.fillText('Select drivers from the sidebar to start on-track simulation', w / 2, h / 2 + 13);
    ctx.textAlign = 'left';
    return;
  }

  // 6. Draw Animated Cars
  livePositions.forEach((pos, idx) => {
    const cx = mapX(pos.x);
    const cy = mapY(pos.y);
    const isFocused = pos.code === focusedDriverCode;

    // Small lateral spread to avoid badge occlusion
    const spread = ((idx % 3) - 1) * 7;
    const perpAngle = pos.heading + Math.PI / 2;
    const finalX = cx + Math.cos(perpAngle) * spread;
    const finalY = cy + Math.sin(perpAngle) * spread;

    // Focused car target ring
    if (isFocused) {
      ctx.strokeStyle = '#ffd700';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(finalX, finalY, 13, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Car dot
    ctx.fillStyle = pos.color || '#fff';
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(finalX, finalY, 6.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Car code label badge
    ctx.fillStyle = 'rgba(0, 0, 0, 0.78)';
    ctx.fillRect(finalX + 9, finalY - 8, 42, 14);
    ctx.strokeStyle = pos.color || '#fff';
    ctx.lineWidth = 1;
    ctx.strokeRect(finalX + 9, finalY - 8, 42, 14);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 8px monospace';
    ctx.fillText(`P${idx + 1} ${pos.code.toUpperCase()}`, finalX + 11, finalY + 2);
  });
}

function renderLiveTimingTower(positions) {
  const container = document.getElementById('liveTimingTower');
  if (!container) return;

  const leadDist = positions.length > 0 ? positions[0].distance_m : 0.0;

  container.innerHTML = positions.map((p, idx) => {
    const isFocused = p.code === focusedDriverCode;
    const intervalTxt = idx === 0 ? "LEADER" : `+${((leadDist - p.distance_m) / Math.max(10, p.speed_kmh / 3.6)).toFixed(2)}s`;
    const depVal = p.energy_deployed_mj ? p.energy_deployed_mj.toFixed(1) + 'M' : '0.0M';
    
    return `
      <div class="timing-row ${isFocused ? 'active-hud' : ''}" onclick="onSelectHudDriver('${p.code}')" title="Click to view onboard HUD">
        <div style="display: flex; align-items: center; gap: 6px;">
          <strong style="color: ${idx === 0 ? '#ffd700' : '#848e9f'}; width: 18px;">P${idx + 1}</strong>
          <span class="driver-dot" style="background-color: ${p.color};"></span>
          <strong>${p.code.toUpperCase()}</strong>
          <span style="font-size: 0.68rem; color: #38bdf8; background: rgba(56,189,248,0.1); padding: 1px 3px; border-radius: 2px;">G${p.gear}</span>
          <span style="font-size: 0.68rem; color: #94a3b8;">${p.speed_kmh}k</span>
        </div>
        <div style="font-family: monospace; font-size: 0.75rem; color: ${idx === 0 ? 'var(--green)' : '#ff6b6b'}; font-weight: 700;">
          ${intervalTxt}
        </div>
      </div>
    `;
  }).join('');
}

function updateCockpitHudState(state) {
  document.getElementById('hudDriverName').innerText = state.name;
  document.getElementById('hudDriverTeam').innerText = state.team;
  document.getElementById('hudDriverDot').style.backgroundColor = state.color;
  document.getElementById('hudSpeed').innerHTML = `${state.speed_kmh} <span style="font-size: 0.7rem; font-weight: normal;">km/h</span>`;
  document.getElementById('hudGear').innerText = state.gear;

  // Throttle & Brake
  const thPct = Math.round(state.throttle * 100);
  const brPct = Math.round(state.brake * 100);
  document.getElementById('hudThrottleVal').innerText = `${thPct}%`;
  document.getElementById('hudBrakeVal').innerText = `${brPct}%`;
  document.getElementById('hudThrottleBar').style.width = `${thPct}%`;
  document.getElementById('hudBrakeBar').style.width = `${brPct}%`;

  // Energy Deployed & Harvested (Dynamic Live HUD)
  const dep = state.energy_deployed_mj || 0.0;
  const harv = state.energy_harvested_mj || 0.0;
  const mguh = state.mguh_power_kw || 0.0;
  document.getElementById('hudDeployVal').innerText = `${dep.toFixed(2)} MJ`;
  document.getElementById('hudHarvestVal').innerText = `${harv.toFixed(2)} MJ`;
  document.getElementById('hudMguhVal').innerText = `${mguh.toFixed(0)} kW`;
  const depPct = Math.min(100, Math.round((dep / 4.0) * 100));
  document.getElementById('hudDeployBar').style.width = `${depPct}%`;

  // Battery SoC
  document.getElementById('hudSoc').innerText = `${state.battery_soc_pct.toFixed(1)}%`;

  // MGU-K Power
  const pwr = state.mguk_power_kw;
  const pwrTxt = pwr >= 0 ? `+${pwr} kW (Deploy)` : `${pwr} kW (Regen)`;
  const pwrEl = document.getElementById('hudMguk');
  pwrEl.innerText = pwrTxt;
  pwrEl.style.color = pwr >= 0 ? '#38bdf8' : '#fbbf24';

  // DRS Flap
  const drsEl = document.getElementById('hudDrsBadge');
  if (state.is_drs) {
    drsEl.className = 'drs-badge drs-on';
    drsEl.innerText = 'DRS OPEN ⚡';
  } else {
    drsEl.className = 'drs-badge drs-off';
    drsEl.innerText = 'DRS CLOSED';
  }
}

function formatSeconds(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toFixed(3).padStart(6, '0')}`;
}

window.addEventListener('load', () => {
  setupHoverEvents();
  initData();
});
window.addEventListener('resize', () => {
  renderCharts();
  const track2d = currentTrack2D || (currentData && currentData.track_2d);
  if (track2d) {
    updateOnTrackState();
  }
});
</script>
</body>
</html>
"""


class F1SimHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for the interactive F1 simulation server."""

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url.query)

        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_INDEX.encode("utf-8"))
            return

        elif url.path == "/api/seasons":
            seasons = list_seasons()
            self._send_json(seasons)
            return

        elif url.path == "/api/tracks":
            year_val = params.get("year", [None])[0]
            year_int = int(year_val) if year_val and year_val.isdigit() else None
            circuits = list_circuits(year=year_int)
            self._send_json(circuits)
            return

        elif url.path == "/api/track-2d":
            track_name = params.get("track", ["monza"])[0]
            try:
                track = get_circuit(track_name)
                t2d = build_smooth_2d_track(track, track.total_length_m)
            except Exception:
                t2d = build_smooth_2d_track(track_name, 5000.0)
            self._send_json(t2d)
            return

        elif url.path == "/api/drivers":
            year_val = params.get("year", [None])[0]
            year_int = int(year_val) if year_val and year_val.isdigit() else None
            drivers = list_driver_presets(year=year_int)
            self._send_json(drivers)
            return

        elif url.path == "/api/export-csv":
            track_name = params.get("track", ["monza"])[0]
            mode = params.get("mode", ["race"])[0]
            year_val = params.get("year", ["2024"])[0]
            year_int = int(year_val) if year_val and year_val.isdigit() else 2024
            track = get_circuit(track_name)
            
            # Use top grid drivers for export
            driver_codes = ["ver", "nor", "lec", "ham", "pia", "sai", "rus", "per"]
            drivers = [get_driver_preset(c, year=year_int) for c in driver_codes]

            if mode == "qualifying":
                sim = QualifyingSimulator()
                res = sim.simulate(track=track, drivers=drivers, year=year_int, dx=2.0)
                csv_content = res.to_csv()
                fname = f"f1_qualifying_{track_name}_{year_int}.csv"
            else:
                sim = LapSimulator()
                lap_results = [sim.simulate(track, d, dx=2.0, year=year_int) for d in drivers]
                comp = TelemetryComparison(lap_results)
                csv_content = comp.to_csv()
                fname = f"f1_telemetry_{track_name}_{year_int}.csv"

            self.send_response(200)
            self.send_header("Content-type", "text/csv")
            self.send_header("Content-Disposition", f"attachment; filename={fname}")
            self.end_headers()
            self.wfile.write(csv_content.encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/simulate":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}

            track_name = data.get("track", "monza")
            year = data.get("year", None)
            mode = data.get("mode", "ontrack")
            track = get_circuit(track_name)

            drivers_spec = data.get("drivers", [{"code": "ver"}, {"code": "ham"}])
            drivers = []

            for spec in drivers_spec:
                code = spec.get("code", "ver")
                drv = get_driver_preset(code, year=year)
                
                # Apply dynamic overrides from UI sliders
                if "strategy" in spec:
                    for m in ERSMode:
                        if m.value == spec["strategy"]:
                            drv.ers_mode = m
                            break
                if "braking_offset_m" in spec:
                    drv.braking_offset_m = float(spec["braking_offset_m"])
                if "lift_and_coast_m" in spec:
                    drv.lift_and_coast_m = float(spec["lift_and_coast_m"])
                if "throttle_aggression" in spec:
                    drv.throttle_aggression = float(spec["throttle_aggression"])
                if "cornering_grip_factor" in spec:
                    drv.cornering_grip_factor = float(spec["cornering_grip_factor"])

                drivers.append(drv)

            # Execute simulation based on requested mode
            if mode == "qualifying":
                sim = QualifyingSimulator()
                dx_step = 3.0 if len(drivers) > 10 else 2.0
                quali_res = sim.simulate(track=track, drivers=drivers, year=year, dx=dx_step)
                resp_dict = quali_res.to_dict()
            else:
                sim = LapSimulator()
                results = []
                for drv in drivers:
                    res = sim.simulate(track, drv, dx=2.0, year=year)
                    results.append(res)
                comparison = TelemetryComparison(results)
                resp_dict = comparison.to_dict()
                resp_dict["mode"] = mode

            # Attach 2D smooth track coordinates, corners, DRS zones, and sectors
            resp_dict["track_2d"] = build_smooth_2d_track(track, track.total_length_m)
            self._send_json(resp_dict)
            return

        self.send_error(404, "Endpoint not found")

    def _send_json(self, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def run_server(port: int = 8050):
    handler = F1SimHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"\n=======================================================")
        print(f" F1 ERS Simulation Web Dashboard is running!")
        print(f" Open your browser at: http://localhost:{port}")
        print(f" Press Ctrl+C to stop the server.")
        print(f"=======================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    port = 8050
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
