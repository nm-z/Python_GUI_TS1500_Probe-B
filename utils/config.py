import os
import yaml
from utils.logger import gui_logger

class Config:
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.config_file = 'config.yaml'
            cls._instance._load_initial_config()
        return cls._instance
    
    def _load_initial_config(self):
        """Load configuration from YAML file only once"""
        if self._config is None:
            try:
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r') as f:
                        self._config = yaml.safe_load(f)
                    gui_logger.info("Configuration loaded successfully")
                else:
                    gui_logger.info("No configuration file found, creating default")
                    self._config = self.create_default_config()
            except Exception as e:
                gui_logger.error(f"Error loading configuration: {str(e)}")
                self._config = self.create_default_config()
        return self._config
    
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
                self._config = config
                
            with open(self.config_file, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False)
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
            return self._config.get(section, {}).get(key, default)
        except Exception as e:
            gui_logger.error(f"Error getting configuration value: {str(e)}")
            return default
            
    def set(self, section, key, value):
        """Set configuration value"""
        try:
            if section not in self._config:
                self._config[section] = {}
            self._config[section][key] = value
            return True
        except Exception as e:
            gui_logger.error(f"Error setting configuration value: {str(e)}")
            return False
            
    def update_test_parameters(self, parameters):
        """Update test parameters in configuration"""
        try:
            self._config['test_parameters'] = parameters
            self.save()
            return True
        except Exception as e:
            gui_logger.error(f"Error updating test parameters: {str(e)}")
            return False 
        
    def load(self):
        """Force reload configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self._config = yaml.safe_load(f)
                gui_logger.info("Configuration reloaded successfully")
            return True
        except Exception as e:
            gui_logger.error(f"Error reloading configuration: {str(e)}")
            return False