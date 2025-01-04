import sys
import os
import logging
import argparse
import time
from datetime import datetime
from hardware.controller import HardwareController
from utils.logger import setup_logger, setup_cli_logger
import colorama
import traceback
import pyautogui

def setup_logging(headless=True):  # Always headless
    """Set up application logging"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Remove any existing handlers to prevent duplicates
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Initialize colorama for Windows support
        colorama.init()
        gui_logger = setup_cli_logger('gui')
        hardware_logger = setup_cli_logger('hardware')
        
        # Set up root logger for uncaught exceptions
        root_logger.setLevel(logging.DEBUG)
        
        # Add file handler for uncaught exceptions
        today = datetime.now().strftime('%Y%m%d')
        uncaught_handler = logging.FileHandler(f'logs/uncaught_{today}.log')
        uncaught_handler.setLevel(logging.ERROR)
        uncaught_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        root_logger.addHandler(uncaught_handler)
        
        return gui_logger, hardware_logger
        
    except Exception as e:
        print(f"Error setting up logging: {str(e)}")
        return None, None

def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Call the default handler for KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def wait_for_ready(controller, timeout=30):
    """Wait for Arduino to initialize and send READY"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = controller._arduino.readline().decode('utf-8').strip()
        if response:
            controller.logger.debug(f'Arduino: {response}')
        if response == "READY":
            return True
        time.sleep(0.1)
    return False

def run_test_setup():
    """Get test parameters from user"""
    try:
        print("\n\033[93mTest Setup\033[0m")
        print("\033[93m==========\033[0m\n")
        
        # First select test type
        print("\033[96mSelect Test Type:\033[0m")
        print("  1. \033[93mTilt Test\033[0m - Starts at min position, increments up")
        print("  2. \033[93mFill Test\033[0m - Uses position 0 as first point")
        while True:
            test_type = input("\n\033[96mEnter test type (1/2): \033[0m").strip()
            if test_type in ["1", "2"]:
                break
            print("\033[91mInvalid choice. Please enter 1 for Tilt Test or 2 for Fill Test\033[0m")
        
        print(f"\n\033[92mSelected: {'Tilt' if test_type == '1' else 'Fill'} Test\033[0m")
        print("\n\033[93mTest Parameters (press Enter to use default value):\033[0m")
        print("\033[93mDefaults shown in [brackets]\033[0m\n")
        
        # Use different defaults based on test type
        if test_type == "2":  # Fill Test
            step_increment = float(input("\033[96mSteps per increment \033[93m[520 steps]\033[96m: \033[0m").strip() or "520")
            num_steps = int(input("\033[96mNumber of steps \033[93m[21]\033[96m: \033[0m").strip() or "21")
            num_loops = int(input("\033[96mNumber of loops \033[93m[20]\033[96m: \033[0m").strip() or "20")
            vna_dwell = float(input("\033[96mVNA dwell time \033[93m[10 seconds]\033[96m: \033[0m").strip() or "10")
            oil_dwell = float(input("\033[96mOil settling time \033[93m[3 seconds]\033[96m: \033[0m").strip() or "3")
            drain_delay = float(input("\033[96mDrain delay time \033[93m[20 seconds]\033[96m: \033[0m").strip() or "20")
        else:  # Tilt Test
            step_increment = float(input("\033[96mSteps per increment \033[93m[200 steps]\033[96m: \033[0m").strip() or "200")
            num_steps = int(input("\033[96mNumber of steps \033[93m[25]\033[96m: \033[0m").strip() or "25")
            num_loops = int(input("\033[96mNumber of loops \033[93m[1]\033[96m: \033[0m").strip() or "1")
            vna_dwell = float(input("\033[96mVNA dwell time \033[93m[3 seconds]\033[96m: \033[0m").strip() or "3")
            oil_dwell = float(input("\033[96mOil settling time \033[93m[3 seconds]\033[96m: \033[0m").strip() or "3")
            drain_delay = float(input("\033[96mDrain delay time \033[93m[20 seconds]\033[96m: \033[0m").strip() or "20")
        
        return {
            'test_type': test_type,
            'step_increment': step_increment,
            'num_steps': num_steps,
            'num_loops': num_loops,
            'vna_dwell': vna_dwell,
            'oil_dwell': oil_dwell,
            'drain_delay': drain_delay
        }
    except ValueError as e:
        print(f"\033[91mInvalid input: {str(e)}\033[0m")
        return None

