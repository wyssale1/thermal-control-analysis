#!/usr/bin/env python3
"""
Command-Line Interface

This module provides a command-line interface for temperature control.
"""

import argparse
import logging
import time
import os
import sys
from utils.logger import Colors

def create_parser():
    """Create and return an argument parser for temperature control."""
    parser = argparse.ArgumentParser(description="Temperature Control System")
    
    # Device options
    device_group = parser.add_argument_group("Device Options")
    device_group.add_argument("--tec-port", help="Serial port for TEC controller")
    device_group.add_argument("--arduino-port", help="Serial port for Arduino")
    device_group.add_argument("--no-arduino", action="store_true", help="Don't use Arduino for monitoring")
    
    # Operation modes
    mode_group = parser.add_argument_group("Operation Modes")
    mode_group.add_argument("--monitor", action="store_true", help="Just monitor temperatures without control")
    mode_group.add_argument("--set-temp", type=float, help="Set a single target temperature")
    mode_group.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    mode_group.add_argument("--direct", action="store_true", help="Direct command mode for TEC controller")
    
    # Experiment options
    exp_group = parser.add_argument_group("Experiment Options")
    exp_group.add_argument("--experiment", action="store_true", help="Run a temperature experiment")
    exp_group.add_argument("--start-temp", type=float, help="Starting temperature for experiment")
    exp_group.add_argument("--stop-temp", type=float, help="Stopping temperature for experiment")
    exp_group.add_argument("--increment", type=float, help="Temperature increment")
    exp_group.add_argument("--stab-time", type=int, default=15, help="Stabilization time in minutes")
    
    # Temperature control options
    control_group = parser.add_argument_group("Control Options")
    control_group.add_argument("--no-correction", action="store_true", help="Disable temperature offset correction")
    control_group.add_argument("--a", type=float, help="Coefficient a for temperature correction")
    control_group.add_argument("--b", type=float, help="Coefficient b for temperature correction")
    control_group.add_argument("--c", type=float, help="Coefficient c for temperature correction")
    control_group.add_argument("--use-ambient", action="store_true", help="Enable ambient temperature correction")
    control_group.add_argument("--ambient-ref", type=float, help="Reference ambient temperature")
    control_group.add_argument("--ambient-coeff", type=float, help="Ambient temperature coefficient")
    
    # Logging and output
    output_group = parser.add_argument_group("Logging and Output")
    output_group.add_argument("--output", help="Output file for data")
    output_group.add_argument("--log-file", help="Log file path")
    output_group.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                            default="INFO", help="Logging level")
    output_group.add_argument("--quiet", action="store_true", help="Suppress console output")
    
    return parser

def direct_command_mode(tec_controller):
    """
    Interactive mode to send commands directly to the TEC controller.
    
    Args:
        tec_controller: TECController instance
    """
    print(f"\n{Colors.CYAN}Direct TEC Controller Command Mode{Colors.RESET}")
    print(f"{Colors.YELLOW}This mode allows you to interact with the TEC controller.{Colors.RESET}")
    print(f"{Colors.YELLOW}Type 'exit' to quit, 'help' for commands.{Colors.RESET}")
    
    try:
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
                print("  status         - Get device status")
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
            elif command.lower() == 'status':
                status = tec_controller.get_device_status()
                print(f"Device Status: {status}")
            elif command.lower().startswith('set target '):
                try:
                    value = float(command.split()[2])
                    success = tec_controller.set_target_temperature(value)
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
    except KeyboardInterrupt:
        print("\nExiting direct command mode.")

def confirm_settings(args, tec_port, arduino_port):
    """
    Display and confirm settings before proceeding.
    
    Args:
        args: Parsed arguments
        tec_port: Selected TEC controller port
        arduino_port: Selected Arduino port
        
    Returns:
        Boolean indicating whether to proceed
    """
    print("\nTemperature Control Settings:")
    print(f"  TEC Controller port: {tec_port}")
    
    if arduino_port:
        print(f"  Arduino port: {arduino_port}")
    else:
        print("  Arduino: Not used")
    
    if args.interactive:
        print("  Mode: Interactive")
    elif args.direct:
        print("  Mode: Direct TEC controller command mode")
    elif args.monitor:
        print("  Mode: Monitor only (will not set temperature)")
    elif args.experiment:
        print("  Mode: Temperature experiment")
        print(f"    Start temperature: {args.start_temp}°C")
        print(f"    Stop temperature: {args.stop_temp}°C")
        print(f"    Increment: {args.increment}°C")
        print(f"    Stabilization time: {args.stab_time} minutes")
        print(f"    Temperature correction: {'Disabled' if args.no_correction else 'Enabled'}")
    elif args.set_temp is not None:
        print(f"  Mode: Set and monitor")
        print(f"    Target temperature: {args.set_temp}°C")
        print(f"    Temperature correction: {'Disabled' if args.no_correction else 'Enabled'}")
    else:
        print("  Mode: Interactive (default)")
    
    if args.output:
        print(f"  Data output file: {args.output}")
    else:
        print("  Data output file: Auto-generated")
    
    # Confirm before proceeding
    confirm = input("\nProceed with these settings? (y/n): ")
    return confirm.lower() == 'y'

def run_monitor_mode(temp_control):
    """
    Run in monitor-only mode.
    
    Args:
        temp_control: TemperatureControl instance
    """
    try:
        temp_control.start_monitoring()
        print(f"\n{Colors.GREEN}Monitoring started. Press Ctrl+C to stop.{Colors.RESET}")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring interrupted{Colors.RESET}")
    finally:
        temp_control.stop_monitoring()

def run_single_temperature_mode(temp_control, target_temp, use_correction):
    """
    Set and monitor a single temperature.
    
    Args:
        temp_control: TemperatureControl instance
        target_temp: Target temperature to set
        use_correction: Whether to use temperature correction
    """
    try:
        # Start monitoring
        temp_control.start_monitoring()
        
        # Set temperature
        if not temp_control.set_temperature(target_temp, use_correction=use_correction):
            print(f"{Colors.RED}Failed to set temperature{Colors.RESET}")
            return
        
        print(f"\n{Colors.GREEN}Temperature set to {target_temp}°C. Press Ctrl+C to stop.{Colors.RESET}")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Temperature control interrupted{Colors.RESET}")
    finally:
        temp_control.stop_monitoring()

def run_experiment_mode(temp_control, start_temp, stop_temp, increment, stab_time, use_correction):
    """
    Run a temperature experiment.
    
    Args:
        temp_control: TemperatureControl instance
        start_temp: Starting temperature
        stop_temp: Final temperature
        increment: Temperature increment
        stab_time: Stabilization time in minutes
        use_correction: Whether to use temperature correction
    """
    try:
        # Start experiment
        success = temp_control.run_experiment(
            start_temp,
            stop_temp,
            increment,
            stab_time,
            use_correction=use_correction
        )
        
        if success:
            print(f"{Colors.GREEN}Experiment completed successfully{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}Experiment stopped or failed{Colors.RESET}")
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Experiment interrupted{Colors.RESET}")
        temp_control.stop_experiment()