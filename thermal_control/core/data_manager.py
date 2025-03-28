#!/usr/bin/env python3
"""
Data Manager

This module handles temperature data collection, storage, and export.
"""

import os
import csv
import logging
import datetime
import threading
from collections import deque

class DataManager:
    """Manages temperature data collection and storage."""
    
    def __init__(self, max_points=10000):
        """
        Initialize the data manager.
        
        Args:
            max_points: Maximum number of data points to store in memory
        """
        self.data = deque(maxlen=max_points)
        self.data_lock = threading.Lock()
        self.start_time = None
    
    def reset(self):
        """Reset data collection."""
        with self.data_lock:
            self.data.clear()
            self.start_time = datetime.datetime.now()

    def add_data_point(self, data_point):
        """
        Add a data point to the collection.
        
        Args:
            data_point: Dictionary containing temperature data
        """
        # Initialize start time if not set
        if self.start_time is None:
            self.start_time = datetime.datetime.now()
        
        # Add timestamp and elapsed time if not present
        if 'timestamp' not in data_point:
            data_point['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if 'elapsed_seconds' not in data_point and self.start_time:
            elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
            data_point['elapsed_seconds'] = elapsed
        
        with self.data_lock:
            self.data.append(data_point)
    
    def get_latest_data(self):
        """Get the latest data point."""
        with self.data_lock:
            if self.data:
                return self.data[-1]
            return None
    
    def get_all_data(self):
        """Get all collected data points."""
        with self.data_lock:
            return list(self.data)
    
    def save_to_csv(self, filename=None):
        """
        Save collected data to a CSV file.
        
        Args:
            filename: Output file path (auto-generated if None)
            
        Returns:
            Path to the saved file
        """
        if filename is None:
            # Auto-generate filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/temperature_data_{timestamp}.csv"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
        
        with self.data_lock:
            if not self.data:
                logging.warning("No data to save")
                return None
            
            try:
                # Determine fieldnames from the first data point
                fieldnames = list(self.data[0].keys())
                
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for data_point in self.data:
                        writer.writerow(data_point)
                
                logging.info(f"Data saved to {filename}")
                return filename
                
            except Exception as e:
                logging.error(f"Error saving data to {filename}: {e}")
                return None
    
    def get_summary_statistics(self, period='all'):
        """
        Calculate summary statistics from the data.
        
        Args:
            period: Time period to use ('all', 'last_minute', 'last_5_minutes', 'last_hour')
            
        Returns:
            Dictionary of statistics
        """
        with self.data_lock:
            if not self.data:
                return None
            
            # Filter data based on period
            filtered_data = self.data
            
            if period != 'all' and len(self.data) > 1:
                now = datetime.datetime.now()
                
                if period == 'last_minute':
                    cutoff = 60  # seconds
                elif period == 'last_5_minutes':
                    cutoff = 300  # seconds
                elif period == 'last_hour':
                    cutoff = 3600  # seconds
                else:
                    cutoff = None
                
                if cutoff:
                    filtered_data = [
                        d for d in self.data 
                        if d.get('elapsed_seconds', float('inf')) >= (self.data[-1].get('elapsed_seconds', 0) - cutoff)
                    ]
            
            # Calculate statistics
            stats = {}
            
            # Calculate for each temperature field
            for field in ['holder_temp', 'liquid_temp', 'ambient_temp', 'sink_temp']:
                # Get values, excluding None
                values = [d.get(field) for d in filtered_data if d.get(field) is not None]
                
                if values:
                    stats[f"{field}_mean"] = sum(values) / len(values)
                    stats[f"{field}_min"] = min(values)
                    stats[f"{field}_max"] = max(values)
                    stats[f"{field}_range"] = stats[f"{field}_max"] - stats[f"{field}_min"]
                    # Standard deviation
                    if len(values) > 1:
                        mean = stats[f"{field}_mean"]
                        variance = sum((x - mean) ** 2 for x in values) / len(values)
                        stats[f"{field}_std"] = variance ** 0.5
                    else:
                        stats[f"{field}_std"] = 0
            
            return stats