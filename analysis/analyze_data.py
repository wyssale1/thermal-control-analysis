#!/usr/bin/env python3
"""
Temperature Data Analysis

This script analyzes temperature data to fit correction parameters and generate visualizations.
It filters out data points with missing liquid temperature readings.
"""

import os
import sys
import argparse
import logging
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent directory to path to allow imports from the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thermal_control.utils.logger import Colors, setup_logger, get_default_log_file
from thermal_control.utils.config_reader import read_config, get_correction_parameters, update_correction_parameters
from analysis.utils.file_selection import select_file_interactive, list_available_files

def read_measurement_file(filename, filepath=None, filter_missing=True):
    """
    Read temperature data from CSV/Excel file and optionally filter out rows with missing data.
    
    Args:
        filename: Name of the file
        filepath: Directory containing the file (default is None)
        filter_missing: Whether to filter out rows with missing liquid temperature
        
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
            df = pd.read_csv(full_path)
        elif ext.lower() == '.csv':
            # CSV file
            df = pd.read_csv(full_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # Try to standardize column names
        column_mapping = {
            'Time': ['Time', 'time', 'timestamp', 'Timestamp', 'elapsed_seconds'],
            'Target Temperature': ['Target Temperature', 'target_temp', 'Target Temp', 'target'],
            'Holder Temperature': ['Holder Temperature', 'holder_temp', 'Holder Temp', 'holder'],
            'Liquid Temperature': ['Liquid Temperature', 'liquid_temp', 'Liquid Temp', 'liquid'],
            'Room Temperature': ['Room Temperature', 'ambient_temp', 'Ambient Temperature', 'ambient'],
            'Heatsink Temperature': ['Heatsink Temperature', 'sink_temp', 'Sink Temperature', 'sink'],
            'Power': ['Power', 'power', 'Power (W)'],
            'Desired Liquid Temperature': ['Desired Liquid Temperature', 'desired_liquid_temp']
        }
        
        # Create standardized DataFrame
        data = pd.DataFrame()
        
        # Find and map columns
        original_columns = {}
        for std_name, variations in column_mapping.items():
            found = False
            for col in df.columns:
                if col in variations or any(var.lower() in col.lower() for var in variations):
                    data[std_name] = df[col]
                    original_columns[std_name] = col
                    found = True
                    break
        
        # Check required columns
        required_cols = ['Time', 'Target Temperature', 'Holder Temperature']
        missing = [col for col in required_cols if col not in data.columns]
        if missing:
            print(f"Error: Missing required columns: {', '.join(missing)}")
            return None
            
        # Check if Liquid Temperature exists
        if 'Liquid Temperature' not in data.columns:
            print("Error: Liquid Temperature column is required for analysis")
            return None
        
        # Calculate data availability statistics
        total_rows = len(data)
        missing_liquid = data['Liquid Temperature'].isna().sum()
        missing_pct = (missing_liquid / total_rows) * 100
        
        print(f"Data statistics:")
        print(f"  Total rows: {total_rows}")
        print(f"  Rows with missing liquid temperature: {missing_liquid} ({missing_pct:.1f}%)")
        
        # Filter out rows with missing liquid temperature if requested
        if filter_missing and missing_liquid > 0:
            data_filtered = data.dropna(subset=['Liquid Temperature'])
            rows_kept = len(data_filtered)
            print(f"  Filtered data: Kept {rows_kept} rows ({(rows_kept/total_rows)*100:.1f}% of original data)")
            return data_filtered
        
        return data
        
    except Exception as e:
        print(f"Error reading file {full_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

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
        import re
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
        
        # If no match found, try to extract from timestamp format
        if settings['start_temp'] is None and '_' in basename:
            parts = basename.split('_')
            if len(parts) >= 2:
                try:
                    timestamp = datetime.strptime('_'.join(parts[:2]), '%Y%m%d_%H%M%S')
                    settings['date'] = timestamp.strftime('%d.%m.%y')
                    settings['time'] = timestamp.strftime('%H.%M')
                except:
                    pass
        
        return settings
        
    except Exception as e:
        print(f"Error extracting settings from filename {filename}: {e}")
        return settings

def split_temperature_steps(df):
    """
    Split data into temperature steps based on changes in target temperature.
    
    Args:
        df: pandas.DataFrame with temperature data
        
    Returns:
        List of DataFrames, one for each temperature step
    """
    try:
        # Get target temperature values
        target_temps = df['Target Temperature'].values
        
        # Find points where target temperature changes
        change_points = [0]  # Always include start
        for i in range(1, len(target_temps)):
            if abs(target_temps[i] - target_temps[i-1]) > 0.1:  # Threshold for change
                change_points.append(i)
        
        change_points.append(len(df))  # Always include end
        
        # Split data into steps
        steps = []
        for i in range(len(change_points) - 1):
            start_idx = change_points[i]
            end_idx = change_points[i+1]
            step_data = df.iloc[start_idx:end_idx].copy()
            
            # Only include steps with enough data points
            if len(step_data) >= 10:  # Minimum number of points for a valid step
                steps.append(step_data)
        
        print(f"Split data into {len(steps)} temperature steps")
        
        return steps
        
    except Exception as e:
        print(f"Error splitting temperature steps: {e}")
        return [df]  # Return original data if splitting fails

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
        stable_data = step_df.iloc[stable_idx:].copy()
        
        # Check if we have enough data points in the stable region
        if len(stable_data) < 5:
            print(f"Warning: Not enough data points in stable region for {step_name}")
            return None
        
        # Calculate statistics for the stable region
        target_temp = stable_data['Target Temperature'].mean()
        
        # Get desired liquid temperature if available
        desired_temp = None
        if 'Desired Liquid Temperature' in stable_data.columns and not stable_data['Desired Liquid Temperature'].isna().all():
            desired_temp = stable_data['Desired Liquid Temperature'].mean()
        
        holder_temp_mean = stable_data['Holder Temperature'].mean()
        holder_temp_std = stable_data['Holder Temperature'].std()
        
        liquid_temp_mean = stable_data['Liquid Temperature'].mean()
        liquid_temp_std = stable_data['Liquid Temperature'].std()
        
        # Get ambient temperature if available
        ambient_temp_mean = None
        ambient_temp_std = None
        if 'Room Temperature' in stable_data.columns and not stable_data['Room Temperature'].isna().all():
            ambient_temp_mean = stable_data['Room Temperature'].mean()
            ambient_temp_std = stable_data['Room Temperature'].std()
        
        # Calculate offsets
        if desired_temp is not None:
            # Use the desired liquid temperature as reference
            holder_offset = holder_temp_mean - desired_temp
            liquid_offset = liquid_temp_mean - desired_temp
            reference_temp = desired_temp
        else:
            # Use the target holder temperature as reference
            holder_offset = holder_temp_mean - target_temp
            liquid_offset = liquid_temp_mean - target_temp
            reference_temp = target_temp
        
        # Create result dictionary
        result = {
            'target_temp': reference_temp,  # This is what we're trying to achieve
            'holder_temp_mean': holder_temp_mean,
            'holder_temp_std': holder_temp_std,
            'holder_offset': holder_offset,
            'liquid_temp_mean': liquid_temp_mean,
            'liquid_temp_std': liquid_temp_std,
            'liquid_offset': liquid_offset,
        }
        
        # Add ambient data if available
        if ambient_temp_mean is not None:
            result['ambient_temp_mean'] = ambient_temp_mean
            result['ambient_temp_std'] = ambient_temp_std
        
        # Log results
        print(f"Results for {step_name}:")
        print(f"  Target Temperature: {reference_temp:.2f}°C")
        print(f"  Holder Temperature: {holder_temp_mean:.2f} ± {holder_temp_std:.3f}°C (offset: {holder_offset:.2f}°C)")
        print(f"  Liquid Temperature: {liquid_temp_mean:.2f} ± {liquid_temp_std:.3f}°C (offset: {liquid_offset:.2f}°C)")
        if ambient_temp_mean is not None:
            print(f"  Ambient Temperature: {ambient_temp_mean:.2f} ± {ambient_temp_std:.3f}°C")
        
        return result
    
    except Exception as e:
        print(f"Error extracting offset data: {e}")
        return None

def fit_correction_parameters(offset_data, use_ambient=False, ambient_ref=20.0, initial_params=None):
    """
    Fit temperature correction parameters to offset data.
    
    Args:
        offset_data: List of dicts with offset data
        use_ambient: Whether to include ambient temperature correction
        ambient_ref: Reference ambient temperature
        initial_params: Initial parameter values (optional)
        
    Returns:
        Dict with fitted parameters
    """
    try:
        # Ensure we have enough data points
        if len(offset_data) < 3:
            print("Error: Not enough data points to fit parameters")
            return None
            
        # Extract data
        target_temps = np.array([d['target_temp'] for d in offset_data])
        liquid_offsets = np.array([d['liquid_offset'] for d in offset_data])
        
        # Set default initial parameters if not provided
        if initial_params is None:
            if use_ambient:
                initial_params = {
                    'a': 0.003,
                    'b': -0.3,
                    'c': 6.0,
                    'ambient_coeff': 0.0
                }
            else:
                initial_params = {
                    'a': 0.003,
                    'b': -0.3,
                    'c': 6.0
                }
        
        # Define model functions
        def quadratic_model(x, a, b, c):
            """Quadratic model: y = ax² + bx + c"""
            return a * x**2 + b * x + c
        
        def quadratic_model_with_ambient(x, a, b, c, d):
            """Quadratic model with ambient correction: y = ax² + bx + c + d*(ambient-ref)"""
            target_temp, ambient_diff = x
            return a * target_temp**2 + b * target_temp + c + d * ambient_diff
        
        # Import curve_fit for parameter fitting
        from scipy.optimize import curve_fit
        
        if use_ambient:
            # Extract ambient temperatures
            if not all('ambient_temp_mean' in d for d in offset_data):
                print("Error: Ambient temperature data not available for all steps")
                use_ambient = False
            else:
                ambient_temps = np.array([d['ambient_temp_mean'] for d in offset_data])
                
                # Calculate ambient temperature differences from reference
                ambient_diffs = ambient_temps - ambient_ref
                
                # Prepare X data for curve_fit (target_temp, ambient_diff)
                X = (target_temps, ambient_diffs)
                
                # Initial parameter values
                p0 = [
                    initial_params.get('a', 0.003),
                    initial_params.get('b', -0.3),
                    initial_params.get('c', 6.0),
                    initial_params.get('ambient_coeff', 0.0)
                ]
                
                # Fit the model
                popt, pcov = curve_fit(quadratic_model_with_ambient, X, liquid_offsets, p0=p0)
                
                # Extract parameters
                a, b, c, ambient_coeff = popt
                
                # Calculate parameter errors
                perr = np.sqrt(np.diag(pcov))
                a_err, b_err, c_err, ambient_coeff_err = perr
                
                # Create result dictionary
                result = {
                    'a': a,
                    'b': b,
                    'c': c,
                    'use_ambient': True,
                    'ambient_ref': ambient_ref,
                    'ambient_coeff': ambient_coeff,
                    'a_err': a_err,
                    'b_err': b_err,
                    'c_err': c_err,
                    'ambient_coeff_err': ambient_coeff_err
                }
                
                # Calculate R² (coefficient of determination)
                model_predictions = quadratic_model_with_ambient(X, a, b, c, ambient_coeff)
                ss_total = np.sum((liquid_offsets - np.mean(liquid_offsets))**2)
                ss_residual = np.sum((liquid_offsets - model_predictions)**2)
                r_squared = 1 - (ss_residual / ss_total)
                
                # Add R² to result
                result['r_squared'] = r_squared
                
                # Calculate RMSE (root mean squared error)
                rmse = np.sqrt(np.mean((liquid_offsets - model_predictions)**2))
                result['rmse'] = rmse
                
                # Print results
                print("\nFitted parameters with ambient temperature correction:")
                print(f"  a = {a:.6f} ± {a_err:.6f}")
                print(f"  b = {b:.6f} ± {b_err:.6f}")
                print(f"  c = {c:.6f} ± {c_err:.6f}")
                print(f"  ambient_coeff = {ambient_coeff:.6f} ± {ambient_coeff_err:.6f}")
                print(f"  R² = {r_squared:.4f}")
                print(f"  RMSE = {rmse:.4f}°C")
                
        else:
            # Fit simple quadratic model
            p0 = [
                initial_params.get('a', 0.003),
                initial_params.get('b', -0.3),
                initial_params.get('c', 6.0)
            ]
            
            # Fit the model
            popt, pcov = curve_fit(quadratic_model, target_temps, liquid_offsets, p0=p0)
            
            # Extract parameters
            a, b, c = popt
            
            # Calculate parameter errors
            perr = np.sqrt(np.diag(pcov))
            a_err, b_err, c_err = perr
            
            # Create result dictionary
            result = {
                'a': a,
                'b': b,
                'c': c,
                'use_ambient': False,
                'a_err': a_err,
                'b_err': b_err,
                'c_err': c_err
            }
            
            # Calculate R² (coefficient of determination)
            model_predictions = quadratic_model(target_temps, a, b, c)
            ss_total = np.sum((liquid_offsets - np.mean(liquid_offsets))**2)
            ss_residual = np.sum((liquid_offsets - model_predictions)**2)
            r_squared = 1 - (ss_residual / ss_total)
            
            # Add R² to result
            result['r_squared'] = r_squared
            
            # Calculate RMSE (root mean squared error)
            rmse = np.sqrt(np.mean((liquid_offsets - model_predictions)**2))
            result['rmse'] = rmse
            
            # Print results
            print("\nFitted parameters without ambient temperature correction:")
            print(f"  a = {a:.6f} ± {a_err:.6f}")
            print(f"  b = {b:.6f} ± {b_err:.6f}")
            print(f"  c = {c:.6f} ± {c_err:.6f}")
            print(f"  R² = {r_squared:.4f}")
            print(f"  RMSE = {rmse:.4f}°C")
        
        return result
    
    except Exception as e:
        print(f"Error fitting correction parameters: {e}")
        import traceback
        traceback.print_exc()
        return None

def visualize_results(df, steps, offset_data, params, filename, output_dir):
    """
    Create visualization of temperature data and fitted model.
    
    Args:
        df: Full data DataFrame
        steps: List of DataFrames for each temperature step
        offset_data: List of dicts with offset data
        params: Dict with fitted parameters
        filename: Original data filename
        output_dir: Directory to save output files
        
    Returns:
        Dict with paths to output files
    """
    try:
        import matplotlib.pyplot as plt
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate base filename
        base_name = os.path.splitext(os.path.basename(filename))[0]
        
        # Create figure for overview
        plt.figure(figsize=(12, 8))
        
        # Plot temperatures
        plt.subplot(2, 1, 1)
        
        # Convert time to hours
        if 'elapsed_seconds' in df.columns:
            time_hours = df['elapsed_seconds'] / 3600
        else:
            time_hours = np.arange(len(df)) / 3600
        
        # Plot holder and liquid temperatures
        plt.plot(time_hours, df['Holder Temperature'], 'r-', label='Holder Temperature')
        plt.plot(time_hours, df['Liquid Temperature'], 'b-', label='Liquid Temperature')
        plt.plot(time_hours, df['Target Temperature'], 'g--', label='Target Temperature')
        
        # Plot room temperature if available
        if 'Room Temperature' in df.columns:
            plt.plot(time_hours, df['Room Temperature'], 'k-', label='Room Temperature')
        
        plt.xlabel('Time (hours)')
        plt.ylabel('Temperature (°C)')
        plt.title('Temperature Data Overview')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Plot power on second subplot
        plt.subplot(2, 1, 2)
        if 'Power' in df.columns:
            plt.plot(time_hours, df['Power'], 'r-')
            plt.xlabel('Time (hours)')
            plt.ylabel('Power (W)')
            plt.title('Power Consumption')
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        overview_path = os.path.join(output_dir, f"{base_name}_overview.png")
        plt.savefig(overview_path, dpi=300)
        plt.close()
        
        # Create figure for temperature offset vs target temperature
        plt.figure(figsize=(10, 8))
        
        # Extract data for plotting
        target_temps = [d['target_temp'] for d in offset_data]
        liquid_offsets = [d['liquid_offset'] for d in offset_data]
        
        # Plot data points
        plt.scatter(target_temps, liquid_offsets, c='b', marker='o', s=50, label='Measured Data')
        
        # Generate smooth curve for the model
        x_range = np.linspace(min(target_temps) - 5, max(target_temps) + 5, 100)
        
        if params and 'a' in params and 'b' in params and 'c' in params:
            # Get parameters
            a, b, c = params['a'], params['b'], params['c']
            
            # Calculate model curve
            y_model = a * x_range**2 + b * x_range + c
            
            # Plot model curve
            plt.plot(x_range, y_model, 'r-', linewidth=2, label='Fitted Model')
            
            # Add formula text
            formula_text = f"$y = {a:.6f}x^2 + {b:.6f}x + {c:.6f}$"
            r_squared_text = f"$R^2 = {params.get('r_squared', 0):.4f}$"
            rmse_text = f"RMSE = {params.get('rmse', 0):.4f}°C"
            
            plt.annotate(formula_text + "\n" + r_squared_text + "\n" + rmse_text,
                      xy=(0.05, 0.95), xycoords='axes fraction',
                      fontsize=12, ha='left', va='top',
                      bbox=dict(boxstyle='round', fc='white', alpha=0.8))
        
        plt.xlabel('Target Temperature (°C)')
        plt.ylabel('Liquid Temperature Offset (°C)')
        plt.title('Liquid Temperature Offset vs Target Temperature')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        offset_path = os.path.join(output_dir, f"{base_name}_offset_model.png")
        plt.savefig(offset_path, dpi=300)
        plt.close()
        
        # Save data for future reference
        offset_data_df = pd.DataFrame(offset_data)
        csv_path = os.path.join(output_dir, f"{base_name}_offset_data.csv")
        offset_data_df.to_csv(csv_path, index=False)
        
        return {
            'overview': overview_path,
            'offset_model': offset_path,
            'offset_data': csv_path
        }
        
    except Exception as e:
        print(f"Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()
        return {}

def analyze_temperature_data(filename, filepath=None, output_dir=None, use_ambient=False, 
                           update_config=False, config_file=None, visualize=True):
    """
    Analyze temperature data to fit correction parameters.
    
    Args:
        filename: Name of the data file
        filepath: Directory containing the file (default: None)
        output_dir: Directory for output files (default: 'data/processed')
        use_ambient: Whether to include ambient correction (default: False)
        update_config: Whether to update config file with new parameters (default: False)
        config_file: Path to config file (default: None)
        visualize: Whether to create visualizations (default: True)
        
    Returns:
        Dict with analysis results
    """
    # Set default output directory if not provided
    if output_dir is None:
        config = read_config(config_file)
        output_dir = config.get('paths', 'processed_data_dir', fallback='data/processed')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{Colors.CYAN}Analyzing temperature data: {filename}{Colors.RESET}")
    print(f"{Colors.CYAN}========================================={Colors.RESET}")
    
    # Read and filter data
    df = read_measurement_file(filename, filepath, filter_missing=True)
    if df is None or len(df) == 0:
        print(f"{Colors.RED}Error: No valid data available after filtering{Colors.RESET}")
        return None
        
    # Extract measurement settings
    settings = extract_measurement_settings(filename)
    
    # Split data into temperature steps
    steps = split_temperature_steps(df)
    if not steps:
        print(f"{Colors.RED}Error: Failed to split data into temperature steps{Colors.RESET}")
        return None
    
    # Extract offset data from each step
    offset_data = []
    for i, step_df in enumerate(steps):
        result = extract_offset_data(step_df, step_name=f"Step {i+1}")
        if result:
            offset_data.append(result)
    
    if not offset_data:
        print(f"{Colors.RED}Error: Failed to extract offset data from temperature steps{Colors.RESET}")
        return None
        
    # Fit correction parameters
    fitted_params = fit_correction_parameters(
        offset_data, 
        use_ambient=use_ambient,
        ambient_ref=20.0  # Default reference temperature
    )
    
    if not fitted_params:
        print(f"{Colors.RED}Error: Failed to fit correction parameters{Colors.RESET}")
        return None
    
    # Create visualizations if requested
    visualization_paths = {}
    if visualize:
        visualization_paths = visualize_results(
            df, steps, offset_data, fitted_params, filename, output_dir
        )
    
    # Update config file if requested
    if update_config and fitted_params:
        # Update config
        success = update_correction_parameters(fitted_params, config_file)
        if success:
            print(f"{Colors.GREEN}Updated configuration with new parameters{Colors.RESET}")
        else:
            print(f"{Colors.RED}Failed to update configuration{Colors.RESET}")
    
    # Return analysis results
    results = {
        'filename': filename,
        'settings': settings,
        'data_points': len(df),
        'temperature_steps': len(steps),
        'offset_data': offset_data,
        'fitted_params': fitted_params,
        'visualization_paths': visualization_paths,
        'config_updated': update_config and fitted_params is not None
    }
    
    return results

def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Temperature Data Analysis")
    parser.add_argument("--file", help="Name of the data file to analyze")
    parser.add_argument("--data-dir", help="Directory containing data files")
    parser.add_argument("--output-dir", help="Directory for output files")
    parser.add_argument("--config-file", help="Path to configuration file")
    parser.add_argument("--use-ambient", action="store_true", help="Include ambient temperature in the model")
    parser.add_argument("--update-config", action="store_true", help="Update configuration with fitted parameters")
    parser.add_argument("--no-visualize", action="store_true", help="Skip visualization generation")
    parser.add_argument("--log-file", help="Path to log file")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                      default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Set up logging
    log_file = args.log_file or get_default_log_file()
    setup_logger(log_file=log_file, level=getattr(logging, args.log_level))
    
    # Get default paths from config
    config = read_config(args.config_file)
    data_dir = args.data_dir or config.get('paths', 'raw_data_dir', fallback='data/raw')
    output_dir = args.output_dir or config.get('paths', 'processed_data_dir', fallback='data/processed')
    
    # Welcome message
    print(f"\n{Colors.CYAN}Temperature Data Analysis{Colors.RESET}")
    print(f"{Colors.CYAN}========================{Colors.RESET}")
    
    filename = args.file
    
    # If no file specified, allow interactive selection
    if not filename:
        selected_file, process_all, file_list = select_file_interactive(
            data_dir,
            prompt="Select a file to analyze"
        )
        
        if selected_file:
            filename = selected_file
        else:
            print(f"{Colors.RED}No file selected{Colors.RESET}")
            return 1
    
    # Analyze the selected file
    if filename:
        results = analyze_temperature_data(
            filename,
            filepath=data_dir,
            output_dir=output_dir,
            use_ambient=args.use_ambient,
            update_config=args.update_config,
            config_file=args.config_file,
            visualize=not args.no_visualize
        )
        
        if results:
            # Print summary of results
            print(f"\n{Colors.GREEN}Analysis completed{Colors.RESET}")
            
            params = results['fitted_params']
            print("\nFitted Parameters:")
            print(f"  a = {params['a']:.6f}")
            print(f"  b = {params['b']:.6f}")
            print(f"  c = {params['c']:.6f}")
            
            if params.get('use_ambient', False):
                print(f"  ambient_ref = {params['ambient_ref']:.2f}°C")
                print(f"  ambient_coeff = {params['ambient_coeff']:.6f}")
            
            print(f"  R² = {params.get('r_squared', 0):.4f}")
            print(f"  RMSE = {params.get('rmse', 0):.4f}°C")
            
            if results.get('visualization_paths'):
                print("\nOutput files:")
                for name, path in results['visualization_paths'].items():
                    print(f"  {name}: {path}")
            
            # Display the formula for calculating corrected target temperature
            a, b, c = params['a'], params['b'], params['c']
            print(f"\n{Colors.CYAN}Temperature Correction Formula:{Colors.RESET}")
            print(f"  y = {a:.6f}x² + {b:.6f}x + {c:.6f}")
            print(f"  Where y is the offset and x is the target temperature")
            print(f"  To calculate corrected target: x = (-{b:.6f} + sqrt({b:.6f}² - 4*{a:.6f}*({c:.6f}-y)))/(2*{a:.6f})")
            
            return 0
        else:
            print(f"{Colors.RED}Analysis failed{Colors.RESET}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())