def run_test_routine(controller, params, gui_logger=None, write_command=None, get_response=None):
    """Run the test routine with given parameters"""
    def log_message(message, color=None):
        """Helper to log messages to both CLI and GUI if available"""
        # Print to terminal with color
        if color == "#FF6B6B":  # Red
            print(f"\033[91m{message}\033[0m")
        elif color == "#98FB98":  # Light green
            print(f"\033[92m{message}\033[0m")
        elif color == "#FFD700":  # Yellow/gold
            print(f"\033[93m{message}\033[0m")
        elif color == "#DDA0DD":  # Purple
            print(f"\033[95m{message}\033[0m")
        elif color == "#87CEEB":  # Light blue
            print(f"\033[96m{message}\033[0m")
        else:
            print(message)
            
        # Send clean message to GUI
        if gui_logger:
            # Strip any existing ANSI codes
            clean_message = message
            for code in ["\033[91m", "\033[92m", "\033[93m", "\033[94m", "\033[95m", "\033[96m", "\033[0m"]:
                clean_message = clean_message.replace(code, "")
            gui_logger(clean_message, color)

    def safe_get_response():
        """Safely get a response with error handling"""
        try:
            return get_response()
        except Exception as e:
            log_message(f"Error getting response: {str(e)}", "#FF6B6B")
            return None

    def safe_write_command(cmd):
        """Safely write a command with error handling"""
        try:
            write_command(cmd)
        except Exception as e:
            log_message(f"Error writing command: {str(e)}", "#FF6B6B")

    try:
        log_message("Preparing to start test...", "#FFD700")
        log_message("IMPORTANT: Please click on your VNA window now to ensure it receives the F12 keypress!", "#FF6B6B")
        
        # Import pyautogui here to avoid startup delay
        pyautogui.FAILSAFE = False  # Disable fail-safe
        
        # Create temperature log directory if it doesn't exist
        temp_log_dir = params.get('export_path', "/home/nate/Desktop/TEMP_Export_Tilt-Test_001")
        if not os.path.exists(temp_log_dir):
            os.makedirs(temp_log_dir)
            
        # Get test number from params or use run counter
        test_number = params.get('test_number', None)
        if test_number is None:
            # Get next test run number from counter file
            run_counter_file = os.path.join(temp_log_dir, ".run_counter")
            if os.path.exists(run_counter_file):
                with open(run_counter_file, 'r') as f:
                    test_number = int(f.read().strip()) + 1
            else:
                test_number = 1
            
            # Save the run counter for next time
            with open(run_counter_file, 'w') as f:
                f.write(str(test_number))
        
        # Create CSV file with timestamp and test number in name
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        temp_log_file = os.path.join(temp_log_dir, f"test_run_{test_number:03d}_{timestamp}_temp.csv")
        
        # Create CSV file with headers
        with open(temp_log_file, 'w') as f:
            f.write("timestamp,temperature\n")
        
        # Countdown
        for i in range(3, 0, -1):
            log_message(f"Starting test in {i}...", "#FFD700")
            time.sleep(1)
            
        log_message("\nTest started!", "#98FB98")

        # For fill test, take first measurement at current position (after homing)
        if params['test_type'] == "2":  # Fill Test
            log_message("Fill Test: Taking first measurement at home position...", "#FFD700")
            time.sleep(params['oil_dwell'])
            
            # Take initial measurement (point 1)
            log_message("Taking measurement at home position (point 1)...", "#FFD700")
            try:
                pyautogui.press('f12')
            except Exception as e:
                log_message(f"Error triggering VNA sweep: {str(e)}", "#FF6B6B")
                log_message("Please press F12 manually in the VNA window now", "#FF6B6B")
                input("Press Enter after pressing F12...")
            
            # Wait for VNA
            log_message(f"Waiting {params['vna_dwell']}s for VNA sweep...", "#FFD700")
            time.sleep(params['vna_dwell'])
            
            # Get temperature and tilt readings
            safe_write_command("TEMP\n")
            temp_response = safe_get_response()
            if temp_response:
                log_message(f"Temperature: {temp_response}", "#98FB98")
            
            safe_write_command("TILT\n")
            tilt_response = safe_get_response()
            if tilt_response:
                log_message(f"Tilt: {tilt_response}", "#98FB98")
            
            # Log temperature to CSV
            try:
                if temp_response:
                    temp_value = float(temp_response.split()[-1])
                    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                    with open(temp_log_file, 'a') as f:
                        f.write(f"{timestamp},{temp_value:.2f}\n")
            except Exception as e:
                log_message(f"Error logging temperature: {str(e)}", "#FF6B6B")

        total_measurements = int(params['num_steps']) * int(params['num_loops'])
        current_measurement = 0

        for loop in range(params['num_loops']):
            log_message(f"\nStarting loop {loop + 1} of {params['num_loops']}", "#DDA0DD")
            
            # Do measurements with step increments
            for i in range(int(params['num_steps'])):
                current_measurement += 1
                progress = (current_measurement / total_measurements) * 100
                log_message(f"Progress: {progress:.1f}% (Loop {loop + 1}/{params['num_loops']})", "#87CEEB")
                
                # Move motor by step increment
                log_message(f"Moving +{params['step_increment']} steps", "#DDA0DD")
                safe_write_command(f"MOVE {params['step_increment']}\n")
                
                # Wait for movement to complete
                movement_complete = False
                while not movement_complete:
                    response = safe_get_response()
                    if not response:
                        continue
                    
                    log_message(response, "#DDA0DD")
                    if "Movement complete" in response:
                        movement_complete = True
                    elif "ERROR" in response:
                        if "MPU6050" in response:
                            # Just log MPU6050 errors and continue
                            log_message(f"Warning: {response}", "#FF6B6B")
                            continue
                        else:
                            raise Exception(f"Movement error: {response}")
                
                # Wait for oil to settle
                log_message(f"Waiting {params['oil_dwell']}s for oil to settle...", "#FFD700")
                time.sleep(params['oil_dwell'])
                
                # Trigger VNA sweep
                log_message("Triggering VNA sweep...", "#FFD700")
                try:
                    pyautogui.press('f12')
                except Exception as e:
                    log_message(f"Error triggering VNA sweep: {str(e)}", "#FF6B6B")
                    log_message("Please press F12 manually in the VNA window now", "#FF6B6B")
                    input("Press Enter after pressing F12...")
                
                # Wait for VNA
                log_message(f"Waiting {params['vna_dwell']}s for VNA sweep...", "#FFD700")
                time.sleep(params['vna_dwell'])
                
                # Get temperature and tilt readings
                safe_write_command("TEMP\n")
                temp_response = safe_get_response()
                if temp_response:
                    log_message(f"Temperature: {temp_response}", "#98FB98")
                
                safe_write_command("TILT\n")
                tilt_response = safe_get_response()
                if tilt_response:
                    log_message(f"Tilt: {tilt_response}", "#98FB98")
                
                # Log temperature to CSV
                try:
                    if temp_response:
                        temp_value = float(temp_response.split()[-1])
                        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                        with open(temp_log_file, 'a') as f:
                            f.write(f"{timestamp},{temp_value:.2f}\n")
                except Exception as e:
                    log_message(f"Error logging temperature: {str(e)}", "#FF6B6B")
            
            # After measurements, move back to home position
            if loop < params['num_loops'] - 1:  # Don't do this on last loop
                log_message("Moving back to home position", "#DDA0DD")
                safe_write_command(f"MOVE {-params['step_increment'] * params['num_steps']}\n")
                
                # Wait for movement to complete
                movement_complete = False
                while not movement_complete:
                    response = safe_get_response()
                    if not response:
                        continue
                    
                    log_message(response, "#DDA0DD")
                    if "Movement complete" in response:
                        movement_complete = True
                    elif "ERROR" in response:
                        if "MPU6050" in response:
                            # Just log MPU6050 errors and continue
                            log_message(f"Warning: {response}", "#FF6B6B")
                            continue
                        else:
                            raise Exception(f"Movement error: {response}")
                
                # Add drain delay after the large reset move
                log_message(f"Waiting {params['drain_delay']}s for oil to drain...", "#FFD700")
                time.sleep(params['drain_delay'])
                
                # For fill test, if there are more loops, take measurement at 0 (this becomes point 1 of next loop)
                if params['test_type'] == "2":  # Fill Test
                    log_message("Taking measurement at home position (point 1 of next loop)...", "#FFD700")
                    try:
                        pyautogui.press('f12')
                    except Exception as e:
                        log_message(f"Error triggering VNA sweep: {str(e)}", "#FF6B6B")
                        log_message("Please press F12 manually in the VNA window now", "#FF6B6B")
                        input("Press Enter after pressing F12...")
                    
                    time.sleep(params['vna_dwell'])
                    
                    # Get temperature and tilt readings
                    safe_write_command("TEMP\n")
                    temp_response = safe_get_response()
                    if temp_response:
                        log_message(f"Temperature: {temp_response}", "#98FB98")
                    
                    safe_write_command("TILT\n")
                    tilt_response = safe_get_response()
                    if tilt_response:
                        log_message(f"Tilt: {tilt_response}", "#98FB98")
                    
                    try:
                        if temp_response:
                            temp_value = float(temp_response.split()[-1])
                            timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                            with open(temp_log_file, 'a') as f:
                                f.write(f"{timestamp},{temp_value:.2f}\n")
                    except Exception as e:
                        log_message(f"Error logging temperature: {str(e)}", "#FF6B6B")
        
        # After all loops, move back to home position
        log_message("Moving back to home position", "#DDA0DD")
        safe_write_command(f"MOVE {-params['step_increment'] * params['num_steps']}\n")
        
        # Wait for movement to complete
        movement_complete = False
        while not movement_complete:
            response = safe_get_response()
            if not response:
                continue
            
            log_message(response, "#DDA0DD")
            if "Movement complete" in response:
                movement_complete = True
            elif "ERROR" in response:
                if "MPU6050" in response:
                    # Just log MPU6050 errors and continue
                    log_message(f"Warning: {response}", "#FF6B6B")
                    continue
                else:
                    raise Exception(f"Movement error: {response}")
        
        # Wait for oil to drain
        log_message(f"Waiting {params['drain_delay']}s for oil to drain...", "#FFD700")
        time.sleep(params['drain_delay'])
            
        log_message("\nTest completed successfully!", "#98FB98")
        log_message(f"Temperature log saved to: {temp_log_file}", "#FFD700")
        
        # Save the run counter for next time
        with open(run_counter_file, 'w') as f:
            f.write(str(test_number))
            
        return True
        
    except KeyboardInterrupt:
        log_message("\nTest interrupted by user", "#FF6B6B")
        return False
    except Exception as e:
        log_message(f"\nError during test: {str(e)}", "#FF6B6B")
        return False

