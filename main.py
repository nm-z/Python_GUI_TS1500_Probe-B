import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from controllers.main_controller import MainController
from gui.styles import Styles
from utils.logger import gui_logger

def main():
    try:
        # Create application
        app = QApplication(sys.argv)
        
        # Set up dark theme
        Styles.setup_application_style(app)
        
        # Create controller
        controller = MainController()
        
        # Create and show main window
        window = MainWindow(controller)
        window.show()
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        gui_logger.error(f"Application startup error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 