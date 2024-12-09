from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QPushButton, QFileDialog)
from utils.logger import gui_logger
from utils.config import Config

class SettingsPanel(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.config = Config()
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        
        # Hardware Settings Group
        hw_group = QGroupBox("Hardware Settings")
        hw_layout = QVBoxLayout()
        
        # Arduino settings
        baud_layout = QHBoxLayout()
        baud_label = QLabel("Baud Rate:")
        self.baud_rate = QSpinBox()
        self.baud_rate.setRange(1200, 115200)
        self.baud_rate.setValue(self.config.get('hardware', 'arduino', 'baud_rate', default=9600))
        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baud_rate)
        hw_layout.addLayout(baud_layout)
        
        # Stepper motor settings
        steps_layout = QHBoxLayout()
        steps_label = QLabel("Steps/Rev:")
        self.steps_per_rev = QSpinBox()
        self.steps_per_rev.setRange(1, 1000)
        self.steps_per_rev.setValue(
            self.config.get('hardware', 'stepper_motor', 'steps_per_revolution', default=200)
        )
        steps_layout.addWidget(steps_label)
        steps_layout.addWidget(self.steps_per_rev)
        hw_layout.addLayout(steps_layout)
        
        hw_group.setLayout(hw_layout)
        
        # Data Collection Settings Group
        data_group = QGroupBox("Data Collection")
        data_layout = QVBoxLayout()
        
        # Logging interval
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Log Interval (s):")
        self.log_interval = QDoubleSpinBox()
        self.log_interval.setRange(0.1, 60.0)
        self.log_interval.setValue(self.config.get('data', 'logging_interval', default=1.0))
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.log_interval)
        data_layout.addLayout(interval_layout)
        
        # History duration
        history_layout = QHBoxLayout()
        history_label = QLabel("History (hours):")
        self.history_hours = QSpinBox()
        self.history_hours.setRange(1, 24)
        self.history_hours.setValue(self.config.get('data', 'max_history_hours', default=1))
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.history_hours)
        data_layout.addLayout(history_layout)
        
        # Backup settings
        backup_layout = QHBoxLayout()
        self.enable_backup = QCheckBox("Enable Backup")
        self.enable_backup.setChecked(self.config.get('data', 'backup', 'enabled', default=True))
        backup_layout.addWidget(self.enable_backup)
        data_layout.addLayout(backup_layout)
        
        data_group.setLayout(data_layout)
        
        # Web Server Settings Group
        web_group = QGroupBox("Web Server")
        web_layout = QVBoxLayout()
        
        # Enable web server
        self.enable_web = QCheckBox("Enable Web Server")
        self.enable_web.setChecked(self.config.get('web_server', 'enabled', default=False))
        
        # Port setting
        port_layout = QHBoxLayout()
        port_label = QLabel("Port:")
        self.web_port = QSpinBox()
        self.web_port.setRange(1024, 65535)
        self.web_port.setValue(self.config.get('web_server', 'port', default=5000))
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.web_port)
        
        web_layout.addWidget(self.enable_web)
        web_layout.addLayout(port_layout)
        web_group.setLayout(web_layout)
        
        # Save and Reset buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Settings")
        self.reset_button = QPushButton("Reset to Defaults")
        self.save_button.clicked.connect(self.save_settings)
        self.reset_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        
        # Add all groups to main layout
        layout.addWidget(hw_group)
        layout.addWidget(data_group)
        layout.addWidget(web_group)
        layout.addLayout(button_layout)
        layout.addStretch()
        
        gui_logger.debug("Settings panel initialized")

    def save_settings(self):
        """Save current settings to configuration"""
        try:
            # Hardware settings
            self.config.update('hardware', 'arduino', 'baud_rate',
                             value=self.baud_rate.value())
            self.config.update('hardware', 'stepper_motor', 'steps_per_revolution',
                             value=self.steps_per_rev.value())
            
            # Data collection settings
            self.config.update('data', 'logging_interval',
                             value=self.log_interval.value())
            self.config.update('data', 'max_history_hours',
                             value=self.history_hours.value())
            self.config.update('data', 'backup', 'enabled',
                             value=self.enable_backup.isChecked())
            
            # Web server settings
            self.config.update('web_server', 'enabled',
                             value=self.enable_web.isChecked())
            self.config.update('web_server', 'port',
                             value=self.web_port.value())
            
            gui_logger.info("Settings saved successfully")
        except Exception as e:
            gui_logger.error(f"Error saving settings: {e}", exc_info=True)

    def reset_settings(self):
        """Reset settings to default values"""
        try:
            # Reset configuration to defaults
            self.config._config = self.config._get_default_config()
            self.config.save()
            
            # Update UI elements
            self.baud_rate.setValue(self.config.get('hardware', 'arduino', 'baud_rate'))
            self.steps_per_rev.setValue(
                self.config.get('hardware', 'stepper_motor', 'steps_per_revolution')
            )
            self.log_interval.setValue(self.config.get('data', 'logging_interval'))
            self.history_hours.setValue(self.config.get('data', 'max_history_hours'))
            self.enable_backup.setChecked(self.config.get('data', 'backup', 'enabled'))
            self.enable_web.setChecked(self.config.get('web_server', 'enabled'))
            self.web_port.setValue(self.config.get('web_server', 'port'))
            
            gui_logger.info("Settings reset to defaults")
        except Exception as e:
            gui_logger.error(f"Error resetting settings: {e}", exc_info=True)
