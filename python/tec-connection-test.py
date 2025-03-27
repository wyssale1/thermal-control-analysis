#!/usr/bin/env python3
"""
Simple script to test connection to TEC controller using pyMeCom

This is a minimal script to test the connection and basic functionality
of the TEC controller with the official pyMeCom library.
"""

import sys
import time
import os

def check_mecom_installed():
    """Check if pyMeCom is properly installed and accessible."""
    try:
        # Try to import directly
        import mecom
        print("pyMeCom found in Python path")
        return True
    except ImportError:
        print("\nERROR: pyMeCom library not found in Python path.")
        
        # Check if it's installed in site-packages
        import site
        site_packages = site.getsitepackages()
        found = False
        for path in site_packages:
            if os.path.exists(os.path.join(path, 'mecom')):
                found = True
                print(f"Found mecom in {path}, but it's not in the Python path")
        
        if found:
            print("\nThe package appears to be installed but not in your Python path.")
            print("This might be because you're using a different Python environment.")
        
        # Check if we're in the pyMeCom directory
        current_dir = os.getcwd()
        if 'pyMeCom' in current_dir or os.path.exists(os.path.join(current_dir, 'mecom')):
            print("\nYou appear to be in or near the pyMeCom directory.")
            print("Try adding the directory to your Python path:")
            print("  import sys; sys.path.append('/full/path/to/pyMeCom')")
        
        print("\nTry one of these solutions:")
        print("1. Add the pyMeCom directory to your PYTHONPATH:")
        print("   export PYTHONPATH=$PYTHONPATH:/path/to/pyMeCom")
        print("2. Reinstall the package:")
        print("   pip install -e /path/to/pyMeCom")
        print("3. Run the script with the absolute path to the package:")
        
        return False


def main():
    """Main function to test TEC controller connection."""
    print("=== TEC Controller Connection Test ===")
    
    # Check if mecom is properly installed
    if not check_mecom_installed():
        # As a last resort, try to add the current directory to the path
        try:
            print("\nAttempting to add the current directory to the Python path...")
            sys.path.append(os.getcwd())
            print(f"Added {os.getcwd()} to Python path")
            
            # Try again
            try:
                import mecom
                print("Successfully imported mecom after path addition!")
            except ImportError:
                print("Still unable to import mecom. Please fix the installation.")
                return 1
        except Exception as e:
            print(f"Error adding to path: {e}")
            return 1
    
    # Get serial port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            
            print("Available ports:")
            for i, p in enumerate(ports):
                print(f"  {i+1}: {p.device} - {p.description}")
            
            port_input = input("Enter TEC controller port number or full port name: ")
            try:
                port_idx = int(port_input) - 1
                if 0 <= port_idx < len(ports):
                    port = ports[port_idx].device
                else:
                    port = port_input
            except ValueError:
                port = port_input
        except ImportError:
            print("Error: pyserial not installed. Please install it with 'pip install pyserial'")
            return 1
    
    try:
        print(f"Attempting to connect to TEC controller on {port}...")
        
        # Try to import MeerstetterTEC
        try:
            from mecom import MeerstetterTEC
        except ImportError as e:
            print(f"\nERROR importing MeerstetterTEC: {e}")
            print("Trying a direct import from current directory...")
            
            # Try a direct import as a last resort
            try:
                sys.path.append(os.path.join(os.getcwd(), '..'))
                from mecom.mecom import MeCom
                print("Successfully imported MeCom directly!")
                
                # Define a minimal MeerstetterTEC class for testing
                class MeerstetterTEC:
                    def __init__(self, port=None, scan_timeout=30, channel=1):
                        self.port = port
                        self.channel = channel
                        self._session = MeCom(serialport=port)
                        self.address = self._session.identify()
                        
                    def identify(self):
                        return self.address
                        
                    def get_parameter(self, parameter_name, address=1):
                        return self._session.get_parameter(parameter_name=parameter_name, address=address)
                        
                    def _tearDown(self):
                        self._session.stop()
            except ImportError as e2:
                print(f"Error with direct import: {e2}")
                print("\nPlease make sure pyMeCom is correctly installed:")
                print("  1. Clone the repository: git clone https://github.com/meerstetter/pyMeCom.git")
                print("  2. Navigate to the directory: cd pyMeCom")
                print("  3. Install the package: pip install -e .")
                return 1
        
        # Create TEC controller instance
        mc = MeerstetterTEC(port=port)
        
        # Get device address and status
        try:
            address = mc.identify()
            print(f"\nSUCCESS: Connected to TEC controller at address: {address}")
            
            # Get object temperature
            try:
                temp = mc.get_parameter(parameter_name="Object Temperature", address=address)
                print(f"Current object temperature: {temp}°C")
            except Exception as e:
                print(f"Error getting temperature: {e}")
            
            # Try to close connection
            try:
                mc._tearDown()
                print("\nConnection closed successfully.")
            except Exception as e:
                print(f"Error closing connection: {e}")
                
            return 0
            
        except Exception as e:
            print(f"\nERROR during communication: {e}")
            try:
                mc._tearDown()
            except:
                pass
            return 1
            
    except Exception as e:
        print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())