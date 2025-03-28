#!/usr/bin/env python3
"""
Simple Temperature Visualization

A minimal script that shows just the target temperature (with ±0.5°C range) and liquid temperature.
Designed for quick assessment of temperature control performance.
Enhanced with missing data handling.
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

def plot_simple_temperature(filename, filepath=None, output_file=None, interpolate=False, max_gap=10):
    """
    Create a simple plot showing target temperature (with ±0.5°C range) and liquid temperature.
    Handles missing data with optional interpolation.
    
    Args:
        filename: CSV file to read
        filepath: Directory containing the file (optional)
        output_file: Where to save the plot (optional)
        interpolate: Whether to interpolate missing liquid temperature values (default: False)
        max_gap: Maximum gap size to interpolate across (default: 10 data points)
    """
    # Construct full path
    full_path = os.path.join(filepath, filename) if filepath else filename
    
    print(f"Reading data from {full_path}")
    
    try:
        # Read data
        df = pd.read_csv(full_path)
        print(f"Successfully read data with {len(df)} rows and {len(df.columns)} columns")
        
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
            found = False
            for col in df.columns:
                if col in variations or any(var.lower() in col.lower() for var in variations):
                    data[std_name] = df[col]
                    found = True
                    print(f"Mapped column '{col}' to '{std_name}'")
                    break
            if not found and std_name != 'Desired Liquid Temperature':  # Optional column
                print(f"Warning: Could not find a match for '{std_name}'")
        
        # Ensure required columns exist
        required_cols = ['Time', 'Target Temperature']
        missing = [col for col in required_cols if col not in data.columns]
        if missing:
            print(f"Error: Missing required columns: {', '.join(missing)}")
            return
        
        # Check if Liquid Temperature exists
        has_liquid_temp = 'Liquid Temperature' in data.columns
        if not has_liquid_temp:
            print("Warning: No liquid temperature data found in file")
        
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
        
        # Create figure with two subplots - main plot and data coverage indicator
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [4, 1]})
        
        # Plot target vs. desired temperature on main plot
        # If desired liquid temperature is available, use it as the reference
        if 'Desired Liquid Temperature' in data.columns and not data['Desired Liquid Temperature'].isna().all():
            reference_temp = data['Desired Liquid Temperature']
            ax1.plot(time_hours, reference_temp, 'g--', linewidth=2, label='Desired Liquid Temperature')
            ax1.fill_between(time_hours, 
                         reference_temp - 0.5, 
                         reference_temp + 0.5, 
                         color='g', alpha=0.2, label='Target Range (±0.5°C)')
            # Show original target temperature as a reference
            ax1.plot(time_hours, data['Target Temperature'], 'y--', linewidth=1, label='Target Holder Temperature')
        else:
            # Fall back to using target temperature
            reference_temp = data['Target Temperature']
            ax1.plot(time_hours, reference_temp, 'g--', linewidth=2, label='Target Temperature')
            ax1.fill_between(time_hours, 
                         reference_temp - 0.5, 
                         reference_temp + 0.5, 
                         color='g', alpha=0.2, label='Target Range (±0.5°C)')
        
        # Plot liquid temperature if available
        if has_liquid_temp:
            # Calculate missing data statistics
            total_points = len(data)
            missing_points = data['Liquid Temperature'].isna().sum()
            missing_percentage = (missing_points / total_points) * 100
            
            print(f"Liquid temperature data: {missing_points} missing points out of {total_points} ({missing_percentage:.1f}%)")
            
            # Apply interpolation if requested
            if interpolate and missing_points > 0:
                # Create a copy to avoid warnings
                plot_data = data.copy()
                
                # Identify missing data points for visualization
                missing_mask = plot_data['Liquid Temperature'].isna()
                
                # Interpolate missing values (limited by max_gap)
                if missing_percentage < 50:  # Only interpolate if less than 50% is missing
                    # First, find the indices of missing values
                    missing_indices = np.where(missing_mask)[0]
                    
                    # Group consecutive missing indices
                    gaps = []
                    current_gap = []
                    for i in missing_indices:
                        if not current_gap or i == current_gap[-1] + 1:
                            current_gap.append(i)
                        else:
                            if current_gap:  # Only append if not empty
                                gaps.append(current_gap)
                            current_gap = [i]
                    if current_gap:
                        gaps.append(current_gap)
                    
                    print(f"Found {len(gaps)} gaps in liquid temperature data")
                    
                    # Interpolate only across gaps smaller than max_gap
                    interpolated_series = plot_data['Liquid Temperature'].copy()
                    interpolated_gaps = 0
                    
                    for gap in gaps:
                        if len(gap) <= max_gap:
                            # Get the indices right before and after the gap
                            start_idx = gap[0] - 1 if gap[0] > 0 else None
                            end_idx = gap[-1] + 1 if gap[-1] < len(plot_data) - 1 else None
                            
                            # Only interpolate if we have valid boundary points
                            if start_idx is not None and end_idx is not None:
                                if not np.isnan(plot_data['Liquid Temperature'].iloc[start_idx]) and \
                                   not np.isnan(plot_data['Liquid Temperature'].iloc[end_idx]):
                                    
                                    # Get the boundary values
                                    start_val = plot_data['Liquid Temperature'].iloc[start_idx]
                                    end_val = plot_data['Liquid Temperature'].iloc[end_idx]
                                    
                                    # Linear interpolation
                                    for i, idx in enumerate(gap):
                                        weight = (i + 1) / (len(gap) + 1)
                                        interpolated_val = start_val + weight * (end_val - start_val)
                                        interpolated_series.iloc[idx] = interpolated_val
                                    
                                    interpolated_gaps += 1
                    
                    print(f"Interpolated {interpolated_gaps} gaps in liquid temperature data")
                    
                    # Use the interpolated series for plotting
                    ax1.plot(time_hours, interpolated_series, 'b-', linewidth=2, label='Liquid Temperature (Interpolated)')
                    
                    # Also plot the original non-missing points to show actual data
                    valid_mask = ~data['Liquid Temperature'].isna()
                    ax1.scatter(time_hours[valid_mask], data.loc[valid_mask, 'Liquid Temperature'], 
                              color='blue', s=20, alpha=0.7, label='Actual Liquid Temp Points')
                else:
                    # If too much data is missing, just plot the available points
                    valid_mask = ~data['Liquid Temperature'].isna()
                    ax1.plot(time_hours[valid_mask], data.loc[valid_mask, 'Liquid Temperature'], 
                           'b-', linewidth=2, label='Liquid Temperature (Fragmented)')
            else:
                # Just plot available points without interpolation
                valid_mask = ~data['Liquid Temperature'].isna()
                # Connect non-consecutive points with line segments
                ax1.plot(time_hours[valid_mask], data.loc[valid_mask, 'Liquid Temperature'], 
                       'bo-', linewidth=2, markersize=3, label='Liquid Temperature')
            
            # Plot data coverage indicator in the smaller subplot
            coverage = ~data['Liquid Temperature'].isna()
            ax2.fill_between(time_hours, 0, 1, where=coverage, color='blue', alpha=0.7, label='Data Available')
            ax2.fill_between(time_hours, 0, 1, where=~coverage, color='red', alpha=0.7, label='Data Missing')
            ax2.set_yticks([])
            ax2.set_xlabel('Time (hours)')
            ax2.set_title(f'Liquid Temperature Data Coverage ({100-missing_percentage:.1f}% available)')
            ax2.legend(loc='upper right')
            
        else:
            ax1.text(0.5, 0.5, "No liquid temperature data available", 
                   transform=ax1.transAxes, fontsize=14, ha='center', 
                   bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))
            
            # Hide the coverage subplot if no liquid data
            ax2.set_visible(False)
        
        # Set labels and title on main plot
        ax1.set_xlabel('Time (hours)')
        ax1.set_ylabel('Temperature (°C)')
        
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
                
        ax1.set_title(title)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Calculate statistics for the stable region (last 20% of data)
        stable_idx = int(0.8 * len(data))
        stable_data = data.iloc[stable_idx:]
        
        target_mean = stable_data['Target Temperature'].mean()
        
        # Add annotation with statistics
        if 'Desired Liquid Temperature' in data.columns and not data['Desired Liquid Temperature'].isna().all():
            desired_mean = stable_data['Desired Liquid Temperature'].mean()
            stats_text = f"Stable region statistics:\n" \
                         f"Desired liquid: {desired_mean:.2f}°C\n"
                        
            # Add liquid temp stats if available for the stable region
            if has_liquid_temp and not stable_data['Liquid Temperature'].isna().all():
                liquid_valid = stable_data['Liquid Temperature'].dropna()
                if len(liquid_valid) > 0:
                    liquid_mean = liquid_valid.mean()
                    liquid_std = liquid_valid.std()
                    stats_text += f"Actual liquid: {liquid_mean:.2f} ± {liquid_std:.3f}°C\n" \
                                 f"Deviation: {liquid_mean - desired_mean:.2f}°C\n"
                else:
                    stats_text += "Actual liquid: No data in stable region\n"
            else:
                stats_text += "Actual liquid: No data available\n"
                
            stats_text += f"Holder target: {target_mean:.2f}°C"
        else:
            stats_text = f"Stable region statistics:\n" \
                         f"Target: {target_mean:.2f}°C\n"
                         
            # Add liquid temp stats if available
            if has_liquid_temp and not stable_data['Liquid Temperature'].isna().all():
                liquid_valid = stable_data['Liquid Temperature'].dropna()
                if len(liquid_valid) > 0:
                    liquid_mean = liquid_valid.mean()
                    liquid_std = liquid_valid.std()
                    stats_text += f"Liquid: {liquid_mean:.2f} ± {liquid_std:.3f}°C\n" \
                                 f"Offset: {liquid_mean - target_mean:.2f}°C"
                else:
                    stats_text += "Liquid: No data in stable region"
            else:
                stats_text += "Liquid: No data available"
        
        # Add missing data info if applicable
        if has_liquid_temp and missing_points > 0:
            stats_text += f"\n\nMissing data: {missing_points}/{total_points} points ({missing_percentage:.1f}%)"
        
        ax1.text(0.02, 0.02, stats_text, transform=ax1.transAxes, fontsize=10,
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
        import traceback
        traceback.print_exc()


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Simple temperature visualization")
    parser.add_argument("--file", help="CSV file to visualize")
    parser.add_argument("--dir", help="Directory containing data files")
    parser.add_argument("--output", help="Output file path for the plot")
    parser.add_argument("--interpolate", action="store_true", help="Interpolate missing liquid temperature values")
    parser.add_argument("--max-gap", type=int, default=10, help="Maximum gap size to interpolate across (default: 10)")
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
    print(f"Looking for data files in: {data_dir}")
    
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
                interpolate_suffix = "_interpolated" if args.interpolate else ""
                output_file = os.path.join(output_dir, f"{base_name}_simple_plot{interpolate_suffix}.png")
        
        # Ask about interpolation if not specified in arguments
        interpolate = args.interpolate
        max_gap = args.max_gap
        if not args.interpolate:
            interp_choice = input("\nInterpolate missing liquid temperature values? (y/n): ")
            if interp_choice.lower() == 'y':
                interpolate = True
                max_gap_str = input("Maximum gap size to interpolate (default: 10): ")
                if max_gap_str.strip():
                    try:
                        max_gap = int(max_gap_str)
                    except ValueError:
                        print(f"Invalid value, using default: {max_gap}")
        
        print(f"\nProcessing file: {filename}")
        print(f"Interpolation: {'Enabled (max gap=' + str(max_gap) + ')' if interpolate else 'Disabled'}")
        
        # Plot the data
        plot_simple_temperature(filename, data_dir, output_file, interpolate=interpolate, max_gap=max_gap)
    else:
        print(f"{Colors.YELLOW}No file selected. Exiting.{Colors.RESET}")

if __name__ == "__main__":
    main()