def cli_mode(controller, gui_logger, hardware_logger):
    """Run the application in CLI mode"""
    try:
        # Check if Arduino is connected
        if not controller or not controller._arduino:
            print("\033[91mError: No Arduino connected - some functionality will be limited\033[0m")
            return 1

        # Wait for Arduino to initialize
        if not wait_for_ready(controller):
            print("\033[91mError: Arduino not ready\033[0m")
            return 1

        print("\033[92mConnected to hardware successfully!\033[0m")
        print("\033[93mAvailable Commands:\033[0m")
        print("  TEST          - Run system test with parameters")
        print("  STATUS        - Show current system status")
        print("  TEMP          - Read current temperature")
        print("  TILT          - Read current tilt angle")
        print("  MOVE <steps>  - Move stepper motor")
        print("  HOME          - Home the stepper motor")
        print("  STOP          - Stop motor movement")
        print("  CALIBRATE     - Calibrate the system")
        print("  HELP          - Show this help message")
        print("  EXIT          - Exit the program")
        print("\033[93mPress Ctrl+C to exit\033[0m")

        while True:
            try:
                command = input("\033[96m> \033[0m").strip().upper()
                
                if command == "EXIT":
                    break
                elif command == "HELP":
                    print("\033[93mAvailable Commands:\033[0m")
                    print("  TEST          - Run system test with parameters")
                    print("  STATUS        - Show current system status")
                    print("  TEMP          - Read current temperature")
                    print("  TILT          - Read current tilt angle")
                    print("  MOVE <steps>  - Move stepper motor")
                    print("  HOME          - Home the stepper motor")
                    print("  STOP          - Stop motor movement")
                    print("  CALIBRATE     - Calibrate the system")
                    print("  HELP          - Show this help message")
                    print("  EXIT          - Exit the program")
                elif command == "TEST":
                    params = run_test_setup()
                    if params:
                        print("\n\033[92mTest parameters:\033[0m")
                        for key, value in params.items():
                            print(f"  \033[93m{key}:\033[0m {value}")
                            
                        # Calculate and show test summary
                        total_distance = params['step_increment'] * params['num_steps']
                        print(f"\n\033[93mTest will move through {params['num_steps']} positions:\033[0m")
                        print(f"  Step size: {params['step_increment']} steps")
                        print(f"  Total distance per loop: {total_distance} steps")
                        print(f"  Number of loops: {params['num_loops']}")
                        print(f"  VNA dwell: {params['vna_dwell']}s")
                        print(f"  Oil dwell: {params['oil_dwell']}s")
                        print(f"  Drain delay: {params['drain_delay']}s")
                        
                        confirm = input("\n\033[96mStart test? (y/n): \033[0m").strip().lower()
                        if confirm == 'y':
                            if run_test_routine(controller, params):
                                print("\n\033[92mTest completed successfully!\033[0m")
                            else:
                                print("\n\033[91mTest failed or was interrupted\033[0m")
                elif command.startswith("MOVE "):
                    try:
                        # Get target steps from user
                        target_steps = int(command.split()[1])
                        print(f"\033[93mMoving to position: {target_steps} steps\033[0m")
                        
                        # Send move command
                        controller._arduino.write(f"MOVE {target_steps}\n".encode())
                        
                        # Wait for movement completion
                        while True:
                            response = controller._arduino.readline().decode('utf-8').strip()
                            if response:
                                print(f"\033[92m{response}\033[0m")
                                if "Movement complete" in response:
                                    break
                                elif "ERROR" in response:
                                    break
                    except (IndexError, ValueError):
                        print("\033[91mError: MOVE command requires steps argument (integer)\033[0m")
                        print("\033[93mUsage: MOVE <steps> - Move to absolute position in steps\033[0m")
                        print("\033[93mExample: MOVE 200  - Move to +200 steps\033[0m")
                        print("\033[93mExample: MOVE -200 - Move to -200 steps\033[0m")
                elif command == "HOME":
                    try:
                        print("\033[93mSelect homing type:\033[0m")
                        print("1. Tilt Home (homes and moves to level position)")
                        print("2. Fill Home (homes without moving to level)")
                        home_type = input("\033[96mEnter choice (1/2): \033[0m").strip()
                        
                        if home_type == "1":
                            controller._arduino.write(b"TILT_HOME\n")
                        elif home_type == "2":
                            controller._arduino.write(b"FILL_HOME\n")
                        else:
                            print("\033[91mInvalid choice. Please enter 1 or 2\033[0m")
                            continue
                        
                        # Read and display messages until homing is complete
                        while True:
                            response = controller._arduino.readline().decode('utf-8').strip()
                            if response:
                                print(f"\033[92m{response}\033[0m")
                                
                                # Show appropriate messages based on Arduino state
                                if "Starting homing sequence" in response or "Starting fill home sequence" in response:
                                    print("\033[93mMoving down to find home switch...\033[0m")
                                elif "Clearing home switch" in response:
                                    print("\033[93mMoving up to clear home switch...\033[0m")
                                elif "Moving to final position" in response:
                                    print("\n\033[93mMoving to level position (2735 steps)...\033[0m")
                                elif "Waiting for level confirmation" in response:
                                    print("\n\033[93mIMPORTANT: Platform is now at level position\033[0m")
                                    print("1. Check the level sensor reading")
                                    print("2. If level sensor confirms position is level, press the leveling button (Pin 4)")
                                    print("3. If not level, press Ctrl+C to abort and adjust manually")
                                    print("\033[93mWaiting for level confirmation button press...\033[0m")
                                elif "Homing and leveling complete" in response or "Fill home complete" in response:
                                    break
                                elif "ERROR" in response:
                                    break
                                    
                    except KeyboardInterrupt:
                        print("\n\033[91mHoming interrupted by user\033[0m")
                    except Exception as e:
                        print(f"\033[91mError during homing: {str(e)}\033[0m")
                else:
                    # Send command directly to Arduino
                    response = controller.send_command(command)
                    print(f"\033[92m{response}\033[0m")
                    
            except KeyboardInterrupt:
                print("\n\033[93mExiting...\033[0m")
                break
            except Exception as e:
                print(f"\033[91mError: {str(e)}\033[0m")
                
        return 0
        
    except Exception as e:
        print(f"\033[91mCritical error in CLI mode: {str(e)}\033[0m")
        if 'hardware_logger' in locals():
            hardware_logger.critical(f"Critical error in CLI mode: {str(e)}", exc_info=True)
        return 1

