#!/usr/bin/env python3
"""
Simple Temperature Control System
A lightweight Python alternative to the LabView script for temperature control
"""

import serial
import time
import datetime
import os
import csv
import threading
import logging
import argparse
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("temperature_control.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

class TECController:
    """Interface for the Meerstetter TEC Controller using pyMeCom."""
    
    def __init__(self, port=None, address=1):
        """Initialize connection to TEC controller."""
        try:
            # Try to import pyMeCom - if not installed, give instructions
            import mecom
            self.mecom_available = True
        except ImportError:
            logging.error("pyMeCom library not found. Please install it using 'pip install pyMeCom'")
            logging.error("More info: https://github.com/makelangelo/pyMeCom")
            self.mecom_available = False
        
        self.port = port
        self.address = address
        self.device = None
        self.connected = False
    
    def connect(self):
        """Establish connection to the TEC controller using pyMeCom."""
        if not self.mecom_available:
            logging.error("Cannot connect: pyMeCom library not available")
            return False
            
        from mecom import MeCom, ResponseException, WrongChecksum
        
        if self.port is None:
            # Try to find the TEC controller on available ports
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                # Look for USB Serial Device
                if "USB" in p.description and "Serial" in p.description:
                    self.port = p.device
                    logging.info(f"Found potential TEC controller on {p.device}")
                    break
        
        if self.port is None:
            logging.error("TEC Controller port not found")
            return False
        
        try:
            # Connect using pyMeCom library
            self.device = MeCom(self.port, address=self.address)
            
            # Test connection by reading device status
            device_status = self.device.get_device_status()
            logging.info(f"Connected to TEC Controller on {self.port}")
            logging.info(f"Device status: {device_status}")
            
            # Get device info for logging
            try:
                device_type = self.device.get_parameter(1)  # Device Type
                serial_number = self.device.get_parameter(3)  # Serial Number
                logging.info(f"Device Type: {device_type}, Serial Number: {serial_number}")
            except (ResponseException, WrongChecksum, ValueError) as e:
                logging.warning(f"Could not retrieve device info: {e}")
            
            self.connected = True
            return True
            
        except Exception as e:
            logging.error(f"Failed to connect to TEC Controller: {e}")
            return False
    
    def disconnect(self):
        """Close the connection."""
        if self.connected and self.device:
            try:
                self.device.close()
                logging.info("Disconnected from TEC Controller")
            except Exception as e:
                logging.error(f"Error disconnecting from TEC Controller: {e}")
            finally:
                self.connected = False
    
    def get_object_temperature(self):
        """Get the object (holder) temperature."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            # Parameter 1000 is Object Temperature
            return self.device.get_parameter(1000)
        except Exception as e:
            logging.error(f"Error getting object temperature: {e}")
            return None
    
    def get_target_temperature(self):
        """Get the target temperature."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            # Parameter 1010 is Target Object Temperature
            return self.device.get_parameter(1010)
        except Exception as e:
            logging.error(f"Error getting target temperature: {e}")
            return None
    
    def set_target_temperature(self, temperature):
        """Set the target temperature."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return False
            
        try:
            # Parameter 1010 is Target Object Temperature
            self.device.set_parameter(1010, temperature)
            logging.info(f"Set target temperature to {temperature:.2f}°C")
            return True
        except Exception as e:
            logging.error(f"Error setting target temperature: {e}")
            return False
    
    def get_sink_temperature(self):
        """Get the heat sink temperature."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            # Parameter 1001 is Sink Temperature
            return self.device.get_parameter(1001)
        except Exception as e:
            logging.error(f"Error getting sink temperature: {e}")
            return None
    
    def calculate_power(self):
        """Calculate the power consumption of the Peltier element."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            # Parameter 1020 is Actual Output Current
            current = self.device.get_parameter(1020)
            # Parameter 1021 is Actual Output Voltage
            voltage = self.device.get_parameter(1021)
            
            return abs(current * voltage)
        except Exception as e:
            logging.error(f"Error calculating power: {e}")
            return None
            
    def get_device_status(self):
        """Get detailed device status information."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            return self.device.get_device_status()
        except Exception as e:
            logging.error(f"Error getting device status: {e}")
            return None


class ArduinoInterface:
    """Interface for the Arduino that reads liquid and ambient temperatures."""
    
    def __init__(self, port=None):
        """Initialize connection to Arduino."""
        self.port = port
        self.ser = None
        self.connected = False
    
    def connect(self):
        """Establish serial connection to the Arduino."""
        if self.port is None:
            # Try to find the Arduino on available ports
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                if "Arduino" in p.description or "Uno" in p.description:
                    self.port = p.device
                    logging.info(f"Found Arduino on {p.device}")
                    break
        
        if self.port is None:
            logging.error("Arduino port not found")
            return False
        
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,  # Standard Arduino baud rate
                timeout=1
            )
            # Allow time for Arduino to reset after connecting
            time.sleep(2)
            self.connected = True
            logging.info(f"Connected to Arduino on {self.port}")
            
            # Test connection
            liquid_temp, ambient_temp = self.read_temperatures()
            if liquid_temp is not None and ambient_temp is not None:
                logging.info(f"Arduino reports: Liquid: {liquid_temp:.2f}°C, Ambient: {ambient_temp:.2f}°C")
                return True
            else:
                logging.error("Failed to read temperatures from Arduino")
                self.disconnect()
                return False
                
        except Exception as e:
            logging.error(f"Failed to connect to Arduino: {e}")
            return False
    
    def disconnect(self):
        """Close the serial connection."""
        if self.ser and self.connected:
            self.ser.close()
            self.connected = False
            logging.info("Disconnected from Arduino")
    
    def read_temperatures(self):
        """Read temperatures from the Arduino."""
        if not self.connected:
            logging.error("Not connected to Arduino")
            return None, None
        
        try:
            # Clear input buffer
            self.ser.reset_input_buffer()
            
            # Request temperatures (Arduino should be programmed to respond to this)
            self.ser.write(b"READ\n")
            
            # Wait for response
            time.sleep(0.1)
            
            # Read response
            response = self.ser.readline().decode().strip()
            
            # Parse response (expected format: "liquid_temp,ambient_temp")
            parts = response.split(',')
            if len(parts) == 2:
                try:
                    liquid_temp = float(parts[0])
                    ambient_temp = float(parts[1])
                    return liquid_temp, ambient_temp
                except ValueError:
                    logging.error(f"Invalid temperature values: {response}")
            else:
                logging.error(f"Unexpected response format: {response}")
            
        except Exception as e:
            logging.error(f"Error reading temperatures from Arduino: {e}")
        
        return None, None


