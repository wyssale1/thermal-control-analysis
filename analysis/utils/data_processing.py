#!/usr/bin/env python3
"""
Data Processing Utilities

This module provides functions for reading and processing temperature data.
"""

import os
import pandas as pd
import numpy as np
import re
import logging
from datetime import datetime

def read_measurement_file(filename, filepath=None):
    """
    Read temperature data from CSV/Excel file.
    
    Args:
        filename: Name of the file
        filepath: Directory containing the file (default is None)
        
    Returns:
        pandas.DataFrame containing the data
    """
    # Construct full path if filepath is provided
    if filepath:
        full_path = os.path.join(filepath, filename)
    else:
        full_path = filename
    
    try:
        # Determine file type by extension
        _, ext = os.path.splitext(filename)
        
        if ext.lower() in ['.xlsx', '.xls']:
            # Excel file
            df = pd.read_excel(full_path)
        elif ext.lower() == '.csv':
            # CSV file
            df = pd.read_csv(full_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        
        logging.info(f"Successfully read data from {full_path}, {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Standardize column names
        df = standardize_columns(df)
        
        return df
    
    except Exception as e:
        logging.error(f"Error reading file {full_path}: {e}")
        return None

def standardize_columns(df):
    """
    Standardize column names in the DataFrame.
    
    Args:
        df: pandas.DataFrame with temperature data
        
    Returns:
        DataFrame with standardized column names
    """
    # Expected column names from the LabVIEW output
    expected_columns = [
        'Time', 
        'Holder Temperature', 
        'Liquid Temperature', 
        'Target Temperature', 
        'Heatsink Temperature', 
        'Room Temperature', 
        'Power'
    ]
    
    # Common variations in column names
    column_mapping = {
        'Time': ['Time', 'time', 'timestamp', 'Timestamp', 'elapse', 'elapsed_seconds'],
        'Holder Temperature': ['Holder Temperature', 'holder_temp', 'holderTemp', 'Holder Temp', 'holder'],
        'Liquid Temperature': ['Liquid Temperature', 'liquid_temp', 'liquidTemp', 'Liquid Temp', 'liquid'],
        'Target Temperature': ['Target Temperature', 'target_temp', 'targetTemp', 'Target Temp', 'target'],
        'Heatsink Temperature': ['Heatsink Temperature', 'sink_temp', 'heatsink_temp', 'Sink Temperature', 'sink'],
        'Room Temperature': ['Room Temperature', 'ambient_temp', 'room_temp', 'Ambient Temperature', 'ambient'],
        'Power': ['Power', 'power', 'Power (W)', 'pwr']
    }
    
    # Get existing columns from the DataFrame
    existing_columns = df.columns.tolist()
    
    # Create a new DataFrame with standardized column names
    new_df = pd.DataFrame()
    
    # First, look for exact column names
    for std_name, variations in column_mapping.items():
        for col in existing_columns:
            if col in variations:
                new_df[std_name] = df[col]
                break
    
    # Then try case-insensitive and partial matching
    for std_name, variations in column_mapping.items():
        if std_name not in new_df.columns:
            for col in existing_columns:
                for var in variations:
                    if var.lower() in col.lower():
                        new_df[std_name] = df[col]
                        break
                if std_name in new_df.columns:
                    break
    
    # If any standard columns are still missing, add them as NaN
    for std_name in expected_columns:
        if std_name not in new_df.columns:
            new_df[std_name] = np.nan
    
    return new_df

def extract_measurement_settings(filename):
    """
    Extract measurement settings from filename.
    
    Args:
        filename: Name of the file (expected format: DATE_TIME_START_STOP_INCREMENT_STABILIZATION.ext)
        
    Returns:
        dict with extracted settings
    """
    # Default settings
    settings = {
        'date': None,
        'time': None,
        'start_temp': None,
        'stop_temp': None,
        'increment': None,
        'stabilization_time': None
    }
    
    try:
        # Extract filename without path and extension
        basename = os.path.basename(filename)
        
        # Try to match different filename patterns
        
        # Pattern 1: DATE_TIME_START_STOP_INCREMENT_STABILIZATION.ext
        # Example: 14.01.25_10.30_20.0_30.0_1.0_15.xlsx
        pattern1 = r'(\d+\.\d+\.\d+)_(\d+\.\d+)_(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)'
        
        # Pattern 2: DATE,TIME,START_STOP_INCREMENT_STABILIZATION.ext
        # Example: 14.01.25,10.30,20.0_30.0_1.0_15.xlsx
        pattern2 = r'(\d+\.\d+\.\d+),(\d+\.\d+),(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)_(\d+\.?\d*)'
        
        # Try to match patterns
        for pattern in [pattern1, pattern2]:
            match = re.search(pattern, basename)
            if match:
                settings['date'] = match.group(1)
                settings['time'] = match.group(2)
                settings['start_temp'] = float(match.group(3))
                settings['stop_temp'] = float(match.group(4))
                settings['increment'] = float(match.group(5))
                settings['stabilization_time'] = float(match.group(6))
                break
        
        # If no match found, try to extract from alternative patterns
        if settings['start_temp'] is None:
            # Try to extract start and stop temps from any pattern
            temp_pattern = r'(\d+\.?\d*)_(\d+\.?\d*)'
            match = re.search(temp_pattern, basename)
            if match:
                settings['start_temp'] = float(match.group(1))
                settings['stop_temp'] = float(match.group(2))
                settings['increment'] = 1.0 if settings['start_temp'] < settings['stop_temp'] else -1.0
        
        # Extract date/time from filename if not from patterns
        if settings['date'] is None:
            date_pattern = r'(\d+\.\d+\.\d+)'
            match = re.search(date_pattern, basename)
            if match:
                settings['date'] = match.group(1)
        
        # If increment is not set but start and stop are, calculate it
        if settings['increment'] is None and settings['start_temp'] is not None and settings['stop_temp'] is not None:
            if settings['start_temp'] < settings['stop_temp']:
                settings['increment'] = 1.0
            else:
                settings['increment'] = -1.0
        
        # Set default stabilization time if not found
        if settings['stabilization_time'] is None:
            settings['stabilization_time'] = 15.0
        
        return settings
        
    except Exception as e:
        logging.error(f"Error extracting settings from filename {filename}: {e}")
        return settings

def split_temperature_steps(df, settings=None):
    """
    Split data into temperature steps.
    
    Args:
        df: pandas.DataFrame with temperature data
        settings: Dict with measurement settings (optional)
        
    Returns:
        List of DataFrames, one for each temperature step
    """
    try:
        # If settings are not provided, try to infer them
        if settings is None or settings['start_temp'] is None or settings['stop_temp'] is None:
            # Try to infer from the data
            target_temps = df['Target Temperature'].dropna().unique()
            
            if len(target_temps) <= 1:
                # Single temperature measurement
                return [df]
            
            settings = {
                'start_temp': target_temps[0],
                'stop_temp': target_temps[-1],
                'increment': target_temps[1] - target_temps[0] if len(target_temps) > 1 else 1.0
            }
        
        # Now split the data based on target temperature changes
        steps = []
        
        # Calculate expected number of steps
        if settings['increment'] == 0:
            # Single temperature
            return [df]
        
        expected_steps = int(abs((settings['stop_temp'] - settings['start_temp']) / settings['increment'])) + 1
        
        # Try to detect temperature changes from the data
        target_temps = df['Target Temperature'].values
        temp_changes = []
        
        for i in range(1, len(target_temps)):
            if abs(target_temps[i] - target_temps[i-1]) > 0.1:
                temp_changes.append(i)
        
        if len(temp_changes) >= expected_steps - 1:
            # We found enough temperature changes
            logging.info(f"Detected {len(temp_changes)} temperature changes in the data")
            
            # Add start and end points
            step_points = [0] + temp_changes + [len(df)]
            
            for i in range(len(step_points) - 1):
                step_data = df.iloc[step_points[i]:step_points[i+1]]
                if not step_data.empty:
                    steps.append(step_data)
        else:
            # Fallback: split by equal segments
            logging.info(f"Could not detect enough temperature changes, splitting data into {expected_steps} equal parts")
            segment_size = len(df) // expected_steps
            
            for i in range(expected_steps):
                start_idx = i * segment_size
                if i == expected_steps - 1:
                    end_idx = len(df)
                else:
                    end_idx = (i + 1) * segment_size
                
                step_data = df.iloc[start_idx:end_idx]
                if not step_data.empty:
                    steps.append(step_data)
        
        # Log information about each step
        for i, step_df in enumerate(steps):
            avg_target = step_df['Target Temperature'].mean()
            logging.info(f"Step {i+1}: Average target temp = {avg_target:.2f}°C, {len(step_df)} data points")
        
        return steps
        
    except Exception as e:
        logging.error(f"Error splitting temperature steps: {e}")
        return [df]  # Return the original DataFrame as a single step

def extract_offset_data(step_df, step_name=None):
    """
    Extract temperature offset data from a temperature step.
    
    Args:
        step_df: pandas.DataFrame for a single temperature step
        step_name: Name of the step for logging (optional)
        
    Returns:
        dict with offset data
    """
    try:
        if step_name is None:
            step_name = f"Step with target {step_df['Target Temperature'].mean():.2f}°C"
        
        # Identify the stable region (last 20% of data)
        stable_idx = int(0.8 * len(step_df))
        stable_data = step_df.iloc[stable_idx:]
        
        # Calculate statistics for the stable region
        target_temp = stable_data['Target Temperature'].mean()
        
        holder_temp_mean = stable_data['Holder Temperature'].mean()
        holder_temp_std = stable_data['Holder Temperature'].std()
        
        liquid_temp_mean = stable_data['Liquid Temperature'].mean()
        liquid_temp_std = stable_data['Liquid Temperature'].std()
        
        ambient_temp_mean = stable_data['Room Temperature'].mean()
        ambient_temp_std = stable_data['Room Temperature'].std()
        
        # Calculate offsets
        holder_offset = holder_temp_mean - target_temp
        liquid_offset = liquid_temp_mean - target_temp
        
        # Determine time to reach stability
        stability_threshold = 0.5  # °C
        
        time_values = step_df['Time'].values
        if isinstance(time_values[0], str):
            # Try to convert string timestamps to seconds
            try:
                time_values = np.array([pd.Timestamp(t).timestamp() for t in time_values])
                time_values = time_values - time_values[0]  # Relative time
            except:
                # If conversion fails, use row indices
                time_values = np.arange(len(step_df))
        
        liquid_temps = step_df['Liquid Temperature'].values
        
        t_stable = None
        for i in range(len(liquid_temps)):
            if abs(liquid_temps[i] - liquid_temp_mean) < stability_threshold:
                t_stable = time_values[i]
                break
        
        if t_stable is None:
            t_stable = time_values[-1] / 2  # Default to halfway point
        
        # Create result dictionary
        result = {
            'target_temp': target_temp,
            'holder_temp_mean': holder_temp_mean,
            'holder_temp_std': holder_temp_std,
            'holder_offset': holder_offset,
            'liquid_temp_mean': liquid_temp_mean,
            'liquid_temp_std': liquid_temp_std,
            'liquid_offset': liquid_offset,
            'ambient_temp_mean': ambient_temp_mean,
            'ambient_temp_std': ambient_temp_std,
            'time_to_stability': t_stable
        }
        
        # Log results
        logging.info(f"Results for {step_name}:")
        logging.info(f"  Target Temperature: {target_temp:.2f}°C")
        logging.info(f"  Holder Temperature: {holder_temp_mean:.2f} ± {holder_temp_std:.3f}°C (offset: {holder_offset:.2f}°C)")
        logging.info(f"  Liquid Temperature: {liquid_temp_mean:.2f} ± {liquid_temp_std:.3f}°C (offset: {liquid_offset:.2f}°C)")
        logging.info(f"  Ambient Temperature: {ambient_temp_mean:.2f} ± {ambient_temp_std:.3f}°C")
        logging.info(f"  Time to stability: {t_stable:.1f} seconds")
        
        return result
    
    except Exception as e:
        logging.error(f"Error extracting offset data: {e}")
        return None

def calculate_corrected_target(desired_liquid_temp, a, b, c, ambient_temp=None, ambient_ref=None, ambient_coeff=None):
    """
    Calculate the corrected target temperature for the holder.
    
    Args:
        desired_liquid_temp: Desired liquid temperature
        a, b, c: Coefficients for the quadratic formula
        ambient_temp: Current ambient temperature (optional)
        ambient_ref: Reference ambient temperature (optional)
        ambient_coeff: Ambient correction coefficient (optional)
        
    Returns:
        Corrected target temperature for the holder
    """
    try:
        # Apply ambient temperature correction if parameters are provided
        ambient_correction = 0.0
        if ambient_temp is not None and ambient_ref is not None and ambient_coeff is not None:
            ambient_correction = ambient_coeff * (ambient_temp - ambient_ref)
        
        # Adjusted desired temperature with ambient correction
        adjusted_desired_temp = desired_liquid_temp - ambient_correction
        
        # Calculate the discriminant
        discriminant = b**2 - 4 * a * (c - adjusted_desired_temp)
        
        if discriminant < 0:
            # No real solutions, use linear approximation
            corrected_target = (adjusted_desired_temp - c) / b
            logging.warning(f"No real solution for T={desired_liquid_temp}°C. Using linear approximation: {corrected_target:.2f}°C")
        else:
            # Use the formula from LabVIEW: x = (-b + sqrt(b^2 - 4*a*(c-y)))/(2*a)
            corrected_target = (-b + np.sqrt(discriminant)) / (2 * a)
            
            # Check if the solution is reasonable (within operating range)
            if corrected_target < 0 or corrected_target > 100:
                alt_target = (-b - np.sqrt(discriminant)) / (2 * a)
                if 0 <= alt_target <= 100:
                    corrected_target = alt_target
        
        return corrected_target
    
    except Exception as e:
        logging.error(f"Error calculating corrected target: {e}")
        return desired_liquid_temp