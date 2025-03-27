#!/usr/bin/env python3
"""
Temperature Monitoring Script

Sets a target temperature on the TEC controller and monitors all sensors in real-time.
"""

import serial
import time
import sys
import os
import datetime
import csv
import re

# Set this to the duration you want to monitor (in seconds)
DEFAULT_DURATION = 600  # 10 minutes

# Set the desired target temperature
DEFAULT_TARGET_TEMP = 50.0  # 50°C

# Terminal colors for nicer output
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"


class TECController:
    """Simple interface for the TEC controller using direct serial communication."""

    def __init__(self, port, address=1):
        """Initialize connection to TEC controller."""
        self.port = port
        self.address = address
        self.ser = None
        self.connected = False

    def connect(self):
        """Connect to the TEC controller."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=57600,  # Default baud rate for Meerstetter
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            self.connected = True
            print(f"{Colors.GREEN}Connected to TEC controller on {self.port}{Colors.RESET}")
            return True

        except Exception as e:
            print(f"{Colors.RED}Failed to connect to TEC controller: {e}{Colors.RESET}")
            return False

    def disconnect(self):
        """Disconnect from the TEC controller."""
        if self.ser and self.connected:
            self.ser.close()
            self.connected = False
            print(f"{Colors.YELLOW}Disconnected from TEC controller{Colors.RESET}")

    def build_command(self, command_type, register, value=None):
        """Build a command string according to Meerstetter protocol."""
        if command_type == 1:  # Query
            return f"{self.address:02d};{command_type:02d};{register:d}\r\n"
        else:  # Set
            return f"{self.address:02d};{command_type:02d};{register:d};{value}\r\n"

    def send_command(self, command):
        """Send a command to the TEC controller and return the response."""
        if not self.connected:
            print(f"{Colors.RED}Not connected to TEC controller{Colors.RESET}")
            return None

        try:
            print(f"{Colors.YELLOW}Sending command: '{command.strip()}'{Colors.RESET}")
            self.ser.write(command.encode())
            # Wait for response
            time.sleep(0.2)  # Increased wait time
            
            # Read all available data
            response = ""
            while self.ser.in_waiting > 0:
                response += self.ser.readline().decode()
            
            response = response.strip()
            print(f"{Colors.YELLOW}Received response: '{response}'{Colors.RESET}")
            return response
        except Exception as e:
            print(f"{Colors.RED}Error sending command to TEC controller: {e}{Colors.RESET}")
            return None

    def get_temperature(self, register):
        """Get a temperature value from the TEC controller."""
        command = self.build_command(1, register)
        response = self.send_command(command)

        if response:
            try:
                parts = response.split(';')
                if len(parts) >= 4:
                    return float(parts[3])
            except Exception as e:
                print(f"{Colors.RED}Error parsing temperature: {e}{Colors.RESET}")

        return None

    def get_object_temperature(self):
        """Get the object (holder) temperature."""
        return self.get_temperature(1000)

    def get_target_temperature(self):
        """Get the target temperature."""
        return self.get_temperature(1010)

    def get_sink_temperature(self):
        """Get the heat sink temperature."""
        return self.get_temperature(1001)

    def set_target_temperature(self, temperature):
        """Set the target temperature."""
        print(f"{Colors.CYAN}Attempting to set target temperature to {temperature:.2f}°C{Colors.RESET}")
        
        # Try different formats in case one works
        attempts = [
            # Standard format with 2 decimal places
            self.build_command(2, 1010, f"{temperature:.2f}"),
            # Try with more decimal places
            self.build_command(2, 1010, f"{temperature:.4f}"),
            # Try with only 1 decimal place
            self.build_command(2, 1010, f"{temperature:.1f}"),
            # Try with no decimal places
            self.build_command(2, 1010, f"{int(temperature)}"),
            # Try with different register (some controllers use 3000 instead of 1010)
            self.build_command(2, 3000, f"{temperature:.2f}")
        ]
        
        for i, command in enumerate(attempts):
            print(f"{Colors.YELLOW}Attempt {i+1} to set temperature...{Colors.RESET}")
            response = self.send_command(command)
            
            if response:
                if ";" in response:  # Check for valid response format
                    parts = response.split(';')
                    if len(parts) >= 3 and parts[0] == f"{self.address:02d}" and parts[1] == "02":
                        print(f"{Colors.GREEN}Target temperature set to {temperature:.2f}°C (attempt {i+1}){Colors.RESET}")
                        return True
            
            # Wait a bit before trying next format
            time.sleep(0.5)
            
        # If we get here, all attempts failed
        print(f"{Colors.RED}Failed to set target temperature after multiple attempts{Colors.RESET}")
        
        # Let's try to identify the correct command format by querying version info
        try:
            print(f"{Colors.YELLOW}Querying TEC controller for diagnostic information...{Colors.RESET}")
            # Try to query device address
            addr_cmd = "00;01;00\r\n"
            addr_response = self.send_command(addr_cmd)
            print(f"{Colors.YELLOW}Device address query response: '{addr_response}'{Colors.RESET}")
            
            # Try to query firmware version
            ver_cmd = f"{self.address:02d};01;01\r\n"
            ver_response = self.send_command(ver_cmd)
            print(f"{Colors.YELLOW}Version query response: '{ver_response}'{Colors.RESET}")
            
            # Try to read current target temperature to see format
            temp_cmd = f"{self.address:02d};01;1010\r\n"
            temp_response = self.send_command(temp_cmd)
            print(f"{Colors.YELLOW}Current target temp query: '{temp_response}'{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Error during diagnostics: {e}{Colors.RESET}")
        
        return False

    def get_current(self):
        """Get the actual output current."""
        command = self.build_command(1, 1020)
        response = self.send_command(command)

        if response:
            try:
                parts = response.split(';')
                if len(parts) >= 4:
                    return float(parts[3])
            except Exception as e:
                print(f"{Colors.RED}Error parsing current: {e}{Colors.RESET}")

        return None

    def get_voltage(self):
        """Get the actual output voltage."""
        command = self.build_command(1, 1021)
        response = self.send_command(command)

        if response:
            try:
                parts = response.split(';')
                if len(parts) >= 4:
                    return float(parts[3])
            except Exception as e:
                print(f"{Colors.RED}Error parsing voltage: {e}{Colors.RESET}")

        return None

    def calculate_power(self):
        """Calculate the power consumption of the Peltier element."""
        current = self.get_current()
        voltage = self.get_voltage()

        if current is not None and voltage is not None:
            return abs(current * voltage)

        return None


class ArduinoInterface:
    """Interface for the Arduino that reads liquid and ambient temperatures."""

    def __init__(self, port):
        """Initialize connection to Arduino."""
        self.port = port
        self.ser = None
        self.connected = False

    def connect(self):
        """Connect to the Arduino."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,  # Standard Arduino baud rate
                timeout=1
            )
            time.sleep(2)  # Allow time for Arduino to reset
            self.connected = True
            print(f"{Colors.GREEN}Connected to Arduino on {self.port}{Colors.RESET}")
            return True

        except Exception as e:
            print(f"{Colors.RED}Failed to connect to Arduino: {e}{Colors.RESET}")
            return False

    def disconnect(self):
        """Disconnect from the Arduino."""
        if self.ser and self.connected:
            self.ser.close()
            self.connected = False
            print(f"{Colors.YELLOW}Disconnected from Arduino{Colors.RESET}")

    def read_temperatures(self):
        """Read temperatures from the Arduino."""
        if not self.connected:
            print(f"{Colors.RED}Not connected to Arduino{Colors.RESET}")
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

            # Parse response using regex to handle the format "Pt100 XX.XXXXXXXXPt1000 YY.YYYYYYYY"
            if response:
                print(f"Arduino response: {response}")
                
                # Extract Pt100 (ambient) temperature
                ambient_match = re.search(r'Pt100\s+([\d.]+)', response)
                # Extract Pt1000 (liquid) temperature
                liquid_match = re.search(r'Pt1000\s+([\d.]+)', response)

                if ambient_match and liquid_match:
                    ambient_temp = float(ambient_match.group(1))
                    liquid_temp = float(liquid_match.group(1))
                    return ambient_temp, liquid_temp
                else:
                    print(f"{Colors.RED}Could not parse temperature values from: {response}{Colors.RESET}")
                    print(f"{Colors.YELLOW}Attempting alternative parsing method...{Colors.RESET}")
                    
                    # Try alternative parsing for format without spaces
                    ambient_match = re.search(r'Pt100([\d.]+)', response)
                    liquid_match = re.search(r'Pt1000([\d.]+)', response)
                    
                    if ambient_match and liquid_match:
                        ambient_temp = float(ambient_match.group(1))
                        liquid_temp = float(liquid_match.group(1))
                        return ambient_temp, liquid_temp
            else:
                print(f"{Colors.RED}No response from Arduino{Colors.RESET}")

        except Exception as e:
            print(f"{Colors.RED}Error reading temperatures from Arduino: {e}{Colors.RESET}")

        return None, None


