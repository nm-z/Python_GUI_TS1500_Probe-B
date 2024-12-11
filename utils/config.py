import os
import yaml
from PyQt6.QtCore import QSettings
from utils.logger import gui_logger

class Config:
    def __init__(self):
        self.settings = QSettings()
        self.config_data = {}
        self.load_config()
        
    def load_config(self, config_path=None):
        """Load configuration from YAML file
        
        Args:
            config_path (str, optional): Path to config file. If None, loads last used or default.
        """
        try:
            if not config_path:
                config_path = self.settings.value("last_config_path")
                
            if config_path and os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.config_data = yaml.safe_load(f)
            else:
                self.load_defaults()
                
        except Exception as e:
            gui_logger.error(f"Error loading configuration: {str(e)}")
            self.load_defaults()
            
    def load_defaults(self):
        """Load default configuration values"""
        self.config_data = {
            'test_parameters': {
                'tilt_increment': 1.0,
                'min_tilt': -30.0,
                'max_tilt': 30.0,
                'oil_level_time': 15
            },
            'vna': {
                'key_event': 'F5',  # Default key event for VNA sweep
                'port': 'COM1'
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/app.log'
            },
            'data_paths': {
                'vna_data': 'data/vna',
                'temperature_data': 'data/temperature',
                'results': 'data/results'
            }
        }
        
    def save_config(self, config_path):
        """Save current configuration to YAML file
        
        Args:
            config_path (str): Path to save configuration file
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
                
            # Save as last used config
            self.settings.setValue("last_config_path", config_path)
            gui_logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            gui_logger.error(f"Error saving configuration: {str(e)}")
            
    def get(self, section, key, default=None):
        """Get configuration value
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        try:
            return self.config_data[section][key]
        except KeyError:
            return default
            
    def set(self, section, key, value):
        """Set configuration value
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            value: Value to set
        """
        if section not in self.config_data:
            self.config_data[section] = {}
        self.config_data[section][key] = value
        
    def update_test_parameters(self, parameters):
        """Update test parameters in configuration
        
        Args:
            parameters (dict): Dictionary of test parameters
        """
        self.config_data['test_parameters'].update(parameters)
        
    def get_test_parameters(self):
        """Get current test parameters
        
        Returns:
            dict: Dictionary of test parameters
        """
        return self.config_data.get('test_parameters', {}) 