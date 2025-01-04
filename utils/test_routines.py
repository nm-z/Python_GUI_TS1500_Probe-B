"""Test routine functionality"""
import time
import os
from datetime import datetime
import pyautogui

def run_test_setup():
    """Get test parameters from user"""
    try:
        print("\n\033[93mTest Setup\033[0m")
        print("\033[93m==========\033[0m\n")
        
        # First select test type
        print("\033[96mSelect Test Type:\033[0m")
        print("  1. \033[93mTilt Test\033[0m - Starts at min position, increments up")
        print("  2. \033[93mFill Test\033[0m - Uses position 0 as first point")
        while True:
            test_type = input("\n\033[96mEnter test type (1/2): \033[0m").strip()
            if test_type in ["1", "2"]:
                break
            print("\033[91mInvalid choice. Please enter 1 for Tilt Test or 2 for Fill Test\033[0m")
        
        print(f"\n\033[92mSelected: {'Tilt' if test_type == '1' else 'Fill'} Test\033[0m")
        print("\n\033[93mTest Parameters (press Enter to use default value):\033[0m")
        print("\033[93mDefaults shown in [brackets]\033[0m\n")
        
        # Use different defaults based on test type
        if test_type == "2":  # Fill Test
            step_increment = float(input("\033[96mSteps per increment \033[93m[520 steps]\033[96m: \033[0m").strip() or "520")
            num_steps = int(input("\033[96mNumber of steps \033[93m[21]\033[96m: \033[0m").strip() or "21")
            num_loops = int(input("\033[96mNumber of loops \033[93m[20]\033[96m: \033[0m").strip() or "20")
            vna_dwell = float(input("\033[96mVNA dwell time \033[93m[10 seconds]\033[96m: \033[0m").strip() or "10")
            oil_dwell = float(input("\033[96mOil settling time \033[93m[3 seconds]\033[96m: \033[0m").strip() or "3")
            drain_delay = float(input("\033[96mDrain delay time \033[93m[20 seconds]\033[96m: \033[0m").strip() or "20")
        else:  # Tilt Test
            step_increment = float(input("\033[96mSteps per increment \033[93m[200 steps]\033[96m: \033[0m").strip() or "200")
            num_steps = int(input("\033[96mNumber of steps \033[93m[25]\033[96m: \033[0m").strip() or "25")
            num_loops = int(input("\033[96mNumber of loops \033[93m[1]\033[96m: \033[0m").strip() or "1")
            vna_dwell = float(input("\033[96mVNA dwell time \033[93m[3 seconds]\033[96m: \033[0m").strip() or "3")
            oil_dwell = float(input("\033[96mOil settling time \033[93m[3 seconds]\033[96m: \033[0m").strip() or "3")
            drain_delay = float(input("\033[96mDrain delay time \033[93m[20 seconds]\033[96m: \033[0m").strip() or "20")
        
        return {
            'test_type': test_type,
            'step_increment': step_increment,
            'num_steps': num_steps,
            'num_loops': num_loops,
            'vna_dwell': vna_dwell,
            'oil_dwell': oil_dwell,
            'drain_delay': drain_delay
        }
    except ValueError as e:
        print(f"\033[91mInvalid input: {str(e)}\033[0m")
        return None