def print_header():
    """Print the monitoring header."""
    header = f"""
{'='*80}
{Colors.YELLOW}Temperature Monitoring{Colors.RESET}
{'='*80}
Time     | Elapsed | {Colors.CYAN}Target{Colors.RESET}  | {Colors.GREEN}Holder{Colors.RESET}  | {Colors.PURPLE}Liquid{Colors.RESET}  | {Colors.BLUE}Ambient{Colors.RESET} | {Colors.RED}Sink{Colors.RESET}    | Power
         | (sec)   | (°C)    | (°C)    | (°C)    | (°C)     | (°C)    | (W)
{'-'*80}"""
    print(header)


def print_status(elapsed, target_temp, holder_temp, liquid_temp, ambient_temp, sink_temp, power):
    """Print the current status row."""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    
    # Format the values with colors and proper alignment
    print(
        f"{now} | "
        f"{elapsed:7.1f} | "
        f"{Colors.CYAN}{target_temp:7.2f}{Colors.RESET} | "
        f"{Colors.GREEN}{holder_temp:7.2f}{Colors.RESET} | "
        f"{Colors.PURPLE}{liquid_temp:7.2f}{Colors.RESET} | "
        f"{Colors.BLUE}{ambient_temp:7.2f}{Colors.RESET} | "
        f"{Colors.RED}{sink_temp:7.2f}{Colors.RESET} | "
        f"{power:7.2f}"
    )


