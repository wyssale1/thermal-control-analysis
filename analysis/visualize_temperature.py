#!/usr/bin/env python3
"""
Temperature Visualization

This module provides functions for visualizing temperature data.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import logging

def setup_plotting_style():
    """Set up the plotting style for consistent visualizations."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12
    plt.rcParams['legend.fontsize'] = 12
    plt.rcParams['figure.titlesize'] = 18

def plot_temperature_data(df, title=None, savefig=None):
    """
    Plot temperature data over time.
    
    Args:
        df: pandas.DataFrame with temperature data
        title: Title for the plot (optional)
        savefig: Path to save the figure (optional)
        
    Returns:
        matplotlib.figure.Figure
    """
    setup_plotting_style()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    # Get time values for x-axis
    time_values = df['Time'].values
    if isinstance(time_values[0], str):
        # Try to convert string timestamps to seconds
        try:
            time_values = np.array([pd.Timestamp(t).timestamp() for t in time_values])
            time_values = (time_values - time_values[0]) / 3600  # Convert to hours
            x_label = 'Time (hours)'
        except:
            # If conversion fails, use row indices
            time_values = np.arange(len(df)) / 3600
            x_label = 'Time (hours)'
    else:
        # Numeric time values, convert to hours
        time_values = time_values / 3600
        x_label = 'Time (hours)'
    
    # Plot temperature data
    ax1.plot(time_values, df['Holder Temperature'], 'r-', linewidth=2, label='Holder')
    ax1.plot(time_values, df['Liquid Temperature'], 'b-', linewidth=2, label='Liquid')
    ax1.plot(time_values, df['Target Temperature'], 'g--', linewidth=2, label='Target')
    ax1.plot(time_values, df['Room Temperature'], 'k-', linewidth=1, label='Ambient')
    ax1.plot(time_values, df['Heatsink Temperature'], 'm-', linewidth=1, label='Heatsink')
    
    # Setup axis 1
    ax1.set_ylabel('Temperature (°C)')
    ax1.legend(loc='best')
    ax1.grid(True)
    
    if title:
        ax1.set_title(title)
    else:
        ax1.set_title('Temperature vs Time')
    
    # Plot power data
    ax2.plot(time_values, df['Power'], 'r-', linewidth=2)
    ax2.set_xlabel(x_label)
    ax2.set_ylabel('Power (W)')
    ax2.grid(True)
    
    plt.tight_layout()
    
    if savefig:
        plt.savefig(savefig, dpi=300, bbox_inches='tight')
    
    return fig

def plot_temperature_step(step_df, target_temp=None, title=None, savefig=None):
    """
    Plot a single temperature step with stability analysis.
    
    Args:
        step_df: pandas.DataFrame for a single temperature step
        target_temp: Target temperature (optional)
        title: Title for the plot (optional)
        savefig: Path to save the figure (optional)
        
    Returns:
        matplotlib.figure.Figure
    """
    setup_plotting_style()
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Get time values for x-axis
    time_values = step_df['Time'].values
    if isinstance(time_values[0], str):
        # Try to convert string timestamps to seconds
        try:
            time_values = np.array([pd.Timestamp(t).timestamp() for t in time_values])
            time_values = (time_values - time_values[0]) / 60  # Convert to minutes
            x_label = 'Time (minutes)'
        except:
            # If conversion fails, use row indices
            time_values = np.arange(len(step_df)) / 60
            x_label = 'Time (minutes)'
    else:
        # Numeric time values, convert to minutes
        time_values = time_values / 60
        x_label = 'Time (minutes)'
    
    # If target temperature is not provided, use the average
    if target_temp is None:
        target_temp = step_df['Target Temperature'].mean()
    
    # Define acceptable range (±0.5°C)
    upper_bound = target_temp + 0.5
    lower_bound = target_temp - 0.5
    
    # Plot the acceptable range
    ax.fill_between(time_values, lower_bound, upper_bound, color='green', alpha=0.2, label='Target Range (±0.5°C)')
    
    # Plot temperature data
    ax.plot(time_values, step_df['Holder Temperature'], 'r-', linewidth=2, label='Holder')
    ax.plot(time_values, step_df['Liquid Temperature'], 'b-', linewidth=2, label='Liquid')
    ax.axhline(y=target_temp, color='g', linestyle='--', linewidth=2, label='Target')
    
    # Identify the stable region (last 20% of data)
    stable_idx = int(0.8 * len(step_df))
    stable_data = step_df.iloc[stable_idx:]
    
    # Calculate statistics for the stable region
    liquid_stable_mean = stable_data['Liquid Temperature'].mean()
    liquid_stable_std = stable_data['Liquid Temperature'].std()
    holder_stable_mean = stable_data['Holder Temperature'].mean()
    holder_stable_std = stable_data['Holder Temperature'].std()
    
    # Add annotation with statistics
    stats_text = (
        f"Statistics (stable region):\n"
        f"Target: {target_temp:.2f}°C (±0.5°C)\n"
        f"Liquid: {liquid_stable_mean:.2f} ± {liquid_stable_std:.3f}°C\n"
        f"Holder: {holder_stable_mean:.2f} ± {holder_stable_std:.3f}°C"
    )
    
    ax.text(0.02, 0.05, stats_text, transform=ax.transAxes, fontsize=12,
            verticalalignment='bottom', bbox={'facecolor': 'white', 'alpha': 0.7, 'pad': 10})
    
    # Setup axis
    ax.set_xlabel(x_label)
    ax.set_ylabel('Temperature (°C)')
    ax.legend(loc='upper right')
    ax.grid(True)
    
    if title:
        ax.set_title(title)
    else:
        ax.set_title(f'Temperature Step Analysis (Target: {target_temp:.2f}°C)')
    
    plt.tight_layout()
    
    if savefig:
        plt.savefig(savefig, dpi=300, bbox_inches='tight')
    
    return fig

