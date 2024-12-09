from PyQt6.QtGui import QPalette, QColor, QFont, QIcon
from PyQt6.QtWidgets import QApplication

class Styles:
    # Color Palette
    COLORS = {
        'background': '#1e1e1e',        # Dark background
        'background_alt': '#252526',    # Slightly lighter background
        'foreground': '#d4d4d4',        # Light text
        'accent': '#0078d4',            # Blue accent
        'accent_alt': '#1a8ad4',        # Lighter blue
        'border': '#3d3d3d',            # Border color
        'error': '#f44336',             # Red for errors
        'warning': '#ff9800',           # Orange for warnings
        'success': '#4caf50',           # Green for success
        'disabled': '#666666',          # Gray for disabled elements
    }

    # Dimensions
    MARGINS = 8
    SPACING = 6
    BORDER_RADIUS = 3

    # Fonts
    HEADER_FONT = QFont('Segoe UI', 10, QFont.Weight.Bold)
    BODY_FONT = QFont('Segoe UI', 9)
    SMALL_FONT = QFont('Segoe UI', 8)

    # Common widget dimensions
    BUTTON_HEIGHT = 28
    INPUT_HEIGHT = 24
    ICON_SIZE = 16

    # Base style sheet
    BASE_STYLE = f"""
        QWidget {{
            background-color: {COLORS['background']};
            color: {COLORS['foreground']};
            font-family: 'Segoe UI';
        }}

        QPushButton {{
            background-color: {COLORS['accent']};
            color: white;
            border: none;
            border-radius: {BORDER_RADIUS}px;
            padding: 6px 12px;
            height: {BUTTON_HEIGHT}px;
            font-weight: bold;
        }}

        QPushButton:hover {{
            background-color: {COLORS['accent_alt']};
        }}

        QPushButton:pressed {{
            background-color: {COLORS['accent']};
        }}

        QPushButton:disabled {{
            background-color: {COLORS['disabled']};
        }}

        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background-color: {COLORS['background_alt']};
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS}px;
            padding: 4px 8px;
            height: {INPUT_HEIGHT}px;
        }}

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border: 1px solid {COLORS['accent']};
        }}

        QGroupBox {{
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS}px;
            margin-top: 12px;
            font-weight: bold;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 3px;
        }}

        QTabWidget::pane {{
            border: 1px solid {COLORS['border']};
            background-color: {COLORS['background']};
        }}

        QTabBar::tab {{
            background-color: {COLORS['background_alt']};
            border-top-left-radius: {BORDER_RADIUS}px;
            border-top-right-radius: {BORDER_RADIUS}px;
            padding: 6px 12px;
            min-width: 80px;
        }}

        QTabBar::tab:selected {{
            background-color: {COLORS['accent']};
            color: white;
        }}

        QScrollBar:vertical {{
            background-color: {COLORS['background']};
            width: 12px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background-color: {COLORS['border']};
            min-height: 20px;
            border-radius: 6px;
            margin: 2px;
        }}

        QScrollBar:horizontal {{
            background-color: {COLORS['background']};
            height: 12px;
            margin: 0;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {COLORS['border']};
            min-width: 20px;
            border-radius: 6px;
            margin: 2px;
        }}

        QProgressBar {{
            border: 1px solid {COLORS['border']};
            border-radius: {BORDER_RADIUS}px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {COLORS['accent']};
        }}
    """

    @staticmethod
    def setup_application_style(app):
        """Set up the application style and icons"""
        # Apply stylesheet
        app.setStyleSheet(Styles.BASE_STYLE)
        
        # Apply dark theme
        Styles.apply_dark_theme(app)
        
        # Set application icon
        app.setWindowIcon(QIcon('path/to/app_icon.png'))  # Update with actual icon path

    @staticmethod
    def apply_dark_theme(app):
        """Apply dark theme to the application"""
        palette = QPalette()
        
        # Get colors from our scheme
        background = QColor(Styles.COLORS['background'])
        background_alt = QColor(Styles.COLORS['background_alt'])
        foreground = QColor(Styles.COLORS['foreground'])
        accent = QColor(Styles.COLORS['accent'])
        border = QColor(Styles.COLORS['border'])
        
        # Set up the palette
        palette_updates = [
            # Window and base colors
            (QPalette.ColorRole.Window, background),
            (QPalette.ColorRole.WindowText, foreground),
            (QPalette.ColorRole.Base, background_alt),
            (QPalette.ColorRole.AlternateBase, background),
            
            # Button colors
            (QPalette.ColorRole.Button, background_alt),
            (QPalette.ColorRole.ButtonText, foreground),
            
            # Selection colors
            (QPalette.ColorRole.Highlight, accent),
            (QPalette.ColorRole.HighlightedText, foreground),
            
            # Tooltip colors
            (QPalette.ColorRole.ToolTipBase, background_alt),
            (QPalette.ColorRole.ToolTipText, foreground),
            
            # Text colors
            (QPalette.ColorRole.Text, foreground),
            (QPalette.ColorRole.BrightText, foreground),
            
            # Link color
            (QPalette.ColorRole.Link, accent),
            (QPalette.ColorRole.LinkVisited, accent)
        ]
        
        # Apply colors to all color groups
        for role, color in palette_updates:
            palette.setColor(QPalette.ColorGroup.All, role, color)
        
        app.setPalette(palette)

    # Alias for backward compatibility
    apply_style = setup_application_style