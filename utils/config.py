import os
import yaml
from utils.logger import gui_logger

class Config:
    def __init__(self):
        self.config_file = 'config.yaml'
        self.config = {}  # Initialize empty config
        self.load_config()  # Load or create default config
        
    def load_config(self):
        """Load configuration from file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config is not None:
                        self.config = loaded_config
            else:
                self.create_default_config()
        except Exception as e:
            print(f"Error loading config: {str(e)}")
            self.create_default_config()
            
    def create_default_config(self):
        """Create default configuration"""
        self.config = {
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
            }
        }
        self.save_config()
            
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            
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
            return self.config.get(section, {}).get(key, default)
        except Exception:
            return default
            
    def set(self, section, key, value):
        """Set configuration value
        
        Args:
            section (str): Configuration section
            key (str): Configuration key
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()
        
    def update_test_parameters(self, parameters):
        """Update test parameters
        
        Args:
            parameters (dict): Dictionary containing test parameters
        """
        if not isinstance(self.config, dict):
            self.config = {}
        self.config['test_parameters'] = parameters
        self.save_config() 

    def load_last_config(self):
        """Load the last used test parameters from configuration"""
        try:
            test_params = self.config.get('test_parameters', None)
            if test_params is None:
                test_params = {
                    'tilt_increment': 1.0,
                    'min_tilt': -30.0,
                    'max_tilt': 30.0,
                    'oil_level_time': 15,
                    'tilt_accuracy': 0.1
                }
                self.config['test_parameters'] = test_params
                self.save_config()
            return test_params
        except Exception as e:
            print(f"Error loading last config: {str(e)}")
            return None