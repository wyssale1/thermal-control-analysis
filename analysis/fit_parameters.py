#!/usr/bin/env python3
"""
Parameter Fitting

This module provides functions for fitting temperature correction parameters.
"""

import os
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import logging
import matplotlib.pyplot as plt
from thermal_control.utils.config_reader import update_correction_parameters

def quadratic_model(x, a, b, c):
    """
    Quadratic model function: y = ax² + bx + c
    
    Args:
        x: Input values
        a, b, c: Model parameters
        
    Returns:
        Model predictions
    """
    return a * x**2 + b * x + c

def quadratic_model_with_ambient(x, a, b, c, d):
    """
    Quadratic model with ambient correction: y = ax² + bx + c + d*(ambient - ref)
    
    Args:
        x: Input values as tuple (target_temp, ambient_temp - ref_temp)
        a, b, c, d: Model parameters
        
    Returns:
        Model predictions
    """
    target_temp, ambient_diff = x
    return a * target_temp**2 + b * target_temp + c + d * ambient_diff

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
        
        if use_ambient:
            # Extract ambient temperatures
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
            
            # Log results
            logging.info("Fitted parameters with ambient temperature correction:")
            logging.info(f"  a = {a:.6f} ± {a_err:.6f}")
            logging.info(f"  b = {b:.6f} ± {b_err:.6f}")
            logging.info(f"  c = {c:.6f} ± {c_err:.6f}")
            logging.info(f"  ambient_coeff = {ambient_coeff:.6f} ± {ambient_coeff_err:.6f}")
            logging.info(f"  R² = {r_squared:.4f}")
            logging.info(f"  RMSE = {rmse:.4f}°C")
            
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
            
            # Log results
            logging.info("Fitted parameters without ambient temperature correction:")
            logging.info(f"  a = {a:.6f} ± {a_err:.6f}")
            logging.info(f"  b = {b:.6f} ± {b_err:.6f}")
            logging.info(f"  c = {c:.6f} ± {c_err:.6f}")
            logging.info(f"  R² = {r_squared:.4f}")
            logging.info(f"  RMSE = {rmse:.4f}°C")
        
        return result
    
    except Exception as e:
        logging.error(f"Error fitting correction parameters: {e}")
        
        # Return default parameters
        if use_ambient:
            return {
                'a': initial_params.get('a', 0.003),
                'b': initial_params.get('b', -0.3),
                'c': initial_params.get('c', 6.0),
                'use_ambient': True,
                'ambient_ref': ambient_ref,
                'ambient_coeff': initial_params.get('ambient_coeff', 0.0)
            }
        else:
            return {
                'a': initial_params.get('a', 0.003),
                'b': initial_params.get('b', -0.3),
                'c': initial_params.get('c', 6.0),
                'use_ambient': False
            }

def create_interpolation_model(offset_data):
    """
    Create an interpolation model from temperature offset data.
    
    Args:
        offset_data: List of dicts with offset data
        
    Returns:
        Dict with interpolation data and statistics
    """
    import numpy as np
    from scipy.interpolate import interp1d
    
    # Extract target temperatures and liquid offsets
    target_temps = np.array([d['target_temp'] for d in offset_data])
    liquid_offsets = np.array([d['liquid_offset'] for d in offset_data])
    
    # Sort data by target temperature
    sorted_indices = np.argsort(target_temps)
    target_temps = target_temps[sorted_indices]
    liquid_offsets = liquid_offsets[sorted_indices]
    
    # Create interpolation model using scipy
    # Check if we have enough points for cubic interpolation
    kind = 'cubic' if len(target_temps) >= 4 else 'linear'
    
    # Create interpolation function
    interp_func = interp1d(target_temps, liquid_offsets, kind=kind, 
                          bounds_error=False, fill_value='extrapolate')
    
    # Calculate metrics to evaluate the model
    # Test the interpolation on the original data points
    predicted_offsets = interp_func(target_temps)
    
    # Calculate RMSE (root mean squared error)
    rmse = np.sqrt(np.mean((liquid_offsets - predicted_offsets)**2))
    
    # Calculate R² (coefficient of determination)
    ss_total = np.sum((liquid_offsets - np.mean(liquid_offsets))**2)
    ss_residual = np.sum((liquid_offsets - predicted_offsets)**2)
    r_squared = 1 - (ss_residual / ss_total)
    
    # Store interpolation data
    interp_data = {
        'target_temps': target_temps.tolist(),  # Convert numpy arrays to lists for JSON serialization
        'liquid_offsets': liquid_offsets.tolist(),
        'interp_kind': kind,
        'temp_min': float(np.min(target_temps)),
        'temp_max': float(np.max(target_temps)),
        'rmse': float(rmse),
        'r_squared': float(r_squared)
    }
    
    # Print results
    print("\nCreated interpolation model:")
    print(f"  Interpolation type: {kind}")
    print(f"  Temperature range: {interp_data['temp_min']:.2f}°C to {interp_data['temp_max']:.2f}°C")
    print(f"  Number of data points: {len(target_temps)}")
    print(f"  R² = {r_squared:.4f}")
    print(f"  RMSE = {rmse:.4f}°C")
    
    return interp_data

