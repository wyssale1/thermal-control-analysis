#!/usr/bin/env python3
"""
TEC Controller Interface

This module provides an interface to the Meerstetter TEC Controller using the MeCom protocol.
"""

import os
import sys
import logging
import time

class TECController:
    """Interface for the Meerstetter TEC Controller."""
    
    def __init__(self, port=None, address=1):
        """Initialize connection to TEC controller."""
        self.port = port
        self.address = address
        self.device = None
        self.connected = False
        
        # Try to import the MeCom library
        try:
            # Import directly from mecom folder
            module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.append(module_dir)
            from mecom.mecom import MeCom
            self.MeCom = MeCom
            logging.info("Successfully imported MeCom library")
            self.mecom_available = True
        except ImportError:
            logging.error("MeCom library not found. Please ensure it's in the Python path.")
            self.mecom_available = False
    
    def connect(self):
        """Establish connection to the TEC controller."""
        if not self.mecom_available:
            logging.error("Cannot connect: MeCom library not available")
            return False
            
        try:
            # Connect using MeCom library
            self.device = self.MeCom(serialport=self.port)
            
            # Get device address
            self.address = self.device.identify()
            logging.info(f"Connected to TEC Controller on {self.port} with address {self.address}")
            
            # Check device status
            status = self.get_device_status()
            logging.info(f"Device status: {status}")
            
            self.connected = True
            return True
            
        except Exception as e:
            logging.error(f"Failed to connect to TEC Controller: {e}")
            return False
    
    def disconnect(self):
        """Close the connection."""
        if self.connected and self.device:
            try:
                self.device.stop()
                logging.info("Disconnected from TEC Controller")
            except Exception as e:
                logging.error(f"Error disconnecting from TEC Controller: {e}")
            finally:
                self.connected = False
    
    def get_device_status(self):
        """Get the device status."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            return self.device.status(address=self.address)
        except Exception as e:
            logging.error(f"Error getting device status: {e}")
            return None
    
    def get_object_temperature(self):
        """Get the object (holder) temperature."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            return self.device.get_parameter(parameter_name="Object Temperature", address=self.address)
        except Exception as e:
            logging.error(f"Error getting object temperature: {e}")
            return None
    
    def get_target_temperature(self):
        """Get the target temperature."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            return self.device.get_parameter(parameter_id=3000, address=self.address)
        except Exception as e:
            logging.error(f"Error getting target temperature: {e}")
            return None
    
    def set_target_temperature(self, temperature):
        """Set the target temperature."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return False
            
        try:
            success = self.device.set_parameter(value=temperature, parameter_id=3000, address=self.address)
            if success:
                logging.info(f"Set target temperature to {temperature:.2f}°C")
            return success
        except Exception as e:
            logging.error(f"Error setting target temperature: {e}")
            return False
    
    def get_sink_temperature(self):
        """Get the heat sink temperature."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            return self.device.get_parameter(parameter_id=1001, address=self.address)
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
            current = self.device.get_parameter(parameter_id=1020, address=self.address)
            # Parameter 1021 is Actual Output Voltage
            voltage = self.device.get_parameter(parameter_id=1021, address=self.address)
            
            if current is not None and voltage is not None:
                return abs(current * voltage)
            return None
        except Exception as e:
            logging.error(f"Error calculating power: {e}")
            return None

    def get_parameter(self, parameter_name=None, parameter_id=None):
        """Get parameter by name or ID."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return None
            
        try:
            if parameter_name:
                return self.device.get_parameter(parameter_name=parameter_name, address=self.address)
            elif parameter_id:
                return self.device.get_parameter_raw(parameter_id=parameter_id, parameter_format="FLOAT32", address=self.address)
            else:
                logging.error("Either parameter_name or parameter_id must be provided")
                return None
        except Exception as e:
            logging.error(f"Error getting parameter: {e}")
            return None
    
    def set_parameter(self, value, parameter_name=None, parameter_id=None):
        """Set parameter by name or ID."""
        if not self.connected:
            logging.error("Not connected to TEC Controller")
            return False
            
        try:
            if parameter_name:
                return self.device.set_parameter(value=float(value), parameter_name=parameter_name, address=self.address)
            elif parameter_id:
                return self.device.set_parameter_raw(value=float(value), parameter_id=parameter_id, 
                                                     parameter_format="FLOAT32", address=self.address)
            else:
                logging.error("Either parameter_name or parameter_id must be provided")
                return False
        except Exception as e:
            logging.error(f"Error setting parameter: {e}")
            return False