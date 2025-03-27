#!/usr/bin/env python3
"""
Simple Connection Test Script

This script tests the connections to the TEC controller and Arduino.
Just a basic verification to ensure communication is working.
"""

import serial
import time
import sys
import os

def test_arduino(port=None):
    """Test connection to Arduino and read temperatures."""
    print("\n--- Arduino Connection Test ---")
    
    if port is None:
        # Try to auto-detect Arduino port
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            arduino_port = None
            
            print("Available ports:")
            for p in ports:
                print(f"  {p.device} - {p.description}")
                if "Arduino" in p.description or "Uno" in p.description:
                    arduino_port = p.device
                    print(f"  -> Detected as Arduino")
            
            if arduino_port is None:
                print("Arduino not automatically detected. Available ports are:")
                for i, p in enumerate(ports):
                    print(f"  {i+1}: {p.device} - {p.description}")
                choice = input("Enter port number or full port name (e.g. COM3): ")
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(ports):
                        arduino_port = ports[index].device
                    else:
                        print(f"Invalid choice: {choice}")
                        return False
                except ValueError:
                    # Not a number, assume it's a port name
                    arduino_port = choice
            
            port = arduino_port
            
        except Exception as e:
            print(f"Error detecting Arduino port: {e}")
            port = input("Enter Arduino port manually (e.g. COM3): ")
    
    print(f"Connecting to Arduino on {port}...")
    
    try:
        # Connect to Arduino
        ser = serial.Serial(port, 9600, timeout=2)
        print("Connection established. Waiting for Arduino to reset...")
        time.sleep(2)  # Wait for Arduino to reset
        
        # Clear any pending data
        ser.reset_input_buffer()
        
        # Send READ command
        print("Sending READ command...")
        ser.write(b"READ\n")
        
        # Wait for response
        print("Waiting for response...")
        response = ser.readline().decode().strip()
        print(f"Response: {response}")
        
        # Parse response (expected format: "liquid_temp,ambient_temp")
        try:
            parts = response.split(',')
            if len(parts) == 2:
                liquid_temp = float(parts[0])
                ambient_temp = float(parts[1])
                print(f"Liquid Temperature: {liquid_temp:.2f}°C")
                print(f"Ambient Temperature: {ambient_temp:.2f}°C")
            else:
                print(f"Unexpected response format: {response}")
        except Exception as e:
            print(f"Error parsing temperatures: {e}")
        
        # Close connection
        ser.close()
        print("Arduino test completed successfully")
        return True
        
    except Exception as e:
        print(f"Arduino connection failed: {e}")
        return False

