import sys
import os
import logging
import argparse
import time
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow
from hardware.controller import HardwareController
from utils.logger import setup_logger, setup_cli_logger
import colorama
import traceback

def setup_logging(headless=False):
    """Set up application logging"""
    try:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
            
        # Set up loggers
        if headless:
            # Initialize colorama for Windows support
            colorama.init()
            gui_logger = setup_cli_logger('gui')
            hardware_logger = setup_cli_logger('hardware')
        else:
            gui_logger = setup_logger('gui')
            hardware_logger = setup_logger('hardware')
        
        # Set up root logger for uncaught exceptions
        root_logger = logging.getLogger()
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

def cli_mode(controller, gui_logger, hardware_logger):
    """Run the application in CLI mode"""
    try:
        # Wait a bit for the hardware connection to stabilize
        time.sleep(1)
        
        if not controller:
            print("\033[91mError: Hardware controller not initialized\033[0m")
            return 1
            
        # Check hardware connection by sending a STATUS command
        status = controller.send_command("STATUS")
        if not status or not isinstance(status, dict) or 'error' in status:
            print("\033[91mError: Hardware not responding\033[0m")
            return 1

        print("\033[92mConnected to hardware successfully!\033[0m")
        print("\033[93mAvailable commands:\033[0m")
        print("  status  - Get current hardware status")
        print("  temp    - Get temperature reading")
        print("  tilt    - Get tilt angle")
        print("  stop    - Emergency stop")
        print("  exit    - Exit the program")
        print("\033[93mPress Ctrl+C to exit\033[0m")

        while True:
            try:
                command = input("\033[96m> \033[0m").strip().lower()
                
                if command == "exit":
                    break
                elif command == "status":
                    status = controller.send_command("STATUS")
                    if isinstance(status, dict) and 'error' not in status:
                        print("\033[92mStatus:\033[0m")
                        for key, value in status.items():
                            print(f"  {key}: {value}")
                    else:
                        print(f"\033[91mError getting status: {status}\033[0m")
                elif command == "temp":
                    temp = controller.send_command("TEMP")
                    if isinstance(temp, dict) and 'temperature' in temp:
                        print(f"\033[92mTemperature: {temp['temperature']}°C\033[0m")
                    else:
                        print("\033[91mError getting temperature\033[0m")
                elif command == "tilt":
                    tilt = controller.send_command("TILT")
                    if isinstance(tilt, dict) and 'angle' in tilt:
                        print(f"\033[92mTilt angle: {tilt['angle']}°\033[0m")
                    else:
                        print("\033[91mError getting tilt angle\033[0m")
                elif command == "stop":
                    if controller.send_command("EMERGENCY_STOP"):
                        print("\033[92mEmergency stop engaged\033[0m")
                    else:
                        print("\033[91mError engaging emergency stop\033[0m")
                else:
                    print("\033[91mUnknown command\033[0m")
                    
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
        # Create QApplication first
        app = QApplication(sys.argv)
        
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='TS1500 Probe Control')
        parser.add_argument('--headless', action='store_true', help='Run in headless mode')
        args = parser.parse_args()
        
        if args.headless:
            # Run in CLI mode
            cli_mode()
        else:
            # Create and show GUI
            window = MainWindow()
            window.show()
            sys.exit(app.exec())
            
    except Exception as e:
        print(f"Error in main: {str(e)}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main()
