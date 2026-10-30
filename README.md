# Formula 1 Energy Recovery System (ERS) Modelling & Driver Lap Time Simulator

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![FIA Regulations](https://img.shields.io/badge/FIA_PU_Regulations-2022--2025_Compliant-red.svg)](https://www.fia.com/)
[![Driver Roster](https://img.shields.io/badge/drivers-36%20F1%20Drivers-blue.svg)]()
[![Track Calendar](https://img.shields.io/badge/tracks-Multi--Season%20Calendars%20(2020--2025)-red.svg)]()
[![Qualifying Mode](https://img.shields.io/badge/qualifying-Q1%2FQ2%2FQ3%20Knockout-purple.svg)]()
[![On-Track Simulation](https://img.shields.io/badge/on--track-2D%20Live%20Simulation-brightgreen.svg)]()
[![Tests Status](https://img.shields.io/badge/tests-27%20passed-brightgreen.svg)]()

A comprehensive physics-based longitudinal vehicle dynamics and powertrain simulation suite for modelling **Formula 1 Energy Recovery Systems (ERS)**. Accurately simulates the harvesting, storage, and deployment dynamics of modern **1.6L V6 Turbocharged Hybrid Power Units** and provides an analytical laboratory to **simulate Qualifying Shootouts (Q1, Q2, Q3 Knockout), Race Pace, and Live 2D On-Track Circuit Racing across ANY number of drivers (1 to full 20+ grid) and every Grand Prix circuit divided by Championship Year**.

---

## Table of Contents
1. [Overview & Engineering Background](#overview--engineering-background)
2. [Powertrain & ERS Physical Architecture](#powertrain--ers-physical-architecture)
   - [Internal Combustion Engine (ICE)](#1-internal-combustion-engine-ice)
   - [MGU-K (Motor Generator Unit - Kinetic)](#2-mgu-k-motor-generator-unit---kinetic)
   - [MGU-H (Motor Generator Unit - Heat)](#3-mgu-h-motor-generator-unit---heat)
   - [Energy Store (ES / Battery Pack)](#4-energy-store-es--battery-pack)
3. [Qualifying Simulation Engine (Q1, Q2, Q3 Knockout)](#qualifying-simulation-engine-q1-q2-q3-knockout)
4. [Complete F1 Driver Database (2020–2025+)](#complete-f1-driver-database-20202025)
5. [Grand Prix Track Calendars Divided by Year](#grand-prix-track-calendars-divided-by-year)
6. [ERS Strategic Deployment Modes](#ers-strategic-deployment-modes)
7. [Mathematical Formulation & Solver](#mathematical-formulation--solver)
8. [Quickstart Guide](#quickstart-guide)
   - [Command-Line Interface (CLI)](#running-via-cli)
   - [Interactive Web Dashboard](#interactive-web-dashboard)
   - [Python API Usage](#python-api-usage)
9. [Telemetry Analysis & Output Metrics](#telemetry-analysis--output-metrics)
10. [Project Architecture](#project-architecture)
11. [Verification & Testing](#verification--testing)

---

## Overview & Engineering Background

In modern Formula 1, vehicle lap time is heavily governed by the optimal management of electrical energy. While internal combustion engines are strictly fuel-flow limited by the FIA ($100\text{ kg/h}$), the **Energy Recovery System (ERS)** contributes up to **120 kW (~161 bhp)** of instantaneous mechanical boost.

However, strict regulatory caps apply:
- **Maximum 4.0 MJ per lap** transferred from the Energy Store (battery) to the MGU-K.
- **Maximum 2.0 MJ per lap** harvested by the MGU-K into the Energy Store under braking.
- **Unlimited energy transfer** between the MGU-H and the Energy Store, and **unlimited direct feed** between the MGU-H and MGU-K via the DC bus.

Because the energy needed to deploy 120 kW over an entire lap exceeds the 4.0 MJ battery budget on high-speed circuits (like Monza, Spa-Francorchamps, Baku, or Las Vegas), cars inevitably suffer from **clipping / derate** (the sudden loss of electrical boost on straights) if energy is deployed aggressively.

This project simulates these coupled electrical, thermal, aerodynamic, and vehicle dynamics, allowing direct comparison of:
- **Every Formula 1 driver** across the modern Turbo-Hybrid era with season-by-season team liveries, numbers, and driving styles.
- **Every Grand Prix circuit divided by championship year** (2020, 2021, 2022, 2023, 2024, 2025).
- **Driver styles**: Aggressive late braking vs. smooth trail-braking, throttle exit snap, and Lift-and-Coast (L&C) harvesting.
- **ERS deployment strategies**: Qualifying Hotlap vs. Race Balanced vs. Overtake Boost vs. Optimal Pontryagin allocation.

---

## Powertrain & ERS Physical Architecture

```
                    ┌────────────────────────────────────────────────────────┐
                    │                   EXHAUST GAS FLOW                     │
                    └──────────────────────────┬─────────────────────────────┘
                                               │
                                               ▼
   ┌─────────────┐                      ┌─────────────┐
   │             │                      │             │
   │  F1 FUEL    │                      │    MGU-H    │◄──── Unlimited Energy Loop ────┐
   │ (100 kg/h)  │                      │ (Turbine/   │                                │
   │             │                      │ Compressor) │                                │
   └──────┬──────┘                      └──────┬──────┘                                │
          │                                    │ Electrical (30-55 kW)                 │
          ▼                                    ▼                                       │
   ┌─────────────┐                      ┌─────────────┐       Direct DC Bus            │
   │   1.6L V6   │── Mechanical Axis ──►│   DC BUS    │────────────────────────┐       │
   │    TURBO    │                      │  (750V DC)  │                        │       │
   │    (ICE)    │                      └──────┬──────┘                        │       │
   └──────┬──────┘                             │                               │       │
          │                                    │ Discharge / Charge            ▼       │
          │ Mechanical                         ▼                       ┌─────────────┐ │
          │ Power                       ┌─────────────┐                │             │ │
          │ (~590 kW)                   │ENERGY STORE │◄───────────────┤    MGU-K    │─┘
          │                             │  (BATTERY)  │  4MJ Deploy    │(Crankshaft) │
          │                             │ 4.0MJ Usable│  2MJ Harvest   │ (Max 120kW) │
          │                             └─────────────┘                └──────┬──────┘
          │                                                                   │
          ▼                                                                   ▼
   ┌─────────────────────────────────────────────────────────────────────────────────┐
   │                           DRIVETRAIN & REAR WHEELS                              │
   │                  Tractive Force = (P_ICE + P_MGUK) / Velocity                   │
   └─────────────────────────────────────────────────────────────────────────────────┘
```

### 1. Internal Combustion Engine (ICE)
- **Architecture**: 1.6-litre $90^\circ$ V6 single turbocharger, 4 valves per cylinder.
- **Fuel Mass Flow Limit**: Maximum $100\text{ kg/h}$ ($0.02778\text{ kg/s}$) above 10,500 RPM.
- **Lower Heating Value**: $44.0\text{ MJ/kg}$.
- **Thermal Efficiency**: Peak $\eta_{th} \approx 50\%$.
- **Peak Mechanical Output**: $\sim 590\text{ kW}$ ($\sim 791\text{ bhp}$).
- **Power Curve**: Incorporates low-speed traction modulation and high-RPM rev-limiter/frictional roll-off up to the terminal gear ratio ceiling.

### 2. MGU-K (Motor Generator Unit - Kinetic)
- **Mechanical Connection**: Geared directly to the engine crankshaft.
- **Maximum Deployment Power**: $120\text{ kW}$ ($160.9\text{ bhp}$).
- **Maximum Regenerative Braking**: $120\text{ kW}$.
- **Regulatory Lap Energy Limits**:
  - Max energy from Energy Store to MGU-K: **$4.0\text{ MJ}$ per lap**.
  - Max energy from MGU-K to Energy Store: **$2.0\text{ MJ}$ per lap**.
- **Efficiencies**: $\eta_{motor} = 96\%$, $\eta_{gen} = 95\%$.
- **Brake-by-Wire Integration**: Under braking, the MGU-K absorbs up to 120 kW of kinetic power; any required deceleration beyond this threshold is handled by the carbon-carbon hydraulic friction brakes.

### 3. MGU-H (Motor Generator Unit - Heat)
- **Mechanical Connection**: Mounted coaxially between the exhaust turbine and compressor wheel of the turbocharger.
- **Regulatory Limit**: **Unlimited per lap**.
- **Harvesting Role**: Under full throttle, excess exhaust enthalpy spins the turbine, allowing MGU-H to generate $30\text{ kW} - 55\text{ kW}$ of continuous electrical power.
- **Direct DC Bus Transfer**: Power generated by the MGU-H can bypass the Energy Store and be routed **directly to the MGU-K**. This allows up to 50+ kW of sustained boost even after the 4.0 MJ battery budget has been exhausted.

### 4. Energy Store (ES / Battery Pack)
- **Total Capacity**: $5.0\text{ MJ}$ ($\approx 1.39\text{ kWh}$), with a $4.0\text{ MJ}$ usable operating window.
- **State-of-Charge (SoC)**: Dynamically tracked between $15\%$ and $95\%$.
- **Internal Resistance & Ohmic Losses**: $P_{loss} = I^2 R_{int} = \frac{P_{elec}^2}{V_{bus}^2} R_{int}$ ($R_{int} = 0.08\,\Omega$, $V_{bus} = 750\text{V}$).
- **Thermal Model**: Tracks cell temperature rise from Joule heating balanced by liquid convective cooling.

---

## Qualifying Simulation Engine (Q1, Q2, Q3 Knockout)

The project includes an authentic Formula 1 **Qualifying Simulation Engine** that models the full intensity of an official Grand Prix qualifying shootout:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        OFFICIAL F1 QUALIFYING SESSIONS                 │
├───────────────────┬───────────────────────────────┬────────────────────┤
│ Q1 Session        │ Q2 Session                    │ Q3 Shootout        │
│ 18 Minutes        │ 15 Minutes                    │ 12 Minutes         │
│ All Drivers Run   │ Top 15 Advance (Top 10 if <16)│ Top 10 for Pole    │
│ Bottom 5 Cutoff   │ Bottom 5 Cutoff               │ POLE POSITION 🏁   │
├───────────────────┼───────────────────────────────┼────────────────────┤
│ Fuel: 3.8 kg      │ Fuel: 3.5 kg                  │ Fuel: 3.2 kg       │
│ Party Mode: +8 kW │ Party Mode: +10 kW            │ Party Mode: +12 kW │
│ Track Grip: 1.025 │ Track Grip: 1.033 (+0.8%)     │ Track Grip: 1.040  │
└───────────────────┴───────────────────────────────┴────────────────────┘
```

### Physical Realism in Qualifying Mode:
1. **Knockout Elimination Brackets**:
   - Supports **ANY number of drivers** (1 driver solo hotlap, 2-driver head-to-head duel, top 10 shootout, or full 20+ grid).
   - If $\ge 16$ drivers: Standard 3-stage elimination ($Q1 \to Q2 \to Q3$).
   - If $11 \dots 15$ drivers: 2-stage elimination into the Top 10 shootout.
   - If $\le 10$ drivers: Dedicated 3-phase shootout evolution for all contenders.
2. **Track Evolution & Rubbering-In**:
   - As cars lay down Pirelli rubber across the session, track surface grip evolves: $+0.8\%$ in Q2 and $+1.5\%$ in Q3, producing the iconic qualifying lap time progression observed in real F1 weekends.
3. **Engine "Party Mode" & Minimum Weight Configuration**:
   - ICE peak power is boosted by $+8\text{ kW}$ (Q1), $+10\text{ kW}$ (Q2), and $+12\text{ kW}$ ($\sim 16\text{ hp}$) in Q3.
   - Vehicle mass drops to qualifying specification ($\sim 3.2\text{ kg}$ fuel payload vs $100+\text{ kg}$ race start fuel).
   - Softest compound Pirelli slicks ($+2.5\%$ baseline lateral grip multiplier).
   - $100\%$ Full-Attack ERS Hotlap deployment strategy with **$0\text{m}$ Lift and Coast**.
4. **Purple Sector & Speed Trap Detection**:
   - Identifies overall session Purple Sector 1, Sector 2, Sector 3 split times and the Top Speed Trap champion ($V_{max}$).

---

## Complete F1 Driver Database (2020–2025+)

The database contains **every single driver** who competed in Formula 1 across recent championship seasons. Drivers automatically adapt their **team livery, car number, and color** depending on the selected Championship Year:

| Code | Driver | Number | Country | Active Seasons | Primary Teams | Style Traits |
|:---:|:---|:---:|:---:|:---:|:---|:---|
| `VER` | **Max Verstappen** | #1 | NED | 2020–2025 | Red Bull Racing | Ultra-late braking ($-7.5\text{m}$), rapid throttle snap, high traction exit. |
| `HAM` | **Lewis Hamilton** | #44 | GBR | 2020–2025 | Mercedes / Ferrari | Smooth trail-braking ($-2.0\text{m}$), high apex roll speed, steady energy flow. |
| `LEC` | **Charles Leclerc** | #16 | MON | 2020–2025 | Scuderia Ferrari | Qualifying speed maestro, dances on knife-edge of rear rotation ($-6.8\text{m}$). |
| `NOR` | **Lando Norris** | #4 | GBR | 2020–2025 | McLaren | Fluid flowing line, mathematically optimal Pontryagin energy distribution. |
| `PIA` | **Oscar Piastri** | #81 | AUS | 2023–2025 | McLaren | Ultra-calm inputs, steady battery equilibrium, precise mid-corner release. |
| `SAI` | **Carlos Sainz** | #55 | ESP | 2020–2025 | Ferrari / Williams / McLaren | Tactical, cerebral approach with high corner-entry stability. |
| `RUS` | **George Russell** | #63 | GBR | 2020–2025 | Mercedes / Williams | High-energy qualifying approach with aggressive apex entry ($-5.0\text{m}$). |
| `ALO` | **Fernando Alonso** | #14 | ESP | 2021–2025 | Aston Martin / Alpine | Tactical battery hoarder; heavy Lift & Coast ($35\text{m}$) then full DRS boost. |
| `PER` | **Sergio Perez** | #11 | MEX | 2020–2024 | Red Bull / Racing Point | Master of rear tire preservation and smooth linear throttle ramp. |
| `ALB` | **Alex Albon** | #23 | THA | 2020, 22–25 | Williams / Red Bull | Extracts maximum straight-line top speed with deep corner-entry commitment. |
| `COL` | **Franco Colapinto**| #43 | ARG | 2024–2025 | Williams | Fearless high-speed commitment and sharp throttle pick-up on street circuits. |
| `GAS` | **Pierre Gasly** | #10 | FRA | 2020–2025 | Alpine / AlphaTauri | High mid-corner momentum carrier with punchy qualifying laps. |
| `OCO` | **Esteban Ocon** | #31 | FRA | 2020–2025 | Haas / Alpine / Renault | Stubborn defensive racer; hoards battery energy to defend straights. |
| `HUL` | **Nico Hulkenberg** | #27 | GER | 2020, 22–25 | Sauber / Haas / Racing Point | Qualifying specialist; extracts 100% of tire grip on single flying laps. |
| `TSU` | **Yuki Tsunoda** | #22 | JPN | 2021–2025 | RB (VCARB) / AlphaTauri | Sharp initial steering bite, commits hard into mid-speed turns. |
| `RIC` | **Daniel Ricciardo**| #3 | AUS | 2020–2024 | RB / McLaren / Renault | Late-braking divebomb specialist with deep progressive trail-braking. |
| `LAW` | **Liam Lawson** | #30 | NZL | 2023–2025 | RB / Red Bull | Assertive combative wheel-to-wheel racer with decisive braking bite. |
| `BOT` | **Valtteri Bottas** | #77 | FIN | 2020–2025 | Sauber / Mercedes / Alfa Romeo | Geometric corner arcs with exceptional single-lap qualifying precision. |
| `ZHO` | **Zhou Guanyu** | #24 | CHN | 2022–2025 | Sauber / Alfa Romeo | Consistent, smooth steering inputs preserving battery charge and tires. |
| `BEA` | **Oliver Bearman** | #38 | GBR | 2024–2025 | Haas / Ferrari | High-speed courage and mature throttle application. |
| `STR` | **Lance Stroll** | #18 | CAN | 2020–2025 | Aston Martin / Racing Point | Strong straight-line traction focus with early upshifts. |
| `MAG` | **Kevin Magnussen** | #20 | DEN | 2020, 22–24 | Haas | Aggressive wheel-to-wheel combatant with violent braking bites. |
| `VET` | **Sebastian Vettel** | #5 | GER | 2020–2022 | Aston Martin / Ferrari | Rear-planted driving style; uses engine braking and MGU-K regen to rotate. |
| `RAI` | **Kimi Raikkonen** | #7 | FIN | 2020–2021 | Alfa Romeo | The Iceman; supreme front-end sensitivity and kinetic energy conservation. |
| `ANT` | **Kimi Antonelli** | #12 | ITA | 2025 | Mercedes | Rapid throttle pick-up and agile high-speed direction change. |
| `DOO` | **Jack Doohan** | #7 | AUS | 2025 | Alpine | Sharp throttle response and aggressive corner exit commitment. |
| `BOR` | **Gabriel Bortoleto**| #5 | BRA | 2025 | Sauber / Audi | F2 & F3 champion with mature racecraft and rapid tire warm-up. |
| `SAR` | **Logan Sargeant** | #2 | USA | 2023–2024 | Williams | Steady progressive braking with moderate cornering loading. |
| `MSC` | **Mick Schumacher** | #47 | GER | 2021–2022 | Haas | Progressive input buildup with methodical lap time improvement. |
| `LAT` | **Nicholas Latifi** | #6 | CAN | 2020–2022 | Williams | Conservative braking markers and steady throttle exit. |
| `GIO` | **Antonio Giovinazzi**| #99 | ITA | 2020–2021 | Alfa Romeo | Strong single-lap qualifying pace on low fuel. |
| `DEV` | **Nyck de Vries** | #21 | NED | 2022–2023 | AlphaTauri / Williams | Formula E champion with deep EV powertrain energy management knowledge. |
| `KVY` | **Daniil Kvyat** | #26 | RUS | 2020 | AlphaTauri | Aggressive apex turn-in and strong initial braking force. |
| `GRO` | **Romain Grosjean** | #8 | FRA | 2020 | Haas | Tremendous raw speed and apex commitment on positive front-end grip. |

---

## Grand Prix Track Calendars Divided by Year

Circuits are cataloged with authentic corner names, radii, elevation profiles, and DRS zones, divided into championship seasons:

| Circuit | Country | Length | Seasons | Key Characteristics & ERS Challenge |
|:---|:---:|:---:|:---:|:---|
| **Monza (Autodromo Nazionale)** | Italy | 5,793 m | 2020–2025 | Temple of Speed. Long straights and violent chicanes. Primary benchmark for **ERS clipping & derating**. |
| **Silverstone Circuit** | UK | 5,891 m | 2020–2025 | High-G lateral corners (Copse, Maggotts, Becketts). Low heavy braking; relies heavily on continuous MGU-H harvest. |
| **Spa-Francorchamps** | Belgium | 7,004 m | 2020–2025 | Dramatic elevation change. Full-throttle climb through Eau Rouge/Raidillon into Kemmel Straight where clipping costs up to $0.4\text{s}$. |
| **Circuit de Monaco** | Monaco | 3,337 m | 2021–2025 | Slowest average speed. Frequent heavy braking enables massive MGU-K regeneration; battery rarely depletes. |
| **Red Bull Ring (Spielberg)** | Austria | 4,318 m | 2020–2025 | Short lap featuring three consecutive uphill DRS straights into heavy braking hairpins. Ideal for comparing overtake tactics. |
| **Bahrain International Circuit** | Bahrain | 5,412 m | 2020–2025 | Traction-demanding layout with 4 DRS straights and punishing braking into Turn 1 and Turn 10. |
| **Jeddah Corniche Circuit** | Saudi Arabia | 6,174 m | 2021–2025 | Fastest street circuit in motorsport history (250+ km/h avg) with continuous full throttle. |
| **Suzuka Circuit** | Japan | 5,807 m | 2022–2025 | Figure-8 layout with high lateral load through the Esses, Degners, and flat-out 130R. |
| **Baku City Circuit** | Azerbaijan | 6,003 m | 2021–2025 | Tight medieval castle section paired with the longest full-throttle straight in F1 (2.2 km). Immense derating battle. |
| **Las Vegas Strip Circuit** | USA | 6,201 m | 2023–2025 | Cold night temperatures with a mammoth 1.9 km full-throttle blast down the Las Vegas Strip. |
| **Interlagos (Autodromo Jose Carlos Pace)**| Brazil | 4,309 m | 2021–2025 | Anti-clockwise amphitheater with steep elevation, Senna S descent, and uphill drag up Subida dos Boxes. |
| **Circuit of the Americas (COTA)** | USA | 5,513 m | 2021–2025 | Steep 11% gradient climb into Turn 1, Silverstone-inspired Esses, and a 1 km back straight. |
| **Albert Park (Melbourne)** | Australia | 5,278 m | 2022–2025 | Fast semi-street parkland track with 4 DRS zones and ultra-high-speed sweepers. |
| **Hungaroring (Budapest)** | Hungary | 4,381 m | 2020–2025 | Monaco without walls. Relentless medium-speed corners testing mechanical grip and MGU-K corner exit punch. |
| **Circuit Zandvoort** | Netherlands | 4,259 m | 2021–2025 | Seaside sand dunes featuring steep 18-degree Indianapolis-style banked corners. |

---

## ERS Strategic Deployment Modes

Drivers switch between different ERS software maps on their steering wheel dials:

1. **`HOTLAP_QUALI` (Qualifying Push)**:
   - Requests full $120\text{ kW}$ MGU-K deployment on every throttle application until the 4.0 MJ regulatory budget is exhausted or the battery hits $15\%$ SoC.
   - Yields the fastest initial acceleration out of early corners, but frequently induces **clipping / derate** on the final straight of power circuits.
2. **`RACE_BALANCED` (Net-Zero Delta Strategy)**:
   - Deploys energy preferentially at low speeds ($v < 200\text{ km/h}$) where acceleration gain is highest ($\Delta a \propto \frac{P}{v}$).
   - Tapers deployment at high speeds above a cutoff threshold ($v > 290\text{ km/h}$) where aerodynamic drag absorbs power with diminishing returns.
   - Targets $\Delta SoC \approx 0$ across the full lap so the strategy can be sustained over a race stint.
3. **`OVERTAKE_PUSH` (Passing / Defensive Boost)**:
   - Conserves battery in twisty sectors where overtaking is impossible.
   - Unleashes full $120\text{ kW}$ boost throughout designated DRS passing zones to maximize top speed ($V_{max}$).
4. **`OPTIMAL_DYNAMIC` (Pontryagin Sensitivity Control)**:
   - Allocates the 4.0 MJ battery budget dynamically based on the local time sensitivity gradient:
     $$\left| \frac{\partial t}{\partial E} \right| \propto \frac{1}{M \cdot v^2 \cdot a_{net}}$$
   - Produces the theoretical minimum lap time for any given energy budget.
5. **`RECHARGE_HARVEST` (In-Lap / Preparation Mode)**:
   - Restricts MGU-K deployment to low levels ($< 40\text{ kW}$) and extends Lift-and-Coast to maximize battery replenishment ($\Delta SoC > +15\%$) prior to a flying lap.

---

## Mathematical Formulation & Solver

The simulation engine uses a **two-pass forward-backward quasi-steady-state numerical integration** scheme with cyclic convergence across start/finish lines:

### 1. Apex Speed Envelope
At every track point $s_i$, the maximum speed permitted by lateral tire friction and aerodynamic downforce is computed:
$$M \frac{v^2}{R} \le \kappa_{grip} \cdot \mu_{lat} \left( M g + \frac{1}{2} \rho C_L A \cdot v^2 \right)$$
Solving for $v_{apex}(s_i)$:
$$v_{apex}(s_i) = \sqrt{ \frac{\kappa_{grip} \mu_{lat} M g}{\frac{M}{R(s_i)} - \frac{1}{2}\rho C_L A \kappa_{grip} \mu_{lat}} }$$

### 2. Backward Pass (Braking Zones)
Starting from each apex backward along the track:
$$v_{back}[i] = \min\left( v_{apex}[i],\, \sqrt{v_{back}[i+1]^2 + 2 \cdot a_{decel}(v) \cdot \Delta s} \right)$$
where deceleration includes tire braking, aerodynamic drag, rolling resistance, and track gradient:
$$a_{decel}(v) = \frac{\alpha_{brake} \cdot \mu_{brake} F_z(v) + \frac{1}{2}\rho C_D A v^2 + C_{rr} F_z(v) + M g \sin\theta}{M}$$

### 3. Forward Pass & Cyclic Convergence
To ensure the start/finish line crossing speed accurately reflects the acceleration out of the circuit's final corner, the solver identifies the slowest apex on the circuit and integrates forward around the track before recording the timed lap:
$$F_{tract} = \min\left( \frac{P_{ICE}(v) + P_{MGUK}(s, v)}{v},\, \mu_{accel} F_z(v) \right)$$
$$a_{net} = \frac{F_{tract} - \frac{1}{2}\rho C_D A v^2 (1 - \Delta_{DRS}) - C_{rr} F_z(v) - M g \sin\theta}{M}$$
$$v_{next} = \min\left( v_{back}[i+1],\, \sqrt{v[i]^2 + 2 a_{net} \Delta s} \right)$$

### 4. Derate & Clipping Detection
When cumulative Energy Store deployment hits the regulatory ceiling:
$$E_{deployed} \ge 4.0\text{ MJ} \quad \text{or} \quad SoC \le 0.15$$
The MGU-K cuts off electrical power from the battery. The vehicle drops to **direct MGU-H feed only** ($\sim 45\text{ kW}$), causing a sharp deceleration penalty on the remainder of the straight.

---

## Quickstart Guide

### Running via CLI

The CLI enables multi-driver comparisons, official qualifying shootouts, season filtering, and automated telemetry exports for **any number of drivers**:

```bash
# 1. Run Official F1 Qualifying Shootout (Q1, Q2, Q3 Knockout) for ALL drivers
python cli.py qualify --drivers all --track monza --year 2024

# 2. Run Qualifying Shootout for any custom group of drivers
python cli.py qualify --drivers ver,nor,lec,pia,ham,rus,sai --track spa --year 2024

# 3. Compare any number of drivers in Race Pace simulation
python cli.py compare --drivers ver,ham,nor,lec --track monza --year 2024
python cli.py compare --drivers all --track silverstone --year 2024

# 4. Compare teammate duels across different seasons
python cli.py compare --drivers nor,pia --track silverstone --year 2024
python cli.py compare --drivers ham,rus --track spa --year 2023

# 5. List all championship seasons, circuits, and drivers
python cli.py list-seasons
python cli.py list-tracks --year 2024
python cli.py list-drivers --year 2024

# 6. Export full spatial telemetry or qualifying grid to CSV
python cli.py export-csv --drivers ver,ham,alo --track jeddah --year 2024 --output jeddah_telemetry.csv
python cli.py qualify --drivers all --track monza --year 2024 --csv-output monza_quali.csv
```

---

### Interactive Web Dashboard

To launch the browser-based graphical laboratory:

```bash
python app.py
```
Open **`http://localhost:8050`** in your browser.

#### Dashboard Capabilities:
- **Simulation Modes (Under Top Dropdown & Quick Buttons)**:
  - `🏎️ On-Track Simulation`: Live 2D interactive circuit map animation where selected cars race against each other with real-time speed, dynamic gap intervals, and an authentic cockpit telemetry HUD.
  - `⚡ Qualifying Shootout (Q1/Q2/Q3)`: Low fuel, engine party mode, soft Pirelli compound, and full 3-stage knockout grid.
  - `▶ Race Simulation`: Full fuel mass, custom driver tactics, and race pace degradation.
- **Interactive 2D On-Track Simulation Arena**:
  - **Live Animated Circuit Map**: Cars visually drive the circuit in real-time with authentic livery colors and driver codes (`VER #1`, `NOR #4`, `LEC #16`, `HAM #44`, etc.).
  - **Dynamic DRS & Sector Glow**: Glowing neon-green DRS straightaways and distinct Sector 1 (cyan), Sector 2 (yellow), and Sector 3 (magenta) zones.
  - **Live Timing Tower**: Instant running order (P1, P2, P3...) with real-time intervals to the car ahead (`+0.24s`).
  - **Live Cockpit Telemetry HUD**: Digital speedometer ($\text{km/h}$), gear gauge ($1 \dots 8$), throttle/brake pedals, battery State-of-Charge $\%$, MGU-K power status ($+120\text{ kW}$ deploy / $-120\text{ kW}$ regen), and DRS wing flap indicator.
  - **Full Playback Controls**: Play, Pause, Restart, playback speed selector ($0.5\times, 1\times, 2\times, 4\times, 8\times$), and spatial lap scrubber slider ($0\text{m} \dots L_{track}$).
- **Compare ANY Number of Drivers**:
  - Select 1, 2, 5, 10, or all 20+ drivers on the grid with zero artificial limits.
  - Quick presets: "Full Grid (All Drivers)", "Top 10 Quali", "Top 4", "Teammate Duels", or "Clear".
  - Interactive legend filter: Click on any driver in the chart legend to toggle their individual telemetry curve on/off without changing the leaderboard!
- **Championship Year Selector**: Choose 2025, 2024, 2023, 2022, 2021, 2020, or All Seasons.
- **Dynamic Track Calendar**: Automatically loads the exact Grand Prix rounds for the selected year.
- **Pole Position & Purple Sector Showcase**: Highlights the Pole winner, Purple Sectors (S1, S2, S3), and Top Speed Trap.
- **Real-Time Driver Tuning**: Expandable tuning drawer on each driver card to adjust Braking Offset, Lift & Coast, Throttle Aggression, and ERS Strategy.
- **Synchronized Telemetry Charts**: Live crosshair scrubbing across Speed, Delta Time, Battery SoC, MGU-K Power, and FIA 4.0 MJ Cumulative Energy.

---

### Python API Usage

```python
from ers_simulator import (
    LapSimulator,
    QualifyingSimulator,
    get_circuit,
    get_driver_preset,
    list_driver_presets,
    ERSMode,
)
from ers_simulator.telemetry import TelemetryComparison

# Load circuit from calendar
spa = get_circuit("spa")

# -------------------------------------------------------------
# 1. Qualifying Shootout Simulation (Any Number of Drivers)
# -------------------------------------------------------------
quali_sim = QualifyingSimulator()
drivers = [
    get_driver_preset("ver", year=2024),
    get_driver_preset("nor", year=2024),
    get_driver_preset("lec", year=2024),
    get_driver_preset("ham", year=2024),
]
quali_result = quali_sim.simulate(track=spa, drivers=drivers, year=2024, dx=2.0)

print(f"POLE POSITION: {quali_result.pole_driver.driver.name} - {quali_result.pole_time_str}")
print(f"PURPLE S1: {quali_result.purple_s1_driver} ({quali_result.purple_s1_s:.3f}s)")
print(f"SPEED TRAP: {quali_result.speed_trap_driver} ({quali_result.speed_trap_kmh:.1f} km/h)")

# -------------------------------------------------------------
# 2. Race Lap Simulation & Telemetry Comparison
# -------------------------------------------------------------
sim = LapSimulator()
res_ver = sim.simulate(spa, drivers[0], dx=2.0)
res_nor = sim.simulate(spa, drivers[1], dx=2.0)

comp = TelemetryComparison([res_ver, res_nor])
print(f"VER Race: {res_ver.lap_time_str} | Deployed: {res_ver.energy_deployed_mj:.2f} MJ")
print(f"NOR Race: {res_nor.lap_time_str} | Deployed: {res_nor.energy_deployed_mj:.2f} MJ")
```

---

## Telemetry Analysis & Output Metrics

| Telemetry Channel | Unit | Description |
|:---|:---:|:---|
| `distance_m` | $\text{m}$ | Distance from start/finish line. |
| `time_s` | $\text{s}$ | Elapsed lap time. |
| `speed_kmh` | $\text{km/h}$ | Instantaneous vehicle ground speed. |
| `delta_time_s` | $\text{s}$ | Instantaneous time delta relative to reference driver ($\Delta t > 0$ means slower). |
| `throttle` | $0.0 \dots 1.0$ | Throttle pedal application. |
| `brake` | $0.0 \dots 1.0$ | Normalized braking force demand. |
| `gear` | $1 \dots 8$ | Seamless gearbox gear ratio estimation. |
| `accel_g` | $\text{g}$ | Longitudinal acceleration/deceleration. |
| `lateral_g` | $\text{g}$ | Lateral cornering acceleration. |
| `mguk_power_kw` | $\text{kW}$ | Mechanical power at crankshaft (positive = deploy up to $120\text{ kW}$, negative = regen). |
| `mguh_power_kw` | $\text{kW}$ | Electrical power generated from exhaust turbine ($30-55\text{ kW}$). |
| `battery_soc` | $\%$ | Energy Store State-of-Charge. |
| `battery_temp_c`| $^\circ\text{C}$ | Battery cell temperature. |
| `cumulative_deployed_mj` | $\text{MJ}$ | Total energy drawn from Energy Store (capped by FIA at $4.0\text{ MJ}$). |
| `is_clipping` | Boolean | True when vehicle is in derate due to 4MJ limit or battery depletion. |
| `is_drs` | Boolean | DRS flap open indicator. |

---

## Project Architecture

```
python project/
├── pyproject.toml              # Build metadata
├── requirements.txt            # Dependency list (NumPy)
├── README.md                   # Complete documentation
├── run.bat                     # Windows interactive launcher
├── run.ps1                     # PowerShell launcher
├── app.py                      # Standalone Web Dashboard & HTTP API
├── cli.py                      # Command-Line Interface
├── ers_simulator/              # Core Simulation Package
│   ├── vehicle.py              # ICE, MGU-K, MGU-H, EnergyStore & Aerodynamics
│   ├── track.py                # Multi-season track calendars (2020-2025) & geometry definitions
│   ├── driver.py               # Complete driver database (36 drivers) with year mappings
│   ├── ers_strategy.py         # Tactical ERS modes (Quali, Balanced, Overtake, Pontryagin)
│   ├── solver.py               # Forward-backward quasi-steady-state numerical integrator
│   ├── telemetry.py            # Multi-driver delta-t comparison, sector audits, CSV/JSON export
│   └── report.py               # Standalone interactive HTML report generator
└── tests/                      # Verification & Unit Test Suite
    ├── test_vehicle.py         # Powertrain physics, power curves & regulatory caps
    ├── test_strategy.py        # Strategy deployment algorithms & Lift & Coast triggers
    ├── test_solver.py          # Lap time integration & driver comparison verification
    └── test_seasons_and_drivers.py # Multi-season calendar & complete driver roster tests
```

---

## Verification & Testing

The test suite validates physical laws, energy balances, and FIA regulatory constraints:

```bash
python -m unittest discover tests
```

Tests cover:
- **ICE Power & Fuel Flow**: Verifies $100\text{ kg/h}$ fuel limit and power roll-off.
- **Battery Dynamics**: Validates $I^2 R$ heat loss, discharge rates, and SoC bounds.
- **FIA 120 kW MGU-K Cap**: Ensures mechanical deployment never exceeds $120\text{ kW}$.
- **FIA 4.0 MJ / 2.0 MJ Caps**: Confirms clipping/derate occurs when the 4.0 MJ allowance is exhausted.
- **Multi-Season Calendar Consistency**: Validates calendar integrity and round ordering across 2020–2025.
- **Driver Database & Year Adaptation**: Verifies drivers change teams and livery colors according to season.
- **Lap Time Plausibility**: Verifies simulated lap times and top speeds against authentic FIA Grand Prix telemetry.

---

## License

This project is open-source under the MIT License. See [LICENSE](LICENSE) for details.
