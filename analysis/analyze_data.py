#!/usr/bin/env python3
"""
Temperature Data Analysis

This script analyzes temperature data to fit correction parameters and generate visualizations.
"""

import os
import sys
import argparse
import logging
import pandas as pd
from datetime import datetime

# Add parent directory to path to allow imports from the package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.utils.data_processing import (
    read_measurement_file, 
    extract_measurement_settings,
    split_temperature_steps,
    extract_offset_data
)
from analysis.visualize_temperature import (
    plot_temperature_data,
    plot_temperature_step,
    plot_offset_vs_temperature,
    create_analysis_report
)
from analysis.fit_parameters import (
    fit_correction_parameters,
    update_config_from_fitted_params,
    plot_parameter_comparison
)
from thermal_control.utils.config_reader import (
    read_config,
    get_correction_parameters
)
from thermal_control.utils.logger import (
    setup_logger,
    get_default_log_file,
    Colors
)

def analyze_temperature_data(filename, filepath=None, output_dir=None, config_file=None, 
                           update_config=False, with_ambient=False, plot_only=False):
    """
    Analyze temperature data from a file.
    
    Args:
        filename: Name of the data file
        filepath: Directory containing the file (default is None)
        output_dir: Directory for output files (default is 'data/processed')
        config_file: Path to configuration file (default is None)
        update_config: Whether to update the configuration file (default is False)
        with_ambient: Whether to include ambient temperature in the model (default is False)
        plot_only: Whether to only generate plots without fitting (default is False)
        
    Returns:
        Dict with analysis results
    """
    # Set default output directory if not provided
    if output_dir is None:
        config = read_config(config_file)
        output_dir = config.get('paths', 'processed_data_dir', fallback='data/processed')
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the data file
    df = read_measurement_file(filename, filepath)
    if df is None:
        logging.error(f"Failed to read file: {filename}")
        return None
    
    # Extract measurement settings from filename
    settings = extract_measurement_settings(filename)
    logging.info(f"Extracted settings: {settings}")
    
    # Split data into temperature steps
    steps = split_temperature_steps(df, settings)
    logging.info(f"Split data into {len(steps)} temperature steps")
    
    # Extract offset data from each step
    offset_data = []
    for i, step_df in enumerate(steps):
        offset_result = extract_offset_data(step_df, step_name=f"Step {i+1}")
        if offset_result:
            offset_data.append(offset_result)
    
    # Get current correction parameters from config
    current_params = get_correction_parameters(read_config(config_file))
    logging.info(f"Current correction parameters: {current_params}")
    
    results = {
        'filename': filename,
        'settings': settings,
        'offset_data': offset_data,
        'current_params': current_params
    }
    
    # Generate analysis report
    figures = create_analysis_report(df, steps, current_params, settings, output_dir)
    results['figures'] = figures
    
    # Fit new parameters if requested
    if not plot_only and offset_data:
        # Get ambient reference temperature (default is 20°C)
        ambient_ref = current_params.get('ambient_ref', 20.0)
        
        # Fit parameters
        fitted_params = fit_correction_parameters(
            offset_data,
            use_ambient=with_ambient,
            ambient_ref=ambient_ref,
            initial_params=current_params
        )
        results['fitted_params'] = fitted_params
        
        # Plot comparison with current parameters
        fig_comparison = plot_parameter_comparison(
            current_params,
            fitted_params,
            savefig=os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_parameter_comparison.png")
        )
        figures['parameter_comparison'] = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_parameter_comparison.png")
        
        # Update config if requested
        if update_config:
            success = update_config_from_fitted_params(fitted_params, config_file)
            results['config_updated'] = success
    
    return results

def analyze_multiple_files(file_list, filepath=None, output_dir=None, config_file=None, 
                          update_config=False, with_ambient=False, plot_only=False):
    """
    Analyze multiple temperature data files.
    
    Args:
        file_list: List of file names
        filepath: Directory containing the files (default is None)
        output_dir: Directory for output files (default is 'data/processed')
        config_file: Path to configuration file (default is None)
        update_config: Whether to update the configuration file (default is False)
        with_ambient: Whether to include ambient temperature in the model (default is False)
        plot_only: Whether to only generate plots without fitting (default is False)
        
    Returns:
        Dict with analysis results for each file
    """
    results = {}
    
    for filename in file_list:
        logging.info(f"Analyzing file: {filename}")
        
        # Analyze file
        file_results = analyze_temperature_data(
            filename,
            filepath=filepath,
            output_dir=output_dir,
            config_file=config_file,
            update_config=update_config,
            with_ambient=with_ambient,
            plot_only=plot_only
        )
        
        if file_results:
            results[filename] = file_results
    
    return results

