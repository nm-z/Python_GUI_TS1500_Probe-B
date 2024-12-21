import os
import csv
import json
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from utils.logger import gui_logger

class DataModel:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.files = {
            "vna_data": os.path.join(self.data_dir, 'vna_data.csv'),
            "temperature": os.path.join(self.data_dir, 'temperature.csv'),
            "test_runs": os.path.join(self.data_dir, 'test_runs.csv')
        }
        
        # Initialize data storage
        self.dataframes = {}
        self.initialize_files()
        
        # Test configuration
        self.test_config = {
            'tilt_range': (-15, 15),  # -15° to +15°
            'step_size': 1,  # 1 degree steps
            'current_run': 1,
            'total_runs': 1,
            'current_angle': 0,
            'start_time': None,
            'completion_percentage': 0
        }
        
        # Current values
        self.last_temp = None
        self.last_vna_data = None
        self.current_tilt = 0.0

    def initialize_files(self):
        """Initialize CSV files with headers"""
        headers = {
            "vna_data": ["Timestamp", "Run", "Angle", "Raw_Data_Path", "Notes"],
            "temperature": ["Timestamp", "Run", "Angle", "Temperature", "Notes"],
            "test_runs": ["Run", "Start_Time", "End_Time", "Status", "Total_Angles", "Completed_Angles", "Notes"]
        }
        
        for key, file in self.files.items():
            if not os.path.exists(file):
                with open(file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers[key])
            try:
                self.dataframes[key] = pd.read_csv(file)
            except Exception as e:
                gui_logger.error(f"Error reading {key} data: {e}")
                self.dataframes[key] = pd.DataFrame(columns=headers[key])

    def log_vna_data(self, raw_data_path, angle, notes=""):
        """Log VNA data with test parameters"""
        try:
            timestamp = datetime.now().isoformat()
            with open(self.files["vna_data"], 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, self.test_config['current_run'], 
                               angle, raw_data_path, notes])
            new_entry = pd.DataFrame([[timestamp, self.test_config['current_run'], 
                                     angle, raw_data_path, notes]], 
                                   columns=self.dataframes["vna_data"].columns)
            self.dataframes["vna_data"] = pd.concat([self.dataframes["vna_data"], 
                                                   new_entry], ignore_index=True)
            self.last_vna_data = raw_data_path
            
            # Verify data was saved
            verification = self.verify_data_storage(self.test_config['current_run'])
            if verification and verification['vna_data']['data_files_exist']:
                gui_logger.info(f"VNA data saved successfully at angle {angle}°")
                return True
            else:
                raise Exception("Data verification failed")
                
        except Exception as e:
            gui_logger.error(f"Error logging VNA data: {e}")
            return False

    def log_temperature(self, temperature, angle, notes=""):
        """Log temperature data with test parameters"""
        try:
            timestamp = datetime.now().isoformat()
            with open(self.files["temperature"], 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, self.test_config['current_run'], 
                               angle, temperature, notes])
            new_entry = pd.DataFrame([[timestamp, self.test_config['current_run'], 
                                     angle, temperature, notes]], 
                                   columns=self.dataframes["temperature"].columns)
            self.dataframes["temperature"] = pd.concat([self.dataframes["temperature"], 
                                                     new_entry], ignore_index=True)
            self.last_temp = temperature
            
            # Verify data was saved
            verification = self.verify_data_storage(self.test_config['current_run'])
            if verification:
                gui_logger.info(f"Temperature data saved successfully at angle {angle}°")
                return True
            else:
                raise Exception("Data verification failed")
                
        except Exception as e:
            gui_logger.error(f"Error logging temperature data: {e}")
            return False

    def start_new_test_run(self):
        """Start a new test run"""
        self.test_config['start_time'] = datetime.now()
        self.test_config['completion_percentage'] = 0
        with open(self.files["test_runs"], 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([self.test_config['current_run'], 
                           self.test_config['start_time'].isoformat(),
                           "", "Running", 
                           len(range(-15, 16)), 0, ""])

    def update_test_progress(self, completed_angles, status="Running", notes=""):
        """Update test run progress"""
        total_angles = len(range(-15, 16))
        self.test_config['completion_percentage'] = (completed_angles / total_angles) * 100
        
        # Update the test runs file
        df = pd.read_csv(self.files["test_runs"])
        current_run_mask = df['Run'] == self.test_config['current_run']
        if any(current_run_mask):
            df.loc[current_run_mask, 'Completed_Angles'] = completed_angles
            df.loc[current_run_mask, 'Status'] = status
            df.loc[current_run_mask, 'Notes'] = notes
            if status == "Completed":
                df.loc[current_run_mask, 'End_Time'] = datetime.now().isoformat()
            df.to_csv(self.files["test_runs"], index=False)

    def get_test_progress(self):
        """Get current test progress information"""
        return {
            'current_run': self.test_config['current_run'],
            'total_runs': self.test_config['total_runs'],
            'current_angle': self.test_config['current_angle'],
            'completion_percentage': self.test_config['completion_percentage'],
            'start_time': self.test_config['start_time']
        }

    def update_test_config(self, **kwargs):
        """Update test configuration parameters"""
        valid_keys = ['tilt_range', 'step_size', 'current_run', 
                     'total_runs', 'current_angle']
        for key, value in kwargs.items():
            if key in valid_keys:
                self.test_config[key] = value

    def load_data(self, file_path):
        """Load data from a file"""
        try:
            df = pd.read_csv(file_path)
            # Determine data type from filename
            for key in self.files:
                if key in file_path.lower():
                    self.dataframes[key] = df
                    gui_logger.info(f"Loaded {key} data from {file_path}")
                    return
            # If no specific type found, try to load based on column names
            if "Temperature" in df.columns:
                self.dataframes["temperature"] = df
            elif "Fill Level" in df.columns:
                self.dataframes["fill_level"] = df
            elif "Tilt Angle" in df.columns:
                self.dataframes["tilt_angle"] = df
            elif "VNA Data" in df.columns:
                self.dataframes["vna_data"] = df
            else:
                raise ValueError("Unknown data format")
        except Exception as e:
            gui_logger.error(f"Error loading data: {e}")
            raise

    def save_data(self, file_path):
        """Save data to a file"""
        try:
            # Determine data type from filename
            for key in self.files:
                if key in file_path.lower():
                    self.dataframes[key].to_csv(file_path, index=False)
                    gui_logger.info(f"Saved {key} data to {file_path}")
                    return
            # If no specific type found, save all data
            with pd.ExcelWriter(file_path) as writer:
                for key, df in self.dataframes.items():
                    df.to_excel(writer, sheet_name=key, index=False)
            gui_logger.info(f"Saved all data to {file_path}")
        except Exception as e:
            gui_logger.error(f"Error saving data: {e}")
            raise

    def export_data(self, file_path, format='csv'):
        """Export data to different formats"""
        try:
            if format == 'csv':
                # Export each dataset as separate CSV files in a ZIP archive
                import zipfile
                zip_path = file_path if file_path.endswith('.zip') else f"{file_path}.zip"
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for key, df in self.dataframes.items():
                        csv_path = f"{key}.csv"
                        df.to_csv(csv_path, index=False)
                        zipf.write(csv_path)
                        os.remove(csv_path)
                gui_logger.info(f"Data exported to ZIP archive: {zip_path}")
            elif format == 'excel':
                # Export all datasets to separate sheets in an Excel file
                with pd.ExcelWriter(file_path) as writer:
                    for key, df in self.dataframes.items():
                        df.to_excel(writer, sheet_name=key, index=False)
                gui_logger.info(f"Data exported to Excel file: {file_path}")
            elif format == 'json':
                # Export all datasets to a single JSON file
                data = {key: df.to_dict(orient='records') for key, df in self.dataframes.items()}
                with open(file_path, 'w') as jsonf:
                    json.dump(data, jsonf, indent=4)
                gui_logger.info(f"Data exported to JSON file: {file_path}")
            else:
                raise ValueError(f"Unsupported export format: {format}")
        except Exception as e:
            gui_logger.error(f"Error exporting data: {e}")
            raise

    def log_data(self, key, timestamp, value):
        """Log data to appropriate CSV file"""
        if key in self.files:
            try:
                with open(self.files[key], 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, value])
                # Update dataframe
                new_entry = pd.DataFrame([[timestamp, value]], columns=["Timestamp", "Value"])
                self.dataframes[key] = pd.concat([self.dataframes[key], new_entry], ignore_index=True)
                gui_logger.debug(f"Logged {key}: {value} at {timestamp}")
            except Exception as e:
                gui_logger.error(f"Error logging {key} data: {e}")
        else:
            gui_logger.warning(f"Attempted to log unknown key: {key}")

    def update_tilt(self, tilt_data):
        """Update current tilt values and log to CSV"""
        self.current_tilt.update(tilt_data)
        timestamp = datetime.now().isoformat()
        self.log_data("tilt_angle", timestamp, tilt_data.get('y', 0))  # Using y-axis tilt as primary measure

    def update_temperature(self, temp):
        """Update temperature value and log to CSV"""
        self.last_temp = temp
        timestamp = datetime.now().isoformat()
        self.log_data("temperature", timestamp, temp)

    def update_fill_level(self, level):
        """Update fill level value and log to CSV"""
        self.last_fill_level = level
        timestamp = datetime.now().isoformat()
        self.log_data("fill_level", timestamp, level)

    def get_latest_tilt(self):
        """Get the most recent tilt values"""
        return self.current_tilt

    def get_latest_temperature(self):
        """Get the most recent temperature value"""
        return self.last_temp

    def get_latest_fill_level(self):
        """Get the most recent fill level value"""
        return self.last_fill_level

    def get_data_history(self, key, hours=1):
        """Get historical data for a specific measurement"""
        if key in self.dataframes:
            df = self.dataframes[key]
            if not df.empty:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                cutoff_time = datetime.now() - timedelta(hours=hours)
                return df[df['Timestamp'] > cutoff_time]
        return pd.DataFrame(columns=["Timestamp", "Value"])

    def get_temperature_history(self, hours=1):
        """Get temperature history for plotting"""
        return self.get_data_history("temperature", hours)

    def get_tilt_history(self, hours=1):
        """Get tilt history for plotting"""
        return self.get_data_history("tilt_angle", hours)

    def get_fill_level_history(self, hours=1):
        """Get fill level history for plotting"""
        return self.get_data_history("fill_level", hours)

    def clear_data(self):
        """Clear all stored data"""
        for key, file in self.files.items():
            try:
                with open(file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Value"])
                self.dataframes[key] = pd.DataFrame(columns=["Timestamp", "Value"])
            except Exception as e:
                gui_logger.error(f"Error clearing {key} data: {e}")
        
        self.last_temp = None
        self.last_fill_level = 0.0
        self.current_tilt = {
            'x': 0.0, 'y': 0.0, 'z': 0.0,
            'gx': 0.0, 'gy': 0.0, 'gz': 0.0
        }

    def update_test_parameters(self, angle_increment=None, angle_step_size=None,
                             oil_leveling_time=None, tilt_angle_range=None):
        """Update test parameters"""
        if angle_increment is not None:
            self.angle_increment = angle_increment
        if angle_step_size is not None:
            self.angle_step_size = angle_step_size
        if oil_leveling_time is not None:
            self.oil_leveling_time = oil_leveling_time
        if tilt_angle_range is not None:
            self.tilt_angle_range = tilt_angle_range

    def verify_data_storage(self, run_number):
        """Verify that data for a specific run was saved correctly"""
        try:
            # Check VNA data
            vna_df = self.dataframes["vna_data"]
            vna_run_data = vna_df[vna_df["Run"] == run_number]
            
            # Check temperature data
            temp_df = self.dataframes["temperature"]
            temp_run_data = temp_df[temp_df["Run"] == run_number]
            
            # Get expected number of angles
            angle_range = range(
                self.test_config['tilt_range'][0],
                self.test_config['tilt_range'][1] + 1,
                self.test_config['step_size']
            )
            expected_angles = len(list(angle_range))
            
            # Verify data completeness
            verification = {
                'vna_data': {
                    'saved_angles': len(vna_run_data),
                    'expected_angles': expected_angles,
                    'missing_angles': [],
                    'data_files_exist': True
                },
                'temperature_data': {
                    'saved_angles': len(temp_run_data),
                    'expected_angles': expected_angles,
                    'missing_angles': []
                }
            }
            
            # Check for missing angles
            saved_vna_angles = set(vna_run_data["Angle"].unique())
            saved_temp_angles = set(temp_run_data["Angle"].unique())
            expected_angle_set = set(angle_range)
            
            verification['vna_data']['missing_angles'] = list(
                expected_angle_set - saved_vna_angles
            )
            verification['temperature_data']['missing_angles'] = list(
                expected_angle_set - saved_temp_angles
            )
            
            # Verify VNA data files exist
            for _, row in vna_run_data.iterrows():
                if not os.path.exists(row["Raw_Data_Path"]):
                    verification['vna_data']['data_files_exist'] = False
                    break
            
            return verification
            
        except Exception as e:
            gui_logger.error(f"Error verifying data storage: {e}")
            return None