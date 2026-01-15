# 3D Option Flight Simulator - Python Backend

A Python backend system for generating, analyzing, and visualizing option market telemetry in a 4D kinematic state space. This module generates synthetic market scenarios, computes flight envelope coordinates, and produces interactive HTML visualizations.

## Overview

The Python backend provides the simulation engine for the 4D Option Flight Simulator. It generates synthetic price and volatility paths, maps them to 3D coordinates (X, Y, Z), computes flight regimes and flags, and outputs both JSONL telemetry logs and interactive HTML visualizations.

**Purpose**: Generate test scenarios, run Monte Carlo simulations, and produce telemetry data for visualization in the frontend Three.js application (`4dflightapp/`).

## Architecture

### Core Concept

The system maps financial market metrics to a 3D kinematic state space:

- **X-axis (Structural Airspeed)**: `|spot - flip| / ATR` - Distance from flip point normalized by Average True Range
- **Y-axis (Load Factor)**: `IV / HV` - Implied Volatility vs. Historical Volatility ratio
- **Z-axis (Wall Proximity)**: Normalized distance to Put/Call option walls (0 at wall, 1 at flip)

The 4th dimension (time) is represented through sequential telemetry frames.

### Module Structure

```
fineagle/4dflight/
├── __init__.py           # Package exports
├── envelope.py           # Flight envelope geometry and coordinate mapping
├── dynamics.py           # Synthetic path generators
├── telemetry.py          # Telemetry computation engine
├── io.py                 # JSONL file I/O
├── renderer.py           # HTML visualization generator
├── scenario_runner.py    # Orchestration and Monte Carlo runner
└── output/               # Generated telemetry logs and HTML files
```

## Modules

### 1. `envelope.py` - Flight Envelope

**Classes**: `EnvelopeConfig`, `FlightEnvelope`

**Purpose**: Defines the flight envelope geometry and maps market data to 3D coordinates.

**Key Components**:

- `**EnvelopeConfig**` (dataclass): Configuration for envelope parameters
  - `atr`: Average True Range
  - `flip`: Flip point (typically at-the-money strike)
  - `put_wall`: Put option wall (support level)
  - `call_wall`: Call option wall (resistance level)
  - `risk_proxy_base`: Base risk proxy value (default: 1.0)
- `**FlightEnvelope**`: Evaluates market state and computes coordinates
  - `evaluate_state(spot, iv, hv)`: Computes X, Y, Z coordinates and breach/stall/overspeed flags
  - `get_regime(x, y)`: Classifies flight regime (TAXI, CRUISE, MANEUVER, RUPTURE)

**Regime Classification**:

- **TAXI**: X < 0.3 (very close to flip)
- **CRUISE**: 0.3 <= X < 2.5 and Y < 1.5 (normal operation)
- **MANEUVER**: X >= 2.5 or Y >= 1.5 (elevated risk)
- **RUPTURE**: X > 4.5 or Y > 2.5 (extreme conditions)

### 2. `dynamics.py` - Path Generator

**Class**: `PathGenerator`

**Purpose**: Generates synthetic price and volatility paths for scenario testing.

**Methods**:

- `**mean_revert_pin(target, intensity, noise)**`: Generates mean-reverting path around a target (e.g., flip point)
- `**breakout(direction, speed, noise)**`: Generates breakout path with follow-through
- `**false_breakout(target_wall, breach_depth, recovery)**`: Generates false breakout that breaches a wall then snaps back
- `**generate_vol_path(start_iv, target_iv, shock_at)**`: Generates implied volatility path with optional shock

**Usage**:

```python
gen = PathGenerator(start_spot=694.0, atr=2.8, steps=200)
spots = gen.mean_revert_pin(target=692.5)
ivs = gen.generate_vol_path(start_iv=0.15)
```

### 3. `telemetry.py` - Telemetry Engine

**Class**: `TelemetryEngine`

**Purpose**: Computes per-step telemetry from price/volatility paths.

**Methods**:

- `**compute_step(spot, iv, hv, timestamp)**`: Computes telemetry frame for a single timestep
  - Returns: `{timestamp, spot, iv, hv, x, y, z, regime, flags}`
  - Flags: `BREACH`, `OVERSPEED`, `STALL` based on envelope evaluation

**Output Format**:

```python
{
    "timestamp": 0,
    "spot": 694.0,
    "iv": 0.15,
    "hv": 0.12,
    "x": 0.536,
    "y": 1.25,
    "z": 0.8,
    "regime": "CRUISE",
    "flags": []
}
```

### 4. `io.py` - Telemetry Logger

**Class**: `TelemetryLogger`

**Purpose**: Handles JSONL file I/O for telemetry data.

**Methods**:

- `**save_log(filepath, data)**`: Saves list of telemetry frames to JSONL file (one JSON object per line)
- `**load_log(filepath)**`: Loads telemetry frames from JSONL file

**File Format**: JSONL (JSON Lines) - one JSON object per line, newline-separated.

### 5. `renderer.py` - Flight Renderer

**Class**: `FlightRenderer`

**Purpose**: Generates interactive 3D HTML visualizations from telemetry logs.

**Methods**:

- `**render_to_html(output_path)**`: Generates self-contained HTML file with embedded JavaScript
  - Includes Canvas 2D rendering for 3D wireframe visualization
  - Interactive controls: play/pause, timeline scrubber, speed selector
  - HUD overlay with telemetry display
  - Keyboard controls (WASD, arrows, Q/E, Space)

**Output**: Self-contained HTML file that can be opened in any modern browser.

### 6. `scenario_runner.py` - Scenario Runner

**Class**: `ScenarioRunner`

**Purpose**: Orchestrates scenario generation, telemetry computation, logging, and rendering.

**Methods**:

- `**run_scenario(name, path_type, steps)**`: Runs a single scenario
  - Generates price/volatility paths
  - Computes telemetry for each step
  - Saves JSONL log to `output/` directory
  - Returns telemetry data
- `**run_monte_carlo(name, path_type, n_runs, steps)**`: Runs multiple simulations
  - Executes `n_runs` scenarios
  - Computes summary statistics (breach rate, max load)
  - Prints results to console

**Supported Path Types**:

- `"mean_revert"`: Mean-reverting path around flip
- `"breakout"`: Upward breakout with follow-through
- `"false_breakout"`: Breach and snap-back pattern

## Usage

### Basic Example

```python
from fineagle.4dflight import EnvelopeConfig, ScenarioRunner

# Configure envelope
config = EnvelopeConfig(
    atr=2.8,
    flip=692.5,
    put_wall=680.0,
    call_wall=700.0
)

# Create runner
runner = ScenarioRunner(config)

# Run a scenario
log_data = runner.run_scenario("my_test", path_type="breakout", steps=200)
# Output: fineagle/4dflight/output/my_test.jsonl

# Generate visualization
from fineagle.4dflight import FlightRenderer
renderer = FlightRenderer(log_data, config)
renderer.render_to_html("fineagle/4dflight/output/my_test.html")
```

### Running the Example Script

```bash
# From project root
python -m fineagle.4dflight.scenario_runner

# This will:
# 1. Generate three test scenarios (mean_revert, breakout, false_breakout)
# 2. Save JSONL logs to output/
# 3. Generate HTML visualizations
# 4. Run a Monte Carlo simulation
```

### Custom Path Generation

```python
from fineagle.4dflight import EnvelopeConfig, FlightEnvelope, PathGenerator, TelemetryEngine, TelemetryLogger

config = EnvelopeConfig(atr=2.8, flip=692.5, put_wall=680.0, call_wall=700.0)
envelope = FlightEnvelope(config)
telemetry = TelemetryEngine(envelope)

# Generate custom path
gen = PathGenerator(start_spot=694.0, atr=2.8, steps=200)
spots = gen.mean_revert_pin(target=692.5, intensity=0.15)
ivs = gen.generate_vol_path(start_iv=0.15, target_iv=0.18)
hvs = [0.12] * 200

# Compute telemetry
log_data = []
for i in range(200):
    step = telemetry.compute_step(spots[i], ivs[i], hvs[i], timestamp=i)
    log_data.append(step)

# Save
TelemetryLogger.save_log("output/custom.jsonl", log_data)
```

