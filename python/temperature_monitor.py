#!/usr/bin/env python3
"""
Temperature Monitor

A simplified script for monitoring temperatures without control functionality.
"""

import os
import sys
import logging
import time
import argparse
import datetime
import signal

# Add parent directory to path to allow imports from the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devices.tec_controller import TECController
from devices.arduino_interface import ArduinoInterface
from core.data_manager import DataManager
from utils.port_selection import select_ports_interactive, print_available_ports, list_available_ports
from utils.logger import setup_logger, get_default_log_file, Colors

def monitor_temperature(tec_controller, arduino_interface, data_manager, duration=None, interval=1.0):
    """
    Monitor temperatures from TEC controller and Arduino.
    
    Args:
        tec_controller: TECController instance
        arduino_interface: ArduinoInterface instance or None
        data_manager: DataManager instance
        duration: Duration in seconds (None for indefinite)
        interval: Reading interval in seconds
    """
    # Initialize
    start_time = datetime.datetime.now()
    data_manager.reset()
    
    # Setup stop flag for handling interrupts
    stop_requested = False
    
    def signal_handler(sig, frame):
        nonlocal stop_requested
        logging.info("Interrupt received, stopping monitoring...")
        stop_requested = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print header
    print("\n" + "="*80)
    print("Temperature Monitoring")
    print("="*80)
    print("Time     | Elapsed | Target  | Holder  | Liquid  | Ambient | Sink    | Power")
    print("         | (sec)   | (°C)    | (°C)    | (°C)    | (°C)    | (°C)    | (W)")
    print("-"*80)
    
    try:
        while not stop_requested:
            # Get current time
            current_time = datetime.datetime.now()
            elapsed = (current_time - start_time).total_seconds()
            
            # Check if duration exceeded
            if duration and elapsed > duration:
                break
            
            # Read TEC controller data
            holder_temp = tec_controller.get_object_temperature()
            target_temp = tec_controller.get_target_temperature()
            sink_temp = tec_controller.get_sink_temperature()
            power = tec_controller.calculate_power()
            
            # Read Arduino data if available
            liquid_temp, ambient_temp = None, None
            if arduino_interface:
                liquid_temp, ambient_temp = arduino_interface.read_temperatures()
            
            # Create data point
            data_point = {
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_seconds": elapsed,
                "holder_temp": holder_temp,
                "target_temp": target_temp,
                "liquid_temp": liquid_temp,
                "sink_temp": sink_temp,
                "ambient_temp": ambient_temp,
                "power": power
            }
            
            # Add to data manager
            data_manager.add_data_point(data_point)
            
            # Format for display
            def format_value(value):
                return f"{value:.2f}" if value is not None else "N/A"
            
            # Print status row with colors
            time_str = current_time.strftime("%H:%M:%S")
            print(
                f"{time_str} | "
                f"{elapsed:7.1f} | "
                f"{Colors.CYAN}{format_value(target_temp)}{Colors.RESET} | "
                f"{Colors.GREEN}{format_value(holder_temp)}{Colors.RESET} | "
                f"{Colors.PURPLE}{format_value(liquid_temp)}{Colors.RESET} | "
                f"{Colors.BLUE}{format_value(ambient_temp)}{Colors.RESET} | "
                f"{Colors.RED}{format_value(sink_temp)}{Colors.RESET} | "
                f"{format_value(power)}"
            )
            
            # Wait before next reading (aiming for consistent interval)
            time_taken = (datetime.datetime.now() - current_time).total_seconds()
            if time_taken < interval:
                time.sleep(interval - time_taken)
            
    except Exception as e:
        logging.error(f"Error during monitoring: {e}")
    
    finally:
        logging.info("Monitoring completed")

def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Temperature Monitoring System")
    parser.add_argument("--tec-port", help="Serial port for TEC controller")
    parser.add_argument("--arduino-port", help="Serial port for Arduino")
    parser.add_argument("--duration", type=int, default=None, help="Monitoring duration in seconds")
    parser.add_argument("--interval", type=float, default=1.0, help="Reading interval in seconds")
    parser.add_argument("--output", help="Output file for data")
    parser.add_argument("--log-file", help="Log file path")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Set up logging
    log_file = args.log_file or get_default_log_file()
    setup_logger(log_file=log_file, level=getattr(logging, args.log_level))
    
    # Welcome message
    print(f"\n{Colors.CYAN}Temperature Monitoring System{Colors.RESET}")
    print(f"{Colors.CYAN}============================{Colors.RESET}")
    
    # Interactive port selection if not specified in command line
    tec_port = args.tec_port
    arduino_port = args.arduino_port
    
    if not tec_port or not arduino_port:
        try:
            tec_port, arduino_port = select_ports_interactive()
        except Exception as e:
            logging.error(f"Error selecting ports: {e}")
            return 1
    
    # Print monitoring settings
    print("\nMonitoring settings:")
    print(f"  TEC Controller port: {tec_port}")
    if arduino_port:
        print(f"  Arduino port: {arduino_port}")
    else:
        print("  Arduino: Not used")
    print(f"  Duration: {args.duration if args.duration else 'Indefinite'} seconds")
    print(f"  Interval: {args.interval} seconds")
    
    # Confirm before proceeding
    confirm = input("\nProceed with these settings? (y/n): ")
    if confirm.lower() != 'y':
        print("Monitoring cancelled.")
        return 0
    
    # Initialize components
    tec_controller = TECController(port=tec_port)
    arduino_interface = ArduinoInterface(port=arduino_port) if arduino_port else None
    data_manager = DataManager()
    
    try:
        # Connect to TEC controller
        if not tec_controller.connect():
            logging.error("Failed to connect to TEC controller. Exiting.")
            return 1
        
        # Connect to Arduino if specified
        if arduino_interface and not arduino_interface.connect():
            logging.warning("Failed to connect to Arduino. Continuing with TEC controller only.")
            arduino_interface = None
        
        # Run monitoring
        monitor_temperature(
            tec_controller,
            arduino_interface,
            data_manager,
            duration=args.duration,
            interval=args.interval
        )
        
        # Save data
        output_file = args.output
        if not output_file:
            # Auto-generate filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/temperature_monitor_{timestamp}.csv"
        
        data_manager.save_to_csv(output_file)
        print(f"\nData saved to {output_file}")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        return 1
    
    finally:
        # Disconnect devices
        if tec_controller:
            tec_controller.disconnect()
        if arduino_interface:
            arduino_interface.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())