#!/usr/bin/env python3
"""
Temperature Monitoring Script - Updated Version

This script monitors temperatures from the TEC controller and Arduino sensors.
It uses direct MeCom import method that has been confirmed to work.
"""

import serial
import time
import datetime
import os
import csv
import logging
import sys
import re
import argparse
from threading import Event

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(module)s:%(levelname)s:%(message)s")

# Global stop event for clean interruption
stop_event = Event()

# Terminal colors for nicer output
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"


class CustomTECController:
    """
    Custom wrapper around MeCom to provide the functionality we need.
    """
    
    def __init__(self, port=None, address=2):  # Using address 2 as default based on test results
        try:
            # Import MeCom directly - this worked in the test
            sys.path.append(os.path.join(os.getcwd(), '..'))
            from mecom.mecom import MeCom
            self._session = MeCom(serialport=port)
            self.address = self._session.identify()
            logging.info(f"Connected to TEC controller with address: {self.address}")
        except Exception as e:
            logging.error(f"Error initializing TEC controller: {e}")
            raise
    
    def identify(self):
        """Get device address."""
        return self.address
    
    def get_parameter(self, parameter_name=None, parameter_id=None, address=None):
        """Get parameter by name or ID."""
        if address is None:
            address = self.address
        
        try:
            if parameter_name:
                return self._session.get_parameter(parameter_name=parameter_name, address=address)
            elif parameter_id:
                return self._session.get_parameter_raw(parameter_id=parameter_id, parameter_format="FLOAT32", address=address)
        except Exception as e:
            logging.error(f"Error getting parameter: {e}")
            return None
    
    def set_parameter(self, value, parameter_name=None, parameter_id=None, address=None):
        """Set parameter by name or ID."""
        if address is None:
            address = self.address
        
        try:
            if parameter_name:
                return self._session.set_parameter(value=float(value), parameter_name=parameter_name, address=address)
            elif parameter_id:
                return self._session.set_parameter_raw(value=float(value), parameter_id=parameter_id, 
                                                       parameter_format="FLOAT32", address=address)
        except Exception as e:
            logging.error(f"Error setting parameter: {e}")
            return False
    
    def set_temp(self, value):
        """Set target temperature."""
        return self.set_parameter(value=value, parameter_id=3000)
    
    def get_object_temperature(self):
        """Get current object temperature."""
        return self.get_parameter(parameter_id=1000)
    
    def get_target_temperature(self):
        """Get target temperature."""
        return self.get_parameter(parameter_id=3000)
    
    def get_sink_temperature(self):
        """Get heat sink temperature."""
        return self.get_parameter(parameter_id=1001)
    
    def calculate_power(self):
        """Calculate power consumption."""
        try:
            current = self.get_parameter(parameter_id=1020)  # Actual Output Current
            voltage = self.get_parameter(parameter_id=1021)  # Actual Output Voltage
            
            if current is not None and voltage is not None:
                return abs(current * voltage)
        except Exception as e:
            logging.error(f"Error calculating power: {e}")
        
        return None
    
    def _tearDown(self):
        """Close the connection."""
        try:
            self._session.stop()
            logging.info("TEC controller connection closed")
        except Exception as e:
            logging.error(f"Error closing TEC controller connection: {e}")


