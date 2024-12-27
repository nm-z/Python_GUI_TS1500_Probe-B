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

# Force headless mode
HEADLESS_ONLY = True

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
        print("\n\033[93mTest Setup (press Enter to use default value):\033[0m")
        print("\033[93mDefaults shown in [brackets]\033[0m\n")
        
        step_increment = float(input("\033[96mSteps per increment \033[93m[200 steps]\033[96m: \033[0m").strip() or "200")
        num_steps = int(input("\033[96mNumber of steps \033[93m[25]\033[96m: \033[0m").strip() or "25")
        num_loops = int(input("\033[96mNumber of loops \033[93m[1]\033[96m: \033[0m").strip() or "1")
        vna_dwell = float(input("\033[96mVNA dwell time \033[93m[3 seconds]\033[96m: \033[0m").strip() or "3")
        oil_dwell = float(input("\033[96mOil settling time \033[93m[3 seconds]\033[96m: \033[0m").strip() or "3")
        
        # Calculate min and max steps
        max_steps = (num_steps // 2) * step_increment
        min_steps = -max_steps
        
        return {
            'min_steps': min_steps,
            'max_steps': max_steps,
            'step_increment': step_increment,
            'num_steps': num_steps,
            'num_loops': num_loops,
            'vna_dwell': vna_dwell,
            'oil_dwell': oil_dwell
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
        temp_log_dir = "/home/nate/Desktop/TEMP_export"
        if not os.path.exists(temp_log_dir):
            os.makedirs(temp_log_dir)
            
        # Get next test run number
        run_counter_file = os.path.join(temp_log_dir, ".run_counter")
        if os.path.exists(run_counter_file):
            with open(run_counter_file, 'r') as f:
                run_number = int(f.read().strip()) + 1
        else:
            run_number = 1
        
        # Create CSV file with timestamp and run number in name
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        temp_log_file = os.path.join(temp_log_dir, f"test_run_{run_number:03d}_{timestamp}_temp.csv")
        
        # Create CSV file with headers
        with open(temp_log_file, 'w') as f:
            f.write("timestamp,temperature,tilt\n")
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"\033[93mStarting test in {i}...\033[0m\n")
            time.sleep(1)
            
        print("\n\033[92mTest started!\033[0m")

        # Move to minimum position at start
        print(f"\033[95mMoving to initial position: {params['min_steps']} steps\033[0m")
        controller._arduino.write(f"MOVE {params['min_steps']}\n".encode())
        while True:
            response = controller._arduino.readline().decode('utf-8').strip()
            if response:
                print(f"\033[95m{response}\033[0m")
                if "Movement complete" in response:
                    break
                elif "ERROR" in response:
                    raise Exception(f"Movement error: {response}")

        total_measurements = int(params['num_steps']) * int(params['num_loops'])
        current_measurement = 0

        for loop in range(params['num_loops']):
            print(f"\n\033[95mStarting loop {loop + 1} of {params['num_loops']}\033[0m")
            
            # Do measurements with +200 steps
            for i in range(int(params['num_steps'])):
                current_measurement += 1
                progress = (current_measurement / total_measurements) * 100
                print(f"\033[96mProgress: {progress:.1f}% (Loop {loop + 1}/{params['num_loops']})\033[0m")
                
                # Move motor +200
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
                
                # Log temperature and tilt to CSV
                try:
                    temp_value = float(temp_response.split()[-1])  # Extract numeric value
                    tilt_value = float(tilt_response.split()[-1])  # Extract numeric value
                    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                    with open(temp_log_file, 'a') as f:
                        f.write(f"{timestamp},{temp_value:.2f},{tilt_value:.2f}\n")
                except Exception as e:
                    print(f"\033[91mError logging temperature: {str(e)}\033[0m")
            
            # After measurements, move double min steps to reset tilt
            if loop < params['num_loops'] - 1:  # Don't do this on last loop
                double_min = params['min_steps'] * 2
                reset_move = double_min - params['step_increment']  # Add extra increment to prevent drift
                print(f"\033[95mResetting tilt position: {reset_move} steps\033[0m")
                controller._arduino.write(f"MOVE {reset_move}\n".encode())
                while True:
                    response = controller._arduino.readline().decode('utf-8').strip()
                    if response:
                        print(f"\033[95m{response}\033[0m")
                        if "Movement complete" in response:
                            break
                        elif "ERROR" in response:
                            raise Exception(f"Movement error: {response}")
        
        # After all loops, move back to 0
        print(f"\033[95mMoving back to 0: {params['min_steps']} steps\033[0m")
        controller._arduino.write(f"MOVE {params['min_steps']}\n".encode())
        while True:
            response = controller._arduino.readline().decode('utf-8').strip()
            if response:
                print(f"\033[95m{response}\033[0m")
                if "Movement complete" in response:
                    break
                elif "ERROR" in response:
                    raise Exception(f"Movement error: {response}")
            
        print("\n\033[92mTest completed successfully!\033[0m")
        print(f"\033[92mTemperature log saved to: {temp_log_file}\033[0m")
        
        # Save the run counter for next time
        with open(run_counter_file, 'w') as f:
            f.write(str(run_number))
            
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
        print("  EMERGENCY_STOP - Toggle emergency stop")
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
                    print("  EMERGENCY_STOP - Toggle emergency stop")
                    print("  HELP          - Show this help message")
                    print("  EXIT          - Exit the program")
                elif command == "TEST":
                    params = run_test_setup()
                    if params:
                        print("\n\033[92mTest parameters:\033[0m")
                        for key, value in params.items():
                            print(f"  \033[93m{key}:\033[0m {value}")
                            
                        # Calculate and show test summary
                        positions = []
                        current_steps = params['min_steps']
                        while current_steps <= params['max_steps']:
                            positions.append(int(current_steps))
                            current_steps += params['step_increment']
                        
                        total_points = len(positions)
                        total_time = total_points * (params['vna_dwell'] + params['oil_dwell'] + 2)  # 2 seconds for movement
                        minutes = int(total_time // 60)
                        seconds = int(total_time % 60)
                        
                        print("\n\033[95mTest Sequence Summary:\033[0m")
                        print(f"  \033[93mTotal test points:\033[0m {total_points}")
                        print(f"  \033[93mStep size:\033[0m {params['step_increment']} steps")
                        print(f"  \033[93mRange:\033[0m {params['min_steps']} to {params['max_steps']} steps")
                        print(f"  \033[93mStep sequence:\033[0m")
                        
                        # Show positions in a more readable format
                        pos_str = ""
                        for i, pos in enumerate(positions):
                            pos_str += f"{pos:6d}"
                            if (i + 1) % 8 == 0:  # New line every 8 positions
                                pos_str += "\n                 "
                        print(f"                 {pos_str}")
                        
                        print(f"  \033[93mEstimated time:\033[0m {minutes} minutes {seconds} seconds")
                        print("\n\033[95mSequence will:\033[0m")
                        print(f"  1. Move to first position ({positions[0]} steps)")
                        print(f"  2. At each position:")
                        print(f"     - Wait {params['oil_dwell']}s for oil to settle")
                        print(f"     - Trigger VNA sweep")
                        print(f"     - Wait {params['vna_dwell']}s for VNA")
                        print(f"     - Record temperature and tilt")
                        print(f"  3. Move to next position (+{params['step_increment']} steps)")
                        print("  4. Repeat until complete")
                        
                        # Ask for confirmation
                        confirm = input("\n\033[93mStart test? (y/n): \033[0m").strip().lower()
                        if confirm == 'y':
                            run_test_routine(controller, params)
                        else:
                            print("\033[91mTest cancelled\033[0m")
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
                        # Send home command
                        controller._arduino.write(b"HOME\n")
                        
                        # Read and display messages until homing is complete
                        while True:
                            response = controller._arduino.readline().decode('utf-8').strip()
                            if response:
                                print(f"\033[92m{response}\033[0m")
                                
                                # Show appropriate messages based on Arduino state
                                if "Starting homing sequence" in response:
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
                                elif "Homing and leveling complete" in response:
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

def main():
    """Main entry point"""
    try:
        if not HEADLESS_ONLY:
            print("\033[91mError: This version only supports headless mode\033[0m")
            sys.exit(1)
            
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
        
        # Run in CLI mode
        exit_code = cli_mode(controller, gui_logger, hardware_logger)
        sys.exit(exit_code)
            
    except Exception as e:
        print(f"Error in main: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main()
