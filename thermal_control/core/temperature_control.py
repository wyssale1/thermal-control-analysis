#!/usr/bin/env python3
"""
Temperature Control System

This module provides the core temperature control logic.
"""

import logging
import time
import threading
import datetime

class TemperatureControl:
    """Main class for temperature control system with offset correction."""
    
    def __init__(self, tec_controller, arduino_interface, data_manager):
        """
        Initialize the temperature control system.
        
        Args:
            tec_controller: TECController instance
            arduino_interface: ArduinoInterface instance
            data_manager: DataManager instance
        """
        self.tec = tec_controller
        self.arduino = arduino_interface
        self.data_manager = data_manager
        self.running = False
        self.experiment_running = False
        self.stop_event = threading.Event()
        self.desired_liquid_temp = None
        
        # Coefficients for temperature correction formula from LabVIEW:
        # x = (-0.5645 + sqrt(0.5645**2 - 4*0.0039*(4.8536-y)))/(2*0.0039)
        # Where y is the desired liquid temperature and x is the corrected target temperature
        self.a = 0.0039  # Coefficient of x²
        self.b = 0.5645  # Coefficient of x
        self.c = 4.8536  # Constant term
        
        # Optional ambient temperature correction
        self.use_ambient_correction = False
        self.ambient_reference = 20.0  # Reference ambient temperature
        self.ambient_coefficient = 0.0  # Coefficient for ambient correction
    
    def connect_devices(self):
        """Connect to both devices."""
        logging.info("Connecting to devices...")
        tec_connected = self.tec.connect()
        
        # Only try to connect to Arduino if it exists
        arduino_connected = True
        if self.arduino:
            arduino_connected = self.arduino.connect()
        
        if tec_connected and arduino_connected:
            logging.info("All devices connected successfully")
            return True
        else:
            if not tec_connected:
                logging.error("Failed to connect to TEC Controller")
            if self.arduino and not arduino_connected:
                logging.error("Failed to connect to Arduino")
            return False
    
    def disconnect_devices(self):
        """Disconnect from both devices."""
        if self.tec:
            self.tec.disconnect()
        if self.arduino:
            self.arduino.disconnect()
        logging.info("All devices disconnected")
    
    def calculate_corrected_target(self, desired_liquid_temp, ambient_temp=None):
        """
        Calculate the corrected target temperature for the holder.
        
        Uses the temperature correction formula from LabVIEW:
        x = (-0.5645 + sqrt(0.5645**2 - 4*0.0039*(4.8536-y)))/(2*0.0039)
        Where y is the desired liquid temperature and x is the corrected target temperature
        
        This is based on solving the quadratic equation: ax² + bx + (c-y) = 0
        Using the quadratic formula: x = (-b ± sqrt(b² - 4a(c-y)))/(2a)
        
        Args:
            desired_liquid_temp: The desired temperature for the liquid
            ambient_temp: Optional ambient temperature for additional compensation
            
        Returns:
            The corrected target temperature to set for the holder
        """
        # Apply ambient temperature correction if enabled and ambient_temp is provided
        ambient_correction = 0.0
        if self.use_ambient_correction and ambient_temp is not None:
            ambient_correction = self.ambient_coefficient * (ambient_temp - self.ambient_reference)
            logging.info(f"Applied ambient correction: {ambient_correction:.2f}°C (ambient: {ambient_temp:.2f}°C)")
        
        # Adjusted target temperature with ambient correction
        adjusted_desired_temp = desired_liquid_temp - ambient_correction
        
        try:
            # Calculate discriminant of quadratic formula
            discriminant = self.b**2 - 4 * self.a * (self.c - adjusted_desired_temp)
            
            if discriminant < 0:
                # No real roots, fallback to linear approximation
                logging.warning(f"No real solution found for temperature {desired_liquid_temp}°C. Using approximation.")
                # Linear approximation: assume ax² is small compared to bx
                corrected_target = (adjusted_desired_temp - self.c) / self.b
            else:
                # Use quadratic formula, taking the positive square root solution
                # This is based on the LabVIEW formula that uses the + sign
                corrected_target = (-self.b + (discriminant)**0.5) / (2 * self.a)
                
                # If result is unreasonably outside the operating range, try other solution
                if corrected_target < 0 or corrected_target > 100:
                    alt_target = (-self.b - (discriminant)**0.5) / (2 * self.a)
                    if 0 <= alt_target <= 100:
                        logging.info(f"Using alternative solution {alt_target:.2f}°C instead of {corrected_target:.2f}°C")
                        corrected_target = alt_target
        
        except Exception as e:
            logging.error(f"Error calculating corrected temperature: {e}")
            # Fallback: use direct setting
            corrected_target = desired_liquid_temp
            logging.warning(f"Using direct temperature setting without correction: {corrected_target:.2f}°C")
        
        logging.info(f"Desired liquid temp: {desired_liquid_temp:.2f}°C, "
                     f"Setting holder to: {corrected_target:.2f}°C")
        
        return corrected_target
    
    def read_all_sensors(self):
        """Read data from all sensors."""
        # Read TEC controller values
        holder_temp = self.tec.get_object_temperature()
        target_temp = self.tec.get_target_temperature()
        sink_temp = self.tec.get_sink_temperature()
        power = self.tec.calculate_power()
        
        # Read Arduino values (if available)
        liquid_temp, ambient_temp = None, None
        if self.arduino:
            liquid_temp, ambient_temp = self.arduino.read_temperatures()
        
        # Create data point
        data_point = {
            "holder_temp": holder_temp,
            "target_temp": target_temp,
            "liquid_temp": liquid_temp,
            "sink_temp": sink_temp,
            "ambient_temp": ambient_temp,
            "power": power,
            "desired_liquid_temp": self.desired_liquid_temp
        }
        
        return data_point
    
    def start_monitoring(self):
        """Start the monitoring loop in a separate thread."""
        if not self.running:
            self.stop_event.clear()
            self.data_manager.reset()
            self.monitor_thread = threading.Thread(target=self._monitoring_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            self.running = True
            logging.info("Monitoring started")
            return True
        return False
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        if self.running:
            self.stop_event.set()
            self.running = False
            if hasattr(self, 'monitor_thread'):
                self.monitor_thread.join(timeout=2)
            logging.info("Monitoring stopped")
            return True
        return False
    
    def _monitoring_loop(self):
        """Main monitoring loop that reads sensors and logs data."""
        logging.info("Monitoring loop started")
        
        while not self.stop_event.is_set():
            try:
                # Read all sensors
                data_point = self.read_all_sensors()
                
                # Add data point to the data manager
                self.data_manager.add_data_point(data_point)
                
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
    
    def set_temperature(self, desired_liquid_temp, use_correction=True):
        """
        Set the temperature with optional offset correction.
        
        Args:
            desired_liquid_temp: Desired liquid temperature in °C
            use_correction: Whether to apply the offset correction formula
            
        Returns:
            Boolean indicating success
        """
        # Store the desired liquid temperature for data collection
        self.desired_liquid_temp = desired_liquid_temp

        if not use_correction:
            # Set temperature directly without correction
            success = self.tec.set_target_temperature(desired_liquid_temp)
            if success:
                logging.info(f"Target temperature set to {desired_liquid_temp:.2f}°C (no correction)")
            return success
        else:
            # Get current ambient temperature if available
            ambient_temp = None
            if self.arduino and self.use_ambient_correction:
                _, ambient_temp = self.arduino.read_temperatures()
            
            # Apply temperature offset correction
            corrected_target = self.calculate_corrected_target(desired_liquid_temp, ambient_temp)
            
            # Set the corrected target temperature
            success = self.tec.set_target_temperature(corrected_target)
            if success:
                logging.info(f"Corrected target temperature set to {corrected_target:.2f}°C "
                             f"(for desired liquid temp {desired_liquid_temp:.2f}°C)")
            return success
    
    def run_experiment(self, start_temp, stop_temp, increment, stabilization_time_minutes, use_correction=True):
        """
        Run an experiment with temperature steps.
        
        Args:
            start_temp: Starting temperature
            stop_temp: Final temperature
            increment: Temperature increment (can be negative)
            stabilization_time_minutes: Minutes to wait at each temperature
            use_correction: Whether to use temperature correction
            
        Returns:
            Boolean indicating success
        """
        if self.experiment_running:
            logging.error("Experiment already running")
            return False
        
        self.experiment_running = True
        logging.info(f"Starting experiment: {start_temp}°C to {stop_temp}°C "
                     f"in {increment}°C steps with {stabilization_time_minutes} minutes stabilization")
        logging.info(f"Temperature correction: {'Enabled' if use_correction else 'Disabled'}")
        
        # Ensure increment has the correct sign
        if start_temp < stop_temp and increment <= 0:
            increment = abs(increment)
        elif start_temp > stop_temp and increment >= 0:
            increment = -abs(increment)
        
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
        was_running = self.running
        if not self.running:
            self.start_monitoring()
        
        try:
            # Run through temperature steps
            for i, temp in enumerate(steps):
                logging.info(f"Step {i+1}/{len(steps)}: Setting temperature to {temp:.2f}°C")
                
                # Set target temperature with or without correction
                if not self.set_temperature(temp, use_correction=use_correction):
                    logging.error(f"Failed to set temperature for step {i+1}")
                    self.experiment_running = False
                    return False
                
                # Save start of this step
                step_start = datetime.datetime.now()
                
                # Wait for stabilization time
                logging.info(f"Waiting {stabilization_time_minutes} minutes for stabilization...")
                
                # Wait in small increments to allow for interruption
                stabilization_seconds = stabilization_time_minutes * 60
                for _ in range(stabilization_seconds):
                    if self.stop_event.is_set() or not self.experiment_running:
                        logging.info("Experiment interrupted")
                        self.experiment_running = False
                        return False
                    time.sleep(1)
                
                step_end = datetime.datetime.now()
                step_duration = (step_end - step_start).total_seconds() / 60
                
                logging.info(f"Step {i+1} completed (duration: {step_duration:.1f} minutes)")
            
            logging.info("Experiment completed successfully")
            self.experiment_running = False
            return True
            
        except Exception as e:
            logging.error(f"Error during experiment: {e}")
            self.experiment_running = False
            return False
        finally:
            self.experiment_running = False
            # Stop monitoring if it wasn't running before
            if not was_running:
                self.stop_monitoring()
    
    def stop_experiment(self):
        """Stop the running experiment."""
        if self.experiment_running:
            self.experiment_running = False
            logging.info("Experiment stopping...")
            return True
        else:
            logging.warning("No experiment running")
            return False
    
    def update_correction_parameters(self, a=None, b=None, c=None, 
                                    use_ambient=None, ambient_ref=None, ambient_coeff=None):
        """
        Update the temperature correction parameters.
        
        Args:
            a: Coefficient of x² in the formula
            b: Coefficient of x in the formula
            c: Constant term in the formula
            use_ambient: Whether to use ambient temperature correction
            ambient_ref: Reference ambient temperature
            ambient_coeff: Coefficient for ambient correction
        """
        if a is not None:
            self.a = a
        if b is not None:
            self.b = b
        if c is not None:
            self.c = c
        if use_ambient is not None:
            self.use_ambient_correction = use_ambient
        if ambient_ref is not None:
            self.ambient_reference = ambient_ref
        if ambient_coeff is not None:
            self.ambient_coefficient = ambient_coeff
            
        logging.info(f"Updated correction parameters for quadratic formula: "
                    f"x = (-{self.b} ± sqrt({self.b}² - 4*{self.a}*({self.c}-y)))/(2*{self.a})")
        if self.use_ambient_correction:
            logging.info(f"Ambient correction enabled with reference temp {self.ambient_reference}°C "
                        f"and coefficient {self.ambient_coefficient}")
        else:
            logging.info("Ambient correction disabled")