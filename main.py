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

def run_test_routine(controller, params):
    """Run the test routine with given parameters"""
    try:
        print("\n\033[93mPreparing to start test...\033[0m")
        print("\033[91mIMPORTANT: Please click on your VNA window now to ensure it receives the F12 keypress!\033[0m")
        
        # Import pyautogui here to avoid startup delay
        pyautogui.FAILSAFE = False  # Disable fail-safe
        
        # Create temperature log directory if it doesn't exist
        temp_log_dir = params.get('export_path', "/home/test/Desktop/TEMP_Export_Tilt-Test_001")
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
            print(f"\033[93mStarting test in {i}...\033[0m\n")
            time.sleep(1)
            
        print("\n\033[92mTest started!\033[0m")

        # For fill test, take first measurement at current position (after homing)
        if params['test_type'] == "2":  # Fill Test
            print("\033[93mFill Test: Taking first measurement at home position...\033[0m")
            time.sleep(params['oil_dwell'])
            
            # Take initial measurement (point 1)
            print("\033[93mTaking measurement at home position (point 1)...\033[0m")
            try:
                pyautogui.press('f12')
            except Exception as e:
                print(f"\033[91mError triggering VNA sweep: {str(e)}\033[0m")
                print("\033[91mPlease press F12 manually in the VNA window now\033[0m")
                input("\033[93mPress Enter after pressing F12...\033[0m")
            
            # Wait for VNA
            print(f"\033[93mWaiting {params['vna_dwell']}s for VNA sweep...\033[0m")
            time.sleep(params['vna_dwell'])
            
            # Get temperature and tilt readings
            controller._arduino.write(b"TEMP\n")
            temp_response = controller._arduino.readline().decode('utf-8').strip()
            print(f"\033[92mTemperature: {temp_response}\033[0m")
            
            controller._arduino.write(b"TILT\n")
            tilt_response = controller._arduino.readline().decode('utf-8').strip()
            print(f"\033[92mTilt: {tilt_response}\033[0m")
            
            # Log temperature to CSV
            try:
                temp_value = float(temp_response.split()[-1])
                timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                with open(temp_log_file, 'a') as f:
                    f.write(f"{timestamp},{temp_value:.2f}\n")
            except Exception as e:
                print(f"\033[91mError logging temperature: {str(e)}\033[0m")

        total_measurements = int(params['num_steps']) * int(params['num_loops'])
        current_measurement = 0

        for loop in range(params['num_loops']):
            print(f"\n\033[95mStarting loop {loop + 1} of {params['num_loops']}\033[0m")
            
            # Do measurements with step increments
            for i in range(int(params['num_steps'])):
                current_measurement += 1
                progress = (current_measurement / total_measurements) * 100
                print(f"\033[96mProgress: {progress:.1f}% (Loop {loop + 1}/{params['num_loops']})\033[0m")
                
                # Move motor by step increment
                print(f"\033[95mMoving +{params['step_increment']} steps\033[0m")
                controller._arduino.write(f"MOVE {params['step_increment']}\n".encode())
                while True:
                    response = controller._arduino.readline().decode('utf-8').strip()
                    if response:
                        print(f"\033[95m{response}\033[0m")
                        if "Movement complete" in response:
                            break
                        elif "ERROR" in response:
                            raise Exception(f"Movement error: {response}")
                
                # Wait for oil to settle
                print(f"\033[93mWaiting {params['oil_dwell']}s for oil to settle...\033[0m")
                time.sleep(params['oil_dwell'])
                
                # Trigger VNA sweep
                print("\033[93mTriggering VNA sweep...\033[0m")
                try:
                    pyautogui.press('f12')
                except Exception as e:
                    print(f"\033[91mError triggering VNA sweep: {str(e)}\033[0m")
                    print("\033[91mPlease press F12 manually in the VNA window now\033[0m")
                    input("\033[93mPress Enter after pressing F12...\033[0m")
                
                # Wait for VNA
                print(f"\033[93mWaiting {params['vna_dwell']}s for VNA sweep...\033[0m")
                time.sleep(params['vna_dwell'])
                
                # Get temperature and tilt readings
                controller._arduino.write(b"TEMP\n")
                temp_response = controller._arduino.readline().decode('utf-8').strip()
                print(f"\033[92mTemperature: {temp_response}\033[0m")
                
                controller._arduino.write(b"TILT\n")
                tilt_response = controller._arduino.readline().decode('utf-8').strip()
                print(f"\033[92mTilt: {tilt_response}\033[0m")
                
                # Log temperature to CSV
                try:
                    temp_value = float(temp_response.split()[-1])
                    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                    with open(temp_log_file, 'a') as f:
                        f.write(f"{timestamp},{temp_value:.2f}\n")
                except Exception as e:
                    print(f"\033[91mError logging temperature: {str(e)}\033[0m")
            
            # After measurements, move back to home position
            if loop < params['num_loops'] - 1:  # Don't do this on last loop
                print(f"\033[95mMoving back to home position\033[0m")
                controller._arduino.write(f"MOVE {-params['step_increment'] * params['num_steps']}\n".encode())
                while True:
                    response = controller._arduino.readline().decode('utf-8').strip()
                    if response:
                        print(f"\033[95m{response}\033[0m")
                        if "Movement complete" in response:
                            break
                        elif "ERROR" in response:
                            raise Exception(f"Movement error: {response}")
                
                # Add drain delay after the large reset move
                print(f"\033[93mWaiting {params['drain_delay']}s for oil to drain...\033[0m")
                time.sleep(params['drain_delay'])
                
                # For fill test, if there are more loops, take measurement at 0 (this becomes point 1 of next loop)
                if params['test_type'] == "2":  # Fill Test
                    print("\033[93mTaking measurement at home position (point 1 of next loop)...\033[0m")
                    try:
                        pyautogui.press('f12')
                    except Exception as e:
                        print(f"\033[91mError triggering VNA sweep: {str(e)}\033[0m")
                        print("\033[91mPlease press F12 manually in the VNA window now\033[0m")
                        input("\033[93mPress Enter after pressing F12...\033[0m")
                    
                    time.sleep(params['vna_dwell'])
                    
                    # Get temperature and tilt readings
                    controller._arduino.write(b"TEMP\n")
                    temp_response = controller._arduino.readline().decode('utf-8').strip()
                    print(f"\033[92mTemperature: {temp_response}\033[0m")
                    
                    controller._arduino.write(b"TILT\n")
                    tilt_response = controller._arduino.readline().decode('utf-8').strip()
                    print(f"\033[92mTilt: {tilt_response}\033[0m")
                    
                    try:
                        temp_value = float(temp_response.split()[-1])
                        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                        with open(temp_log_file, 'a') as f:
                            f.write(f"{timestamp},{temp_value:.2f}\n")
                    except Exception as e:
                        print(f"\033[91mError logging temperature: {str(e)}\033[0m")
        
        # After all loops, move back to home position
        print(f"\033[95mMoving back to home position\033[0m")
        controller._arduino.write(f"MOVE {-params['step_increment'] * params['num_steps']}\n".encode())
        while True:
            response = controller._arduino.readline().decode('utf-8').strip()
            if response:
                print(f"\033[95m{response}\033[0m")
                if "Movement complete" in response:
                    break
                elif "ERROR" in response:
                    raise Exception(f"Movement error: {response}")
        
        # Wait for oil to drain
        print(f"\033[93mWaiting {params['drain_delay']}s for oil to drain...\033[0m")
        time.sleep(params['drain_delay'])
            
        print("\n\033[92mTest completed successfully!\033[0m")
        print(f"\033[92mTemperature log saved to: {temp_log_file}\033[0m")
        
        # Save the run counter for next time
        with open(run_counter_file, 'w') as f:
            f.write(str(test_number))
            
        return True
        
    except KeyboardInterrupt:
        print("\n\033[91mTest interrupted by user\033[0m")
        return False
    except Exception as e:
        print(f"\n\033[91mError during test: {str(e)}\033[0m")
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

        def __init__(self, controller):
            super().__init__()
            self.controller = controller
            self.running = True

        def run(self):
            while self.running and self.controller and self.controller._arduino:
                try:
                    response = self.controller._arduino.readline().decode('utf-8').strip()
                    if response:
                        # Map responses to colors similar to CLI mode
                        color = "white"  # default
                        if "ERROR" in response:
                            color = "#FF6B6B"  # red
                        elif "complete" in response.lower():
                            color = "#98FB98"  # light green
                        elif "READY" in response:
                            color = "#90EE90"  # pale green
                        elif "Moving" in response:
                            color = "#DDA0DD"  # plum
                        elif "Temperature" in response:
                            color = "#98FB98"  # light green
                        elif "Tilt" in response:
                            color = "#98FB98"  # light green
                        self.log_signal.emit(response, color)
                except Exception as e:
                    self.log_signal.emit(f"Error reading Arduino: {str(e)}", "#FF6B6B")
                    break

    class MainWindow(QMainWindow):
        def __init__(self, controller, parent=None):
            super().__init__(parent)
            self.controller = controller
            self.setup_ui()
            self.logger_thread = None
            self.is_homed = False

            # Start logger thread
            if self.controller and self.controller._arduino:
                self.logger_thread = LoggerThread(self.controller)
                self.logger_thread.log_signal.connect(self.append_colored_text)
                self.logger_thread.start()

        def setup_ui(self):
            self.setWindowTitle("TS1500 Probe Control")
            self.setMinimumSize(800, 1000)

            # Create central widget and main layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            layout.setSpacing(20)

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
            """)

            # Temperature Export Path Section
            export_frame = QFrame()
            export_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
            export_layout = QVBoxLayout(export_frame)
            
            path_layout = QHBoxLayout()
            self.export_path = QLineEdit()
            self.export_path.setPlaceholderText("Temperature Export Path")
            self.export_path.setText(os.path.expanduser("~/Desktop/TEMP_Export_Tilt-Test_001"))
            browse_btn = QPushButton("Browse...")
            browse_btn.clicked.connect(self.browse_export_path)
            path_layout.addWidget(QLabel("Export Path:"))
            path_layout.addWidget(self.export_path)
            path_layout.addWidget(browse_btn)
            export_layout.addLayout(path_layout)
            
            # Test Number Entry
            test_num_layout = QHBoxLayout()
            self.test_number = QLineEdit()
            self.test_number.setPlaceholderText("Test Number")
            self.test_number.setText("1")
            test_num_layout.addWidget(QLabel("Test Number:"))
            test_num_layout.addWidget(self.test_number)
            export_layout.addLayout(test_num_layout)
            
            layout.addWidget(export_frame)

            # Home Button (must be used first)
            self.home_btn = QPushButton("HOME SYSTEM (Required First)")
            self.home_btn.clicked.connect(self.home_system)
            layout.addWidget(self.home_btn)

            # Parameter Entry Section
            param_frame = QFrame()
            param_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
            param_layout = QVBoxLayout(param_frame)

            # Test Type
            type_layout = QHBoxLayout()
            self.test_type = QLineEdit()
            self.test_type.setPlaceholderText("1 for Tilt, 2 for Fill")
            self.test_type.setText("1")
            type_layout.addWidget(QLabel("Test Type:"))
            type_layout.addWidget(self.test_type)
            param_layout.addLayout(type_layout)

            # Steps per increment
            step_layout = QHBoxLayout()
            self.step_inc = QLineEdit()
            self.step_inc.setText("200")
            step_layout.addWidget(QLabel("Steps/Increment:"))
            step_layout.addWidget(self.step_inc)
            param_layout.addLayout(step_layout)

            # Number of steps
            num_steps_layout = QHBoxLayout()
            self.num_steps = QLineEdit()
            self.num_steps.setText("25")
            num_steps_layout.addWidget(QLabel("Number of Steps:"))
            num_steps_layout.addWidget(self.num_steps)
            param_layout.addLayout(num_steps_layout)

            # Number of loops
            loops_layout = QHBoxLayout()
            self.num_loops = QLineEdit()
            self.num_loops.setText("1")
            loops_layout.addWidget(QLabel("Number of Loops:"))
            loops_layout.addWidget(self.num_loops)
            param_layout.addLayout(loops_layout)

            # VNA dwell time
            vna_layout = QHBoxLayout()
            self.vna_dwell = QLineEdit()
            self.vna_dwell.setText("3")
            vna_layout.addWidget(QLabel("VNA Dwell (s):"))
            vna_layout.addWidget(self.vna_dwell)
            param_layout.addLayout(vna_layout)

            # Oil dwell time
            oil_layout = QHBoxLayout()
            self.oil_dwell = QLineEdit()
            self.oil_dwell.setText("3")
            oil_layout.addWidget(QLabel("Oil Dwell (s):"))
            oil_layout.addWidget(self.oil_dwell)
            param_layout.addLayout(oil_layout)

            # Drain delay time
            drain_layout = QHBoxLayout()
            self.drain_delay = QLineEdit()
            self.drain_delay.setText("20")
            drain_layout.addWidget(QLabel("Drain Delay (s):"))
            drain_layout.addWidget(self.drain_delay)
            param_layout.addLayout(drain_layout)

            layout.addWidget(param_frame)

            # Logger Window
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setMinimumHeight(400)
            layout.addWidget(self.log_area)

            # Run Test Button
            self.run_btn = QPushButton("Run Test")
            self.run_btn.setEnabled(False)  # Disabled until homed
            self.run_btn.clicked.connect(self.run_test)
            layout.addWidget(self.run_btn)

            # Exit Button
            exit_btn = QPushButton("Exit")
            exit_btn.clicked.connect(self.close)
            layout.addWidget(exit_btn)

            self.append_colored_text("GUI Started. Please HOME the system first!", "#FFD700")

        def browse_export_path(self):
            path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
            if path:
                self.export_path.setText(path)

        def append_colored_text(self, text, color="white"):
            self.log_area.append(f'<span style="color: {color};">{text}</span>')
            # Auto-scroll to bottom
            scrollbar = self.log_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        def home_system(self):
            if not self.controller or not self.controller._arduino:
                QMessageBox.warning(self, "Error", "No Arduino connected!")
                return

            reply = QMessageBox.question(self, "Home System",
                                       "Select homing type:\n\n"
                                       "Yes = Tilt Home (homes and moves to level)\n"
                                       "No = Fill Home (homes without moving to level)",
                                       QMessageBox.StandardButton.Yes | 
                                       QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                self.controller._arduino.write(b"TILT_HOME\n")
            else:
                self.controller._arduino.write(b"FILL_HOME\n")

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
                        success = run_test_routine(self.controller, params)
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

        def closeEvent(self, event):
            if self.logger_thread:
                self.logger_thread.running = False
                self.logger_thread.wait()
            event.accept()

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
