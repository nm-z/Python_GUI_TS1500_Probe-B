from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSpinBox, QPushButton, QGroupBox,
    QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from .styles import Styles
from utils.config import Config

class SettingsDialog(QDialog):
    settings_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Initialize the settings dialog UI"""
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Theme settings
        theme_group = QGroupBox("Theme Settings")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Mode", "Light Mode"])
        self.theme_combo.setStyleSheet(Styles.SPINBOX_STYLE)
        theme_layout.addRow("Theme:", self.theme_combo)
        
        # Font settings
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setValue(12)
        self.font_size.setStyleSheet(Styles.SPINBOX_STYLE)
        theme_layout.addRow("Font Size:", self.font_size)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(Styles.BUTTON_STYLE)
        save_btn.clicked.connect(self.save_settings)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(Styles.BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
    def load_settings(self):
        """Load current settings"""
        # Load theme
        is_dark_mode = self.config.get('theme', 'dark_mode', default=True)
        self.theme_combo.setCurrentText("Dark Mode" if is_dark_mode else "Light Mode")
        
        # Load font size
        font_size = self.config.get('theme', 'font_size', default=12)
        self.font_size.setValue(font_size)
        
    def save_settings(self):
        """Save settings and emit update signal"""
        settings = {
            'theme': {
                'dark_mode': self.theme_combo.currentText() == "Dark Mode",
                'font_size': self.font_size.value()
            }
        }
        
        # Save to config
        self.config.set('theme', 'dark_mode', settings['theme']['dark_mode'])
        self.config.set('theme', 'font_size', settings['theme']['font_size'])
        self.config.save()
        
        # Emit signal for UI update
        self.settings_updated.emit(settings)
        self.accept()
        
    def reject(self):
        """Handle dialog rejection"""
        print("[DEBUG] Settings dialog: Changes cancelled by user")
        super().reject()
        
    def resizeEvent(self, event):
        """Handle dialog resize events"""
        try:
            super().resizeEvent(event)
            print(f"[DEBUG] Settings dialog resized to {self.width()}x{self.height()}")
        except Exception as e:
            import traceback
            print(f"[ERROR] Settings dialog resize error: {str(e)}")
            print("[ERROR] Traceback:")
            print(traceback.format_exc()) 