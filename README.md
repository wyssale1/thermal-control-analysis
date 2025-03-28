# Temperature Control System

A Python-based system for precise temperature control of sample vials using a TEC (Thermoelectric Cooler) controller and Arduino for additional temperature sensing.

## Overview

This temperature control system provides:

- Temperature control from 5°C to 50°C with ±0.5°C accuracy
- Stable temperature control for extended periods (24+ hours)
- Real-time monitoring of holder, liquid, sink, and ambient temperatures
- Temperature correction to compensate for thermal offset between the holder and liquid
- Experiment mode for automated temperature sequences
- Data collection and analysis with parameter fitting
- Interactive and command-line interfaces

## Repository Structure

```
thermal_control/
├── README.md                          # Main documentation
├── temperature_control.py             # Main temperature control script
├── temperature_monitor.py             # Monitoring-only script
├── config.ini                         # Configuration file (for correction parameters)
│
├── thermal_control/                   # Core package
│   ├── devices/                       # Device communication
│   ├── core/                          # Core functionality
│   ├── utils/                         # Utility functions
│   └── ui/                            # User interfaces
│
├── analysis/                          # Analysis tools
│   ├── analyze_data.py                # Main analysis script
│   ├── visualize_temperature.py       # Plotting functions
│   ├── fit_parameters.py              # Parameter fitting
│   └── utils/                         # Analysis utilities
│
├── arduino/                           # Arduino firmware
│   └── temperature_sensors/           # Firmware for temperature sensors
│
└── data/                              # Data directory
    ├── raw/                           # Raw measurement data
    └── processed/                     # Processed results
```

## How It Works

### Temperature Control Logic

The system uses a quadratic correction formula to compensate for the thermal offset between the holder and liquid temperatures:

```
x = (-b + sqrt(b² - 4*a*(c-y)))/(2*a)
```

Where:
- `y` is the desired liquid temperature
- `x` is the corrected target temperature for the holder
- `a`, `b`, and `c` are coefficients determined by fitting measurement data
- Current values: a = 0.0039, b = 0.5645, c = 4.8536

This formula accounts for the non-linear relationship between holder and liquid temperatures due to thermal resistance and heat transfer characteristics.

### Device Communication

- **TEC Controller**: Communicates via serial port using the MeCom protocol, controls the Peltier element to reach and maintain the target temperature.
- **Arduino**: Reads additional temperature sensors (Pt100 for ambient, Pt1000 for liquid) and communicates values via serial port.

### Data Collection and Analysis

1. During operation, the system continuously logs:
   - Holder temperature (from TEC controller)
   - Liquid temperature (from Arduino)
   - Ambient temperature (from Arduino)
   - Sink temperature (from TEC controller)
   - Target temperature
   - Power consumption

2. After data collection, the analysis module can:
   - Visualize temperature data
   - Calculate statistics for each temperature step
   - Extract temperature offsets
   - Fit correction parameters
   - Update the configuration

## Installation

### Requirements

- Python 3.7 or higher
- TEC Controller connected via serial port
- Arduino (optional) with Pt100 and Pt1000 temperature sensors
- Python packages:
  - pyserial
  - numpy
  - pandas
  - matplotlib
  - scipy

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/thermal_control.git
   cd thermal_control
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Arduino (optional):
   - Upload the firmware in `arduino/temperature_sensors/` to your Arduino
   - Connect the Pt100 and Pt1000 sensors to the Arduino

## Usage

### Temperature Control

Run the main control script:

```bash
python temperature_control.py
```

This will start the interactive mode, which allows you to:
- Set temperatures
- Monitor readings
- Run experiments
- Save and analyze data

### Basic Options

- `--tec-port PORT`: Specify TEC controller serial port
- `--arduino-port PORT`: Specify Arduino serial port
- `--no-arduino`: Run without Arduino
- `--output FILE`: Specify output data file
- `--log-file FILE`: Specify log file

### Operation Modes

- `--monitor`: Just monitor temperatures without control
- `--set-temp TEMP`: Set a single target temperature
- `--interactive`: Run in interactive mode (default)
- `--direct`: Direct command mode for TEC controller

### Experiment Mode

- `--experiment`: Run a temperature experiment
- `--start-temp TEMP`: Starting temperature
- `--stop-temp TEMP`: Final temperature
- `--increment TEMP`: Temperature increment
- `--stab-time MINUTES`: Stabilization time at each temperature

### Temperature Monitoring Only

For monitoring without control:

```bash
python temperature_monitor.py
```

### Data Analysis

After collecting data, analyze it with:

```bash
python -m analysis.analyze_data --file FILENAME
```

Options:
- `--all`: Analyze all files in the data directory
- `--update-config`: Update configuration with fitted parameters
- `--with-ambient`: Include ambient temperature in the model

## Interactive Mode Commands

- `set X`: Set temperature to X°C (with offset correction)
- `setraw X`: Set temperature to X°C (without offset correction)
- `mon`: Start/stop monitoring
- `exp X Y Z W`: Run experiment from X°C to Y°C in Z°C steps with W minutes stabilization
- `expraw X Y Z W`: Run experiment without offset correction
- `stop`: Stop running experiment
- `save [file]`: Save collected data to CSV file
- `status`: Show current temperatures
- `stats`: Show summary statistics
- `config`: Show/change correction parameters
- `help`: Show help
- `exit`: Exit program

## Example Workflow

1. **Set Up and Connect**:
   ```bash
   python temperature_control.py
   ```
   Follow the prompts to select serial ports for your devices.

2. **Run an Experiment**:
   ```bash
   python temperature_control.py --experiment --start-temp 20 --stop-temp 40 --increment 5 --stab-time 15
   ```
   This runs an experiment from 20°C to 40°C in steps of 5°C with 15 minutes stabilization at each temperature.

3. **Analyze the Data**:
   ```bash
   python -m analysis.analyze_data
   ```
   This will list available data files and let you select one to analyze.

4. **Update Correction Parameters**:
   ```bash
   python -m analysis.analyze_data --file your_data_file.csv --update-config
   ```
   This analyzes the data and updates the correction parameters in config.ini.

## Troubleshooting

- **Connection Issues**: Ensure devices are powered on and connected properly. Check that the correct ports are selected.
- **Temperature Control Issues**: Verify thermal paste application and ambient conditions. Check correction parameters.
- **Data Analysis Problems**: Ensure data files are in the correct format. Check the logs for error messages.

## Extending the System

- **New Sensors**: Add new sensors by updating the Arduino firmware and the `read_all_sensors()` method.
- **Alternative Models**: Implement different correction models in `calculate_corrected_target()`.
- **Advanced Analysis**: Add new analysis methods in the `analysis/` package.

## License

This project is licensed under the MIT License - see the LICENSE file for details.