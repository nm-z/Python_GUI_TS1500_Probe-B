import os
import shutil
import datetime
from utils.logger import gui_logger

def backup_data(source_dir, backup_base_dir='backup'):
    """
    Backup data files to a timestamped directory.
    
    Args:
        source_dir (str): Directory containing data files to backup
        backup_base_dir (str): Base directory for backups
        
    Returns:
        str: Path to backup directory if successful, None otherwise
    """
    try:
        # Create timestamp for backup directory
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(backup_base_dir, f"backup_{timestamp}")
        
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Copy all CSV files
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.csv'):
                    src_path = os.path.join(root, file)
                    dst_path = os.path.join(backup_dir, file)
                    shutil.copy2(src_path, dst_path)
                    gui_logger.debug(f"Backed up {file}")
        
        gui_logger.info(f"Data backed up to {backup_dir}")
        return backup_dir
    except Exception as e:
        gui_logger.error(f"Failed to backup data: {e}", exc_info=True)
        return None

def cleanup_old_backups(backup_base_dir='backup', max_backups=10):
    """
    Remove old backups keeping only the most recent ones.
    
    Args:
        backup_base_dir (str): Base directory for backups
        max_backups (int): Maximum number of backups to keep
        
    Returns:
        bool: True if cleanup successful, False otherwise
    """
    try:
        if not os.path.exists(backup_base_dir):
            return True
            
        # List all backup directories
        backup_dirs = []
        for item in os.listdir(backup_base_dir):
            item_path = os.path.join(backup_base_dir, item)
            if os.path.isdir(item_path) and item.startswith('backup_'):
                backup_dirs.append(item_path)
        
        # Sort by creation time (newest first)
        backup_dirs.sort(key=lambda x: os.path.getctime(x), reverse=True)
        
        # Remove old backups
        for old_backup in backup_dirs[max_backups:]:
            shutil.rmtree(old_backup)
            gui_logger.debug(f"Removed old backup: {old_backup}")
        
        return True
    except Exception as e:
        gui_logger.error(f"Failed to cleanup old backups: {e}", exc_info=True)
        return False 