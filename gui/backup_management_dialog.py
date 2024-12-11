from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPushButton, 
                             QFileDialog, QMessageBox, QLabel, QProgressBar)
from PyQt6.QtCore import Qt
import os
import shutil
import json
from datetime import datetime
from utils.logger import gui_logger
from .styles import Styles

class BackupManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Backup Management")
        self.setStyleSheet(Styles.DIALOG_STYLE)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Select an operation:")
        self.status_label.setStyleSheet(Styles.LABEL_STYLE)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setStyleSheet(Styles.PROGRESS_STYLE)
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # Backup button
        backup_btn = QPushButton("Create Backup")
        backup_btn.setStyleSheet(Styles.BUTTON_STYLE)
        backup_btn.clicked.connect(self.create_backup)
        layout.addWidget(backup_btn)
        
        # Restore button
        restore_btn = QPushButton("Restore from Backup")
        restore_btn.setStyleSheet(Styles.BUTTON_STYLE)
        restore_btn.clicked.connect(self.restore_backup)
        layout.addWidget(restore_btn)
        
    def create_backup(self):
        try:
            # Get backup directory from user
            backup_dir = QFileDialog.getExistingDirectory(
                self, "Select Backup Location",
                os.path.expanduser("~"),
                QFileDialog.Option.ShowDirsOnly
            )
            
            if not backup_dir:
                return
                
            # Create timestamped backup folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"ts1500_backup_{timestamp}")
            os.makedirs(backup_path)
            
            # Files and directories to backup
            to_backup = [
                "config.yaml",
                "data",
                "logs",
                "configs"
            ]
            
            self.progress.setMaximum(len(to_backup))
            self.progress.show()
            
            # Copy files and directories
            for i, item in enumerate(to_backup):
                src = os.path.join(os.path.dirname(os.path.dirname(__file__)), item)
                dst = os.path.join(backup_path, item)
                
                if os.path.exists(src):
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                        
                self.progress.setValue(i + 1)
                self.status_label.setText(f"Backing up: {item}")
                
            # Create backup info file
            info = {
                "timestamp": timestamp,
                "items": to_backup
            }
            
            with open(os.path.join(backup_path, "backup_info.json"), "w") as f:
                json.dump(info, f, indent=4)
                
            self.progress.hide()
            self.status_label.setText("Backup completed successfully!")
            gui_logger.info(f"Backup created at: {backup_path}")
            
            QMessageBox.information(
                self,
                "Backup Complete",
                f"Backup has been created at:\n{backup_path}"
            )
            
        except Exception as e:
            self.progress.hide()
            error_msg = f"Error creating backup: {str(e)}"
            self.status_label.setText(error_msg)
            gui_logger.error(error_msg)
            QMessageBox.critical(
                self,
                "Backup Error",
                error_msg
            )
            
    def restore_backup(self):
        try:
            # Get backup directory from user
            backup_dir = QFileDialog.getExistingDirectory(
                self, "Select Backup to Restore",
                os.path.expanduser("~"),
                QFileDialog.Option.ShowDirsOnly
            )
            
            if not backup_dir or not os.path.exists(os.path.join(backup_dir, "backup_info.json")):
                QMessageBox.warning(
                    self,
                    "Invalid Backup",
                    "Please select a valid backup directory containing backup_info.json"
                )
                return
                
            # Read backup info
            with open(os.path.join(backup_dir, "backup_info.json")) as f:
                info = json.load(f)
                
            # Confirm restore
            reply = QMessageBox.question(
                self,
                "Confirm Restore",
                "This will overwrite existing files. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
                
            self.progress.setMaximum(len(info["items"]))
            self.progress.show()
            
            # Restore files and directories
            for i, item in enumerate(info["items"]):
                src = os.path.join(backup_dir, item)
                dst = os.path.join(os.path.dirname(os.path.dirname(__file__)), item)
                
                if os.path.exists(src):
                    # Remove existing
                    if os.path.exists(dst):
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        else:
                            os.remove(dst)
                            
                    # Copy from backup
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                        
                self.progress.setValue(i + 1)
                self.status_label.setText(f"Restoring: {item}")
                
            self.progress.hide()
            self.status_label.setText("Restore completed successfully!")
            gui_logger.info(f"Backup restored from: {backup_dir}")
            
            QMessageBox.information(
                self,
                "Restore Complete",
                "Backup has been restored successfully.\nPlease restart the application."
            )
            
        except Exception as e:
            self.progress.hide()
            error_msg = f"Error restoring backup: {str(e)}"
            self.status_label.setText(error_msg)
            gui_logger.error(error_msg)
            QMessageBox.critical(
                self,
                "Restore Error",
                error_msg
            )