def monitor_temperatures(tec_port, arduino_port, target_temp=DEFAULT_TARGET_TEMP, duration=DEFAULT_DURATION, set_temperature=True):
    """Monitor temperatures after setting a target temperature."""
    # Initialize devices
    tec = TECController(tec_port)
    arduino = ArduinoInterface(arduino_port)

    # Connect to devices
    tec_connected = tec.connect()
    arduino_connected = arduino.connect()

    if not tec_connected or not arduino_connected:
        print(f"{Colors.RED}Failed to connect to one or more devices. Exiting.{Colors.RESET}")
        return

    # Create output directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Create a CSV file for data
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "set" if set_temperature else "monitor"
    csv_filename = f"data/temperature_{mode}_{int(target_temp)}C_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = [
            "timestamp", "elapsed", "target_temp", "holder_temp",
            "liquid_temp", "ambient_temp", "sink_temp", "power"
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        try:
            # Set target temperature if requested
            if set_temperature:
                if not tec.set_target_temperature(target_temp):
                    print(f"{Colors.RED}Failed to set target temperature. Continuing in monitor-only mode.{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}Running in monitor-only mode (not setting temperature).{Colors.RESET}")

            # Get current target temperature to confirm
            current_target = tec.get_target_temperature()
            if current_target is not None:
                print(f"Current target temperature: {current_target:.2f}°C")
            else:
                print(f"{Colors.YELLOW}Could not read current target temperature.{Colors.RESET}")

            # Start monitoring
            print(f"{Colors.GREEN}Starting temperature monitoring for {duration} seconds...{Colors.RESET}")
            print_header()

            # Record start time
            start_time = time.time()
            end_time = start_time + duration

            # Monitoring loop
            while time.time() < end_time:
                # Calculate elapsed time
                current_time = time.time()
                elapsed = current_time - start_time

                # Read temperatures
                holder_temp = tec.get_object_temperature()
                target_temp = tec.get_target_temperature()
                sink_temp = tec.get_sink_temperature()
                ambient_temp, liquid_temp = arduino.read_temperatures()
                power = tec.calculate_power()

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

                # Wait before next reading
                time.sleep(1)

            print(f"{Colors.GREEN}Monitoring completed. Data saved to {csv_filename}{Colors.RESET}")

        except KeyboardInterrupt:
            print(f"{Colors.YELLOW}Monitoring interrupted by user.{Colors.RESET}")
            print(f"{Colors.GREEN}Data saved to {csv_filename}{Colors.RESET}")

        finally:
            # Disconnect from devices
            tec.disconnect()
            arduino.disconnect()


