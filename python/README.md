# Temperature Control System

A Python-based system for precise temperature control of sample vials using a TEC (Thermoelectric Cooler) controller and Arduino for additional temperature sensing.

## Overview

This temperature control system provides:

- Temperature control from 5°C to 50°C with ±0.5°C accuracy
- Stable temperature control for extended periods
- Real-time monitoring of holder, liquid, sink, and ambient temperatures
- Temperature correction to compensate for thermal offset between the holder and liquid
- Interactive, command-line, and experiment modes
- Data logging and export

## Requirements

- Python 3.7 or higher
- TEC Controller connected via serial port
- Arduino (optional) connected via serial port for additional temperature sensing
- Python packages:
  - pyserial
  - numpy
  - matplotlib (optional, for visualization)

Install dependencies:

```bash
pip install pyserial numpy matplotlib
```

## Project Structure

```
thermal_control/
├── __init__.py                # Package initialization
├── devices/                   # Device communication
│   ├── __init__.py
│   ├── tec_controller.py      # TEC controller interface
│   └── arduino_interface.py   # Arduino interface
├── core/                      # Core functionality
│   ├── __init__.py
│   ├── temperature_control.py # Temperature control logic
│   └── data_manager.py        # Data handling and storage
├── utils/                     # Utility functions
│   ├── __init__.py
│   ├── port_selection.py      # Serial port selection
│   └── logger.py              # Logging utilities
├── ui/                        # User interfaces
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   └── interactive.py         # Interactive mode
├── temperature_control.py     # Main script
└── temperature_monitor.py     # Monitoring-only script
```

## How It Works

### Temperature Control Logic

The system uses a quadratic correction formula to compensate for the thermal offset between the holder and liquid temperatures. The formula used is:

```
x = (-0.5645 + sqrt(0.5645² - 4*0.0039*(4.8536-y)))/(2*0.0039)
```

Where:
- `y` is the desired liquid temperature
- `x` is the corrected target temperature for the holder

This formula accounts for the non-linear relationship between holder and liquid temperatures due to thermal resistance and heat transfer characteristics.

### Communication with Devices

- **TEC Controller**: Communicates via serial port using the MeCom protocol. Controls the Peltier element to reach and maintain the target temperature.
- **Arduino**: Reads additional temperature sensors (Pt100 for ambient, Pt1000 for liquid) and communicates the values via serial port.

### Data Management

The system continuously logs temperature data, including:
- Holder temperature (from TEC controller)
- Liquid temperature (from Arduino)
- Ambient temperature (from Arduino)
- Sink temperature (from TEC controller)
- Target temperature
- Power consumption

Data is saved to CSV files for later analysis.

## Usage

### Running the Temperature Control System

```bash
python temperature_control.py [options]
```

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
- `--start-temp TEMP`: Starting temperature for experiment
- `--stop-temp TEMP`: Stopping temperature for experiment
- `--increment TEMP`: Temperature increment
- `--stab-time MINUTES`: Stabilization time in minutes

### Control Options

- `--no-correction`: Disable temperature offset correction
- `--a VALUE`: Coefficient a for temperature correction
- `--b VALUE`: Coefficient b for temperature correction
- `--c VALUE`: Coefficient c for temperature correction
- `--use-ambient`: Enable ambient temperature correction
- `--ambient-ref TEMP`: Reference ambient temperature
- `--ambient-coeff VALUE`: Ambient temperature coefficient

### Monitoring Only

For monitoring without control:

```bash
python temperature_monitor.py [options]
```

## Interactive Mode Commands

In interactive mode, you can use the following commands:

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

## Example Scenarios

### Basic Temperature Monitoring

```bash
python temperature_monitor.py
```
This will guide you through selecting ports and then display real-time temperature readings.

### Set and Monitor a Specific Temperature

```bash
python temperature_control.py --set-temp 25.0
```
Sets the temperature to 25°C (with correction) and monitors the system.

### Running a Temperature Experiment

```bash
python temperature_control.py --experiment --start-temp 20 --stop-temp 40 --increment 5 --stab-time 15
```
Runs an experiment from 20°C to 40°C in steps of 5°C, waiting 15 minutes at each temperature for stabilization.

### Interactive Control

```bash
python temperature_control.py --interactive
```
Starts the system in interactive mode where you can use commands to control temperatures, run experiments, and view statistics.

## Troubleshooting

### Connection Issues

- Ensure the correct serial ports are selected
- Check that the TEC controller is powered on
- Verify the Arduino has the correct firmware installed
- Try a lower baud rate if connection is unstable

### Temperature Control Issues

- Check that the thermal paste between the holder and Peltier element is properly applied
- Ensure adequate ventilation for the heat sink
- Verify that the correction formula parameters are appropriate for your setup
- For extreme temperatures, be aware of ambient conditions affecting performance

## Data Analysis

The CSV files generated by the system contain time-stamped temperature data. You can analyze this data using:

- Excel or other spreadsheet software
- Python with pandas and matplotlib
- Any data analysis tool that supports CSV import

The data format includes:
- Timestamp
- Elapsed time (seconds)
- Holder temperature (°C)
- Liquid temperature (°C)
- Target temperature (°C)
- Sink temperature (°C)
- Ambient temperature (°C)
- Power consumption (W)

## Contributing

Contributions to improve the system are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.