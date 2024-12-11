from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QFormLayout, QLineEdit, QPushButton,
    QLabel, QSpinBox, QComboBox, QGroupBox,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from .styles import Styles

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        self.setStyleSheet(Styles.DIALOG_STYLE)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(Styles.TAB_STYLE)
        
        # Hardware tab
        hardware_tab = QWidget()
        hardware_layout = QVBoxLayout()
        
        # VNA group
        vna_group = QGroupBox("VNA Settings")
        vna_layout = QFormLayout()
        
        self.vna_key = QLineEdit()
        self.vna_key.setStyleSheet(Styles.SPINBOX_STYLE)
        self.vna_key.setText("F5")
        vna_layout.addRow("Trigger Key:", self.vna_key)
        
        self.vna_port = QComboBox()
        self.vna_port.setStyleSheet(Styles.COMBOBOX_STYLE)
        self.vna_port.addItems(["COM1", "COM2", "COM3", "COM4"])
        vna_layout.addRow("Port:", self.vna_port)
        
        vna_group.setLayout(vna_layout)
        hardware_layout.addWidget(vna_group)
        hardware_tab.setLayout(hardware_layout)
        
        # Data tab
        data_tab = QWidget()
        data_layout = QVBoxLayout()
        
        # Data paths group
        data_group = QGroupBox("Data Paths")
        paths_layout = QFormLayout()
        
        self.vna_data_path = QLineEdit()
        self.vna_data_path.setStyleSheet(Styles.SPINBOX_STYLE)
        self.vna_data_path.setText("data/vna")
        paths_layout.addRow("VNA Data:", self.vna_data_path)
        
        self.temp_data_path = QLineEdit()
        self.temp_data_path.setStyleSheet(Styles.SPINBOX_STYLE)
        self.temp_data_path.setText("data/temperature")
        paths_layout.addRow("Temperature Data:", self.temp_data_path)
        
        self.results_path = QLineEdit()
        self.results_path.setStyleSheet(Styles.SPINBOX_STYLE)
        self.results_path.setText("data/results")
        paths_layout.addRow("Results:", self.results_path)
        
        data_group.setLayout(paths_layout)
        data_layout.addWidget(data_group)
        data_tab.setLayout(data_layout)
        
        # Add tabs
        tab_widget.addTab(hardware_tab, "Hardware")
        tab_widget.addTab(data_tab, "Data")
        layout.addWidget(tab_widget)
        
        # Add dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Style buttons
        for button in button_box.buttons():
            button.setStyleSheet(Styles.BUTTON_STYLE)
            
        layout.addWidget(button_box)
        
    def accept(self):
        """Handle dialog acceptance"""
        try:
            print("[DEBUG] Settings dialog: Saving settings...")
            
            # Save settings
            settings = {
                'vna': {
                    'key': self.vna_key.text(),
                    'port': self.vna_port.currentText()
                },
                'data_paths': {
                    'vna': self.vna_data_path.text(),
                    'temperature': self.temp_data_path.text(),
                    'results': self.results_path.text()
                }
            }
            
            print(f"[DEBUG] Settings to save: {settings}")
            
            # Update parent's configuration
            if self.parent and hasattr(self.parent, 'controller'):
                self.parent.controller.update_settings(settings)
                self.parent.logger.append_message("Settings updated successfully", 'SUCCESS')
                print("[DEBUG] Settings saved successfully")
            else:
                print("[WARNING] Settings dialog: No parent controller found")
            
            super().accept()
            
        except Exception as e:
            import traceback
            print(f"[ERROR] Settings save error: {str(e)}")
            print("[ERROR] Traceback:")
            print(traceback.format_exc())
            
            if self.parent:
                self.parent.logger.append_message(f"Error saving settings: {str(e)}", 'ERROR')
            
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