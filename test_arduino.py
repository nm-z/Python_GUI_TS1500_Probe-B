import serial
import time

def test_arduino():
    try:
        # Open serial port
        print("Opening serial port...")
        ser = serial.Serial(
            port='/dev/ttyACM0',
            baudrate=250000,
            timeout=1,
            write_timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        print("Waiting for Arduino reset...")
        time.sleep(3)  # Wait for Arduino reset
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Wait for initialization messages
        print("Waiting for initialization messages...")
        start_time = time.time()
        while (time.time() - start_time) < 10:  # 10 second timeout
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"Received: {line}")
                        if line == "READY":
                            print("READY signal received!")
                            break
                except UnicodeDecodeError:
                    print("Received non-text data")
            time.sleep(0.1)
            
        # Test commands
        commands = ["STATUS", "TEMP", "TILT", "HELP"]
        for cmd in commands:
            print(f"\nSending command: {cmd}")
            ser.write(f"{cmd}\n".encode('utf-8'))
            ser.flush()
            time.sleep(0.5)
            
            while ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"Response: {line}")
                except UnicodeDecodeError:
                    print("Received non-text data")
                    
        # Clean up
        ser.close()
        print("\nTest complete")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_arduino() 