class ArduinoInterface:
    """Interface for the Arduino that reads liquid and ambient temperatures."""
    
    def __init__(self, port):
        self.port = port
        self.ser = None
        self.connected = False
    
    def connect(self):
        """Connect to the Arduino."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,
                timeout=1
            )
            # Allow time for Arduino to reset
            time.sleep(2)
            self.connected = True
            logging.info(f"Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to Arduino: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the Arduino."""
        if self.ser and self.connected:
            self.ser.close()
            self.connected = False
            logging.info(f"Disconnected from Arduino")
    
    def read_temperatures(self):
        """Read temperatures from the Arduino."""
        if not self.connected:
            logging.error("Not connected to Arduino")
            return None, None
        
        try:
            # Clear input buffer
            self.ser.reset_input_buffer()
            
            # Request temperatures
            self.ser.write(b"READ\n")
            
            # Wait for response
            time.sleep(0.1)
            
            # Read response
            response = self.ser.readline().decode().strip()
            logging.debug(f"Arduino response: {response}")
            
            # Parse response using various methods
            if response:
                # Try to extract temperatures using various patterns
                ambient_temp = None
                liquid_temp = None
                
                # Try pattern: "Pt100 XX.XXXXXPt1000 YY.YYYYY"
                ambient_match = re.search(r'Pt100\s+([\d.]+)', response)
                liquid_match = re.search(r'Pt1000\s+([\d.]+)', response)
                
                if ambient_match and liquid_match:
                    ambient_temp = float(ambient_match.group(1))
                    liquid_temp = float(liquid_match.group(1))
                else:
                    # Try pattern without spaces: "Pt100XX.XXXXXPt1000YY.YYYYY"
                    ambient_match = re.search(r'Pt100([\d.]+)', response)
                    liquid_match = re.search(r'Pt1000([\d.]+)', response)
                    
                    if ambient_match and liquid_match:
                        ambient_temp = float(ambient_match.group(1))
                        liquid_temp = float(liquid_match.group(1))
                    else:
                        # Try just finding any numbers
                        nums = re.findall(r'([\d.]+)', response)
                        if len(nums) >= 2:
                            ambient_temp = float(nums[0])
                            liquid_temp = float(nums[1])
                
                return ambient_temp, liquid_temp
                
            else:
                logging.warning("No response from Arduino")
        except Exception as e:
            logging.error(f"Error reading temperatures from Arduino: {e}")
        
        return None, None


def format_value(value):
    """Format a value for display, handling None values."""
    return f"{value:.2f}" if value is not None else "N/A"


def print_status(elapsed, target_temp, holder_temp, liquid_temp, ambient_temp, sink_temp, power):
    """Print the current status row with colors."""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Format with colors
    print(
        f"{now} | "
        f"{elapsed:7.1f} | "
        f"{Colors.CYAN}{format_value(target_temp)}{Colors.RESET} | "
        f"{Colors.GREEN}{format_value(holder_temp)}{Colors.RESET} | "
        f"{Colors.PURPLE}{format_value(liquid_temp)}{Colors.RESET} | "
        f"{Colors.BLUE}{format_value(ambient_temp)}{Colors.RESET} | "
        f"{Colors.RED}{format_value(sink_temp)}{Colors.RESET} | "
        f"{format_value(power)}"
    )