def gui_mode(controller, gui_logger, hardware_logger):
    """
    Run the application in a simplified GUI mode for technicians.
    No direct commands; only test selection, parameter input, and real-time logs.
    """
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                                QTextEdit, QFrame, QMessageBox, QFileDialog)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QPalette, QColor
    import sys
    import threading
    import os

    class LoggerThread(QThread):
        """Thread to handle Arduino responses and logging"""
        log_signal = pyqtSignal(str, str)  # message, color
        response_signal = pyqtSignal(str)  # For test routine to receive responses

        def __init__(self, controller):
            super().__init__()
            self.controller = controller
            self.running = True
            self._lock = threading.Lock()

        def write_command(self, command):
            """Write a command to Arduino"""
            with self._lock:
                if not self.running or not self.controller._arduino.is_open:
                    return
                self.controller._arduino.write(command.encode())
                self.controller._arduino.flush()

        def run(self):
            while self.running and self.controller and self.controller._arduino:
                try:
                    with self._lock:
                        if not self.running or not self.controller._arduino.is_open:
                            break
                        response = self.controller._arduino.readline().decode('utf-8').strip()
                        if response:
                            # Map responses to colors similar to CLI mode
                            color = "white"  # default
                            if "ERROR" in response:
                                color = "#FF6B6B"  # red
                                print(f"\033[91m{response}\033[0m")
                            elif "complete" in response.lower():
                                color = "#98FB98"  # light green
                                print(f"\033[92m{response}\033[0m")
                            elif "READY" in response:
                                color = "#90EE90"  # pale green
                                print(f"\033[92m{response}\033[0m")
                            elif "Moving" in response:
                                color = "#DDA0DD"  # plum
                                print(f"\033[95m{response}\033[0m")
                            elif "Temperature" in response:
                                color = "#98FB98"  # light green
                                print(f"\033[92m{response}\033[0m")
                            elif "Tilt" in response:
                                color = "#98FB98"  # light green
                                print(f"\033[92m{response}\033[0m")
                            else:
                                print(response)
                            
                            # Send to GUI
                            self.log_signal.emit(response, color)
                            # Send to test routine
                            self.response_signal.emit(response)

                except Exception as e:
                    error_msg = f"Error reading Arduino: {str(e)}"
                    print(f"\033[91m{error_msg}\033[0m")
                    self.log_signal.emit(error_msg, "#FF6B6B")
                    break

                time.sleep(0.01)  # Small delay to prevent CPU hogging

        def stop(self):
            """Safely stop the thread"""
            self.running = False
            self.wait()

    class MainWindow(QMainWindow):
        def __init__(self, controller, parent=None):
            super().__init__(parent)
            self.controller = controller
            self.logger_thread = None
            self.is_homed = False
            self.setup_ui()
            self.test_responses = []
            self.test_response_lock = threading.Lock()

            # Start logger thread
            if self.controller and self.controller._arduino:
                self.logger_thread = LoggerThread(self.controller)
                self.logger_thread.log_signal.connect(self.append_colored_text)
                self.logger_thread.response_signal.connect(self.handle_response)
                self.logger_thread.start()

        def handle_response(self, response):
            """Handle responses from Arduino"""
            with self.test_response_lock:
                self.test_responses.append(response)

        def get_next_response(self):
            """Get next response from Arduino"""
            timeout = time.time() + 5.0  # 5 second timeout
            while time.time() < timeout:
                with self.test_response_lock:
                    if self.test_responses:
                        return self.test_responses.pop(0)
                time.sleep(0.01)
            raise Exception("Timeout waiting for Arduino response")

        def closeEvent(self, event):
            """Clean up when window is closed"""
            if self.logger_thread:
                self.logger_thread.stop()
            event.accept()

        def home_system(self):
            if not self.controller or not self.controller._arduino:
                QMessageBox.warning(self, "Error", "No Arduino connected!")
                return

            # Create custom dialog with two buttons
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Home System")
            dialog.setText("Select homing type:")
            
            # Remove default buttons
            dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)
            
            # Add simple Tilt and Fill buttons
            tilt_btn = dialog.addButton("Tilt", QMessageBox.ButtonRole.AcceptRole)
            fill_btn = dialog.addButton("Fill", QMessageBox.ButtonRole.RejectRole)
            
            # Make buttons bigger and more readable
            for btn in [tilt_btn, fill_btn]:
                btn.setMinimumWidth(100)
                btn.setMinimumHeight(40)
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 16px;
                        font-weight: bold;
                        padding: 10px;
                    }
                """)
            
            dialog.exec()
            
            # Check which button was clicked
            clicked_button = dialog.clickedButton()
            if clicked_button == tilt_btn:
                self.logger_thread.write_command("TILT_HOME\n")
            elif clicked_button == fill_btn:
                self.logger_thread.write_command("FILL_HOME\n")
            else:
                return  # Dialog was closed without selecting

            self.is_homed = True
            self.run_btn.setEnabled(True)
            self.home_btn.setEnabled(False)
            self.home_btn.setText("System Homed")

        def run_test(self):
            if not self.is_homed:
                QMessageBox.warning(self, "Error", "Please home the system first!")
                return

            try:
                # Get and validate export path
                export_path = self.export_path.text().strip()
                if not export_path:
                    raise ValueError("Export path is required")
                os.makedirs(export_path, exist_ok=True)

                # Get and validate test number
                test_num = int(self.test_number.text().strip())
                if test_num < 1:
                    raise ValueError("Test number must be positive")

                # Build params dict
                params = {
                    'test_type': self.test_type.text().strip(),
                    'step_increment': float(self.step_inc.text().strip()),
                    'num_steps': int(self.num_steps.text().strip()),
                    'num_loops': int(self.num_loops.text().strip()),
                    'vna_dwell': float(self.vna_dwell.text().strip()),
                    'oil_dwell': float(self.oil_dwell.text().strip()),
                    'drain_delay': float(self.drain_delay.text().strip()),
                    'export_path': export_path,
                    'test_number': test_num
                }

                # Show summary
                self.append_colored_text("\n=== Test Parameters ===", "#FFD700")
                for k, v in params.items():
                    self.append_colored_text(f"{k}: {v}", "#98FB98")

                # Run test in background thread
                def worker():
                    try:
                        success = run_test_routine(self.controller, params, 
                                                gui_logger=self.append_colored_text,
                                                write_command=self.logger_thread.write_command,
                                                get_response=self.get_next_response)
                        if success:
                            self.append_colored_text("\nTest completed successfully!", "#90EE90")
                        else:
                            self.append_colored_text("\nTest failed or was interrupted.", "#FF6B6B")
                    except Exception as e:
                        self.append_colored_text(f"\nError during test: {str(e)}", "#FF6B6B")

                threading.Thread(target=worker, daemon=True).start()

            except ValueError as e:
                QMessageBox.warning(self, "Invalid Input", str(e))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Unexpected error: {str(e)}")

        def setup_ui(self):
            self.setWindowTitle("TS1500 Probe Control")
            self.setMinimumSize(800, 1000)  # Back to original size

            # Create central widget and main layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            layout.setSpacing(5)
            layout.setContentsMargins(10, 10, 10, 10)

            # Create a top container for all controls
            top_container = QWidget()
            top_layout = QVBoxLayout(top_container)
            top_layout.setSpacing(5)
            top_layout.setContentsMargins(0, 0, 0, 0)

            # Temperature Export Path Section
            export_frame = QFrame()
            export_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
            export_layout = QVBoxLayout(export_frame)
            export_layout.setSpacing(5)
            export_layout.setContentsMargins(5, 5, 5, 5)
            
            path_layout = QHBoxLayout()
            path_layout.setSpacing(10)  # Add spacing between elements
            self.export_path = QLineEdit()
            self.export_path.setPlaceholderText("Temperature Export Path")
            self.export_path.setText(os.path.expanduser("~/Desktop/TEMP_Export_Tilt-Test_001"))
            browse_btn = QPushButton("Browse...")
            browse_btn.setFixedWidth(100)  # Fixed width for browse button
            path_layout.addWidget(QLabel("Export Path:"), 1)
            path_layout.addWidget(self.export_path, 4)  # Give more space to path field
            path_layout.addWidget(browse_btn, 1)
            export_layout.addLayout(path_layout)
            
            # Test Number Entry
            test_num_layout = QHBoxLayout()
            test_num_layout.setSpacing(10)
            self.test_number = QLineEdit()
            self.test_number.setPlaceholderText("Test Number")
            self.test_number.setText("1")
            test_num_layout.addWidget(QLabel("Test Number:"), 1)
            test_num_layout.addWidget(self.test_number, 5)
            export_layout.addLayout(test_num_layout)
            
            top_layout.addWidget(export_frame)

            # Home Button
            self.home_btn = QPushButton("HOME SYSTEM (Required First)")
            self.home_btn.clicked.connect(self.home_system)
            top_layout.addWidget(self.home_btn)

            # Parameter Entry Section
            param_frame = QFrame()
            param_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
            param_layout = QVBoxLayout(param_frame)
            param_layout.setSpacing(5)
            param_layout.setContentsMargins(5, 5, 5, 5)

            # Create two columns for parameters
            param_columns = QHBoxLayout()
            param_columns.setSpacing(20)  # Add spacing between columns
            left_column = QVBoxLayout()
            left_column.setSpacing(5)
            right_column = QVBoxLayout()
            right_column.setSpacing(5)

            # Helper function to create parameter rows
            def create_param_row(label_text, default_value=""):
                layout = QHBoxLayout()
                layout.setSpacing(10)
                label = QLabel(label_text)
                label.setFixedWidth(120)  # Fixed width for labels
                entry = QLineEdit()
                entry.setText(default_value)
                layout.addWidget(label)
                layout.addWidget(entry)
                return layout, entry

            # Left Column
            type_layout, self.test_type = create_param_row("Test Type:", "1")
            self.test_type.setPlaceholderText("1 for Tilt, 2 for Fill")
            left_column.addLayout(type_layout)

            step_layout, self.step_inc = create_param_row("Steps/Increment:", "200")
            left_column.addLayout(step_layout)

            num_steps_layout, self.num_steps = create_param_row("Number of Steps:", "25")
            left_column.addLayout(num_steps_layout)

            loops_layout, self.num_loops = create_param_row("Number of Loops:", "1")
            left_column.addLayout(loops_layout)

            # Right Column
            vna_layout, self.vna_dwell = create_param_row("VNA Dwell (s):", "3")
            right_column.addLayout(vna_layout)

            oil_layout, self.oil_dwell = create_param_row("Oil Dwell (s):", "3")
            right_column.addLayout(oil_layout)

            drain_layout, self.drain_delay = create_param_row("Drain Delay (s):", "20")
            right_column.addLayout(drain_layout)

            # Add columns to parameter layout
            param_columns.addLayout(left_column)
            param_columns.addLayout(right_column)
            param_layout.addLayout(param_columns)

            top_layout.addWidget(param_frame)

            # Button Container - Horizontal layout
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setSpacing(10)
            button_layout.setContentsMargins(0, 0, 0, 0)

            # Run Test Button
            self.run_btn = QPushButton("Run Test")
            self.run_btn.setEnabled(False)
            self.run_btn.clicked.connect(self.run_test)
            button_layout.addWidget(self.run_btn)

            # Exit Button
            exit_btn = QPushButton("Exit")
            exit_btn.clicked.connect(self.close)
            button_layout.addWidget(exit_btn)

            top_layout.addWidget(button_container)

            # Add the top container to main layout
            layout.addWidget(top_container)

            # Logger Window
            log_container = QWidget()
            log_layout = QVBoxLayout(log_container)
            log_layout.setContentsMargins(0, 0, 0, 0)
            
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setMinimumHeight(400)  # Back to original height
            log_layout.addWidget(self.log_area)
            
            # Add the log container to main layout with stretch
            layout.addWidget(log_container, 1)

            # Initial message
            self.append_colored_text("GUI Started. Please HOME the system first!", "#FFD700")

            # Set dark theme
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QLabel {
                    font-size: 14px;
                }
                QLineEdit {
                    background-color: #3b3b3b;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 3px;
                    font-size: 14px;
                    min-height: 25px;
                }
                QPushButton {
                    background-color: #0d47a1;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 5px;
                    font-size: 14px;
                    min-width: 100px;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QPushButton:disabled {
                    background-color: #666666;
                }
                QTextEdit {
                    background-color: #1b1b1b;
                    color: #ffffff;
                    border: 1px solid #555555;
                    font-family: "Courier New";
                    font-size: 14px;
                    padding: 10px;
                }
                QFrame {
                    margin-bottom: 5px;
                }
            """)

        def browse_export_path(self):
            path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
            if path:
                self.export_path.setText(path)

        def append_colored_text(self, text, color="white"):
            """Add colored text to log area and ensure it's visible"""
            self.log_area.append(f'<span style="color: {color};">{text}</span>')
            
            # Force processing of pending events to ensure text is added
            QApplication.processEvents()
            
            # Move cursor to end
            cursor = self.log_area.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.log_area.setTextCursor(cursor)
            
            # Ensure the last line is visible
            self.log_area.ensureCursorVisible()
            
            # Force scroll to bottom
            scrollbar = self.log_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    # Create and run application
    app = QApplication(sys.argv)
    window = MainWindow(controller)
    window.show()
    return app.exec()

def main():
    """Main entry point"""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='TS1500 Probe Control')
        parser.add_argument('--mode', choices=['cli', 'gui'], default='cli',
                          help='Run mode: cli (default) or gui')
        args = parser.parse_args()
            
        # Set up logging
        gui_logger, hardware_logger = setup_logging(headless=True)
        if not gui_logger or not hardware_logger:
            print("Failed to set up logging")
            sys.exit(1)
            
        # Set up exception handler
        sys.excepthook = handle_exception
        
        try:
            # Initialize hardware controller
            controller = HardwareController(hardware_logger)
        except Exception as e:
            print(f"\033[91mWarning: Failed to initialize hardware controller: {str(e)}\033[0m")
            print("\033[91mContinuing in limited functionality mode...\033[0m")
            controller = None
        
        # Run in selected mode
        if args.mode == 'gui':
            exit_code = gui_mode(controller, gui_logger, hardware_logger)
        else:
            exit_code = cli_mode(controller, gui_logger, hardware_logger)
            
        sys.exit(exit_code)
            
    except Exception as e:
        print(f"Error in main: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main()