def main():
    """Main function to parse arguments and run the monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Temperature Monitoring Script")
    parser.add_argument("--tec-port", help="Serial port for TEC controller")
    parser.add_argument("--arduino-port", help="Serial port for Arduino")
    parser.add_argument("--target", type=float, default=DEFAULT_TARGET_TEMP, 
                        help=f"Target temperature in °C (default: {DEFAULT_TARGET_TEMP})")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION,
                        help=f"Monitoring duration in seconds (default: {DEFAULT_DURATION})")
    parser.add_argument("--monitor-only", action="store_true",
                        help="Monitor temperatures without setting a new target temperature")
    
    args = parser.parse_args()
    
    # Auto-detect ports if not specified
    if not args.tec_port or not args.arduino_port:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        
        print("Detecting available ports:")
        for i, p in enumerate(ports):
            print(f"  {i+1}: {p.device} - {p.description}")
        
        if not args.tec_port:
            # Try auto-detection first
            for p in ports:
                if "USB" in p.description and "Serial" in p.description:
                    args.tec_port = p.device
                    print(f"Auto-detected TEC controller on {p.device}")
                    break
            
            # If auto-detection fails, ask user
            if not args.tec_port:
                port_input = input("Enter TEC controller port number or full port name: ")
                # Check if input is a number (port index)
                try:
                    port_idx = int(port_input) - 1
                    if 0 <= port_idx < len(ports):
                        args.tec_port = ports[port_idx].device
                    else:
                        print(f"Invalid port index. Using '{port_input}' as port name.")
                        args.tec_port = port_input
                except ValueError:
                    # Not a number, use as literal port name
                    args.tec_port = port_input
        
        if not args.arduino_port:
            # Try auto-detection first
            for p in ports:
                if "Arduino" in p.description or "Uno" in p.description:
                    args.arduino_port = p.device
                    print(f"Auto-detected Arduino on {p.device}")
                    break
                
            # If auto-detection fails, ask user
            if not args.arduino_port:
                port_input = input("Enter Arduino port number or full port name: ")
                # Check if input is a number (port index)
                try:
                    port_idx = int(port_input) - 1
                    if 0 <= port_idx < len(ports):
                        args.arduino_port = ports[port_idx].device
                    else:
                        print(f"Invalid port index. Using '{port_input}' as port name.")
                        args.arduino_port = port_input
                except ValueError:
                    # Not a number, use as literal port name
                    args.arduino_port = port_input
    
    print(f"\nMonitoring settings:")
    print(f"  TEC Controller port: {args.tec_port}")
    print(f"  Arduino port: {args.arduino_port}")
    if args.monitor_only:
        print(f"  Mode: Monitor only (will not set temperature)")
    else:
        print(f"  Mode: Set and monitor")
        print(f"  Target temperature: {args.target}°C")
    print(f"  Duration: {args.duration} seconds")
    
    # Confirm before proceeding
    confirm = input("\nProceed with these settings? (y/n): ")
    if confirm.lower() != 'y':
        print("Monitoring cancelled.")
        return
    
    # Run monitoring
    monitor_temperatures(args.tec_port, args.arduino_port, args.target, args.duration, not args.monitor_only)


if __name__ == "__main__":
    main()