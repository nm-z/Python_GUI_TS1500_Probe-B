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
        min_angle = float(input("\033[96mMinimum angle \033[93m[-13 degrees]\033[96m: \033[0m").strip() or "-13")
        max_angle = float(input("\033[96mMaximum angle \033[93m[13 degrees]\033[96m: \033[0m").strip() or "13")
        increment = float(input("\033[96mAngle increment \033[93m[1 degree]\033[96m: \033[0m").strip() or "1")
        vna_dwell = float(input("\033[96mVNA dwell time \033[93m[6 seconds]\033[96m: \033[0m").strip() or "6")
        oil_dwell = float(input("\033[96mOil settling time \033[93m[2 seconds]\033[96m: \033[0m").strip() or "2")
        
        return {
            'min_angle': min_angle,
            'max_angle': max_angle,
            'increment': increment,
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
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"\033[93mStarting in {i}...\033[0m\n")
            time.sleep(1)
            
        print("\n\033[92mTest started!\033[0m")
        
        # Calculate number of steps for progress
        current_angle = params['min_angle']
        total_steps = int((params['max_angle'] - params['min_angle']) / params['increment']) + 1
        step = 0
        
        while current_angle <= params['max_angle']:
            # Show progress
            progress = (step / total_steps) * 100
            print(f"\033[96mProgress: {progress:.1f}% (Angle: {current_angle:.1f}°)\033[0m")
            
            # Move to angle
            steps = int(current_angle * 5)  # Convert angle to steps (5 steps per degree)
            print(f"\033[95mMoving to {current_angle:.1f}°\033[0m")
            response = controller.send_command("MOVE", {"steps": steps})
            print(f"\033[95m{response}\033[0m")
            
            # Wait fixed time for movement (1 second is enough for any movement)
            time.sleep(1)
            
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
            temp_response = controller.send_command("TEMP")
            tilt_response = controller.send_command("TILT")
            print(f"\033[92mTemperature: {temp_response}\033[0m")
            print(f"\033[92mTilt: {tilt_response}\033[0m")
            
            # Move to next angle
            current_angle += params['increment']
            step += 1
            
        print("\n\033[92mTest completed successfully!\033[0m")
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
                        run_test_routine(controller, params)
                elif command.startswith("MOVE "):
                    try:
                        steps = int(command.split()[1])
                        response = controller.send_command("MOVE", {"steps": steps})
                        print(f"\033[92m{response}\033[0m")
                    except (IndexError, ValueError):
                        print("\033[91mError: MOVE command requires steps argument (integer)\033[0m")
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
