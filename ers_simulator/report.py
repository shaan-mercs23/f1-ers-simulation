"""
Formula 1 ERS Simulation Report & Visualization Generator
==========================================================
Produces interactive standalone HTML comparison reports and publication-quality
Matplotlib multi-pane telemetry analysis charts.
"""

from typing import Optional
import json
import os
from .telemetry import TelemetryComparison


def generate_html_report(comparison: TelemetryComparison, output_path: str = "f1_ers_report.html"):
    """
    Generate an interactive, dark-themed HTML report comparing driver telemetry.
    Pure self-contained HTML/CSS/JS with embedded SVG and Canvas telemetry graphs.
    """
    data = comparison.to_dict()
    json_data = json.dumps(data)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>F1 ERS Telemetry Comparison - {data['track_name']}</title>
<style>
  :root {{
    --bg-dark: #0f1117;
    --card-bg: #1a1d26;
    --card-border: #2a2e3d;
    --text-primary: #f0f2f5;
    --text-secondary: #9ba1b0;
    --accent-red: #e10600;
    --accent-green: #00d26a;
    --accent-yellow: #ffb703;
    --accent-blue: #00b4d8;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  body {{ background-color: var(--bg-dark); color: var(--text-primary); padding: 24px; line-height: 1.5; }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  
  header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--accent-red); padding-bottom: 16px; margin-bottom: 24px; }}
  h1 {{ font-size: 1.8rem; font-weight: 800; letter-spacing: -0.5px; display: flex; align-items: center; gap: 12px; }}
  .f1-badge {{ background: var(--accent-red); color: white; padding: 4px 10px; border-radius: 4px; font-size: 0.85rem; font-weight: 900; letter-spacing: 1px; }}
  .track-meta {{ color: var(--text-secondary); font-size: 0.95rem; text-align: right; }}

  /* Cards */
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; margin-bottom: 24px; }}
  .card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 8px; padding: 18px; }}
  .card h2 {{ font-size: 1.1rem; color: var(--text-secondary); margin-bottom: 14px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; border-bottom: 1px solid var(--card-border); padding-bottom: 8px; }}

  /* Leaderboard Table */
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; }}
  th {{ color: var(--text-secondary); padding: 10px 12px; font-weight: 600; border-bottom: 2px solid var(--card-border); }}
  td {{ padding: 12px; border-bottom: 1px solid var(--card-border); }}
  tr:hover {{ background: rgba(255, 255, 255, 0.03); }}
  .driver-tag {{ display: inline-flex; align-items: center; gap: 8px; font-weight: 700; }}
  .driver-pill {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
  .lap-time {{ font-family: monospace; font-size: 1.05rem; font-weight: 700; color: #fff; }}
  .gap-pos {{ color: var(--accent-green); font-family: monospace; }}
  .gap-neg {{ color: var(--accent-red); font-family: monospace; }}
  .derate-badge {{ background: rgba(225, 6, 0, 0.2); color: #ff6b6b; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }}

  /* Charts Container */
  .chart-box {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 8px; padding: 18px; margin-bottom: 20px; }}
  .chart-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
  .chart-title {{ font-size: 1.05rem; font-weight: 700; }}
  canvas {{ width: 100%; height: 260px; display: block; }}
  
  .legend {{ display: flex; gap: 16px; font-size: 0.85rem; font-weight: 600; flex-wrap: wrap; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; }}
  .legend-color {{ width: 14px; height: 4px; border-radius: 2px; }}

  .insights-card {{ border-left: 4px solid var(--accent-yellow); }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div>
      <h1><span class="f1-badge">F1 ERS</span> Energy Recovery & Deployment Telemetry</h1>
      <p style="color: var(--text-secondary); margin-top: 4px;">Dynamic multi-driver energy flow & lap time sensitivity analysis</p>
    </div>
    <div class="track-meta">
      <div style="font-size: 1.2rem; font-weight: 700; color: #fff;">{data['track_name']}</div>
      <div>Circuit Length: {data['track_length_m']:,.0f} m &bull; Reference: <strong>{data['reference_driver']}</strong></div>
    </div>
  </header>

  <!-- Leaderboard -->
  <div class="card" style="margin-bottom: 24px;">
    <h2>Driver Comparison Leaderboard & ERS Balance</h2>
    <table>
      <thead>
        <tr>
          <th>Pos</th>
          <th>Driver</th>
          <th>Team / Strategy</th>
          <th>Lap Time</th>
          <th>Gap</th>
          <th>Top Speed</th>
          <th>Avg Speed</th>
          <th>Deployed (ES)</th>
          <th>Harvested (K+H)</th>
          <th>Net &Delta;SoC</th>
          <th>Derate / Clipping</th>
        </tr>
      </thead>
      <tbody>
        {"".join(f'''
        <tr>
          <td><strong>P{row['rank']}</strong></td>
          <td>
            <div class="driver-tag">
              <span class="driver-pill" style="background-color: {row['color']};"></span>
              <span>{row['name']}</span>
              <span style="font-size: 0.75rem; color: var(--text-secondary);">({row['code']})</span>
            </div>
          </td>
          <td>{row['team']} <br><span style="font-size: 0.75rem; color: var(--accent-blue); text-transform: uppercase;">{row['ers_mode']}</span></td>
          <td class="lap-time">{row['lap_time']}</td>
          <td><span class="{ 'gap-pos' if row['rank'] == 1 else 'gap-neg' }">{row['gap']}</span></td>
          <td><strong>{row['top_speed']}</strong> km/h</td>
          <td>{row['avg_speed']} km/h</td>
          <td><strong>{row['energy_deployed_mj']:.2f}</strong> MJ</td>
          <td><strong>{row['energy_harvested_mj']:.2f}</strong> MJ</td>
          <td style="color: {'var(--accent-green)' if row['net_soc_delta_pct'] >= 0 else 'var(--accent-red)'}; font-weight: bold;">
            {row['net_soc_delta_pct']:+.1f}%
          </td>
          <td>
            {f"<span class='derate-badge'>{row['derate_time_s']:.1f}s ({row['derate_pct']:.1f}%)</span>" if row['derate_time_s'] > 0 else "<span style='color: var(--accent-green); font-size: 0.85rem;'>None (Clean)</span>"}
          </td>
        </tr>
        ''' for row in data['leaderboard'])}
      </tbody>
    </table>
  </div>

  <!-- Sector Splits -->
  <div class="card" style="margin-bottom: 24px;">
    <h2>Sector Split Times (S1 / S2 / S3)</h2>
    <table>
      <thead>
        <tr>
          <th>Driver</th>
          <th>Sector 1</th>
          <th>Sector 2</th>
          <th>Sector 3</th>
          <th>Total Lap</th>
        </tr>
      </thead>
      <tbody>
        {"".join(f'''
        <tr>
          <td><strong>{row['name']}</strong></td>
          <td>{row['s1']}</td>
          <td>{row['s2']}</td>
          <td>{row['s3']}</td>
          <td class="lap-time">{row['lap_time']}</td>
        </tr>
        ''' for row in data['leaderboard'])}
      </tbody>
    </table>
  </div>

  <!-- Charts Section -->
  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Velocity Profile (km/h vs Distance)</div>
      <div class="legend" id="legend-speed"></div>
    </div>
    <canvas id="chartSpeed"></canvas>
  </div>

  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Time Delta vs Reference Driver (&Delta;t in seconds - Positive = Slower, Negative = Faster)</div>
      <div class="legend" id="legend-delta"></div>
    </div>
    <canvas id="chartDelta"></canvas>
  </div>

  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Energy Store State-of-Charge (Battery % vs Distance)</div>
      <div class="legend" id="legend-soc"></div>
    </div>
    <canvas id="chartSoC"></canvas>
  </div>

  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">MGU-K Power (kW: Positive = Deployment, Negative = Braking Regen)</div>
      <div class="legend" id="legend-mguk"></div>
    </div>
    <canvas id="chartMguk"></canvas>
  </div>

  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Cumulative Energy Deployed from Battery (MJ vs Distance &bull; Regulatory Limit: 4.0 MJ)</div>
      <div class="legend" id="legend-deploy"></div>
    </div>
    <canvas id="chartDeploy"></canvas>
  </div>

</div>

<script>
const simData = {json_data};

function initLegends() {{
  const drivers = simData.leaderboard;
  ['legend-speed', 'legend-delta', 'legend-soc', 'legend-mguk', 'legend-deploy'].forEach(id => {{
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = drivers.map(d => `
      <div class="legend-item">
        <span class="legend-color" style="background-color: ${{d.color}}"></span>
        <span>${{d.name}} (${{d.code}})</span>
      </div>
    `).join('');
  }});
}}

function renderChart(canvasId, seriesGetter, yLabel, yRange, drawZeroLine = false, drawLimitLine = null) {{
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  const padL = 60, padR = 25, padT = 20, padB = 30;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const dists = simData.downsampled_distance_m;
  const maxDist = dists[dists.length - 1];

  let minY = yRange ? yRange[0] : Infinity;
  let maxY = yRange ? yRange[1] : -Infinity;

  if (!yRange) {{
    for (const code in simData.drivers) {{
      const vals = seriesGetter(simData.drivers[code]);
      for (const v of vals) {{
        if (v < minY) minY = v;
        if (v > maxY) maxY = v;
      }}
    }}
    const margin = (maxY - minY) * 0.1 || 1;
    minY -= margin;
    maxY += margin;
  }}

  // Background grid
  ctx.strokeStyle = '#222634';
  ctx.lineWidth = 1;
  const gridStepsY = 5;
  for (let i = 0; i <= gridStepsY; i++) {{
    const yVal = minY + (i / gridStepsY) * (maxY - minY);
    const py = padT + plotH - (i / gridStepsY) * plotH;
    ctx.beginPath();
    ctx.moveTo(padL, py);
    ctx.lineTo(padL + plotW, py);
    ctx.stroke();

    ctx.fillStyle = '#7a8294';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(yVal.toFixed(1), padL - 8, py + 3);
  }}

  // Zero line if requested
  if (drawZeroLine && minY < 0 && maxY > 0) {{
    const pyZero = padT + plotH - ((0 - minY) / (maxY - minY)) * plotH;
    ctx.strokeStyle = '#4a5162';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(padL, pyZero);
    ctx.lineTo(padL + plotW, pyZero);
    ctx.stroke();
  }}

  // Regulatory limit line (e.g. 4.0 MJ)
  if (drawLimitLine !== null) {{
    const pyLim = padT + plotH - ((drawLimitLine - minY) / (maxY - minY)) * plotH;
    ctx.strokeStyle = '#e10600';
    ctx.setLineDash([6, 4]);
    ctx.beginPath();
    ctx.moveTo(padL, pyLim);
    ctx.lineTo(padL + plotW, pyLim);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#ff6b6b';
    ctx.fillText('FIA 4.0 MJ Limit', padL + plotW - 80, pyLim - 6);
  }}

  // Draw driver series
  for (const code in simData.drivers) {{
    const drv = simData.drivers[code];
    const vals = seriesGetter(drv);
    ctx.strokeStyle = drv.color;
    ctx.lineWidth = 2.0;
    ctx.beginPath();

    for (let i = 0; i < dists.length; i++) {{
      const px = padL + (dists[i] / maxDist) * plotW;
      const py = padT + plotH - ((vals[i] - minY) / (maxY - minY)) * plotH;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }}
    ctx.stroke();
  }}
}}

window.addEventListener('load', () => {{
  initLegends();
  renderChart('chartSpeed', d => d.speed_kmh, 'km/h');
  renderChart('chartDelta', d => d.delta_time_s, '&Delta;t (s)', null, true);
  renderChart('chartSoC', d => d.battery_soc_pct, 'SoC %', [0, 100]);
  renderChart('chartMguk', d => d.mguk_power_kw, 'MGU-K kW', [-130, 130], true);
  renderChart('chartDeploy', d => d.energy_deployed_mj, 'MJ', [0, 4.5], false, 4.0);
}});
window.addEventListener('resize', () => {{
  renderChart('chartSpeed', d => d.speed_kmh, 'km/h');
  renderChart('chartDelta', d => d.delta_time_s, '&Delta;t (s)', null, true);
  renderChart('chartSoC', d => d.battery_soc_pct, 'SoC %', [0, 100]);
  renderChart('chartMguk', d => d.mguk_power_kw, 'MGU-K kW', [-130, 130], true);
  renderChart('chartDeploy', d => d.energy_deployed_mj, 'MJ', [0, 4.5], false, 4.0);
}});
</script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path


def generate_matplotlib_script(comparison: TelemetryComparison, script_path: str = "plot_telemetry.py"):
    """
    Generate a standalone python script that creates multi-pane matplotlib figures.
    Can be run independently if matplotlib is installed.
    """
    script_content = f'''"""
Standalone Matplotlib Visualizer for F1 ERS Telemetry Comparison
================================================================
Generated automatically by the F1 ERS Simulation Suite.
Run with: python {script_path}
"""
import sys

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Error: matplotlib is required to run this script.")
    print("Install it with: pip install matplotlib")
    sys.exit(1)

import json

# Load telemetry
with open("telemetry_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

dists = np.array(data["downsampled_distance_m"])
drivers = data["drivers"]

fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
plt.style.use('dark_background')

# Plot 1: Speed Profile
ax0 = axes[0]
for code, d in drivers.items():
    ax0.plot(dists, d["speed_kmh"], label=f"{{d['name']}} ({{code}})", color=d["color"], lw=1.8)
ax0.set_ylabel("Speed (km/h)")
ax0.set_title(f"F1 Telemetry Comparison - {{data['track_name']}}", fontsize=14, fontweight='bold', pad=10)
ax0.legend(loc="lower right")
ax0.grid(True, alpha=0.25)

# Plot 2: Delta Time vs Reference
ax1 = axes[1]
ref_code = data["reference_driver"]
for code, d in drivers.items():
    ax1.plot(dists, d["delta_time_s"], label=f"&Delta;t vs {{ref_code}}", color=d["color"], lw=1.8)
ax1.axhline(0, color="gray", linestyle="--", alpha=0.7)
ax1.set_ylabel("&Delta;Time (s)")
ax1.legend(loc="upper left")
ax1.grid(True, alpha=0.25)

# Plot 3: Battery SoC & Clipping
ax2 = axes[2]
for code, d in drivers.items():
    ax2.plot(dists, d["battery_soc_pct"], label=f"{{code}} SoC", color=d["color"], lw=1.8)
ax2.set_ylabel("Battery SoC (%)")
ax2.set_ylim([0, 100])
ax2.legend(loc="lower left")
ax2.grid(True, alpha=0.25)

# Plot 4: MGU-K Power and FIA 4MJ Energy Limit
ax3 = axes[3]
for code, d in drivers.items():
    ax3.plot(dists, d["mguk_power_kw"], label=f"{{code}} MGU-K", color=d["color"], lw=1.5)
ax3.axhline(120, color="red", linestyle=":", label="120 kW FIA Cap")
ax3.axhline(-120, color="green", linestyle=":", label="-120 kW Regen Cap")
ax3.set_ylabel("MGU-K Power (kW)")
ax3.set_xlabel("Track Distance (meters)")
ax3.legend(loc="lower right")
ax3.grid(True, alpha=0.25)

plt.tight_layout()
plt.savefig("f1_telemetry_comparison.png", dpi=200)
print("Saved comparison chart to f1_telemetry_comparison.png")
plt.show()
'''
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    return script_path
