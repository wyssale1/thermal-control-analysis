#!/usr/bin/env python3
"""
Arduino Interface

This module provides an interface to the Arduino that reads liquid and ambient temperatures.
"""

import serial
import time
import logging
import re

class ArduinoInterface:
    """Interface for the Arduino that reads liquid and ambient temperatures."""
    
    def __init__(self, port=None):
        """Initialize connection to Arduino."""
        self.port = port
        self.ser = None
        self.connected = False
    
    def connect(self):
        """Establish serial connection to the Arduino."""
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
            try:
                self.ser.close()
                logging.info("Disconnected from Arduino")
            except Exception as e:
                logging.error(f"Error disconnecting from Arduino: {e}")
            finally:
                self.connected = False
    
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
            
            # Parse response (try multiple patterns)
            # Try pattern with Pt100/Pt1000 prefixes
            pt100_match = re.search(r'Pt100\s*([\d.]+)', response)
            pt1000_match = re.search(r'Pt1000\s*([\d.]+)', response)
            
            if pt100_match and pt1000_match:
                ambient_temp = float(pt100_match.group(1))
                liquid_temp = float(pt1000_match.group(1))
                return liquid_temp, ambient_temp
            
            # Try simple comma-separated pattern
            if ',' in response:
                parts = response.split(',')
                if len(parts) >= 2:
                    try:
                        liquid_temp = float(parts[0])
                        ambient_temp = float(parts[1])
                        return liquid_temp, ambient_temp
                    except ValueError:
                        pass
            
            # Try finding any numbers as last resort
            numbers = re.findall(r'([\d.]+)', response)
            if len(numbers) >= 2:
                try:
                    liquid_temp = float(numbers[1])  # Pt1000 usually comes second
                    ambient_temp = float(numbers[0])  # Pt100 usually comes first
                    return liquid_temp, ambient_temp
                except ValueError:
                    pass
            
            logging.error(f"Could not parse temperatures from response: {response}")
            
        except Exception as e:
            logging.error(f"Error reading temperatures from Arduino: {e}")
        
        return None, None