def run_test_routine(controller, params, logger):
    """Run the test routine with given parameters"""
    try:
        logger.info("Starting test routine...")
        
        # Create temperature log directory if it doesn't exist
        temp_log_dir = "/home/nate/Desktop/TEMP_Export_Tilt-Test_001"
        if not os.path.exists(temp_log_dir):
            os.makedirs(temp_log_dir)
            
        # Get next test run number
        run_counter_file = os.path.join(temp_log_dir, ".run_counter")
        if os.path.exists(run_counter_file):
            with open(run_counter_file, 'r') as f:
                run_number = int(f.read().strip()) + 1
        else:
            run_number = 1
        
        # Create CSV file with timestamp and run number in name
        timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
        temp_log_file = os.path.join(temp_log_dir, f"test_run_{run_number:03d}_{timestamp}_temp.csv")
        
        # Create CSV file with headers
        with open(temp_log_file, 'w') as f:
            f.write("timestamp,temperature,tilt\n")
        
        # For fill test, take first measurement at current position (after homing)
        if params['test_type'] == "fill":
            logger.info("Fill Test: Taking first measurement at home position...")
            time.sleep(params['oil_dwell'])
            
            # Take initial measurement (point 1)
            logger.info("Taking measurement at home position (point 1)...")
            try:
                pyautogui.press('f12')
            except Exception as e:
                logger.error(f"Error triggering VNA sweep: {str(e)}")
                return False
            
            # Wait for VNA
            logger.info(f"Waiting {params['vna_dwell']}s for VNA sweep...")
            time.sleep(params['vna_dwell'])
            
            # Get temperature and tilt readings
            controller._arduino.write(b"TEMP\n")
            temp_response = controller._arduino.readline().decode('utf-8').strip()
            logger.info(f"Temperature: {temp_response}")
            
            controller._arduino.write(b"TILT\n")
            tilt_response = controller._arduino.readline().decode('utf-8').strip()
            logger.info(f"Tilt: {tilt_response}")
            
            # Log temperature and tilt to CSV
            try:
                temp_value = float(temp_response.split()[-1])
                tilt_value = float(tilt_response.split()[-1])
                timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                with open(temp_log_file, 'a') as f:
                    f.write(f"{timestamp},{temp_value:.2f},{tilt_value:.2f}\n")
            except Exception as e:
                logger.error(f"Error logging data: {str(e)}")
                return False

        total_measurements = int(params['num_steps']) * int(params['num_loops'])
        current_measurement = 0

        for loop in range(params['num_loops']):
            logger.info(f"Starting loop {loop + 1} of {params['num_loops']}")
            
            # Do measurements with step increments
            for i in range(int(params['num_steps'])):
                current_measurement += 1
                progress = (current_measurement / total_measurements) * 100
                logger.info(f"Progress: {progress:.1f}% (Loop {loop + 1}/{params['num_loops']})")
                
                # Move motor by step increment
                logger.info(f"Moving +{params['step_increment']} steps")
                controller._arduino.write(f"MOVE {params['step_increment']}\n".encode())
                while True:
                    response = controller._arduino.readline().decode('utf-8').strip()
                    if response:
                        logger.info(response)
                        if "Movement complete" in response:
                            break
                        elif "ERROR" in response:
                            logger.error(f"Movement error: {response}")
                            return False
                
                # Wait for oil to settle
                logger.info(f"Waiting {params['oil_dwell']}s for oil to settle...")
                time.sleep(params['oil_dwell'])
                
                # Trigger VNA sweep
                logger.info("Triggering VNA sweep...")
                try:
                    pyautogui.press('f12')
                except Exception as e:
                    logger.error(f"Error triggering VNA sweep: {str(e)}")
                    return False
                
                # Wait for VNA
                logger.info(f"Waiting {params['vna_dwell']}s for VNA sweep...")
                time.sleep(params['vna_dwell'])
                
                # Get temperature and tilt readings
                controller._arduino.write(b"TEMP\n")
                temp_response = controller._arduino.readline().decode('utf-8').strip()
                logger.info(f"Temperature: {temp_response}")
                
                controller._arduino.write(b"TILT\n")
                tilt_response = controller._arduino.readline().decode('utf-8').strip()
                logger.info(f"Tilt: {tilt_response}")
                
                # Log temperature and tilt to CSV
                try:
                    temp_value = float(temp_response.split()[-1])
                    tilt_value = float(tilt_response.split()[-1])
                    timestamp = datetime.now().strftime('%y%m%d_%H%M%S')
                    with open(temp_log_file, 'a') as f:
                        f.write(f"{timestamp},{temp_value:.2f},{tilt_value:.2f}\n")
                except Exception as e:
                    logger.error(f"Error logging data: {str(e)}")
                    return False
                    
                # Wait for drain delay if specified
                if params['drain_delay'] > 0:
                    logger.info(f"Waiting {params['drain_delay']}s for drain delay...")
                    time.sleep(params['drain_delay'])
                    
        # Test completed successfully
        logger.info("Test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        return False 