def test_tec_controller_raw(port=None):
    """Test connection to TEC controller using direct serial communication."""
    print("\n--- TEC Controller Connection Test (Raw Serial) ---")
    
    if port is None:
        # Try to auto-detect TEC controller port
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            tec_port = None
            
            print("Available ports:")
            for p in ports:
                print(f"  {p.device} - {p.description}")
                if "USB" in p.description and "Serial" in p.description:
                    tec_port = p.device
                    print(f"  -> Potential TEC controller")
            
            if tec_port is None:
                print("TEC controller not automatically detected. Available ports are:")
                for i, p in enumerate(ports):
                    print(f"  {i+1}: {p.device} - {p.description}")
                choice = input("Enter port number or full port name (e.g. COM3): ")
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(ports):
                        tec_port = ports[index].device
                    else:
                        print(f"Invalid choice: {choice}")
                        return False
                except ValueError:
                    # Not a number, assume it's a port name
                    tec_port = choice
            
            port = tec_port
            
        except Exception as e:
            print(f"Error detecting TEC controller port: {e}")
            port = input("Enter TEC controller port manually (e.g. COM3): ")
    
    print(f"Connecting to TEC controller on {port}...")
    
    try:
        # Connect to TEC controller
        ser = serial.Serial(
            port=port,
            baudrate=57600,  # Default baud rate for Meerstetter
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        print("Connection established")
        
        # Send a query command for device address (Query param 0 on device 0)
        query_command = "00;01;00\r\n"
        print(f"Sending command: {query_command.strip()}")
        ser.write(query_command.encode())
        
        # Wait for response
        time.sleep(0.1)
        response = ser.readline().decode().strip()
        print(f"Response: {response}")
        
        if response:
            print("TEC controller communication successful")
            
            # Try reading object temperature (param 1000)
            query_temp = "01;01;1000\r\n"
            print(f"Reading object temperature, sending: {query_temp.strip()}")
            ser.write(query_temp.encode())
            time.sleep(0.1)
            response = ser.readline().decode().strip()
            print(f"Response: {response}")
            
            try:
                # Parse response (format should be "01;01;1000;temperature")
                parts = response.split(';')
                if len(parts) >= 4:
                    temp = float(parts[3])
                    print(f"Object Temperature: {temp:.2f}°C")
                else:
                    print(f"Unexpected response format: {response}")
            except Exception as e:
                print(f"Error parsing temperature: {e}")
        
        # Close connection
        ser.close()
        print("TEC controller test completed")
        return True
        
    except Exception as e:
        print(f"TEC controller connection failed: {e}")
        return False

def test_tec_controller_mecom(port=None):
    """Test connection to TEC controller using pyMeCom library (if available)."""
    print("\n--- TEC Controller Connection Test (pyMeCom) ---")
    
    try:
        import mecom
        print("pyMeCom library found")
    except ImportError:
        print("pyMeCom library not found. Skipping this test.")
        print("To install pyMeCom, follow the instructions in the README.")
        return False
    
    if port is None:
        # Try to auto-detect TEC controller port
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            tec_port = None
            
            print("Available ports:")
            for p in ports:
                print(f"  {p.device} - {p.description}")
                if "USB" in p.description and "Serial" in p.description:
                    tec_port = p.device
                    print(f"  -> Potential TEC controller")
            
            if tec_port is None:
                print("TEC controller not automatically detected. Available ports are:")
                for i, p in enumerate(ports):
                    print(f"  {i+1}: {p.device} - {p.description}")
                choice = input("Enter port number or full port name (e.g. COM3): ")
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(ports):
                        tec_port = ports[index].device
                    else:
                        print(f"Invalid choice: {choice}")
                        return False
                except ValueError:
                    # Not a number, assume it's a port name
                    tec_port = choice
            
            port = tec_port
            
        except Exception as e:
            print(f"Error detecting TEC controller port: {e}")
            port = input("Enter TEC controller port manually (e.g. COM3): ")
    
    print(f"Connecting to TEC controller on {port} using pyMeCom...")
    
    try:
        # Connect using pyMeCom
        tec = mecom.MeCom(port, address=1)
        print("Connection established")
        
        # Get device status
        try:
            status = tec.get_device_status()
            print(f"Device status: {status}")
        except Exception as e:
            print(f"Error getting device status: {e}")
        
        # Read some basic parameters
        try:
            # Read Object Temperature (Parameter 1000)
            object_temp = tec.get_parameter(1000)
            print(f"Object Temperature: {object_temp:.2f}°C")
            
            # Read Target Temperature (Parameter 1010)
            target_temp = tec.get_parameter(1010)
            print(f"Target Temperature: {target_temp:.2f}°C")
            
            # Read Sink Temperature (Parameter 1001)
            sink_temp = tec.get_parameter(1001)
            print(f"Sink Temperature: {sink_temp:.2f}°C")
        except Exception as e:
            print(f"Error reading temperatures: {e}")
        
        # Close connection
        tec.close()
        print("TEC controller test with pyMeCom completed successfully")
        return True
        
    except Exception as e:
        print(f"TEC controller connection with pyMeCom failed: {e}")
        return False

def main():
    """Main function that runs all tests."""
    print("=== Simple Connection Test Script ===")
    print("This script tests communication with the TEC controller and Arduino.")
    
    # Check if specific ports are provided as arguments
    tec_port = None
    arduino_port = None
    
    if len(sys.argv) > 1:
        tec_port = sys.argv[1]
    if len(sys.argv) > 2:
        arduino_port = sys.argv[2]
    
    # Run the tests
    print("\nRunning tests...")
    
    # Test TEC controller with raw serial first (doesn't require pyMeCom)
    tec_raw_success = test_tec_controller_raw(tec_port)
    
    # Test TEC controller with pyMeCom if available
    tec_mecom_success = test_tec_controller_mecom(tec_port)
    
    # Test Arduino
    arduino_success = test_arduino(arduino_port)
    
    # Print summary
    print("\n=== Test Results Summary ===")
    print(f"TEC Controller (Raw Serial): {'SUCCESS' if tec_raw_success else 'FAILED'}")
    print(f"TEC Controller (pyMeCom):    {'SUCCESS' if tec_mecom_success else 'NOT TESTED/FAILED'}")
    print(f"Arduino:                     {'SUCCESS' if arduino_success else 'FAILED'}")
    
    if tec_raw_success and arduino_success:
        print("\nAll necessary connections are working!")
        print("You can now proceed to using the full temperature control script.")
    else:
        print("\nSome connections failed. Please check your setup and try again.")

if __name__ == "__main__":
    main()