def monitor_temperature(tec_port, arduino_port=None, target_temp=None, duration=300, set_temperature=True):
    """Monitor temperatures from the TEC controller and Arduino."""
    try:
        # Create and connect to TEC controller
        tec_controller = CustomTECController(port=tec_port)
        
        # Create and connect to Arduino if port provided
        arduino = None
        arduino_connected = False
        if arduino_port:
            arduino = ArduinoInterface(arduino_port)
            arduino_connected = arduino.connect()
        
        # Create output directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Create a CSV file for data
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        mode = "set" if set_temperature and target_temp is not None else "monitor"
        
        if target_temp is not None:
            csv_filename = f"data/temperature_{mode}_{int(target_temp)}C_{timestamp}.csv"
        else:
            csv_filename = f"data/temperature_monitor_{timestamp}.csv"
        
        with open(csv_filename, 'w', newline='') as csvfile:
            fieldnames = [
                "timestamp", "elapsed", "target_temp", "holder_temp",
                "liquid_temp", "ambient_temp", "sink_temp", "power"
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            try:
                # Set target temperature if requested
                if set_temperature and target_temp is not None:
                    logging.info(f"Setting target temperature to {target_temp}°C")
                    success = tec_controller.set_temp(target_temp)
                    if success:
                        logging.info(f"Target temperature set successfully")
                    else:
                        logging.warning(f"Failed to set target temperature. Continuing in monitor-only mode.")
                else:
                    logging.info("Running in monitor-only mode (not setting temperature)")
                
                # Get current target temperature
                current_target = tec_controller.get_target_temperature()
                if current_target is not None:
                    logging.info(f"Current target temperature: {current_target:.2f}°C")
                
                # Start monitoring
                logging.info(f"Starting temperature monitoring for {duration} seconds...")
                
                # Print header
                print("\n" + "="*80)
                print("Temperature Monitoring")
                print("="*80)
                print("Time     | Elapsed | Target  | Holder  | Liquid  | Ambient | Sink    | Power")
                print("         | (sec)   | (°C)    | (°C)    | (°C)    | (°C)    | (°C)    | (W)")
                print("-"*80)
                
                # Record start time
                start_time = time.time()
                end_time = start_time + duration
                
                # Monitoring loop
                while time.time() < end_time and not stop_event.is_set():
                    # Calculate elapsed time
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # Read TEC controller data
                    holder_temp = tec_controller.get_object_temperature()
                    target_temp = tec_controller.get_target_temperature()
                    sink_temp = tec_controller.get_sink_temperature()
                    power = tec_controller.calculate_power()
                    
                    # Read Arduino data if connected
                    ambient_temp, liquid_temp = None, None
                    if arduino_connected:
                        ambient_temp, liquid_temp = arduino.read_temperatures()
                    
                    # Print status
                    print_status(
                        elapsed, target_temp, holder_temp, 
                        liquid_temp, ambient_temp, sink_temp, power
                    )
                    
                    # Save data to CSV
                    data_row = {
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "elapsed": elapsed,
                        "target_temp": target_temp,
                        "holder_temp": holder_temp,
                        "liquid_temp": liquid_temp,
                        "ambient_temp": ambient_temp,
                        "sink_temp": sink_temp,
                        "power": power
                    }
                    writer.writerow(data_row)
                    csvfile.flush()  # Ensure data is written to disk
                    
                    # Wait before next reading (aim for approximately 1 second per iteration)
                    time.sleep(max(0.1, 1.0 - (time.time() - current_time)))
                
                logging.info(f"Monitoring completed. Data saved to {csv_filename}")
                
            except KeyboardInterrupt:
                logging.info("Monitoring interrupted by user.")
                logging.info(f"Data saved to {csv_filename}")
            
        return True
    except Exception as e:
        logging.error(f"Error in monitoring: {e}")
        return False
    finally:
        # Clean up TEC controller
        if 'tec_controller' in locals() and tec_controller:
            tec_controller._tearDown()
        
        # Clean up Arduino
        if 'arduino' in locals() and arduino and arduino_connected:
            arduino.disconnect()


def direct_command_mode(tec_port):
    """Interactive mode to send commands to the TEC controller."""
    tec_controller = None
    
    try:
        print(f"\n{Colors.CYAN}Direct TEC Controller Command Mode{Colors.RESET}")
        print(f"{Colors.YELLOW}This mode allows you to interact with the TEC controller.{Colors.RESET}")
        print(f"{Colors.YELLOW}Type 'exit' to quit, 'help' for commands.{Colors.RESET}")
        
        # Create TEC controller
        tec_controller = CustomTECController(port=tec_port)
        
        while True:
            command = input(f"\n{Colors.CYAN}TEC> {Colors.RESET}").strip()
            
            if command.lower() == 'exit':
                break
            elif command.lower() == 'help':
                print("\nAvailable commands:")
                print("  get temp       - Get object temperature")
                print("  get target     - Get target temperature")
                print("  get sink       - Get heat sink temperature")
                print("  get current    - Get output current")
                print("  get voltage    - Get output voltage")
                print("  get power      - Get power consumption")
                print("  set target X   - Set target temperature to X°C")
                print("  get param X    - Get parameter with ID X")
                print("  set param X Y  - Set parameter X to value Y")
                print("  exit           - Exit direct mode")
            elif command.lower() == 'get temp':
                temp = tec_controller.get_object_temperature()
                print(f"Object Temperature: {temp:.2f}°C")
            elif command.lower() == 'get target':
                temp = tec_controller.get_target_temperature()
                print(f"Target Temperature: {temp:.2f}°C")
            elif command.lower() == 'get sink':
                temp = tec_controller.get_sink_temperature()
                print(f"Sink Temperature: {temp:.2f}°C")
            elif command.lower() == 'get current':
                current = tec_controller.get_parameter(parameter_id=1020)
                print(f"Output Current: {current:.3f} A")
            elif command.lower() == 'get voltage':
                voltage = tec_controller.get_parameter(parameter_id=1021)
                print(f"Output Voltage: {voltage:.3f} V")
            elif command.lower() == 'get power':
                power = tec_controller.calculate_power()
                print(f"Power Consumption: {power:.3f} W")
            elif command.lower().startswith('set target '):
                try:
                    value = float(command.split()[2])
                    success = tec_controller.set_temp(value)
                    if success:
                        print(f"Target temperature set to {value:.2f}°C")
                    else:
                        print("Failed to set target temperature")
                except Exception as e:
                    print(f"Error: {e}")
            elif command.lower().startswith('get param '):
                try:
                    param_id = int(command.split()[2])
                    value = tec_controller.get_parameter(parameter_id=param_id)
                    print(f"Parameter {param_id} value: {value}")
                except Exception as e:
                    print(f"Error: {e}")
            elif command.lower().startswith('set param '):
                try:
                    parts = command.split()
                    param_id = int(parts[2])
                    value = float(parts[3])
                    success = tec_controller.set_parameter(value=value, parameter_id=param_id)
                    if success:
                        print(f"Parameter {param_id} set to {value}")
                    else:
                        print(f"Failed to set parameter {param_id}")
                except Exception as e:
                    print(f"Error: {e}")
            else:
                print(f"Unknown command: {command}. Type 'help' for available commands.")
    
    except Exception as e:
        print(f"{Colors.RED}Error in direct command mode: {e}{Colors.RESET}")
    finally:
        if tec_controller:
            tec_controller._tearDown()


def main():
    """Main function to parse arguments and run the monitoring."""
    parser = argparse.ArgumentParser(description="TEC Controller Temperature Monitoring")
    parser.add_argument("--tec-port", help="Serial port for TEC controller")
    parser.add_argument("--arduino-port", help="Serial port for Arduino (optional)")
    parser.add_argument("--target", type=float, help="Target temperature in °C")
    parser.add_argument("--duration", type=int, default=300, help="Monitoring duration in seconds (default: 300)")
    parser.add_argument("--monitor-only", action="store_true", help="Monitor without setting temperature")
    parser.add_argument("--direct", action="store_true", help="Enter direct command mode")
    
    args = parser.parse_args()
    
    # Set up signal handlers for clean exit
    import signal
    def signal_handler(sig, frame):
        logging.info("Received interrupt signal, shutting down gracefully...")
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Auto-detect ports if not specified
    if not args.tec_port:
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            
            print("Detecting available ports:")
            for i, p in enumerate(ports):
                print(f"  {i+1}: {p.device} - {p.description}")
            
            port_input = input("Enter TEC controller port number or full port name: ")
            try:
                port_idx = int(port_input) - 1
                if 0 <= port_idx < len(ports):
                    args.tec_port = ports[port_idx].device
                else:
                    args.tec_port = port_input
            except ValueError:
                args.tec_port = port_input
        except ImportError:
            logging.error("pyserial not installed. Please install with 'pip install pyserial'")
            return 1
    
    # Run direct command mode if requested
    if args.direct:
        direct_command_mode(args.tec_port)
        return 0
    
    # Ask for Arduino port if not specified
    if not args.arduino_port:
        use_arduino = input("Do you want to monitor Arduino sensors? (y/n): ").lower() == 'y'
        if use_arduino:
            try:
                import serial.tools.list_ports
                ports = list(serial.tools.list_ports.comports())
                
                print("Available ports:")
                for i, p in enumerate(ports):
                    print(f"  {i+1}: {p.device} - {p.description}")
                
                port_input = input("Enter Arduino port number or full port name: ")
                try:
                    port_idx = int(port_input) - 1
                    if 0 <= port_idx < len(ports):
                        args.arduino_port = ports[port_idx].device
                    else:
                        args.arduino_port = port_input
                except ValueError:
                    args.arduino_port = port_input
            except ImportError:
                logging.error("pyserial not installed. Please install with 'pip install pyserial'")
                return 1
    
    # Print monitoring settings
    print("\nMonitoring settings:")
    print(f"  TEC Controller port: {args.tec_port}")
    if args.arduino_port:
        print(f"  Arduino port: {args.arduino_port}")
    else:
        print("  Arduino: Not used")
    
    if args.monitor_only:
        print("  Mode: Monitor only (will not set temperature)")
    else:
        if args.target is not None:
            print(f"  Mode: Set and monitor")
            print(f"  Target temperature: {args.target}°C")
        else:
            print("  Mode: Monitor only (no target specified)")
    
    print(f"  Duration: {args.duration} seconds")
    
    # Confirm before proceeding
    confirm = input("\nProceed with these settings? (y/n): ")
    if confirm.lower() != 'y':
        print("Monitoring cancelled.")
        return 0
    
    # Start monitoring
    monitor_temperature(
        args.tec_port, 
        args.arduino_port, 
        args.target, 
        args.duration, 
        set_temperature=not args.monitor_only and args.target is not None
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())