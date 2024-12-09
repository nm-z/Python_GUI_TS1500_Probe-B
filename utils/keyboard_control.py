import keyboard
import time
import logging
from utils.logger import gui_logger

def trigger_vna_sweep(key='F11'):
    """
    Trigger VNA sweep by simulating key press
    
    Args:
        key (str): Key to press (default: F11)
    """
    try:
        # Press and release the configured key
        keyboard.press(key)
        time.sleep(0.1)  # Small delay to ensure key press is registered
        keyboard.release(key)
        gui_logger.info(f"VNA sweep triggered using {key}")
        return True
    except Exception as e:
        gui_logger.error(f"Failed to trigger VNA sweep with {key}: {e}")
        return False 