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
import argparse
from datetime import datetime

# Add parent directory to path to allow imports from the package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from thermal_control.devices.tec_controller import TECController
from thermal_control.devices.arduino_interface import ArduinoInterface
from thermal_control.core.temperature_control import TemperatureControl
from thermal_control.core.data_manager import DataManager
from thermal_control.utils.port_selection import select_ports_interactive
from thermal_control.utils.logger import setup_logger, get_default_log_file, Colors
from thermal_control.utils.config_reader import read_config, get_correction_parameters
from thermal_control.ui.interactive import InteractiveUI
from thermal_control.ui.cli import create_parser, confirm_settings, direct_command_mode
from thermal_control.ui.cli import run_monitor_mode, run_single_temperature_mode, run_experiment_mode

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

    # Load interpolation model if specified
    temp_control.load_interpolation_model()

    
    # Load correction parameters from config file
    config = read_config()
    correction_params = get_correction_parameters(config)
    
    # Update correction parameters
    if args.a is not None or args.b is not None or args.c is not None or args.use_ambient or args.ambient_ref is not None or args.ambient_coeff is not None:
        # Use command-line parameters
        temp_control.update_correction_parameters(
            a=args.a,
            b=args.b,
            c=args.c,
            use_ambient=args.use_ambient,
            ambient_ref=args.ambient_ref,
            ambient_coeff=args.ambient_coeff
        )
    else:
        # Use parameters from config file
        temp_control.update_correction_parameters(
            a=correction_params['a'],
            b=correction_params['b'],
            c=correction_params['c'],
            use_ambient=correction_params['use_ambient'],
            ambient_ref=correction_params['ambient_ref'],
            ambient_coeff=correction_params['ambient_coeff']
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
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Get raw data directory from config
                raw_data_dir = config.get('paths', 'raw_data_dir', fallback='data/raw')
                
                # Ensure directory exists
                os.makedirs(raw_data_dir, exist_ok=True)
                
                # Create filename with relevant information
                if args.experiment and args.start_temp is not None and args.stop_temp is not None and args.increment is not None:
                    # For experiments, include temperature range info
                    filename = f"{timestamp}_{args.start_temp:.1f}_{args.stop_temp:.1f}_{args.increment:.1f}_{args.stab_time}.csv"
                elif args.set_temp is not None:
                    # For single temperature, include target temperature
                    filename = f"{timestamp}_{args.set_temp:.1f}.csv"
                else:
                    # Default filename
                    filename = f"temperature_data_{timestamp}.csv"
                
                output_file = os.path.join(raw_data_dir, filename)
            
            data_manager.save_to_csv(output_file)
            print(f"\nData saved to {output_file}")
            
            # Ask if user wants to analyze the data
            analyze_data = input("\nDo you want to analyze the collected data? (y/n): ")
            if analyze_data.lower() == 'y':
                # Get just the filename without the path
                filename = os.path.basename(output_file)
                
                # Run the analysis script
                try:
                    print(f"\n{Colors.CYAN}Running analysis...{Colors.RESET}")
                    
                    # Import the analysis module
                    from analysis.analyze_data import analyze_temperature_data
                    
                    # Get output directory from config
                    processed_data_dir = config.get('paths', 'processed_data_dir', fallback='data/processed')
                    
                    # Analyze the data
                    results = analyze_temperature_data(
                        filename,
                        filepath=os.path.dirname(output_file),
                        output_dir=processed_data_dir,
                        plot_only=False  # Generate plots and fit parameters
                    )
                    
                    if results:
                        print(f"\n{Colors.GREEN}Analysis completed{Colors.RESET}")
                        print(f"Results saved to {processed_data_dir}")
                        
                        # Ask if user wants to update the correction parameters
                        if 'fitted_params' in results:
                            update_params = input("\nDo you want to update the correction parameters with the new fit? (y/n): ")
                            if update_params.lower() == 'y':
                                # Update the config file
                                from analysis.fit_parameters import update_config_from_fitted_params
                                success = update_config_from_fitted_params(results['fitted_params'])
                                
                                if success:
                                    print(f"{Colors.GREEN}Correction parameters updated successfully{Colors.RESET}")
                                else:
                                    print(f"{Colors.RED}Failed to update correction parameters{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}Analysis failed{Colors.RESET}")
                
                except Exception as e:
                    print(f"{Colors.RED}Error running analysis: {e}{Colors.RESET}")
        
        # Disconnect devices
        temp_control.disconnect_devices()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())