def plot_offset_vs_temperature(data, fitted_params=None, ambient_data=False, savefig=None):
    """
    Plot liquid temperature offset vs target temperature with fitted model.
    
    Args:
        data: List of dicts with offset data
        fitted_params: Dict with fitted parameters (optional)
        ambient_data: Whether to include ambient temperature data (optional)
        savefig: Path to save the figure (optional)
        
    Returns:
        matplotlib.figure.Figure
    """
    setup_plotting_style()
    
    if ambient_data:
        fig, axs = plt.subplots(2, 2, figsize=(14, 12))
        axs = axs.flatten()
    else:
        fig, axs = plt.subplots(1, 2, figsize=(14, 6))
        axs = [axs[0], axs[1], None, None]
    
    # Extract data
    target_temps = np.array([d['target_temp'] for d in data])
    liquid_offsets = np.array([d['liquid_offset'] for d in data])
    
    if ambient_data:
        ambient_temps = np.array([d['ambient_temp_mean'] for d in data])
        # Define colormap for ambient temperature
        cmap = plt.cm.viridis
        norm = plt.Normalize(min(ambient_temps), max(ambient_temps))
    
    # Plot 1: Offset vs Target Temperature with model fit
    if ambient_data:
        sc = axs[0].scatter(target_temps, liquid_offsets, c=ambient_temps, cmap=cmap, 
                        s=80, label='Measured Data')
        cbar = plt.colorbar(sc, ax=axs[0])
        cbar.set_label('Ambient Temperature (°C)')
    else:
        axs[0].scatter(target_temps, liquid_offsets, c='b', s=80, label='Measured Data')
    
    # Add model fit if provided
    if fitted_params:
        # Create smooth curve for the model
        temp_range = np.linspace(min(target_temps) - 5, max(target_temps) + 5, 100)
        
        if 'a' in fitted_params and 'b' in fitted_params and 'c' in fitted_params:
            a, b, c = fitted_params['a'], fitted_params['b'], fitted_params['c']
            
            # Model: y = ax² + bx + c
            model_offsets = a * temp_range**2 + b * temp_range + c
            
            # Add ambient effect if available
            if ambient_data and 'ambient_ref' in fitted_params and 'ambient_coeff' in fitted_params:
                ambient_ref = fitted_params['ambient_ref']
                ambient_coeff = fitted_params['ambient_coeff']
                
                # Add curve for reference ambient
                axs[0].plot(temp_range, model_offsets, 'r-', linewidth=2, 
                         label=f'Model (Ambient={ambient_ref:.1f}°C)')
                
                # Add curves for different ambient temperatures
                for delta in [-3, 3]:
                    amb_temp = ambient_ref + delta
                    model_amb = model_offsets + ambient_coeff * delta
                    axs[0].plot(temp_range, model_amb, '--', linewidth=1.5, 
                             label=f'Model (Ambient={amb_temp:.1f}°C)')
            else:
                axs[0].plot(temp_range, model_offsets, 'r-', linewidth=2, label='Fitted Model')
            
            # Add formula text
            if ambient_data and 'ambient_coeff' in fitted_params:
                formula_text = (
                    f"$y = {a:.4f}x^2 + {b:.4f}x + {c:.4f} + {fitted_params['ambient_coeff']:.4f}(T_{{amb}} - {fitted_params['ambient_ref']:.1f})$"
                )
            else:
                formula_text = f"$y = {a:.4f}x^2 + {b:.4f}x + {c:.4f}$"
            
            axs[0].text(0.05, 0.95, formula_text, transform=axs[0].transAxes, fontsize=12,
                     verticalalignment='top', bbox={'facecolor': 'white', 'alpha': 0.7, 'pad': 10})
    
    axs[0].set_xlabel('Target Temperature (°C)')
    axs[0].set_ylabel('Liquid Temperature Offset (°C)')
    axs[0].set_title('Liquid Temperature Offset vs Target Temperature')
    axs[0].legend(loc='best')
    axs[0].grid(True)
    
    # Plot 2: Residuals if fitted_params is provided
    if fitted_params and 'a' in fitted_params and 'b' in fitted_params and 'c' in fitted_params:
        a, b, c = fitted_params['a'], fitted_params['b'], fitted_params['c']
        
        # Calculate model predictions
        model_offsets = a * target_temps**2 + b * target_temps + c
        
        # Add ambient effect if available
        if ambient_data and 'ambient_ref' in fitted_params and 'ambient_coeff' in fitted_params:
            ambient_coeff = fitted_params['ambient_coeff']
            ambient_ref = fitted_params['ambient_ref']
            for i in range(len(model_offsets)):
                model_offsets[i] += ambient_coeff * (ambient_temps[i] - ambient_ref)
        
        # Calculate residuals
        residuals = liquid_offsets - model_offsets
        
        # Plot residuals
        if ambient_data:
            sc = axs[1].scatter(target_temps, residuals, c=ambient_temps, cmap=cmap, s=80)
            cbar = plt.colorbar(sc, ax=axs[1])
            cbar.set_label('Ambient Temperature (°C)')
        else:
            axs[1].scatter(target_temps, residuals, c='r', s=80)
        
        axs[1].axhline(y=0, color='k', linestyle='--', linewidth=1)
        axs[1].set_xlabel('Target Temperature (°C)')
        axs[1].set_ylabel('Residuals (°C)')
        axs[1].set_title('Model Residuals')
        axs[1].grid(True)
        
        # Calculate RMSE
        rmse = np.sqrt(np.mean(residuals**2))
        axs[1].text(0.05, 0.05, f"RMSE: {rmse:.3f}°C", transform=axs[1].transAxes, fontsize=12,
                 verticalalignment='bottom', bbox={'facecolor': 'white', 'alpha': 0.7, 'pad': 10})
    
    # Additional plots for ambient temperature if enabled
    if ambient_data and axs[2] is not None and axs[3] is not None:
        # Plot 3: Ambient temperature vs Target Temperature
        sc = axs[2].scatter(target_temps, ambient_temps, c=liquid_offsets, cmap='coolwarm', s=80)
        cbar = plt.colorbar(sc, ax=axs[2])
        cbar.set_label('Liquid Offset (°C)')
        
        axs[2].set_xlabel('Target Temperature (°C)')
        axs[2].set_ylabel('Ambient Temperature (°C)')
        axs[2].set_title('Ambient Temperature vs Target Temperature')
        axs[2].grid(True)
        
        # Plot 4: 3D visualization if model is available
        if fitted_params and 'a' in fitted_params and 'b' in fitted_params and 'c' in fitted_params:
            from mpl_toolkits.mplot3d import Axes3D
            
            # Convert 2D axis to 3D
            ax3d = fig.add_subplot(2, 2, 4, projection='3d')
            
            # Create mesh grid for the 3D surface
            X, Y = np.meshgrid(
                np.linspace(min(target_temps) - 5, max(target_temps) + 5, 30),
                np.linspace(min(ambient_temps) - 2, max(ambient_temps) + 2, 30)
            )
            Z = np.zeros_like(X)
            
            # Calculate Z values from the model
            a, b, c = fitted_params['a'], fitted_params['b'], fitted_params['c']
            ambient_coeff = fitted_params.get('ambient_coeff', 0.0)
            ambient_ref = fitted_params.get('ambient_ref', 20.0)
            
            for i in range(Z.shape[0]):
                for j in range(Z.shape[1]):
                    target_temp = X[i, j]
                    ambient_temp = Y[i, j]
                    Z[i, j] = a * target_temp**2 + b * target_temp + c
                    
                    if ambient_coeff != 0.0:
                        Z[i, j] += ambient_coeff * (ambient_temp - ambient_ref)
            
            # Plot 3D surface
            surf = ax3d.plot_surface(X, Y, Z, cmap='viridis', alpha=0.7)
            
            # Add measured data points
            ax3d.scatter(target_temps, ambient_temps, liquid_offsets, c='r', s=50, label='Measured Data')
            
            ax3d.set_xlabel('Target Temperature (°C)')
            ax3d.set_ylabel('Ambient Temperature (°C)')
            ax3d.set_zlabel('Liquid Offset (°C)')
            ax3d.set_title('3D Model of Temperature Offset')
            
            # Add colorbar
            cbar = plt.colorbar(surf, ax=ax3d, shrink=0.5, aspect=5)
            cbar.set_label('Offset (°C)')
    
    plt.tight_layout()
    
    if savefig:
        plt.savefig(savefig, dpi=300, bbox_inches='tight')
    
    return fig

