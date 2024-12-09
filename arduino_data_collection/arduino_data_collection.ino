#include <AccelStepper.h>
#include <Wire.h>
#include <MPU6050.h>

// Pin Definitions
#define HOMING_SWITCH_PIN 3     // Limit switch for homing
#define EMERGENCY_STOP_PIN 4    // Emergency stop button
#define STEPS_PER_REV 200      // Steps per revolution for your stepper

// System Limits
#define MIN_ANGLE -360.0
#define MAX_ANGLE 360.0
#define MAX_STEPS (MAX_ANGLE * STEPS_PER_REV / 360.0)
#define MIN_STEPS (-MAX_STEPS)
#define SERIAL_TIMEOUT 1000     // Serial timeout in milliseconds

// AccelStepper Setup
AccelStepper stepper(1, 9, 8);  // (Type:driver, STEP, DIR)

// MPU6050 Setup
MPU6050 mpu;
bool mpuInitialized = false;

// Constants
const int MAX_SPEED = 1000.0;     // Maximum speed in steps/second
const int DEFAULT_SPEED = 200.0;   // Default speed in steps/second
const int ACCELERATION = 500.0;    // Acceleration in steps/second^2
const int POST_MOVE_DELAY = 5;     // wait for move to finish and settle
const int POST_MEASURE_DELAY = 250; // wait for measurement to complete
const float STEPS_PER_DEGREE = STEPS_PER_REV / 360.0; // For angle calculations

// System State
bool isEmergencyStopped = false;
bool isHomed = false;
unsigned long lastMoveTime = 0;
unsigned long IDLE_TIMEOUT = 300000; // 5 minutes in milliseconds

// Time tracking
unsigned long startTime;
String inputBuffer = "";

// MPU6050 data
int16_t ax, ay, az;
int16_t gx, gy, gz;
float pitch, roll;

// Calculate tilt angles from accelerometer data
void calculateTilt() {
  // Get raw accelerometer data
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  
  // Convert to angles (in degrees)
  // Using atan2 for better quadrant handling
  pitch = atan2(ay, sqrt(pow(ax, 2) + pow(az, 2))) * 180.0 / M_PI;
  roll = atan2(-ax, sqrt(pow(ay, 2) + pow(az, 2))) * 180.0 / M_PI;
}

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  Serial.setTimeout(1000);
  
  // Configure stepper
  stepper.setMaxSpeed(MAX_SPEED);
  stepper.setSpeed(DEFAULT_SPEED);
  stepper.setAcceleration(ACCELERATION);
  stepper.setCurrentPosition(0);
  
  // Initialize I2C for MPU6050
  Wire.begin();
  delay(50);  // Give I2C time to initialize
  
  // Initialize MPU6050
  mpu.initialize();
  mpuInitialized = mpu.testConnection();
  
  if (mpuInitialized) {
    // Configure MPU6050 settings
    mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2); // ±2g range for better precision
    mpu.setDLPFMode(MPU6050_DLPF_BW_5);            // Set digital low-pass filter
  }
  
  // Initialize time
  startTime = millis();
  lastMoveTime = startTime;
  
  // Send ready signal
  Serial.println("READY");
}

void loop() {
  // Check emergency stop
  if (digitalRead(EMERGENCY_STOP_PIN) == LOW && !isEmergencyStopped) {
    emergencyStop();
  }
  
  // Check idle timeout
  if (millis() - lastMoveTime > IDLE_TIMEOUT) {
    stepper.disableOutputs();
  }
  
  // Read and process serial commands
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      processCommand(inputBuffer);
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }
  
  // Run stepper
  stepper.run();
}

void processCommand(String command) {
  if (command == "TEST") {
    Serial.println("START_TEST");
    
    // Test stepper motor
    stepper.enableOutputs();
    bool stepperOk = true;
    
    // Test MPU6050
    bool mpuOk = mpuInitialized;
    
    // Test limit switch
    bool limitOk = (digitalRead(HOMING_SWITCH_PIN) == HIGH || digitalRead(HOMING_SWITCH_PIN) == LOW);
    
    // Test emergency stop
    bool emergencyOk = (digitalRead(EMERGENCY_STOP_PIN) == HIGH || digitalRead(EMERGENCY_STOP_PIN) == LOW);
    
    // Report results
    Serial.print("STEPPER:");
    Serial.println(stepperOk ? "OK" : "FAIL");
    
    Serial.print("MPU6050:");
    Serial.println(mpuOk ? "OK" : "FAIL");
    
    Serial.print("LIMIT_SWITCH:");
    Serial.println(limitOk ? "OK" : "FAIL");
    
    Serial.print("EMERGENCY_STOP:");
    Serial.println(emergencyOk ? "OK" : "FAIL");
    
    Serial.println("END_TEST");
  }
  else if (command == "STATUS") {
    // Update tilt measurement
    if (mpuInitialized) {
      calculateTilt();
    }
    
    // Send current position in format expected by GUI
    Serial.print("POS ");
    Serial.print(stepper.currentPosition());
    Serial.print(" ANGLE ");
    Serial.print(roll, 2);
    Serial.print(" SPEED ");
    Serial.print(stepper.speed());
    Serial.print(" ACCEL ");
    Serial.print(stepper.acceleration());
    Serial.print(" HOMED ");
    Serial.print(isHomed ? "YES" : "NO");
    Serial.print(" E_STOP ");
    Serial.println(isEmergencyStopped ? "YES" : "NO");
  }
  else if (command == "MOVE") {
    // Handle move command
  }
  else if (command == "HOME") {
    // Handle home command
  }
  else if (command == "STOP") {
    stepper.stop();
    Serial.println("OK STOPPED");
  }
  else {
    Serial.print("ERROR UNKNOWN_COMMAND: ");
    Serial.println(command);
  }
}

void emergencyStop() {
  stepper.stop();
  stepper.disableOutputs();
  isEmergencyStopped = true;
  Serial.println("EMERGENCY_STOP_TRIGGERED");
}