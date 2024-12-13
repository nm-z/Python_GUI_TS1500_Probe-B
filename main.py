import os
import sys
import logging
from PyQt6.QtWidgets import QApplication
from controllers.main_controller import MainController
from gui.main_window import MainWindow
from utils.logger import gui_logger
from utils.config import Config
from utils.time_sync import sync_system_time
from gui.styles import Styles

def setup_environment():
    """Set up the application environment"""
    # Set the Qt platform plugin path
    qt_plugin_path = "/usr/lib/qt6/plugins"
    if os.path.exists(qt_plugin_path):
        os.environ["QT_PLUGIN_PATH"] = qt_plugin_path
    
    # Try XCB platform first, fallback to Wayland
    os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"
    
    # Configure logging levels for external libraries
    logging.getLogger('PIL').setLevel(logging.INFO)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

def main():
    """Main application entry point"""
    try:
        # Set up environment
        setup_environment()
        
        # Initialize Qt application with platform plugin
        app = QApplication(sys.argv)
        
        # Load configuration
        config = Config()
        
        # Set up logging level
        log_level = getattr(logging, config.get('logging', 'level', default='INFO'))
        gui_logger.setLevel(log_level)
        
        # Attempt to sync system time if running as root
        if os.geteuid() == 0:
            sync_system_time()
        
        # Apply application styles
        Styles.setup_application_style(app)
        
        # Create controller and main window
        controller = MainController()
        window = MainWindow(controller)
        
        # Initialize with default test parameters through the controller
        test_parameters = {
            'tilt_increment': 1.0,  # Default 1 degree, up to 3 degrees fallback
            'min_tilt': -30.0,     # -30 degrees
            'max_tilt': 30.0,      # +30 degrees
            'oil_level_time': 15,  # 15 seconds for oil stabilization
            'tilt_accuracy': 0.1   # 0.1 degrees accuracy, up to 3 degrees fallback
        }
        controller.update_test_parameters(test_parameters)
        
        window.show()
        
        # Start web server if enabled
        if config.get('web_server', 'enabled', default=False):
            gui_logger.info("Starting web server...")
            host = config.get('web_server', 'host', default='0.0.0.0')
            port = config.get('web_server', 'port', default=5000)
            controller.run_web_server(host=host, port=port)
        
        # Enter Qt event loop
        gui_logger.info("Entering main event loop...")
        sys.exit(app.exec())
    
    except PermissionError as e:
        gui_logger.error(f"Permission error: {e}", exc_info=True)
        print("Try running the script with sudo or grant necessary permissions to the serial ports.")
    except Exception as e:
        gui_logger.error(f"An error occurred: {e}", exc_info=True)
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main() 