#!/usr/bin/env python3
"""
Interactive Mode UI

This module provides an interactive command-line interface for temperature control.
"""

import logging
from utils.logger import Colors

class InteractiveUI:
    """Interactive user interface for temperature control."""
    
    def __init__(self, temp_control, data_manager):
        """
        Initialize the interactive UI.
        
        Args:
            temp_control: TemperatureControl instance
            data_manager: DataManager instance
        """
        self.temp_control = temp_control
        self.data_manager = data_manager
        self.running = False
    
    def print_help(self):
        """Print available commands."""
        print(f"\n{Colors.CYAN}Temperature Control Interactive Mode{Colors.RESET}")
        print(f"{Colors.CYAN}================================={Colors.RESET}")
        print("Available commands:")
        print(f"  {Colors.GREEN}set X{Colors.RESET}     - Set temperature to X°C (with offset correction)")
        print(f"  {Colors.GREEN}setraw X{Colors.RESET}  - Set temperature to X°C (without offset correction)")
        print(f"  {Colors.GREEN}mon{Colors.RESET}       - Start/stop monitoring")
        print(f"  {Colors.GREEN}exp X Y Z W{Colors.RESET} - Run experiment from X°C to Y°C in Z°C steps with W minutes stabilization")
        print(f"  {Colors.GREEN}expraw X Y Z W{Colors.RESET} - Run experiment without offset correction")
        print(f"  {Colors.GREEN}stop{Colors.RESET}      - Stop running experiment")
        print(f"  {Colors.GREEN}save [file]{Colors.RESET} - Save collected data to CSV file")
        print(f"  {Colors.GREEN}status{Colors.RESET}    - Show current temperatures")
        print(f"  {Colors.GREEN}stats{Colors.RESET}     - Show summary statistics")
        print(f"  {Colors.GREEN}config{Colors.RESET}    - Show/change correction parameters")
        print(f"  {Colors.GREEN}help{Colors.RESET}      - Show this help")
        print(f"  {Colors.GREEN}exit{Colors.RESET}      - Exit program")
    
    def print_status(self):
        """Print current temperature status."""
        data_point = self.temp_control.read_all_sensors()
        
        print(f"\n{Colors.CYAN}Current Temperatures:{Colors.RESET}")
        print(f"  Holder:  {data_point['holder_temp']:.2f}°C" if data_point['holder_temp'] is not None else "  Holder:  N/A")
        print(f"  Liquid:  {data_point['liquid_temp']:.2f}°C" if data_point['liquid_temp'] is not None else "  Liquid:  N/A")
        print(f"  Ambient: {data_point['ambient_temp']:.2f}°C" if data_point['ambient_temp'] is not None else "  Ambient: N/A")
        print(f"  Target:  {data_point['target_temp']:.2f}°C" if data_point['target_temp'] is not None else "  Target:  N/A")
        print(f"  Sink:    {data_point['sink_temp']:.2f}°C" if data_point['sink_temp'] is not None else "  Sink:    N/A")
        print(f"  Power:   {data_point['power']:.2f}W" if data_point['power'] is not None else "  Power:   N/A")
    
    def print_statistics(self):
        """Print summary statistics."""
        stats = self.data_manager.get_summary_statistics()
        if not stats:
            print(f"{Colors.YELLOW}No data available for statistics{Colors.RESET}")
            return
        
        print(f"\n{Colors.CYAN}Summary Statistics:{Colors.RESET}")
        print(f"  {Colors.CYAN}Holder Temperature:{Colors.RESET}")
        print(f"    Mean: {stats.get('holder_temp_mean', 'N/A'):.2f}°C")
        print(f"    Min:  {stats.get('holder_temp_min', 'N/A'):.2f}°C")
        print(f"    Max:  {stats.get('holder_temp_max', 'N/A'):.2f}°C")
        print(f"    Std:  {stats.get('holder_temp_std', 'N/A'):.3f}°C")
        
        if 'liquid_temp_mean' in stats:
            print(f"  {Colors.CYAN}Liquid Temperature:{Colors.RESET}")
            print(f"    Mean: {stats.get('liquid_temp_mean'):.2f}°C")
            print(f"    Min:  {stats.get('liquid_temp_min'):.2f}°C")
            print(f"    Max:  {stats.get('liquid_temp_max'):.2f}°C")
            print(f"    Std:  {stats.get('liquid_temp_std'):.3f}°C")
        
        if 'ambient_temp_mean' in stats:
            print(f"  {Colors.CYAN}Ambient Temperature:{Colors.RESET}")
            print(f"    Mean: {stats.get('ambient_temp_mean'):.2f}°C")
            print(f"    Min:  {stats.get('ambient_temp_min'):.2f}°C")
            print(f"    Max:  {stats.get('ambient_temp_max'):.2f}°C")
            print(f"    Std:  {stats.get('ambient_temp_std'):.3f}°C")
    
    def show_config(self):
        """Show and optionally update correction parameters."""
        print(f"\n{Colors.CYAN}Current Correction Parameters:{Colors.RESET}")
        print(f"  Formula: y = {self.temp_control.a}x² + {self.temp_control.b}x + {self.temp_control.c}")
        print(f"  Ambient correction: {'Enabled' if self.temp_control.use_ambient_correction else 'Disabled'}")
        if self.temp_control.use_ambient_correction:
            print(f"  Ambient reference: {self.temp_control.ambient_reference}°C")
            print(f"  Ambient coefficient: {self.temp_control.ambient_coefficient}")
        
        change = input("\nDo you want to change these parameters? (y/n): ")
        if change.lower() == 'y':
            try:
                a_input = input(f"Enter coefficient a [{self.temp_control.a}]: ")
                b_input = input(f"Enter coefficient b [{self.temp_control.b}]: ")
                c_input = input(f"Enter coefficient c [{self.temp_control.c}]: ")
                
                use_ambient_input = input(f"Enable ambient correction? (y/n) [{'y' if self.temp_control.use_ambient_correction else 'n'}]: ")
                
                # Update parameters
                a = float(a_input) if a_input.strip() else None
                b = float(b_input) if b_input.strip() else None
                c = float(c_input) if c_input.strip() else None
                use_ambient = use_ambient_input.lower() == 'y' if use_ambient_input.strip() else None
                
                # If ambient correction enabled, ask for additional parameters
                ambient_ref = None
                ambient_coeff = None
                if use_ambient or (use_ambient is None and self.temp_control.use_ambient_correction):
                    ambient_ref_input = input(f"Enter ambient reference temperature [{self.temp_control.ambient_reference}]: ")
                    ambient_coeff_input = input(f"Enter ambient coefficient [{self.temp_control.ambient_coefficient}]: ")
                    
                    ambient_ref = float(ambient_ref_input) if ambient_ref_input.strip() else None
                    ambient_coeff = float(ambient_coeff_input) if ambient_coeff_input.strip() else None
                
                # Update parameters
                self.temp_control.update_correction_parameters(
                    a=a, b=b, c=c, 
                    use_ambient=use_ambient, 
                    ambient_ref=ambient_ref, 
                    ambient_coeff=ambient_coeff
                )
                
                print(f"{Colors.GREEN}Parameters updated successfully{Colors.RESET}")
                
            except ValueError as e:
                print(f"{Colors.RED}Error: Invalid input - {e}{Colors.RESET}")
    
    def handle_command(self, command):
        """
        Handle a command from the user.
        
        Args:
            command: User-entered command string
            
        Returns:
            Boolean indicating whether to continue or exit
        """
        try:
            if command.lower() == 'help':
                self.print_help()
            
            elif command.lower() == 'exit':
                return False
            
            elif command.lower() == 'status':
                self.print_status()
            
            elif command.lower() == 'stats':
                self.print_statistics()
            
            elif command.lower() == 'config':
                self.show_config()
            
            elif command.lower() == 'mon':
                if self.temp_control.running:
                    self.temp_control.stop_monitoring()
                    print(f"{Colors.GREEN}Monitoring stopped{Colors.RESET}")
                else:
                    self.temp_control.start_monitoring()
                    print(f"{Colors.GREEN}Monitoring started{Colors.RESET}")
            
            elif command.lower().startswith('set '):
                try:
                    temp = float(command[4:])
                    if self.temp_control.set_temperature(temp, use_correction=True):
                        print(f"{Colors.GREEN}Temperature set to {temp:.2f}°C with correction{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}Failed to set temperature{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}Invalid temperature{Colors.RESET}")
            
            elif command.lower().startswith('setraw '):
                try:
                    temp = float(command[7:])
                    if self.temp_control.set_temperature(temp, use_correction=False):
                        print(f"{Colors.GREEN}Temperature set to {temp:.2f}°C without correction{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}Failed to set temperature{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}Invalid temperature{Colors.RESET}")
            
            elif command.lower().startswith('exp '):
                try:
                    parts = command[4:].split()
                    if len(parts) != 4:
                        print(f"{Colors.YELLOW}Usage: exp START_TEMP STOP_TEMP INCREMENT STAB_TIME{Colors.RESET}")
                        return True
                    
                    start_temp = float(parts[0])
                    stop_temp = float(parts[1])
                    increment = float(parts[2])
                    stab_time = int(parts[3])
                    
                    # Run experiment with correction
                    if self.temp_control.run_experiment(start_temp, stop_temp, increment, stab_time, use_correction=True):
                        print(f"{Colors.GREEN}Experiment completed successfully{Colors.RESET}")
                    else:
                        print(f"{Colors.YELLOW}Experiment stopped{Colors.RESET}")
                    
                except ValueError as e:
                    print(f"{Colors.RED}Invalid experiment parameters: {e}{Colors.RESET}")
            
            elif command.lower().startswith('expraw '):
                try:
                    parts = command[7:].split()
                    if len(parts) != 4:
                        print(f"{Colors.YELLOW}Usage: expraw START_TEMP STOP_TEMP INCREMENT STAB_TIME{Colors.RESET}")
                        return True
                    
                    start_temp = float(parts[0])
                    stop_temp = float(parts[1])
                    increment = float(parts[2])
                    stab_time = int(parts[3])
                    
                    # Run experiment without correction
                    if self.temp_control.run_experiment(start_temp, stop_temp, increment, stab_time, use_correction=False):
                        print(f"{Colors.GREEN}Experiment completed successfully{Colors.RESET}")
                    else:
                        print(f"{Colors.YELLOW}Experiment stopped{Colors.RESET}")
                    
                except ValueError as e:
                    print(f"{Colors.RED}Invalid experiment parameters: {e}{Colors.RESET}")
            
            elif command.lower() == 'stop':
                if self.temp_control.stop_experiment():
                    print(f"{Colors.GREEN}Experiment stopped{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}No experiment running{Colors.RESET}")
            
            elif command.lower().startswith('save'):
                parts = command.split(maxsplit=1)
                filename = parts[1] if len(parts) > 1 else None
                
                saved_file = self.data_manager.save_to_csv(filename)
                if saved_file:
                    print(f"{Colors.GREEN}Data saved to {saved_file}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}Failed to save data{Colors.RESET}")
            
            else:
                print(f"{Colors.YELLOW}Unknown command: {command}. Type 'help' for available commands.{Colors.RESET}")
        
        except Exception as e:
            logging.error(f"Error handling command: {e}")
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        
        return True
    
    def run(self):
        """Run the interactive mode."""
        self.running = True
        self.print_help()
        
        try:
            while self.running:
                command = input(f"\n{Colors.CYAN}> {Colors.RESET}").strip()
                
                if not self.handle_command(command):
                    self.running = False
        
        except KeyboardInterrupt:
            logging.info("Interactive mode interrupted")
            print(f"\n{Colors.YELLOW}Interactive mode interrupted{Colors.RESET}")
            self.running = False
        
        return True