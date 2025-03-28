#!/usr/bin/env python3
"""
Port Selection Utility

This module provides functions for selecting serial ports interactively.
"""

import logging

def list_available_ports():
    """List all available serial ports."""
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        return ports
    except ImportError:
        logging.error("pyserial not installed. Please install with 'pip install pyserial'")
        return []
    except Exception as e:
        logging.error(f"Error listing ports: {e}")
        return []

def print_available_ports(ports=None):
    """Print available serial ports."""
    if ports is None:
        ports = list_available_ports()
    
    if not ports:
        print("\nNo serial ports detected.")
        return
    
    print("\nDetected serial ports:")
    for i, p in enumerate(ports):
        print(f"  {i+1}: {p.device} - {p.description}")
    return ports

def select_port(prompt, ports=None, default=None):
    """
    Interactively select a serial port.
    
    Args:
        prompt: The prompt to display to the user
        ports: List of port objects (optional, will be retrieved if None)
        default: Default port to use if no selection is made
        
    Returns:
        Selected port name or None if failed
    """
    if ports is None:
        ports = list_available_ports()
        if not ports:
            return default  # No ports available
    
    print_available_ports(ports)
    
    if default:
        port_input = input(f"\n{prompt} (or press Enter for default: {default}): ")
        if not port_input.strip():
            return default
    else:
        port_input = input(f"\n{prompt}: ")
    
    try:
        # If input is a number, use it as an index
        port_idx = int(port_input) - 1
        if 0 <= port_idx < len(ports):
            selected_port = ports[port_idx].device
            print(f"Selected port: {selected_port}")
            return selected_port
        else:
            print(f"Invalid selection: {port_input}, will try to use as direct port name")
            return port_input
    except ValueError:
        # Not a number, use as direct port name
        print(f"Using port: {port_input}")
        return port_input

def detect_arduino_port(ports=None):
    """Try to automatically detect Arduino port."""
    if ports is None:
        ports = list_available_ports()
    
    for p in ports:
        if "Arduino" in p.description or "Uno" in p.description:
            logging.info(f"Detected Arduino on {p.device}")
            return p.device
    
    logging.info("Arduino not automatically detected")
    return None

def detect_tec_port(ports=None):
    """Try to automatically detect TEC controller port."""
    if ports is None:
        ports = list_available_ports()
    
    # TEC controllers are often USB-Serial devices without specific identifiers
    # Look for USB-Serial devices that aren't Arduino
    for p in ports:
        if "USB" in p.description and "Serial" in p.description and not ("Arduino" in p.description or "Uno" in p.description):
            logging.info(f"Potentially detected TEC controller on {p.device}")
            return p.device
    
    logging.info("TEC controller not automatically detected")
    return None

def select_ports_interactive():
    """
    Interactively select TEC and Arduino ports.
    
    Returns:
        Tuple of (tec_port, arduino_port)
    """
    ports = list_available_ports()
    
    # Try to auto-detect ports
    tec_port = detect_tec_port(ports)
    arduino_port = detect_arduino_port(ports)
    
    # Let user select or confirm TEC port
    if tec_port:
        confirm = input(f"\nUse detected TEC controller port ({tec_port})? (y/n): ")
        if confirm.lower() != 'y':
            tec_port = select_port("Select TEC controller port", ports)
    else:
        tec_port = select_port("Select TEC controller port", ports)
    
    # Let user select or confirm Arduino port
    if arduino_port:
        confirm = input(f"\nUse detected Arduino port ({arduino_port})? (y/n): ")
        if confirm.lower() != 'y':
            arduino_port = select_port("Select Arduino port", ports)
    else:
        use_arduino = input("\nDo you want to use an Arduino for additional temperature monitoring? (y/n): ")
        if use_arduino.lower() == 'y':
            arduino_port = select_port("Select Arduino port", ports)
        else:
            arduino_port = None
    
    return tec_port, arduino_port