import os
import json
import logging
from utils.logger import gui_logger

class Config:
    def __init__(self, config_file='config.json'):
        self.logger = gui_logger
        self.config_file = config_file
        self.config = self.load_default_config()
        
        # Load existing config if it exists
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    saved_config = json.load(f)
                self.config.update(saved_config)
                self.logger.info("Configuration loaded successfully")
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")
        else:
            self.save()
            self.logger.info("Created new configuration file")
    
    def load_default_config(self):
        """Load default configuration"""
        return {
            'logging': {
                'level': 'INFO',
                'file': 'app.log'
            },
            'hardware': {
                'port': None,
                'baudrate': 115200,
                'timeout': 1.0
            },
            'web_server': {
                'enabled': False,
                'host': '0.0.0.0',
                'port': 5000
            },
            'test': {
                'default_angle_range': (-15, 15),
                'default_step_size': 1,
                'default_dwell_time': 5
            }
        }
    
    def get(self, section, key, default=None):
        """Get configuration value"""
        try:
            return self.config.get(section, {}).get(key, default)
        except Exception as e:
            self.logger.error(f"Error getting config value {section}.{key}: {e}")
            return default
    
    def set(self, section, key, value):
        """Set configuration value"""
        try:
            if section not in self.config:
                self.config[section] = {}
            self.config[section][key] = value
            self.logger.info(f"Config updated: {section}.{key} = {value}")
        except Exception as e:
            self.logger.error(f"Error setting config value {section}.{key}: {e}")
    
    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = self.load_default_config()
        self.save()
        self.logger.info("Configuration reset to defaults") 