#!/usr/bin/env python3
"""
Simple Temperature Visualization

A minimal script that shows just the target temperature (with ±0.5°C range) and liquid temperature.
Designed for quick assessment of temperature control performance.
"""

import os
import sys
import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Add parent directory to path to allow imports from the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from thermal_control.utils.logger import Colors, setup_logger, get_default_log_file
from thermal_control.utils.config_reader import read_config
from analysis.utils.file_selection import select_file_interactive, list_available_files

def plot_simple_temperature(filename, filepath=None, output_file=None):
    """
    Create a simple plot showing target temperature (with ±0.5°C range) and liquid temperature.
    
    Args:
        filename: CSV file to read
        filepath: Directory containing the file (optional)
        output_file: Where to save the plot (optional)
    """
    # Construct full path
    full_path = os.path.join(filepath, filename) if filepath else filename
    
    try:
        # Read data
        df = pd.read_csv(full_path)
        
        # Try to standardize column names
        column_mapping = {
            'Time': ['Time', 'time', 'timestamp', 'Timestamp', 'elapsed_seconds'],
            'Target Temperature': ['Target Temperature', 'target_temp', 'targetTemp', 'Target Temp', 'target'],
            'Liquid Temperature': ['Liquid Temperature', 'liquid_temp', 'liquidTemp', 'Liquid Temp', 'liquid'],
            'Desired Liquid Temperature': ['Desired Liquid Temperature', 'desired_liquid_temp', 'desiredTemp']
        }
        
        # Create standardized DataFrame
        data = pd.DataFrame()
        
        # Find and map columns
        for std_name, variations in column_mapping.items():
            for col in df.columns:
                if col in variations or any(var.lower() in col.lower() for var in variations):
                    data[std_name] = df[col]
                    break
        
        # Ensure required columns exist
        required_cols = ['Time', 'Target Temperature', 'Liquid Temperature']
        missing = [col for col in required_cols if col not in data.columns]
        if missing:
            print(f"Error: Missing required columns: {', '.join(missing)}")
            return
        
        # Convert time to hours if numeric
        if pd.api.types.is_numeric_dtype(data['Time']):
            time_hours = data['Time'] / 3600  # Convert seconds to hours
        else:
            # Try to parse as datetime, otherwise use row indices
            try:
                time_hours = pd.to_datetime(data['Time'])
                time_hours = (time_hours - time_hours.iloc[0]).dt.total_seconds() / 3600
            except:
                time_hours = np.arange(len(data)) / 60  # Use minutes if can't convert
        
        # Create figure
        plt.figure(figsize=(12, 6))
        
        # Plot target vs. desired temperature
        # If desired liquid temperature is available, use it as the reference
        if 'Desired Liquid Temperature' in data.columns and not data['Desired Liquid Temperature'].isna().all():
            reference_temp = data['Desired Liquid Temperature']
            plt.plot(time_hours, reference_temp, 'g--', linewidth=2, label='Desired Liquid Temperature')
            plt.fill_between(time_hours, 
                         reference_temp - 0.5, 
                         reference_temp + 0.5, 
                         color='g', alpha=0.2, label='Target Range (±0.5°C)')
            # Show original target temperature as a reference
            plt.plot(time_hours, data['Target Temperature'], 'y--', linewidth=1, label='Target Holder Temperature')
        else:
            # Fall back to using target temperature
            reference_temp = data['Target Temperature']
            plt.plot(time_hours, reference_temp, 'g--', linewidth=2, label='Target Temperature')
            plt.fill_between(time_hours, 
                         reference_temp - 0.5, 
                         reference_temp + 0.5, 
                         color='g', alpha=0.2, label='Target Range (±0.5°C)')
        
        # Plot liquid temperature
        plt.plot(time_hours, data['Liquid Temperature'], 'b-', linewidth=2, label='Liquid Temperature')
        
        # Set labels and title
        plt.xlabel('Time (hours)')
        plt.ylabel('Temperature (°C)')
        
        # Extract information from filename if available
        title = "Temperature Control Performance"
        filename_parts = os.path.basename(filename).split('_')
        if len(filename_parts) >= 3:
            try:
                # Try to extract temperature information from filename
                target_info = "_".join(filename_parts[2:5])
                title = f"Temperature Control: {target_info}"
            except:
                pass
                
        plt.title(title)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Calculate statistics for the stable region (last 20% of data)
        stable_idx = int(0.8 * len(data))
        stable_data = data.iloc[stable_idx:]
        
        target_mean = stable_data['Target Temperature'].mean()
        liquid_mean = stable_data['Liquid Temperature'].mean()
        liquid_std = stable_data['Liquid Temperature'].std()
        
        # Add annotation with statistics
        if 'Desired Liquid Temperature' in data.columns and not data['Desired Liquid Temperature'].isna().all():
            desired_mean = stable_data['Desired Liquid Temperature'].mean()
            stats_text = (
                f"Stable region statistics:\n"
                f"Desired liquid: {desired_mean:.2f}°C\n"
                f"Actual liquid: {liquid_mean:.2f} ± {liquid_std:.3f}°C\n"
                f"Deviation: {liquid_mean - desired_mean:.2f}°C\n"
                f"Holder target: {target_mean:.2f}°C"
            )
        else:
            stats_text = (
                f"Stable region statistics:\n"
                f"Target: {target_mean:.2f}°C\n"
                f"Liquid: {liquid_mean:.2f} ± {liquid_std:.3f}°C\n"
                f"Offset: {liquid_mean - target_mean:.2f}°C"
            )
        
        plt.text(0.02, 0.02, stats_text, transform=plt.gca().transAxes, fontsize=10,
                 bbox=dict(facecolor='white', alpha=0.7))
        
        # Tight layout
        plt.tight_layout()
        
        # Save or show
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {output_file}")
        else:
            plt.show()
            
    except Exception as e:
        print(f"Error: {e}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Simple temperature visualization")
    parser.add_argument("--file", help="CSV file to visualize")
    parser.add_argument("--dir", help="Directory containing data files")
    parser.add_argument("--output", help="Output file path for the plot")
    parser.add_argument("--log-file", help="Path to log file")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Set up logging
    log_file = args.log_file or get_default_log_file()
    setup_logger(log_file=log_file, level=getattr(logging, args.log_level))
    
    # Get default paths from config
    config = read_config()
    data_dir = args.dir or config.get('paths', 'raw_data_dir', fallback='data/raw')
    
    # Welcome message
    print(f"\n{Colors.CYAN}Simple Temperature Visualization{Colors.RESET}")
    print(f"{Colors.CYAN}================================{Colors.RESET}")
    
    filename = args.file
    
    # If no file specified, allow interactive selection
    if not filename:
        selected_file, _, _ = select_file_interactive(
            data_dir, 
            prompt="Select a file to visualize"
        )
        filename = selected_file
    
    if filename:
        # Determine output file path if not provided
        output_file = args.output
        if not output_file:
            # Check if user wants to save the plot
            save_plot = input("\nDo you want to save the plot? (y/n): ")
            if save_plot.lower() == 'y':
                # Auto-generate output filename
                output_dir = config.get('paths', 'processed_data_dir', fallback='data/processed')
                os.makedirs(output_dir, exist_ok=True)
                base_name = os.path.splitext(os.path.basename(filename))[0]
                output_file = os.path.join(output_dir, f"{base_name}_simple_plot.png")
        
        # Plot the data
        plot_simple_temperature(filename, data_dir, output_file)
    else:
        print(f"{Colors.YELLOW}No file selected. Exiting.{Colors.RESET}")

if __name__ == "__main__":
    main()