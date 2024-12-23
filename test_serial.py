import serial
import time

def test_arduino_connection():
    try:
        # Open serial connection
        ser = serial.Serial('/dev/ttyACM1', 250000, timeout=1)
        print(f"Opened {ser.name}")
        
        # Wait for Arduino reset
        time.sleep(3)
        print("Waiting for initialization messages...")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Read for 5 seconds
        start_time = time.time()
        while (time.time() - start_time) < 5:
            if ser.in_waiting:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f"Received: {line}")
                except UnicodeDecodeError:
                    print("Received non-text data")
            time.sleep(0.1)
            
        # Send test command
        print("\nSending STATUS command...")
        ser.write(b"STATUS\n")
        ser.flush()
        
        # Read response
        time.sleep(0.5)
        while ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    print(f"Response: {line}")
            except UnicodeDecodeError:
                print("Received non-text data")
                
        ser.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_arduino_connection() 