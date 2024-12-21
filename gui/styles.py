from PyQt6.QtGui import QPalette, QColor, QFont, QIcon
from PyQt6.QtWidgets import QApplication

class Styles:
    # Font settings
    FONT = QFont("Ubuntu", 10, QFont.Weight.Bold)
    
    # Dark theme colors
    DARK_BG = "#121212"
    DARK_SURFACE = "#1F1F1F"
    DARK_TEXT = "#FFFFFF"
    DARK_BORDER = "#47A8E5"
    DARK_HOVER = "#2F3438"
    DARK_PRESSED = "#1A1F24"
    
    # Light theme colors
    LIGHT_BG = "#FFFFFF"
    LIGHT_SURFACE = "#F5F5F5"
    LIGHT_TEXT = "#000000"
    LIGHT_BORDER = "#47A8E5"
    LIGHT_HOVER = "#F0F0F0"
    LIGHT_PRESSED = "#E0E0E0"
    
    # Status colors
    SUCCESS_COLOR = "#4CAF50"
    ERROR_COLOR = "#F44336"
    WARNING_COLOR = "#FFC107"
    
    # Dark theme styles
    DARK_WINDOW_STYLE = f"""
        QMainWindow, QDialog {{
            background-color: {DARK_BG};
            color: {DARK_TEXT};
        }}
        QWidget {{
            background-color: {DARK_BG};
            color: {DARK_TEXT};
        }}
        QGroupBox {{
            border: 1px solid {DARK_BORDER};
            border-radius: 3px;
            margin-top: 0.5em;
            padding-top: 0.5em;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }}
    """
    
    DARK_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: {DARK_SURFACE};
            color: {DARK_TEXT};
            border: 1px solid {DARK_BORDER};
            padding: 5px;
            border-radius: 3px;
        }}
        QPushButton:hover {{
            background-color: {DARK_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {DARK_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {DARK_BG};
            color: #666666;
            border: 1px solid #666666;
        }}
    """
    
    DARK_SPINBOX_STYLE = f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {DARK_SURFACE};
            color: {DARK_TEXT};
            border: 1px solid {DARK_BORDER};
            padding: 2px;
            border-radius: 3px;
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            background-color: {DARK_SURFACE};
            border: none;
            border-left: 1px solid {DARK_BORDER};
            border-bottom: 1px solid {DARK_BORDER};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: {DARK_SURFACE};
            border: none;
            border-left: 1px solid {DARK_BORDER};
        }}
    """
    
    DARK_LOG_STYLE = f"""
        QTextEdit {{
            background-color: {DARK_SURFACE};
            color: {DARK_TEXT};
            border: 1px solid {DARK_BORDER};
            border-radius: 3px;
        }}
    """
    
    # Light theme styles
    LIGHT_WINDOW_STYLE = f"""
        QMainWindow, QDialog {{
            background-color: {LIGHT_BG};
            color: {LIGHT_TEXT};
        }}
        QWidget {{
            background-color: {LIGHT_BG};
            color: {LIGHT_TEXT};
        }}
        QGroupBox {{
            border: 1px solid {LIGHT_BORDER};
            border-radius: 3px;
            margin-top: 0.5em;
            padding-top: 0.5em;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }}
    """
    
    LIGHT_BUTTON_STYLE = f"""
        QPushButton {{
            background-color: {LIGHT_SURFACE};
            color: {LIGHT_TEXT};
            border: 1px solid {LIGHT_BORDER};
            padding: 5px;
            border-radius: 3px;
        }}
        QPushButton:hover {{
            background-color: {LIGHT_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {LIGHT_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {LIGHT_BG};
            color: #999999;
            border: 1px solid #CCCCCC;
        }}
    """
    
    LIGHT_SPINBOX_STYLE = f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {LIGHT_SURFACE};
            color: {LIGHT_TEXT};
            border: 1px solid {LIGHT_BORDER};
            padding: 2px;
            border-radius: 3px;
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            background-color: {LIGHT_SURFACE};
            border: none;
            border-left: 1px solid {LIGHT_BORDER};
            border-bottom: 1px solid {LIGHT_BORDER};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: {LIGHT_SURFACE};
            border: none;
            border-left: 1px solid {LIGHT_BORDER};
        }}
    """
    
    LIGHT_LOG_STYLE = f"""
        QTextEdit {{
            background-color: {LIGHT_SURFACE};
            color: {LIGHT_TEXT};
            border: 1px solid {LIGHT_BORDER};
            border-radius: 3px;
        }}
    """
    
    # Emergency button style (always red)
    EMERGENCY_BUTTON_STYLE = """
        QPushButton {
            background-color: #F44336;
            color: white;
            border: 2px solid #D32F2F;
            padding: 5px;
            border-radius: 3px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #D32F2F;
        }
        QPushButton:pressed {
            background-color: #B71C1C;
        }
    """
    
    # Progress bar style
    PROGRESS_STYLE = f"""
        QProgressBar {{
            border: 1px solid {DARK_BORDER};
            border-radius: 3px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {DARK_BORDER};
        }}
    """
    
    # Status styles
    STATUS_ERROR_STYLE = f"""
        QLabel {{
            color: {ERROR_COLOR};
            padding: 5px;
            border-radius: 3px;
            background-color: {DARK_SURFACE};
            border: 1px solid {ERROR_COLOR};
        }}
    """
    
    STATUS_SUCCESS_STYLE = f"""
        QLabel {{
            color: {SUCCESS_COLOR};
            padding: 5px;
            border-radius: 3px;
            background-color: {DARK_SURFACE};
            border: 1px solid {SUCCESS_COLOR};
        }}
    """
    
    STATUS_WARNING_STYLE = f"""
        QLabel {{
            color: {WARNING_COLOR};
            padding: 5px;
            border-radius: 3px;
            background-color: {DARK_SURFACE};
            border: 1px solid {WARNING_COLOR};
        }}
    """
    
    @classmethod
    def get_theme(cls, is_dark_mode=True):
        """Get theme styles based on mode
        
        Args:
            is_dark_mode (bool): Whether to use dark mode
            
        Returns:
            dict: Dictionary of style strings
        """
        if is_dark_mode:
            return {
                'window': cls.DARK_WINDOW_STYLE,
                'button': cls.DARK_BUTTON_STYLE,
                'spinbox': cls.DARK_SPINBOX_STYLE,
                'log': cls.DARK_LOG_STYLE,
                'bg_color': cls.DARK_BG,
                'text_color': cls.DARK_TEXT,
                'border_color': cls.DARK_BORDER
            }
        else:
            return {
                'window': cls.LIGHT_WINDOW_STYLE,
                'button': cls.LIGHT_BUTTON_STYLE,
                'spinbox': cls.LIGHT_SPINBOX_STYLE,
                'log': cls.LIGHT_LOG_STYLE,
                'bg_color': cls.LIGHT_BG,
                'text_color': cls.LIGHT_TEXT,
                'border_color': cls.LIGHT_BORDER
            }
    
    @staticmethod
    def setup_application_style(app):
        """Set up global application style
        
        Args:
            app (QApplication): Application instance
        """
        app.setStyle("Fusion")
        
        # Set default font
        app.setFont(Styles.FONT)
        
        # Create dark palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(Styles.DARK_BG))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(Styles.DARK_TEXT))
        palette.setColor(QPalette.ColorRole.Base, QColor(Styles.DARK_SURFACE))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Styles.DARK_BG))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Styles.DARK_TEXT))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(Styles.DARK_TEXT))
        palette.setColor(QPalette.ColorRole.Text, QColor(Styles.DARK_TEXT))
        palette.setColor(QPalette.ColorRole.Button, QColor(Styles.DARK_SURFACE))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(Styles.DARK_TEXT))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(Styles.DARK_TEXT))
        palette.setColor(QPalette.ColorRole.Link, QColor(Styles.DARK_BORDER))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(Styles.DARK_BORDER))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Styles.DARK_TEXT))
        
        # Set the dark palette
        app.setPalette(palette)
        
        # Set global stylesheet for dark theme
        app.setStyleSheet(f"""
            QMainWindow, QDialog {{
                background-color: {Styles.DARK_BG};
                color: {Styles.DARK_TEXT};
            }}
            QWidget {{
                background-color: {Styles.DARK_BG};
                color: {Styles.DARK_TEXT};
            }}
            QGroupBox {{
                border: 1px solid {Styles.DARK_BORDER};
                border-radius: 3px;
                margin-top: 6px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
            QMenuBar {{
                background-color: {Styles.DARK_SURFACE};
                color: {Styles.DARK_TEXT};
            }}
            QMenuBar::item:selected {{
                background-color: {Styles.DARK_HOVER};
            }}
            QMenu {{
                background-color: {Styles.DARK_SURFACE};
                color: {Styles.DARK_TEXT};
                border: 1px solid {Styles.DARK_BORDER};
            }}
            QMenu::item:selected {{
                background-color: {Styles.DARK_HOVER};
            }}
            QToolBar {{
                background-color: {Styles.DARK_SURFACE};
                border: none;
            }}
            QStatusBar {{
                background-color: {Styles.DARK_SURFACE};
                color: {Styles.DARK_TEXT};
            }}
        """)