## Dependencies

- **Python 3.7+**
- **numpy**: For numerical operations
- **Standard Library**: `json`, `os`, `dataclasses`, `random`

No external dependencies beyond NumPy (which is commonly available in scientific Python environments).

## Output Structure

The module writes output to `fineagle/4dflight/output/`:

```
output/
├── breakout_test.jsonl          # Telemetry log
├── breakout_test.html            # Interactive visualization
├── mean_revert_test.jsonl
├── mean_revert_test.html
├── false_breakout_test.jsonl
├── false_breakout_test.html
└── mc_breakout_*.jsonl          # Monte Carlo run logs
```

### JSONL Format

Each line is a JSON object:

```json
{"timestamp": 0, "spot": 694.0, "iv": 0.15, "hv": 0.12, "x": 0.536, "y": 1.25, "z": 0.8, "regime": "CRUISE", "flags": []}
{"timestamp": 1, "spot": 694.2, "iv": 0.151, "hv": 0.12, "x": 0.607, "y": 1.258, "z": 0.79, "regime": "CRUISE", "flags": []}
...
```

### HTML Visualization

The generated HTML files are self-contained and include:

- Canvas 2D rendering for 3D wireframe visualization
- Interactive playback controls
- HUD overlay with real-time telemetry
- Keyboard controls for navigation
- File upload for loading custom JSONL logs

## Integration with Frontend

The generated JSONL files can be loaded into the Three.js frontend application (`4dflightapp/`):

1. **Copy JSONL to frontend**: Place files in `4dflightapp/public/` or load via file upload
2. **Load in app**: Use the strategy selector or file upload in the web app
3. **Visualize**: The frontend renders the telemetry in an interactive 3D scene

## Key Design Decisions

1. **Modular Architecture**: Clear separation of concerns (envelope, dynamics, telemetry, I/O, rendering)
2. **JSONL Format**: Line-delimited JSON for streaming and easy parsing
3. **Self-Contained HTML**: Generated visualizations require no external dependencies
4. **Deterministic Paths**: Uses random but seeded-able generation for reproducibility
5. **Regime Classification**: Simple threshold-based classification for clarity

## Limitations

1. **Simplified Dynamics**: Path generators use basic random walk models, not full market simulation
2. **Fixed HV**: Historical volatility is static in most scenarios (can be extended)
3. **HTML Renderer**: Uses Canvas 2D, not WebGL (frontend uses Three.js for better performance)
4. **No Real Data**: Generates synthetic data only (real market data integration would require additional modules)

## Extension Points

Potential enhancements:

1. **Real Market Data**: Integrate with data providers to generate telemetry from historical options data
2. **Advanced Path Models**: Add GARCH, stochastic volatility, or other advanced models
3. **Monte Carlo Analysis**: Enhanced statistics and visualization of batch results
4. **Export Formats**: Support for CSV, Parquet, or other formats
5. **WebGL Renderer**: Upgrade HTML renderer to use WebGL for better performance
6. **API Server**: Expose as REST API for programmatic access

## Related Documentation

- **Frontend Application**: See `4dflightapp/README.md` for the Three.js visualization app
- **Frontend Summary**: See `4dflightapp/summary.md` for detailed frontend architecture

## Example Workflow

1. **Define Envelope**: Configure ATR, flip, walls based on option structure
2. **Generate Scenarios**: Use `ScenarioRunner` to create test scenarios
3. **Run Monte Carlo**: Execute batch simulations for statistical analysis
4. **Export Telemetry**: JSONL files are saved to `output/` directory
5. **Visualize**: Open HTML files in browser or load JSONL into frontend app
6. **Analyze**: Review telemetry logs, breach rates, regime distributions

This backend provides the foundation for testing and visualizing option market dynamics in a structured, reproducible way.
