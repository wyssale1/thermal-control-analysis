#!/usr/bin/env python3
"""
File Selection Utility

This module provides functions for listing and selecting data files.
"""

import os
import logging
import datetime
from thermal_control.utils.logger import Colors
from thermal_control.utils.config_reader import read_config

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
    
    # Sort files by modification time (newest first)
    file_list.sort(key=lambda x: os.path.getmtime(os.path.join(data_dir, x)), reverse=True)
    
    return file_list

def print_available_files(data_dir=None):
    """
    Print available data files with numbering.
    
    Args:
        data_dir: Directory to scan (default is 'data/raw')
        
    Returns:
        List of file names
    """
    file_list = list_available_files(data_dir)
    
    if not file_list:
        print(f"{Colors.YELLOW}No data files found in {data_dir}{Colors.RESET}")
        return []
    
    print("\nAvailable data files:")
    for i, f in enumerate(file_list):
        # Try to include modification time
        try:
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(data_dir, f)))
            mod_time_str = f" ({mod_time.strftime('%Y-%m-%d %H:%M')})"
        except:
            mod_time_str = ""
            
        print(f"  {i+1}: {f}{mod_time_str}")
    
    return file_list

def select_file_interactive(data_dir=None, prompt="Select a file number, or 'all' to process all files"):
    """
    Allow user to interactively select a file.
    
    Args:
        data_dir: Directory to scan (default is 'data/raw')
        prompt: Prompt message to display
        
    Returns:
        tuple: (selected_file, process_all, all_files)
        - selected_file: Name of selected file (or None if process_all is True)
        - process_all: Boolean indicating whether to process all files
        - all_files: List of all available files
    """
    file_list = print_available_files(data_dir)
    
    if not file_list:
        return None, False, []
    
    # Prompt user to select a file
    try:
        selection = input(f"\n{prompt} (default: 1): ")
        
        if selection.lower() == 'all':
            return None, True, file_list
        elif selection.strip():
            idx = int(selection) - 1
            if 0 <= idx < len(file_list):
                return file_list[idx], False, file_list
            else:
                print(f"{Colors.RED}Invalid selection: {selection}{Colors.RESET}")
                return None, False, file_list
        else:
            # Default to first file
            return file_list[0], False, file_list
    except ValueError:
        print(f"{Colors.RED}Invalid selection: {selection}{Colors.RESET}")
        return None, False, file_list