class TemperatureControl:
    """Main class for temperature control system."""
    
    def __init__(self, tec_port=None, arduino_port=None):
        """Initialize the temperature control system."""
        self.tec = TECController(port=tec_port)
        self.arduino = ArduinoInterface(port=arduino_port)
        self.running = False
        self.experiment_running = False
        self.data = []
        self.data_lock = threading.Lock()
        self.start_time = None
    
    def connect_devices(self):
        """Connect to both devices."""
        logging.info("Connecting to devices...")
        tec_connected = self.tec.connect()
        arduino_connected = self.arduino.connect()
        
        if tec_connected and arduino_connected:
            logging.info("All devices connected successfully")
            return True
        else:
            if not tec_connected:
                logging.error("Failed to connect to TEC Controller")
            if not arduino_connected:
                logging.error("Failed to connect to Arduino")
            return False
    
    def disconnect_devices(self):
        """Disconnect from both devices."""
        self.tec.disconnect()
        self.arduino.disconnect()
    
    def read_all_sensors(self):
        """Read data from all sensors."""
        # Read TEC controller values
        holder_temp = self.tec.get_object_temperature()
        target_temp = self.tec.get_target_temperature()
        sink_temp = self.tec.get_sink_temperature()
        power = self.tec.calculate_power()
        
        # Read Arduino values
        liquid_temp, ambient_temp = self.arduino.read_temperatures()
        
        # Get current time
        now = datetime.datetime.now()
        elapsed = 0
        if self.start_time:
            elapsed = (now - self.start_time).total_seconds()
        
        # Create data point
        data_point = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": elapsed,
            "holder_temp": holder_temp,
            "target_temp": target_temp,
            "liquid_temp": liquid_temp,
            "sink_temp": sink_temp,
            "ambient_temp": ambient_temp,
            "power": power
        }
        
        return data_point
    
    def monitoring_loop(self):
        """Main monitoring loop that reads sensors and logs data."""
        self.start_time = datetime.datetime.now()
        self.running = True
        
        logging.info("Starting monitoring loop")
        
        while self.running:
            try:
                # Read all sensors
                data_point = self.read_all_sensors()
                
                # Log data point
                with self.data_lock:
                    self.data.append(data_point)
                
                # Print current status (with checks for None values)
                status = "Current status: "
                if data_point["holder_temp"] is not None:
                    status += f"Holder: {data_point['holder_temp']:.2f}°C, "
                if data_point["liquid_temp"] is not None:
                    status += f"Liquid: {data_point['liquid_temp']:.2f}°C, "
                if data_point["ambient_temp"] is not None:
                    status += f"Ambient: {data_point['ambient_temp']:.2f}°C, "
                if data_point["power"] is not None:
                    status += f"Power: {data_point['power']:.2f}W, "
                if data_point["target_temp"] is not None:
                    status += f"Target: {data_point['target_temp']:.2f}°C"
                
                logging.info(status)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
            
            # Wait before next reading
            time.sleep(1)
    
    def start_monitoring(self):
        """Start the monitoring loop in a separate thread."""
        if not self.running:
            self.monitor_thread = threading.Thread(target=self.monitoring_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            logging.info("Monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        if self.running:
            self.running = False
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.join(timeout=2)
            logging.info("Monitoring stopped")
    
    def set_temperature(self, temperature):
        """Set the target temperature on the TEC controller."""
        success = self.tec.set_target_temperature(temperature)
        if success:
            logging.info(f"Target temperature set to {temperature:.2f}°C")
        else:
            logging.error(f"Failed to set target temperature to {temperature:.2f}°C")
        return success
    
    def save_data(self, filename=None):
        """Save collected data to a CSV file."""
        if not filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/temperature_data_{timestamp}.csv"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
        
        with self.data_lock:
            if not self.data:
                logging.warning("No data to save")
                return
            
            try:
                with open(filename, 'w', newline='') as csvfile:
                    fieldnames = ["timestamp", "elapsed_seconds", "holder_temp", "target_temp",
                                 "liquid_temp", "sink_temp", "ambient_temp", "power"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for data_point in self.data:
                        writer.writerow(data_point)
                
                logging.info(f"Data saved to {filename}")
                
            except Exception as e:
                logging.error(f"Error saving data: {e}")
    
    def run_experiment(self, start_temp, stop_temp, increment, stabilization_time_minutes):
        """Run an experiment with temperature steps."""
        if self.experiment_running:
            logging.error("Experiment already running")
            return False
        
        self.experiment_running = True
        logging.info(f"Starting experiment: {start_temp}°C to {stop_temp}°C "
                     f"in {increment}°C steps with {stabilization_time_minutes} minutes stabilization")
        
        # Calculate temperature steps
        steps = []
        current_temp = start_temp
        
        if increment > 0:  # Increasing temperature
            while current_temp <= stop_temp:
                steps.append(current_temp)
                current_temp += increment
        else:  # Decreasing temperature
            while current_temp >= stop_temp:
                steps.append(current_temp)
                current_temp += increment  # Note: increment is negative here
        
        # Start monitoring if not already running
        if not self.running:
            self.start_monitoring()
        
        try:
            # Run through temperature steps
            for i, temp in enumerate(steps):
                logging.info(f"Step {i+1}/{len(steps)}: Setting temperature to {temp:.2f}°C")
                
                # Set target temperature
                if not self.set_temperature(temp):
                    logging.error(f"Failed to set temperature for step {i+1}")
                    return False
                
                # Save start of this step
                step_start = datetime.datetime.now()
                
                # Wait for stabilization time
                logging.info(f"Waiting {stabilization_time_minutes} minutes for stabilization...")
                
                # Wait in small increments to allow for interruption
                stabilization_seconds = stabilization_time_minutes * 60
                for _ in range(stabilization_seconds):
                    if not self.experiment_running:
                        logging.info("Experiment interrupted")
                        return False
                    time.sleep(1)
                
                step_end = datetime.datetime.now()
                step_duration = (step_end - step_start).total_seconds() / 60
                
                logging.info(f"Step {i+1} completed (duration: {step_duration:.1f} minutes)")
            
            logging.info("Experiment completed successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error during experiment: {e}")
            return False
        finally:
            self.experiment_running = False
    
    def stop_experiment(self):
        """Stop the running experiment."""
        if self.experiment_running:
            self.experiment_running = False
            logging.info("Experiment stopping...")
            return True
        else:
            logging.warning("No experiment running")
            return False


def main():
    """Main function to parse arguments and run the temperature control system."""
    parser = argparse.ArgumentParser(description="Temperature Control System")
    parser.add_argument("--tec-port", help="Serial port for TEC controller")
    parser.add_argument("--arduino-port", help="Serial port for Arduino")
    parser.add_argument("--monitor", action="store_true", help="Just monitor temperatures without running an experiment")
    parser.add_argument("--set-temp", type=float, help="Set a single target temperature")
    parser.add_argument("--experiment", action="store_true", help="Run an experiment")
    parser.add_argument("--start-temp", type=float, help="Starting temperature for experiment")
    parser.add_argument("--stop-temp", type=float, help="Stopping temperature for experiment")
    parser.add_argument("--increment", type=float, help="Temperature increment")
    parser.add_argument("--stab-time", type=int, default=15, help="Stabilization time in minutes")
    parser.add_argument("--output", help="Output file for data")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    # Create temperature control system
    temp_control = TemperatureControl(tec_port=args.tec_port, arduino_port=args.arduino_port)
    
    try:
        # Connect to devices
        if not temp_control.connect_devices():
            logging.error("Failed to connect to devices. Exiting.")
            return 1
        
        # Start monitoring
        temp_control.start_monitoring()
        
        if args.set_temp is not None:
            # Set a single temperature
            if not temp_control.set_temperature(args.set_temp):
                return 1
                
            # Keep monitoring until interrupted
            try:
                logging.info(f"Maintaining temperature at {args.set_temp}°C (press Ctrl+C to stop)")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logging.info("Temperature control interrupted")
        
        elif args.experiment and args.start_temp is not None and args.stop_temp is not None and args.increment is not None:
            # Run an experiment
            success = temp_control.run_experiment(
                args.start_temp,
                args.stop_temp,
                args.increment,
                args.stab_time
            )
            
            if not success:
                return 1
        
        elif args.monitor:
            # Just monitor temperatures
            try:
                logging.info("Monitoring temperatures (press Ctrl+C to stop)")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logging.info("Monitoring interrupted")
        
        elif args.interactive:
            # Interactive mode
            print("\nInteractive Temperature Control")
            print("==============================")
            print("Commands:")
            print("  set X     - Set temperature to X°C")
            print("  exp X Y Z W - Run experiment from X°C to Y°C in Z°C steps with W minutes stabilization")
            print("  stop      - Stop running experiment")
            print("  save      - Save current data")
            print("  help      - Show this help")
            print("  exit      - Exit program")
            
            try:
                while True:
                    cmd = input("\n> ").strip()
                    
                    if cmd.startswith("set "):
                        try:
                            temp = float(cmd[4:])
                            temp_control.set_temperature(temp)
                        except ValueError:
                            logging.error("Invalid temperature")
                    
                    elif cmd.startswith("exp "):
                        try:
                            parts = cmd[4:].split()
                            if len(parts) != 4:
                                logging.error("Usage: exp START_TEMP STOP_TEMP INCREMENT STAB_TIME")
                                continue
                            
                            start_temp = float(parts[0])
                            stop_temp = float(parts[1])
                            increment = float(parts[2])
                            stab_time = int(parts[3])
                            
                            if start_temp == stop_temp:
                                logging.error("Start and stop temperatures must be different")
                                continue
                                
                            if increment == 0:
                                logging.error("Increment cannot be zero")
                                continue
                                
                            # Ensure increment sign matches direction
                            if start_temp < stop_temp and increment < 0:
                                increment = -increment
                            elif start_temp > stop_temp and increment > 0:
                                increment = -increment
                            
                            temp_control.run_experiment(start_temp, stop_temp, increment, stab_time)
                            
                        except ValueError:
                            logging.error("Invalid experiment parameters")
                    
                    elif cmd == "stop":
                        temp_control.stop_experiment()
                    
                    elif cmd == "save":
                        filename = input("Enter filename (or press Enter for auto-generated): ").strip()
                        if filename:
                            temp_control.save_data(filename)
                        else:
                            temp_control.save_data()
                    
                    elif cmd == "help":
                        print("Commands:")
                        print("  set X     - Set temperature to X°C")
                        print("  exp X Y Z W - Run experiment from X°C to Y°C in Z°C steps with W minutes stabilization")
                        print("  stop      - Stop running experiment")
                        print("  save      - Save current data")
                        print("  help      - Show this help")
                        print("  exit      - Exit program")
                    
                    elif cmd == "exit":
                        break
                    
                    else:
                        logging.warning(f"Unknown command: {cmd}")
            
            except KeyboardInterrupt:
                logging.info("Interactive mode interrupted")
        
        else:
            # Default to interactive mode
            logging.info("No action specified. Running in interactive mode.")
            parser.print_help()
            print("\nInteractive Temperature Control")
            print("==============================")
            print("Commands:")
            print("  set X     - Set temperature to X°C")
            print("  exp X Y Z W - Run experiment from X°C to Y°C in Z°C steps with W minutes stabilization")
            print("  stop      - Stop running experiment")
            print("  save      - Save current data")
            print("  help      - Show this help")
            print("  exit      - Exit program")
            
            try:
                while True:
                    cmd = input("\n> ").strip()
                    
                    if cmd.startswith("set "):
                        try:
                            temp = float(cmd[4:])
                            temp_control.set_temperature(temp)
                        except ValueError:
                            logging.error("Invalid temperature")
                    
                    elif cmd.startswith("exp "):
                        try:
                            parts = cmd[4:].split()
                            if len(parts) != 4:
                                logging.error("Usage: exp START_TEMP STOP_TEMP INCREMENT STAB_TIME")
                                continue
                            
                            start_temp = float(parts[0])
                            stop_temp = float(parts[1])
                            increment = float(parts[2])
                            stab_time = int(parts[3])
                            temp_control.run_experiment(start_temp, stop_temp, increment, stab_time)
                            
                        except ValueError:
                            logging.error("Invalid experiment parameters")
                    
                    elif cmd == "stop":
                        temp_control.stop_experiment()
                    
                    elif cmd == "save":
                        filename = input("Enter filename (or press Enter for auto-generated): ").strip()
                        if filename:
                            temp_control.save_data(filename)
                        else:
                            temp_control.save_data()
                    
                    elif cmd == "help":
                        print("Commands:")
                        print("  set X     - Set temperature to X°C")
                        print("  exp X Y Z W - Run experiment from X°C to Y°C in Z°C steps with W minutes stabilization")
                        print("  stop      - Stop running experiment")
                        print("  save      - Save current data")
                        print("  help      - Show this help")
                        print("  exit      - Exit program")
                    
                    elif cmd == "exit":
                        break
                    
                    else:
                        logging.warning(f"Unknown command: {cmd}")
            
            except KeyboardInterrupt:
                logging.info("Interactive mode interrupted")
        
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1
    
    finally:
        # Stop monitoring
        temp_control.stop_monitoring()
        
        # Save data if requested
        if args.output:
            temp_control.save_data(args.output)
        else:
            # Auto-generate filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_control.save_data(f"data/temperature_data_{timestamp}.csv")
        
        # Disconnect devices
        temp_control.disconnect_devices()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())