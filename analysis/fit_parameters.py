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