def update_config_from_fitted_params(fitted_params, config_file=None):
    """
    Update configuration file with fitted parameters.
    
    Args:
        fitted_params: Dict with fitted parameters
        config_file: Path to config file (optional)
        
    Returns:
        Boolean indicating success
    """
    # Check if parameters are valid
    if 'a' not in fitted_params or 'b' not in fitted_params or 'c' not in fitted_params:
        logging.error("Missing required parameters (a, b, c)")
        return False
    
    # Convert parameters to right format for update_correction_parameters
    params = {
        'a': fitted_params['a'],
        'b': fitted_params['b'],
        'c': fitted_params['c']
    }
    
    # Add ambient correction parameters if available
    if fitted_params.get('use_ambient', False):
        params['use_ambient'] = True
        
        if 'ambient_ref' in fitted_params:
            params['ambient_ref'] = fitted_params['ambient_ref']
        if 'ambient_coeff' in fitted_params:
            params['ambient_coeff'] = fitted_params['ambient_coeff']
    else:
        params['use_ambient'] = False
    
    # Update the configuration file
    success = update_correction_parameters(params, config_file)
    
    if success:
        logging.info("Updated configuration with fitted parameters")
    else:
        logging.error("Failed to update configuration")
    
    return success

def compare_parameters(old_params, new_params):
    """
    Compare old and new parameter sets.
    
    Args:
        old_params: Dict with old parameters
        new_params: Dict with new parameters
        
    Returns:
        Dict with parameter changes
    """
    changes = {}
    
    # Compare basic parameters
    for param in ['a', 'b', 'c']:
        if param in old_params and param in new_params:
            old_val = old_params[param]
            new_val = new_params[param]
            diff = new_val - old_val
            pct_change = (diff / old_val) * 100 if old_val != 0 else float('inf')
            
            changes[param] = {
                'old': old_val,
                'new': new_val,
                'diff': diff,
                'pct_change': pct_change
            }
    
    # Compare ambient correction parameters
    if 'use_ambient' in old_params and 'use_ambient' in new_params:
        changes['use_ambient'] = {
            'old': old_params['use_ambient'],
            'new': new_params['use_ambient']
        }
        
        if old_params.get('use_ambient', False) and new_params.get('use_ambient', False):
            for param in ['ambient_ref', 'ambient_coeff']:
                if param in old_params and param in new_params:
                    old_val = old_params[param]
                    new_val = new_params[param]
                    diff = new_val - old_val
                    pct_change = (diff / old_val) * 100 if old_val != 0 else float('inf')
                    
                    changes[param] = {
                        'old': old_val,
                        'new': new_val,
                        'diff': diff,
                        'pct_change': pct_change
                    }
    
    return changes

