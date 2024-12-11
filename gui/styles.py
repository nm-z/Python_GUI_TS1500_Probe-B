from PyQt6.QtGui import QPalette, QColor, QFont, QIcon
from PyQt6.QtWidgets import QApplication

class Styles:
    # Font configuration
    FONT = QFont('Ubuntu')
    FONT.setBold(True)
    
    # Color scheme
    COLORS = {
        'background': '#121212',
        'background_alt': '#1E1E1E',
        'foreground': '#FFFFFF',
        'accent': '#47A8E5',  # Light blue
        'border': '#2D2D2D',
        'error': '#FF073A',
        'warning': '#FFA500',
        'success': '#0FFF50',
        'divider': '#47A8E5'  # Light blue for dividers
    }
    
    # Dialog styles
    DIALOG_STYLE = f"""
        QDialog {{
            background-color: {COLORS['background']};
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
            min-width: 400px;
            padding: 20px;
        }}
    """
    
    # Label styles
    LABEL_STYLE = f"""
        QLabel {{
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
            padding: 5px;
        }}
    """
    
    # Progress bar styles
    PROGRESS_STYLE = f"""
        QProgressBar {{
            border: 2px solid {COLORS['border']};
            border-radius: 5px;
            text-align: center;
            color: {COLORS['foreground']};
            background-color: {COLORS['background_alt']};
        }}
        QProgressBar::chunk {{
            background-color: {COLORS['accent']};
            width: 10px;
            margin: 0.5px;
        }}
    """
    
    # Button styles
    BUTTON_STYLE = f"""
        QPushButton {{
            background-color: {COLORS['background_alt']};
            color: {COLORS['foreground']};
            border: 2px solid {COLORS['border']};
            border-radius: 5px;
            padding: 8px 16px;
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {COLORS['accent']};
            border-color: {COLORS['accent']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['background']};
        }}
    """
    
    # Spinbox styles
    SPINBOX_STYLE = f"""
        QSpinBox, QDoubleSpinBox, QLineEdit {{
            background-color: {COLORS['background_alt']};
            color: {COLORS['foreground']};
            border: 2px solid {COLORS['border']};
            border-radius: 5px;
            padding: 5px;
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{
            border-color: {COLORS['accent']};
        }}
    """
    
    # Combobox styles
    COMBOBOX_STYLE = f"""
        QComboBox {{
            background-color: {COLORS['background_alt']};
            color: {COLORS['foreground']};
            border: 2px solid {COLORS['border']};
            border-radius: 5px;
            padding: 5px;
            font-family: 'Ubuntu';
            font-weight: bold;
            min-width: 100px;
        }}
        QComboBox:hover {{
            border-color: {COLORS['accent']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: url(icons/dropdown.png);
            width: 12px;
            height: 12px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLORS['background_alt']};
            color: {COLORS['foreground']};
            selection-background-color: {COLORS['accent']};
            selection-color: {COLORS['background']};
        }}
    """
    
    # Tab styles
    TAB_STYLE = f"""
        QTabWidget::pane {{
            border: 1px solid {COLORS['border']};
            background-color: {COLORS['background_alt']};
            top: -1px;
        }}
        QTabBar::tab {{
            background-color: {COLORS['background']};
            color: {COLORS['foreground']};
            border: 1px solid {COLORS['border']};
            padding: 8px 12px;
            font-family: 'Ubuntu';
            font-weight: bold;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {COLORS['accent']};
            color: {COLORS['background']};
        }}
        QTabBar::tab:hover {{
            background-color: {COLORS['background_alt']};
        }}
    """
    
    # Group box styles
    GROUP_STYLE = f"""
        QGroupBox {{
            background-color: {COLORS['background_alt']};
            color: {COLORS['foreground']};
            border: 2px solid {COLORS['border']};
            border-radius: 5px;
            margin-top: 1em;
            font-family: 'Ubuntu';
            font-weight: bold;
            padding: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
        }}
    """
    
    # Spacing and margins
    SPACING = 5
    MARGINS = 10
    BORDER_RADIUS = 4
    
    # Styles
    DIVIDER_STYLE = f"""
        QSplitter::handle {{
            background-color: {COLORS['background']};
            border: 1px solid {COLORS['divider']};
        }}
        QSplitter::handle:horizontal {{
            width: 4px;
            background-color: {COLORS['divider']};
        }}
        QSplitter::handle:vertical {{
            height: 4px;
            background-color: {COLORS['divider']};
        }}
        QSplitter::handle:hover {{
            background-color: {COLORS['accent']};
        }}
    """
    
    BASE_STYLE = f"""
        QMainWindow, QDialog {{
            background-color: {COLORS['background']};
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QWidget {{
            background-color: {COLORS['background']};
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QGroupBox {{
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS}px;
            margin-top: 1em;
            padding-top: 1em;
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QPushButton {{
            background-color: {COLORS['background_alt']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS}px;
            padding: 5px 15px;
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {COLORS['accent']};
            color: {COLORS['background']};
        }}
        QPushButton:disabled {{
            background-color: {COLORS['background']};
            color: {COLORS['border']};
        }}
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {COLORS['background_alt']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS}px;
            padding: 5px;
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QTextEdit, QListWidget {{
            background-color: {COLORS['background_alt']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS}px;
            padding: 5px;
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QLabel {{
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QProgressBar {{
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS}px;
            text-align: center;
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {COLORS['accent']};
        }}
        QToolBar {{
            background-color: {COLORS['background']};
            border-bottom: 1px solid {COLORS['border']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QStatusBar {{
            background-color: {COLORS['background']};
            color: {COLORS['foreground']};
            border-top: 1px solid {COLORS['border']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QMenuBar {{
            background-color: {COLORS['background']};
            color: {COLORS['foreground']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
        }}
        QMenuBar::item:selected {{
            background-color: {COLORS['accent']};
            color: {COLORS['background']};
        }}
        QMenu {{
            background-color: {COLORS['background']};
            color: {COLORS['foreground']};
            border: 1px solid {COLORS['border']};
            font-family: 'Ubuntu';
            font-weight: bold;
        }}
        QMenu::item:selected {{
            background-color: {COLORS['accent']};
            color: {COLORS['background']};
        }}
    """
    
    @staticmethod
    def setup_application_style(app: QApplication):
        """Apply the application-wide style"""
        app.setStyle("Fusion")
        app.setStyleSheet(Styles.BASE_STYLE)
        
        # Set up dark palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(Styles.COLORS['background']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(Styles.COLORS['foreground']))
        palette.setColor(QPalette.ColorRole.Base, QColor(Styles.COLORS['background_alt']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Styles.COLORS['background']))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Styles.COLORS['background']))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(Styles.COLORS['foreground']))
        palette.setColor(QPalette.ColorRole.Text, QColor(Styles.COLORS['foreground']))
        palette.setColor(QPalette.ColorRole.Button, QColor(Styles.COLORS['background_alt']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(Styles.COLORS['foreground']))
        palette.setColor(QPalette.ColorRole.Link, QColor(Styles.COLORS['accent']))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(Styles.COLORS['accent']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Styles.COLORS['background']))
        
        app.setPalette(palette)