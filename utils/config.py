import os
import yaml
from utils.logger import gui_logger

class Config:
    def __init__(self):
        self.config_file = 'config.yaml'
        self.config = self.load_config()
        
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f)
                gui_logger.info("Configuration loaded successfully")
                return config or {}
            else:
                gui_logger.info("No configuration file found, creating default")
                return self.create_default_config()
        except Exception as e:
            gui_logger.error(f"Error loading configuration: {str(e)}")
            return self.create_default_config()
            
    def create_default_config(self):
        """Create default configuration"""
        config = {
            'theme': {
                'dark_mode': True,
                'font_size': 12
            },
            'test_parameters': {
                'tilt_increment': 1.0,
                'min_tilt': -30.0,
                'max_tilt': 30.0,
                'oil_level_time': 15,
                'tilt_accuracy': 0.1
            },
            'vna': {
                'key': 'F5',
                'port': 'COM1'
            },
            'data_paths': {
                'vna': 'data/vna',
                'temperature': 'data/temperature',
                'results': 'data/results'
            },
            'logging': {
                'level': 'INFO'
            }
        }
        
        self.save_config(config)
        return config
        
    def save_config(self, config=None):
        """Save configuration to YAML file"""
        try:
            if config is not None:
                self.config = config
                
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            gui_logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            gui_logger.error(f"Error saving configuration: {str(e)}")
            return False
            
    def save(self):
        """Save current configuration"""
        return self.save_config()
        
    def get(self, section, key, default=None):
        """Get configuration value"""
        try:
            return self.config.get(section, {}).get(key, default)
        except Exception as e:
            gui_logger.error(f"Error getting configuration value: {str(e)}")
            return default
            
    def set(self, section, key, value):
        """Set configuration value"""
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            return True
        except Exception as e:
            gui_logger.error(f"Error setting configuration value: {str(e)}")
            return False
            
    def update_test_parameters(self, parameters):
        """Update test parameters in configuration"""
        try:
            self.config['test_parameters'] = parameters
            self.save()
            return True
        except Exception as e:
            gui_logger.error(f"Error updating test parameters: {str(e)}")
            return False 