def create_analysis_report(data, steps, fitted_params, settings, output_dir):
    """
    Create a comprehensive analysis report with multiple plots.
    
    Args:
        data: pandas.DataFrame with temperature data
        steps: List of DataFrames for each temperature step
        fitted_params: Dict with fitted parameters
        settings: Dict with measurement settings
        output_dir: Directory to save the report
        
    Returns:
        Dict with paths to saved figures
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for filenames
        timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        
        # Create base filename
        if settings and settings['date'] and settings['time']:
            base_filename = f"{settings['date']}_{settings['time']}"
        else:
            base_filename = timestamp
        
        # Dictionary to store paths to saved figures
        figures = {}
        
        # 1. Plot overall temperature data
        fig_overall = plot_temperature_data(
            data, 
            title=f"Temperature Data Overview ({base_filename})",
            savefig=os.path.join(output_dir, f"{base_filename}_overview.png")
        )
        figures['overview'] = os.path.join(output_dir, f"{base_filename}_overview.png")
        plt.close(fig_overall)
        
        # 2. Plot each temperature step
        for i, step_df in enumerate(steps):
            target_temp = step_df['Target Temperature'].mean()
            fig_step = plot_temperature_step(
                step_df,
                target_temp=target_temp,
                title=f"Temperature Step {i+1} - Target: {target_temp:.2f}°C",
                savefig=os.path.join(output_dir, f"{base_filename}_step_{i+1}.png")
            )
            figures[f'step_{i+1}'] = os.path.join(output_dir, f"{base_filename}_step_{i+1}.png")
            plt.close(fig_step)
        
        # 3. Extract offset data
        offset_data = []
        for i, step_df in enumerate(steps):
            offset_result = extract_offset_data(step_df, step_name=f"Step {i+1}")
            if offset_result:
                offset_data.append(offset_result)
        
        # 4. Plot offset vs temperature
        if offset_data:
            # Check if ambient temperature data is available
            has_ambient = all('ambient_temp_mean' in d for d in offset_data)
            
            fig_offset = plot_offset_vs_temperature(
                offset_data,
                fitted_params=fitted_params,
                ambient_data=has_ambient,
                savefig=os.path.join(output_dir, f"{base_filename}_offset_analysis.png")
            )
            figures['offset_analysis'] = os.path.join(output_dir, f"{base_filename}_offset_analysis.png")
            plt.close(fig_offset)
        
        # 5. Save offset data to CSV
        if offset_data:
            df_offset = pd.DataFrame(offset_data)
            csv_path = os.path.join(output_dir, f"{base_filename}_offset_data.csv")
            df_offset.to_csv(csv_path, index=False)
            figures['offset_data_csv'] = csv_path
        
        return figures
    
    except Exception as e:
        logging.error(f"Error creating analysis report: {e}")
        return {}