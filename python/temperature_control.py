#!/usr/bin/env python3
"""
Temperature Control

Main script for temperature control system.
"""

import os
import sys
import logging
import time
import signal

# Add parent directory to path to allow imports from the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devices.tec_controller import TECController
from devices.arduino_interface import ArduinoInterface
from core.temperature_control import TemperatureControl
from core.data_manager import DataManager
from utils.port_selection import select_ports_interactive
from utils.logger import setup_logger, get_default_log_file, Colors
from ui.interactive import InteractiveUI
from ui.cli import create_parser, confirm_settings, direct_command_mode
from ui.cli import run_monitor_mode, run_single_temperature_mode, run_experiment_mode

def main():
    """Main function."""
    # Parse command-line arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Set up logging
    log_file = args.log_file or get_default_log_file()
    logger = setup_logger(log_file=log_file, level=getattr(logging, args.log_level), console=not args.quiet)
    
    # Handle interrupt signals gracefully
    stop_requested = False
    
    def signal_handler(sig, frame):
        nonlocal stop_requested
        if not stop_requested:
            logger.info("Interrupt received, cleaning up...")
            stop_requested = True
        else:
            logger.warning("Second interrupt received, exiting immediately...")
            sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Welcome message
    print(f"\n{Colors.CYAN}Temperature Control System{Colors.RESET}")
    print(f"{Colors.CYAN}========================{Colors.RESET}")
    
    # Interactive port selection if not specified in command line
    tec_port = args.tec_port
    arduino_port = args.arduino_port if not args.no_arduino else None
    
    if not tec_port or (not arduino_port and not args.no_arduino):
        try:
            tec_port, arduino_port = select_ports_interactive()
        except Exception as e:
            logger.error(f"Error selecting ports: {e}")
            return 1
    
    # Confirm settings
    if not confirm_settings(args, tec_port, arduino_port):
        print("Operation cancelled.")
        return 0
    
    # Initialize components
    tec_controller = TECController(port=tec_port)
    arduino_interface = ArduinoInterface(port=arduino_port) if arduino_port else None
    data_manager = DataManager()
    
    # Create temperature control system
    temp_control = TemperatureControl(tec_controller, arduino_interface, data_manager)
    
    # Update correction parameters if provided
    if args.a is not None or args.b is not None or args.c is not None or args.use_ambient or args.ambient_ref is not None or args.ambient_coeff is not None:
        temp_control.update_correction_parameters(
            a=args.a,
            b=args.b,
            c=args.c,
            use_ambient=args.use_ambient,
            ambient_ref=args.ambient_ref,
            ambient_coeff=args.ambient_coeff
        )
    
    try:
        # Connect to devices
        if not temp_control.connect_devices():
            logger.error("Failed to connect to devices. Exiting.")
            return 1
        
        # Run in the selected mode
        if args.direct:
            # Direct command mode
            direct_command_mode(tec_controller)
        elif args.monitor:
            # Monitor-only mode
            run_monitor_mode(temp_control)
        elif args.set_temp is not None:
            # Set and monitor a single temperature
            run_single_temperature_mode(temp_control, args.set_temp, not args.no_correction)
        elif args.experiment and args.start_temp is not None and args.stop_temp is not None and args.increment is not None:
            # Run an experiment
            run_experiment_mode(temp_control, args.start_temp, args.stop_temp, args.increment, args.stab_time, not args.no_correction)
        else:
            # Interactive mode (default)
            interactive_ui = InteractiveUI(temp_control, data_manager)
            interactive_ui.run()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    finally:
        # Save data if requested or by default
        if data_manager.get_all_data():
            output_file = args.output
            if not output_file:
                # Auto-generate filename
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"data/temperature_data_{timestamp}.csv"
            
            data_manager.save_to_csv(output_file)
            print(f"\nData saved to {output_file}")
        
        # Disconnect devices
        temp_control.disconnect_devices()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())