def plot_parameter_comparison(old_params, new_params, savefig=None):
    """
    Plot comparison between old and new parameter sets.
    
    Args:
        old_params: Dict with old parameters
        new_params: Dict with new parameters
        savefig: Path to save the figure (optional)
        
    Returns:
        matplotlib.figure.Figure
    """
    # Get parameter changes
    changes = compare_parameters(old_params, new_params)
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Plot 1: Compare correction formulas
    temp_range = np.linspace(5, 50, 100)
    
    # Calculate old model
    if 'a' in old_params and 'b' in old_params and 'c' in old_params:
        old_offsets = quadratic_model(temp_range, old_params['a'], old_params['b'], old_params['c'])
        ax1.plot(temp_range, old_offsets, 'b-', linewidth=2, label='Old Model')
    
    # Calculate new model
    if 'a' in new_params and 'b' in new_params and 'c' in new_params:
        new_offsets = quadratic_model(temp_range, new_params['a'], new_params['b'], new_params['c'])
        ax1.plot(temp_range, new_offsets, 'r-', linewidth=2, label='New Model')
    
    ax1.set_xlabel('Target Temperature (°C)')
    ax1.set_ylabel('Liquid Temperature Offset (°C)')
    ax1.set_title('Comparison of Correction Models')
    ax1.legend(loc='best')
    ax1.grid(True)
    
    # Plot 2: Parameter changes
    param_names = []
    param_changes = []
    
    for param in ['a', 'b', 'c']:
        if param in changes:
            param_names.append(param)
            param_changes.append(changes[param]['pct_change'])
    
    # Add ambient correction parameters if available
    if 'ambient_coeff' in changes:
        param_names.append('ambient_coeff')
        param_changes.append(changes['ambient_coeff']['pct_change'])
    
    # Convert to numpy arrays
    param_names = np.array(param_names)
    param_changes = np.array(param_changes)
    
    # Create bar colors based on change direction
    colors = ['g' if c > 0 else 'r' for c in param_changes]
    
    # Plot the bars
    bars = ax2.bar(param_names, param_changes, color=colors)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            vert_align = 'bottom'
            y_pos = height + 0.5
        else:
            vert_align = 'top'
            y_pos = height - 0.5
        
        ax2.text(bar.get_x() + bar.get_width()/2., y_pos,
                f'{height:.1f}%', ha='center', va=vert_align)
    
    ax2.set_xlabel('Parameter')
    ax2.set_ylabel('Percent Change (%)')
    ax2.set_title('Parameter Changes')
    ax2.grid(True, axis='y')
    
    # Add a horizontal line at y=0
    ax2.axhline(y=0, color='k', linestyle='-', alpha=0.3)
    
    # Add text with exact parameter values
    text_lines = []
    
    for param in ['a', 'b', 'c']:
        if param in changes:
            text_lines.append(f"{param}: {changes[param]['old']:.6f} → {changes[param]['new']:.6f}")
    
    if 'ambient_coeff' in changes:
        text_lines.append(f"ambient_coeff: {changes['ambient_coeff']['old']:.6f} → {changes['ambient_coeff']['new']:.6f}")
    
    if 'ambient_ref' in changes:
        text_lines.append(f"ambient_ref: {changes['ambient_ref']['old']:.1f} → {changes['ambient_ref']['new']:.1f}")
    
    if 'use_ambient' in changes:
        text_lines.append(f"use_ambient: {changes['use_ambient']['old']} → {changes['use_ambient']['new']}")
    
    if 'r_squared' in new_params:
        text_lines.append(f"R²: {new_params['r_squared']:.4f}")
    
    if 'rmse' in new_params:
        text_lines.append(f"RMSE: {new_params['rmse']:.4f}°C")
    
    ax2.text(0.02, 0.02, '\n'.join(text_lines), transform=ax2.transAxes, fontsize=10,
             verticalalignment='bottom', bbox={'facecolor': 'white', 'alpha': 0.7, 'pad': 10})
    
    plt.tight_layout()
    
    if savefig:
        plt.savefig(savefig, dpi=300, bbox_inches='tight')
    
    return fig

