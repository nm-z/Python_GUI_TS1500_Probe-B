from PyQt6.QtGui import QPalette, QColor, QFont, QIcon
from PyQt6.QtWidgets import QApplication

class Styles:
    # Font configuration
    FONT = QFont('Ubuntu')
    FONT.setBold(True)
    FONT_STYLE = "font-family: 'Ubuntu'; font-weight: bold;"
    
    # Theme colors
    DARK_BG = "#121212"
    PRIMARY = "#47A8E5"
    PRIMARY_LIGHT = "#64B1E8"
    PRIMARY_LIGHTER = "#7BBBEB"
    SURFACE_DARK = "#1A1F24"
    SURFACE = "#2F3438"
    SURFACE_LIGHT = "#464A4E"
    
    # Graph colors
    TILT_LINE_COLOR = "#FF073A"
    TEMP_LINE_COLOR = "#0FFF50"
    
    # Styles
    DIVIDER_STYLE = f"""
        QSplitter::handle {{
            background-color: {PRIMARY};
            border: 1px solid {PRIMARY};
        }}
        QSplitter::handle:hover {{
            background-color: {PRIMARY_LIGHT};
        }}
    """
    
    BUTTON_STYLE = f"""
        QPushButton {{
            background-color: {SURFACE};
            color: white;
            border: 2px solid {PRIMARY};
            border-radius: 5px;
            padding: 8px;
            {FONT_STYLE}
        }}
        QPushButton:hover {{
            background-color: {PRIMARY};
        }}
        QPushButton:pressed {{
            background-color: {PRIMARY_LIGHT};
        }}
        QPushButton:disabled {{
            background-color: {SURFACE_DARK};
            border-color: {SURFACE_LIGHT};
            color: #666666;
        }}
    """
    
    SPINBOX_STYLE = f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {SURFACE};
            color: white;
            border: 2px solid {PRIMARY};
            border-radius: 5px;
            padding: 5px;
            {FONT_STYLE}
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {PRIMARY_LIGHT};
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            background-color: {SURFACE_LIGHT};
            border: none;
            border-left: 2px solid {PRIMARY};
            border-bottom: 1px solid {PRIMARY};
            border-top-right-radius: 3px;
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: {SURFACE_LIGHT};
            border: none;
            border-left: 2px solid {PRIMARY};
            border-top: 1px solid {PRIMARY};
            border-bottom-right-radius: 3px;
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {PRIMARY};
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            image: url(icons/up.png);
            width: 10px;
            height: 10px;
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            image: url(icons/down.png);
            width: 10px;
            height: 10px;
        }}
    """
    
    COMBOBOX_STYLE = f"""
        QComboBox {{
            background-color: {SURFACE};
            color: white;
            border: 2px solid {PRIMARY};
            border-radius: 5px;
            padding: 5px;
            {FONT_STYLE}
        }}
        QComboBox:hover {{
            border-color: {PRIMARY_LIGHT};
        }}
        QComboBox:focus {{
            border-color: {PRIMARY_LIGHT};
        }}
        QComboBox::drop-down {{
            border: none;
            border-left: 2px solid {PRIMARY};
            background-color: {SURFACE_LIGHT};
            width: 20px;
        }}
        QComboBox::drop-down:hover {{
            background-color: {PRIMARY};
        }}
        QComboBox::down-arrow {{
            image: url(icons/down.png);
            width: 10px;
            height: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {SURFACE};
            color: white;
            selection-background-color: {PRIMARY};
            selection-color: white;
            border: 2px solid {PRIMARY};
        }}
    """
    
    PROGRESS_STYLE = f"""
        QProgressBar {{
            border: 2px solid {PRIMARY};
            border-radius: 5px;
            text-align: center;
            {FONT_STYLE}
            color: white;
            background-color: {SURFACE_DARK};
        }}
        QProgressBar::chunk {{
            background-color: {PRIMARY};
            width: 10px;
            margin: 0.5px;
        }}
    """
    
    LOGGER_STYLE = f"""
        QTextEdit {{
            background-color: {SURFACE_DARK};
            color: white;
            border: 2px solid {PRIMARY};
            border-radius: 5px;
            padding: 5px;
            {FONT_STYLE}
        }}
    """
    
    @staticmethod
    def setup_application_style(app):
        """Apply global application style"""
        app.setStyleSheet(f"""
            QMainWindow {{
                background-color: {Styles.DARK_BG};
                color: white;
                {Styles.FONT_STYLE}
            }}
            QWidget {{
                background-color: {Styles.DARK_BG};
                color: white;
                {Styles.FONT_STYLE}
            }}
            QGroupBox {{
                border: 2px solid {Styles.PRIMARY};
                border-radius: 5px;
                margin-top: 1em;
                padding-top: 1em;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: white;
            }}
            QLabel {{
                color: white;
            }}
            QToolBar {{
                background-color: {Styles.SURFACE_DARK};
                border-bottom: 2px solid {Styles.PRIMARY};
                spacing: 5px;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                padding: 5px;
            }}
            QToolButton:hover {{
                background-color: {Styles.PRIMARY};
                border-radius: 3px;
            }}
        """)