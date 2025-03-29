#!/usr/bin/env python3
"""
Configuration Reader

This module provides functions to read and write configuration settings.
"""

import os
import configparser
import logging

# Default config file path
DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.ini')

def read_config(config_file=None):
    """
    Read configuration from file.
    
    Args:
        config_file: Path to config file (uses default if None)
        
    Returns:
        ConfigParser instance
    """
    config_file = config_file or DEFAULT_CONFIG_FILE
    
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        try:
            config.read(config_file)
            logging.info(f"Configuration loaded from {config_file}")
        except Exception as e:
            logging.error(f"Error loading configuration from {config_file}: {e}")
            # Create default config
            create_default_config(config)
    else:
        logging.warning(f"Config file {config_file} not found, using default settings")
        # Create default config
        create_default_config(config)
    
    return config

def create_default_config(config):
    """
    Create default configuration.
    
    Args:
        config: ConfigParser instance to update
    """
    config['temperature_correction'] = {
        'a': '0.0039',
        'b': '0.5645',
        'c': '4.8536'
    }
    
    config['ambient_correction'] = {
        'enabled': 'false',
        'reference_temp': '20.0',
        'coefficient': '0.0'
    }
    
    config['paths'] = {
        'data_dir': 'data',
        'raw_data_dir': 'data/raw',
        'processed_data_dir': 'data/processed'
    }

def save_config(config, config_file=None):
    """
    Save configuration to file.
    
    Args:
        config: ConfigParser instance
        config_file: Path to config file (uses default if None)
        
    Returns:
        Boolean indicating success
    """
    config_file = config_file or DEFAULT_CONFIG_FILE
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        logging.info(f"Configuration saved to {config_file}")
        return True
    except Exception as e:
        logging.error(f"Error saving configuration to {config_file}: {e}")
        return False

def get_correction_parameters(config=None):
    """
    Get temperature correction parameters from config.
    
    Args:
        config: ConfigParser instance (read from file if None)
        
    Returns:
        Dict with correction parameters
    """
    if config is None:
        config = read_config()
    
    try:
        a = config.getfloat('temperature_correction', 'a')
        b = config.getfloat('temperature_correction', 'b')
        c = config.getfloat('temperature_correction', 'c')
        
        use_ambient = config.getboolean('ambient_correction', 'enabled')
        ambient_ref = config.getfloat('ambient_correction', 'reference_temp')
        ambient_coeff = config.getfloat('ambient_correction', 'coefficient')
        
        return {
            'a': a,
            'b': b,
            'c': c,
            'use_ambient': use_ambient,
            'ambient_ref': ambient_ref,
            'ambient_coeff': ambient_coeff
        }
    except Exception as e:
        logging.error(f"Error reading correction parameters: {e}")
        return {
            'a': 0.0039,
            'b': 0.5645,
            'c': 4.8536,
            'use_ambient': False,
            'ambient_ref': 20.0,
            'ambient_coeff': 0.0
        }

def update_correction_parameters(params, config_file=None):
    """
    Update temperature correction parameters in config file.
    
    Args:
        params: Dict with parameters to update
        config_file: Path to config file (uses default if None)
        
    Returns:
        Boolean indicating success
    """
    config = read_config(config_file)
    
    try:
        # Update temperature correction parameters
        if 'a' in params:
            config.set('temperature_correction', 'a', str(params['a']))
        if 'b' in params:
            config.set('temperature_correction', 'b', str(params['b']))
        if 'c' in params:
            config.set('temperature_correction', 'c', str(params['c']))
        
        # Update ambient correction parameters
        if 'use_ambient' in params:
            config.set('ambient_correction', 'enabled', str(params['use_ambient']).lower())
        if 'ambient_ref' in params:
            config.set('ambient_correction', 'reference_temp', str(params['ambient_ref']))
        if 'ambient_coeff' in params:
            config.set('ambient_correction', 'coefficient', str(params['ambient_coeff']))
        
        # Save config file
        return save_config(config, config_file)
    except Exception as e:
        logging.error(f"Error updating correction parameters: {e}")
        return False

def save_interpolation_data(interp_data, filename=None):
    """
    Save interpolation data to a JSON file.
    
    Args:
        interp_data: Dict with interpolation data
        filename: Output file path (optional)
    
    Returns:
        Boolean indicating success
    """
    import os
    import json
    import logging
    
    # Default filename if not provided
    if filename is None:
        filename = os.path.join(os.path.dirname(DEFAULT_CONFIG_FILE), 'temp_correction_interp.json')
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    try:
        with open(filename, 'w') as f:
            json.dump(interp_data, f, indent=2)
        
        logging.info(f"Interpolation data saved to {filename}")
        return True
    
    except Exception as e:
        logging.error(f"Error saving interpolation data: {e}")
        return False

def load_interpolation_data(filename=None):
    """
    Load interpolation data from a JSON file.
    
    Args:
        filename: Input file path (optional)
    
    Returns:
        Dict with interpolation data or None if file not found or error
    """
    import os
    import json
    import logging
    
    # Default filename if not provided
    if filename is None:
        filename = os.path.join(os.path.dirname(DEFAULT_CONFIG_FILE), 'temp_correction_interp.json')
    
    try:
        if not os.path.exists(filename):
            logging.warning(f"Interpolation data file {filename} not found")
            return None
        
        with open(filename, 'r') as f:
            interp_data = json.load(f)
        
        logging.info(f"Interpolation data loaded from {filename}")
        return interp_data
    
    except Exception as e:
        logging.error(f"Error loading interpolation data: {e}")
        return None