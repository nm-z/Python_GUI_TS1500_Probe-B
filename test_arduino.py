import serial
import time

def read_response(ser, timeout=2):
    """Read response with timeout"""
    start_time = time.time()
    response = []
    
    while (time.time() - start_time) < timeout:
        if ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    print(f"← Received: {line}")
                    response.append(line)
            except UnicodeDecodeError:
                print("← Received non-text data")
        time.sleep(0.1)
    
    return response

def test_arduino(port='/dev/ttyACM0', baudrate=250000):
    try:
        # Open serial connection
        print(f"Opening {port} at {baudrate} baud...")
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=1,
            writeTimeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        print("Connected! Waiting for Arduino reset...")
        time.sleep(3)  # Due needs more time to reset
        
        # Clear any startup messages
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Send initial newline to clear any partial commands
        ser.write(b'\n')
        time.sleep(0.1)
        ser.reset_input_buffer()
        
        # Test commands
        commands = [
            "TEST",
            "STATUS",
            "TEMP",
            "HOME",
            "STOP"
        ]
        
        for cmd in commands:
            print(f"\n→ Sending: {cmd}")
            ser.write(f"{cmd}\n".encode('utf-8'))
            ser.flush()  # Ensure command is sent
            
            # Read and print response
            responses = read_response(ser)
            if not responses:
                print("No response received!")
            
            time.sleep(1)  # Longer delay for Due
            
    except serial.SerialException as e:
        print(f"Serial Error: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Check if Arduino is properly connected")
        print("2. Make sure you're using the Native port (not Programming port) on the Due")
        print("3. Try unplugging and replugging the USB cable")
        print("4. Check permissions: sudo chmod 666 /dev/ttyACM0")
        print("5. Make sure the correct firmware is uploaded")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("\nSerial connection closed")

def list_ports():
    """List all available serial ports"""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No serial ports found!")
        return
    
    print("\nAvailable ports:")
    for port in ports:
        print(f"- {port.device}: {port.description}")
        if "Arduino Due" in port.description:
            print("  ↳ This is an Arduino Due port")
            if "Programming Port" in port.description:
                print("  ↳ This is the Programming Port (use the other port for communication)")
            else:
                print("  ↳ This is the Native Port (use this for communication)")

if __name__ == "__main__":
    list_ports()
    print("\nStarting Arduino test...")
    
    # Look for Native port first
    import serial.tools.list_ports
    for port in serial.tools.list_ports.comports():
        if "Arduino Due" in port.description and "Programming" not in port.description:
            print(f"Found Arduino Due Native port at {port.device}")
            test_arduino(port=port.device)
            break
    else:
        # Fall back to default if Native port not found
        test_arduino() 