def visualize_interpolation(offset_data, interp_data, filename, output_dir):
    """
    Create visualizations of the interpolation model.
    
    Args:
        offset_data: List of dicts with offset data
        interp_data: Dict with interpolation data
        filename: Original data filename
        output_dir: Directory to save output files
        
    Returns:
        Dict with paths to output files
    """
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.interpolate import interp1d
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate base filename
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    # Extract data for plotting
    target_temps = np.array(interp_data['target_temps'])
    liquid_offsets = np.array(interp_data['liquid_offsets'])
    kind = interp_data.get('interp_kind', 'linear')
    
    # Create figure
    plt.figure(figsize=(12, 8))
    
    # Plot measured data points
    plt.scatter(target_temps, liquid_offsets, c='b', marker='o', s=70, 
               label='Measured Data Points', zorder=3)
    
    # Create interpolation function
    interp_func = interp1d(target_temps, liquid_offsets, kind=kind, 
                          bounds_error=False, fill_value='extrapolate')
    
    # Generate smooth curve for visualization
    x_smooth = np.linspace(min(target_temps) - 2, max(target_temps) + 2, 500)
    y_smooth = interp_func(x_smooth)
    
    # Plot interpolation curve
    plt.plot(x_smooth, y_smooth, 'r-', linewidth=2, 
            label=f'{kind.capitalize()} Spline Interpolation', zorder=2)
    
    # Plot zero-offset line
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.5, zorder=1)
    
    # Add labels and title
    plt.xlabel('Target Temperature (°C)', fontsize=12)
    plt.ylabel('Liquid Temperature Offset (°C)', fontsize=12)
    plt.title('Temperature Correction: Interpolation Model', fontsize=14)
    
    # Add statistics text
    stats_text = (
        f"Interpolation type: {kind}\n"
        f"Data points: {len(target_temps)}\n"
        f"Temperature range: {interp_data['temp_min']:.1f}°C to {interp_data['temp_max']:.1f}°C\n"
        f"R² = {interp_data.get('r_squared', 0):.4f}\n"
        f"RMSE = {interp_data.get('rmse', 0):.4f}°C"
    )
    
    plt.annotate(stats_text, xy=(0.02, 0.02), xycoords='axes fraction',
                fontsize=10, ha='left', va='bottom',
                bbox=dict(boxstyle='round', fc='white', alpha=0.8))
    
    # Add legend
    plt.legend(loc='best', fontsize=10)
    
    # Add grid
    plt.grid(True, alpha=0.3, zorder=0)
    
    # Set tight layout
    plt.tight_layout()
    
    # Save figure
    interp_plot_path = os.path.join(output_dir, f"{base_name}_interp_model.png")
    plt.savefig(interp_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create a second plot showing the corrected temperatures
    plt.figure(figsize=(12, 8))
    
    # Calculate corrected temperatures
    corrected_temps = target_temps - liquid_offsets
    
    # Plot target vs corrected temperatures
    plt.scatter(target_temps, corrected_temps, c='g', marker='o', s=70,
               label='Corrected Target Temperatures', zorder=3)
    
    # Generate smooth curve
    corrected_smooth = x_smooth - interp_func(x_smooth)
    
    # Plot smooth curve
    plt.plot(x_smooth, corrected_smooth, 'g-', linewidth=2,
            label='Interpolated Correction', zorder=2)
    
    # Plot 1:1 line
    plt.plot([min(x_smooth), max(x_smooth)], [min(x_smooth), max(x_smooth)],
            'k--', alpha=0.5, label='1:1 Line (No Correction)', zorder=1)
    
    # Add labels and title
    plt.xlabel('Desired Liquid Temperature (°C)', fontsize=12)
    plt.ylabel('Corrected Holder Temperature (°C)', fontsize=12)
    plt.title('Temperature Correction: Target vs. Corrected Temperatures', fontsize=14)
    
    # Add legend
    plt.legend(loc='best', fontsize=10)
    
    # Add grid
    plt.grid(True, alpha=0.3, zorder=0)
    
    # Set tight layout
    plt.tight_layout()
    
    # Save figure
    corrected_plot_path = os.path.join(output_dir, f"{base_name}_corrected_temps.png")
    plt.savefig(corrected_plot_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'interp_model': interp_plot_path,
        'corrected_temps': corrected_plot_path
    }