def list_available_files(data_dir=None):
    """
    List available temperature data files.
    
    Args:
        data_dir: Directory to scan (default is 'data/raw')
        
    Returns:
        List of file names
    """
    # Set default data directory if not provided
    if data_dir is None:
        config = read_config()
        data_dir = config.get('paths', 'raw_data_dir', fallback='data/raw')
    
    # List files in directory
    if not os.path.exists(data_dir):
        logging.error(f"Data directory does not exist: {data_dir}")
        return []
    
    # List files with supported extensions
    supported_extensions = ['.csv', '.xlsx', '.xls']
    file_list = [f for f in os.listdir(data_dir) if any(f.lower().endswith(ext) for ext in supported_extensions)]
    
    return file_list

def main():
    """Main function."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Temperature Data Analysis")
    parser.add_argument("--file", help="Name of the data file to analyze")
    parser.add_argument("--data-dir", help="Directory containing data files")
    parser.add_argument("--output-dir", help="Directory for output files")
    parser.add_argument("--config-file", help="Path to configuration file")
    parser.add_argument("--all", action="store_true", help="Analyze all data files")
    parser.add_argument("--update-config", action="store_true", help="Update configuration with fitted parameters")
    parser.add_argument("--with-ambient", action="store_true", help="Include ambient temperature in the model")
    parser.add_argument("--plot-only", action="store_true", help="Only generate plots without fitting")
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
    
    # List available files if no file specified
    if not args.file and not args.all:
        print("\nAvailable data files:")
        file_list = list_available_files(data_dir)
        
        if not file_list:
            print(f"{Colors.YELLOW}No data files found in {data_dir}{Colors.RESET}")
            return 1
        
        for i, f in enumerate(file_list):
            print(f"  {i+1}: {f}")
        
        # Prompt user to select a file
        try:
            selection = input("\nSelect a file number, or 'all' to analyze all files (default: 1): ")
            
            if selection.lower() == 'all':
                args.all = True
            elif selection.strip():
                idx = int(selection) - 1
                if 0 <= idx < len(file_list):
                    args.file = file_list[idx]
                else:
                    print(f"{Colors.RED}Invalid selection: {selection}{Colors.RESET}")
                    return 1
            else:
                # Default to first file
                args.file = file_list[0]
        except ValueError:
            print(f"{Colors.RED}Invalid selection: {selection}{Colors.RESET}")
            return 1
    
    # Analyze data
    if args.all:
        # Analyze all files
        file_list = list_available_files(data_dir)
        
        if not file_list:
            print(f"{Colors.YELLOW}No data files found in {data_dir}{Colors.RESET}")
            return 1
        
        results = analyze_multiple_files(
            file_list,
            filepath=data_dir,
            output_dir=output_dir,
            config_file=args.config_file,
            update_config=args.update_config,
            with_ambient=args.with_ambient,
            plot_only=args.plot_only
        )
        
        # Print summary
        print(f"\n{Colors.GREEN}Analysis completed for {len(results)} files{Colors.RESET}")
        print(f"Results saved to {output_dir}")
        
    elif args.file:
        # Analyze single file
        results = analyze_temperature_data(
            args.file,
            filepath=data_dir,
            output_dir=output_dir,
            config_file=args.config_file,
            update_config=args.update_config,
            with_ambient=args.with_ambient,
            plot_only=args.plot_only
        )
        
        if results:
            print(f"\n{Colors.GREEN}Analysis completed{Colors.RESET}")
            
            # Print fitted parameters if available
            if 'fitted_params' in results:
                params = results['fitted_params']
                print("\nFitted parameters:")
                print(f"  a = {params['a']:.6f}")
                print(f"  b = {params['b']:.6f}")
                print(f"  c = {params['c']:.6f}")
                
                if params.get('use_ambient', False):
                    print(f"  ambient_ref = {params['ambient_ref']:.2f}°C")
                    print(f"  ambient_coeff = {params['ambient_coeff']:.6f}")
                
                if 'r_squared' in params:
                    print(f"  R² = {params['r_squared']:.4f}")
                
                if 'rmse' in params:
                    print(f"  RMSE = {params['rmse']:.4f}°C")
                
                if args.update_config and results.get('config_updated', False):
                    print(f"\n{Colors.GREEN}Configuration updated with fitted parameters{Colors.RESET}")
                elif args.update_config:
                    print(f"\n{Colors.YELLOW}Failed to update configuration{Colors.RESET}")
            
            print(f"\nResults saved to {output_dir}")
        else:
            print(f"{Colors.RED}Analysis failed{Colors.RESET}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())