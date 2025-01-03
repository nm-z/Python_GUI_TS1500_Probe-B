/*
Required Libraries:
1. Wire.h (Built-in with Arduino IDE)
2. MPU6050 by Electronic Cats (Install via Library Manager)
3. MAX6675 (standard library)
4. AccelStepper by Mike McCauley (Install via Library Manager)

Installation Instructions:
1. Open Arduino IDE
2. Go to Tools > Manage Libraries...
3. Search for and install:
   - "MPU6050" by Electronic Cats
   - "MAX6675" (standard library)
   - "AccelStepper" by Mike McCauley
*/

#include <Wire.h>
#include <MPU6050.h>
#include <max6675.h>
#include <AccelStepper.h>
#include <SPI.h>

// Pin Definitions for Stepper Motor
const uint8_t MOTOR_STEP_PIN = 9;    // Stepper STEP pin
const uint8_t MOTOR_DIR_PIN = 8;     // Stepper DIR pin
const uint8_t MOTOR_ENABLE_PIN = 7;  // Stepper ENABLE pin
const uint8_t HOME_SWITCH_PIN = 3;   // Home switch pin
const uint8_t EMERGENCY_STOP_PIN = 4; // Emergency stop pin

// MPU6050 I2C Pins (defined by Wire library)
// SDA -> Pin 20
// SCL -> Pin 21
// VCC -> 3.3V
// GND -> GND

// MAX6675 Thermocouple pins (Hardware SPI)
const uint8_t THERMOCOUPLE_CS_PIN = 10;    // CS -> Pin 10
const uint8_t THERMOCOUPLE_SCK_PIN = 13;   // SCK -> Pin 13 (Hardware SPI SCK)
const uint8_t THERMOCOUPLE_SO_PIN = 12;    // SO/MISO -> Pin 12 (Hardware SPI MISO)
// VCC -> 3.3V/5V (based on module)
// GND -> GND

// Constants
const float STEPS_PER_REV = 200.0;
const float STEPS_PER_DEGREE = STEPS_PER_REV / 360.0;
const int32_t MOTOR_MAX_SPEED = 100;
const int32_t MOTOR_DEFAULT_SPEED = 100;
const int32_t MOTOR_HOMING_SPEED = -100;  // Negative speed for downward homing movement
const int32_t MOTOR_CLEARING_SPEED = 50;   // Positive speed for upward clearing movement
const int32_t MOTOR_ACCELERATION = 100;
const uint32_t SERIAL_BAUD_RATE = 250000;  // Increased baud rate
const uint16_t STRING_BUFFER_SIZE = 200;
const uint16_t TEMP_READ_DELAY = 250;

// Command Queue
const int QUEUE_SIZE = 10;
String commandQueue[QUEUE_SIZE];
int queueHead = 0;
int queueTail = 0;

// Global Objects
MPU6050 mpu;
MAX6675 *thermocouple = NULL;
AccelStepper stepper(AccelStepper::DRIVER, MOTOR_STEP_PIN, MOTOR_DIR_PIN);

// Global Variables
volatile bool isEmergencyStopped = false;
volatile bool isCalibrated = false;
volatile bool isHomed = false;
volatile bool isLevel = false;
volatile bool isCleared = false;
unsigned long lastTempRead = 0;
float lastValidTemp = 0.0f;
bool tempSensorOk = false;
bool mpuInitialized = false;

// MPU6050 data
int16_t ax, ay, az;
int16_t gx, gy, gz;
float pitch, roll;

// Function declarations
void reportStatus();
void readTemperature();
void performSelfTest();
void moveMotor(int32_t steps);
void homeMotor();
void stopMotor();
void calibrateSystem();
void emergencyStop();
void enableMotor(bool enable);
void logDiagnostic(const char* component, const char* message, bool isError = false);
void logValue(const char* component, const char* valueName, float value);
void level();

void calculateTilt() {
    if (!mpuInitialized) {
        Serial.println(F("TILT ERROR: MPU6050 not initialized"));
        return;
    }
    
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    pitch = atan2(ay, sqrt(pow(ax, 2) + pow(az, 2))) * 180.0 / M_PI;
    roll = atan2(-ax, sqrt(pow(ay, 2) + pow(az, 2))) * 180.0 / M_PI;
}

void setup() {
    // Initialize serial port with higher baud rate
    Serial.begin(SERIAL_BAUD_RATE);
    Serial.println(F("Debug port initialized"));
    
    // Initialize I2C for MPU6050
    Wire.begin();
    Wire.setClock(400000); // Set I2C clock to 400kHz for better stability
    delay(100); // Increased delay for I2C stability
    
    // Initialize MPU6050 with multiple attempts
    Serial.println(F("Initializing MPU6050..."));
    for(int attempt = 0; attempt < 3 && !mpuInitialized; attempt++) {
        mpu.initialize();
        delay(50);
        
        if (mpu.testConnection()) {
            mpuInitialized = true;
            mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2);
            mpu.setDLPFMode(MPU6050_DLPF_BW_5);
            Serial.println(F("MPU6050 initialization successful"));
        } else {
            Wire.begin();
            delay(200);
        }
    }
    
    if (!mpuInitialized) {
        Serial.println(F("ERROR: MPU6050 initialization failed!"));
        Serial.println(F("Check I2C connections and power supply"));
    }
    
    // Initialize SPI for MAX6675
    SPI.begin();
    SPI.setClockDivider(SPI_CLOCK_DIV4); // Set SPI clock for stability
    pinMode(THERMOCOUPLE_CS_PIN, OUTPUT);
    digitalWrite(THERMOCOUPLE_CS_PIN, HIGH);
    delay(100);
    
    // Initialize MAX6675
    thermocouple = new MAX6675(THERMOCOUPLE_SCK_PIN, THERMOCOUPLE_CS_PIN, THERMOCOUPLE_SO_PIN);
    delay(500);  // Give the MAX6675 time to stabilize
    
    // Test temperature sensor
    float temp = thermocouple->readCelsius();
    if (!isnan(temp) && temp > 0.0f && temp <= 150.0f) {
        tempSensorOk = true;
    } else {
        Serial.println(F("ERROR: Temperature sensor initialization failed"));
    }
    
    // Configure stepper
    stepper.setMaxSpeed(MOTOR_MAX_SPEED);
    stepper.setSpeed(MOTOR_DEFAULT_SPEED);
    stepper.setAcceleration(MOTOR_ACCELERATION);
    stepper.setCurrentPosition(0);
    
    // Initialize pins
    pinMode(HOME_SWITCH_PIN, INPUT_PULLUP);
    pinMode(EMERGENCY_STOP_PIN, INPUT_PULLUP);
    pinMode(MOTOR_ENABLE_PIN, OUTPUT);
    digitalWrite(MOTOR_ENABLE_PIN, LOW); // Enable motor
    
    Serial.println(F("Initialization complete"));
    Serial.println(F("READY"));
    
    // Clear any leftover serial data
    clearSerialBuffer();
}

void loop() {
    // Process serial commands with queue
    while (Serial.available()) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        
        if (command.length() > 0) {
            // Add to queue if not full
            int nextTail = (queueTail + 1) % QUEUE_SIZE;
            if (nextTail != queueHead) {
                commandQueue[queueTail] = command;
                queueTail = nextTail;
            } else {
                Serial.println(F("ERROR: Command queue full"));
            }
        }
    }
    
    // Process one command from queue
    if (queueHead != queueTail) {
        String command = commandQueue[queueHead];
        queueHead = (queueHead + 1) % QUEUE_SIZE;
        
        command.toUpperCase();
        processCommand(command);
    }
    
    // Run stepper
    stepper.run();
}

void clearSerialBuffer() {
    while (Serial.available()) {
        Serial.read();
    }
}

void processCommand(const String& command) {
    if (command.length() == 0) {
        Serial.println(F("ERROR: Empty command"));
        return;
    }

    if (command == "TEST") {
        performSelfTest();
    }
    else if (command == "STATUS") {
        reportStatus();
    }
    else if (command == "TEMP") {
        readTemperature();
    }
    else if (command == "TILT") {
        calculateTilt();
        Serial.print(F("TILT "));
        Serial.println(roll, 2);
    }
    else if (command == "LEVEL") {
        if (!isHomed) {
            Serial.println(F("ERROR: Must home before leveling"));
            return;
        }
        // Calculate steps for 16.8 degrees (STEPS_PER_DEGREE * 16.8)
        long steps = (long)(2895);
        stepper.setMaxSpeed(MOTOR_MAX_SPEED);
        stepper.setSpeed(MOTOR_DEFAULT_SPEED);
        stepper.moveTo(steps);
        while (stepper.currentPosition() != steps) {
            stepper.run();
        }
        Serial.println(F("Leveling complete"));
    }
    else if (command.startsWith("MOVE ")) {
        String stepsStr = command.substring(5);
        int32_t steps = stepsStr.toInt();
        moveMotor(steps);
    }
    else if (command == "HOME") {
        homeMotor();  // Original tilt home
    }
    else if (command == "FILL_HOME") {
        fillHome();   // New fill home
    }
    else if (command == "TILT_HOME") {
        homeMotor();  // Explicit tilt home
    }
    else if (command == "STOP") {
        stopMotor();
    }
    else if (command == "CALIBRATE") {
        calibrateSystem();
    }
    else if (command == "HELP") {
        printHelp();
    }
    else {
        Serial.print(F("ERROR: Unknown command: "));
        Serial.println(command);
    }
}

void readTemperature() {
    Serial.println(thermocouple->readCelsius());
}

void performSelfTest() {
    Serial.println(F("START_TEST"));
    
    // Test MPU6050
    if (mpuInitialized) {
        Serial.println(F("MPU6050: OK"));
        calculateTilt();
        Serial.print(F("TILT ")); 
        Serial.println(roll, 2);
    } else {
        Serial.println(F("MPU6050: FAIL"));
    }
    
    // Test MAX6675
    if (thermocouple != NULL) {
        float temp = thermocouple->readCelsius();
        if (!isnan(temp) && temp >= 0.0f && temp <= 150.0f) {
            Serial.print(F("TEMP "));
            Serial.println(temp, 2);
            Serial.println(F("MAX6675: OK"));
        } else {
            Serial.println(F("MAX6675: FAIL - Invalid reading"));
            Serial.print(F("Raw value: "));
            Serial.println(temp);
        }
    } else {
        Serial.println(F("MAX6675: FAIL - Not initialized"));
    }
    
    // Test motor
    bool motorEnabled = (digitalRead(MOTOR_ENABLE_PIN) == LOW);
    Serial.print(F("MOTOR: "));
    Serial.println(motorEnabled ? F("OK") : F("FAIL"));
    
    Serial.println(F("END_TEST"));
}

float getCurrentAngle() {
    calculateTilt();
    return roll;
}

void moveMotor(int32_t steps) {
    if (!isHomed) {
        Serial.println(F("ERROR: Movement rejected - not homed"));
        return;
    }
    if (isEmergencyStopped) {
        Serial.println(F("ERROR: Movement rejected - emergency stop active"));
        return;
    }

    Serial.print(F("Moving steps: "));
    Serial.println(steps);
    
    stepper.setMaxSpeed(150);
    stepper.setSpeed(150);
    stepper.move(-steps);  // Negate steps to swap direction
    
    Serial.println(F("Movement started"));
    
    while (stepper.distanceToGo() != 0 && !isEmergencyStopped) {
        stepper.run();
    }
    
    stepper.stop();
    
    if (isEmergencyStopped) {
        Serial.println(F("ERROR: Movement interrupted by emergency stop"));
    } else {
        Serial.println(F("Movement complete"));
    }
}

//=============================================================================
// WARNING: DO NOT MODIFY THIS FUNCTION - IT IS WORKING CORRECTLY
// This implementation has been tested and verified to:
// 1. Move down to home switch
// 2. Clear the switch correctly
// 3. Move exactly 2715 steps at 150 speed to level position
// ANY changes to speeds, steps, or logic will break the calibrated movement
//=============================================================================
void homeMotor() {
    if (isEmergencyStopped) {
        Serial.println(F("ERROR: Homing rejected - emergency stop active"));
        return;
    }

    Serial.println(F("Starting homing sequence..."));
    // Move down until home switch is hit
    while (digitalRead(HOME_SWITCH_PIN) == HIGH && !isEmergencyStopped) {
        stepper.setSpeed(MOTOR_HOMING_SPEED);  // downward toward homing switch
        stepper.runSpeed();
        delay(10);  // simulates debouncing
    }

    if (!isEmergencyStopped) {
        stepper.stop();  // Stop motor movement
        delay(1000);     // Wait 1 second after hitting switch

        // Clear the switch by moving up until switch is released
        Serial.println(F("Clearing home switch..."));
        while (digitalRead(HOME_SWITCH_PIN) == LOW && !isEmergencyStopped) {
            stepper.setSpeed(MOTOR_CLEARING_SPEED);  // Upward
            stepper.runSpeed();
            delay(5);  // debouncing
        }
        
        stepper.stop();
        delay(1000);  // Wait 1 second after clearing

        // Move to level position first
        stepper.setCurrentPosition(0);  // Set current position as 0
        stepper.setMaxSpeed(150);       // Set max speed to 150
        stepper.setSpeed(150);          // Set speed to 150
        stepper.moveTo(2735);           // Move to level position
        
        Serial.println(F("Moving to level position..."));
        while (stepper.currentPosition() != 2735 && !isEmergencyStopped) {
            stepper.run();              // Use run() for full speed
        }

        // Now that we're at level position, wait for confirmation
        Serial.println(F("Waiting for level confirmation..."));
        bool wasEmergencyStopped = isEmergencyStopped;  // Store current state
        isEmergencyStopped = false;  // Temporarily disable emergency stop
        
        while (digitalRead(4) == HIGH) {
            delay(10);  // Check every 10ms
        }

        if (!wasEmergencyStopped) {  // Only complete if it wasn't stopped before
            isHomed = true;
            isEmergencyStopped = false;  // Ensure emergency stop is off after successful homing
            digitalWrite(MOTOR_ENABLE_PIN, LOW);  // Re-enable motor
            Serial.println(F("Homing and leveling complete"));
        } else {
            isEmergencyStopped = true;  // Restore emergency stop if it was active
            digitalWrite(MOTOR_ENABLE_PIN, HIGH);  // Keep motor disabled
        }
    }
}

void clearHomeMotor() {
    //========= Clear the tilt limit switch ====================================================
    while (digitalRead(HOME_SWITCH_PIN) == LOW) {
        stepper.setSpeed(MOTOR_CLEARING_SPEED);  // Upward
        stepper.runSpeed();
        delay(5);  // this delay simulate debouncing
    }
    isCleared = true;
    Serial.println("Homing switch has been cleared");
    delay(1000);
}

void calibrateSystem() {
    if (isEmergencyStopped) {
        Serial.println(F("ERROR: Calibration rejected - emergency stop active"));
        return;
    }

    Serial.println(F("Starting calibration..."));
    
    if (mpuInitialized) {
        calculateTilt();
        stepper.setCurrentPosition(0L);
        isCalibrated = true;
        Serial.println(F("Calibration complete"));
    } else {
        Serial.println(F("ERROR: Calibration failed - MPU6050 not initialized"));
    }
}

void enableMotor(bool enable) {
    digitalWrite(MOTOR_ENABLE_PIN, enable ? LOW : HIGH);
    logDiagnostic("MOTOR", enable ? "Motor enabled" : "Motor disabled");
}

void stopMotor() {
    Serial.println(F("Stopping motor..."));
    stepper.stop();
    stepper.setCurrentPosition(stepper.currentPosition());
    Serial.print(F("Final position: "));
    Serial.println(stepper.currentPosition());
    Serial.println(F("Motor stopped"));
}

float readTemperatureSafe() {
    if (thermocouple == NULL) {
        return 0.0f;
    }
    
    float temp = thermocouple->readCelsius();
    if (!isnan(temp) && temp >= 0.0f && temp <= 150.0f) {
        tempSensorOk = true;
        return temp;
    } else {
        tempSensorOk = false;
        return 0.0f;
    }
}

void displayCommands() {
    SerialUSB.println(F("=== Available Commands ==="));
    SerialUSB.println(F("TEST         - Run system self-test"));
    SerialUSB.println(F("STATUS       - Show current system status"));
    SerialUSB.println(F("TEMP         - Read current temperature"));
    SerialUSB.println(F("TILT         - Read current tilt angle"));  // Add TILT command
    SerialUSB.println(F("MOVE <steps> - Move stepper motor by specified steps"));
    SerialUSB.println(F("HOME         - Home the stepper motor"));
    SerialUSB.println(F("STOP         - Stop all motor movement"));
    SerialUSB.println(F("CALIBRATE    - Perform system calibration"));
    SerialUSB.println(F("EMERGENCY_STOP - Toggle emergency stop"));
    SerialUSB.println(F("DEBUG        - Show detailed diagnostic information"));
    SerialUSB.println(F("======================"));
}

void logDiagnostic(const char* component, const char* message, bool isError) {
    String output = String("[") + component + "] ";
    if (isError) {
        output += "ERROR: ";
    }
    output += message;
    
    Serial.println(output);
    SerialUSB.println(output);
}

void logValue(const char* component, const char* valueName, float value) {
    String output = String("[") + component + "][" + valueName + "=" + String(value) + "]";
    Serial.println(output);
    SerialUSB.println(output);
}

void reportStatus() {
    calculateTilt();
    int32_t pos = stepper.currentPosition();
    float speed = stepper.speed();
    float accel = MOTOR_ACCELERATION;
    
    Serial.print(F("POS "));
    Serial.print(pos);
    Serial.print(F(" ANGLE "));
    Serial.print(roll, 2);
    Serial.print(F(" SPEED "));
    Serial.print(speed);
    Serial.print(F(" ACCEL "));
    Serial.print(accel);
    Serial.print(F(" HOMED "));
    Serial.println(isHomed ? F("YES") : F("NO"));
}

void printHelp() {
    Serial.println(F("Available Commands:"));
    Serial.println(F("  TEST          - Run system self-test"));
    Serial.println(F("  STATUS        - Show current system status"));
    Serial.println(F("  TEMP          - Read current temperature"));
    Serial.println(F("  TILT          - Read current tilt angle"));
    Serial.println(F("  LEVEL         - Move to 16.8 degree position"));
    Serial.println(F("  MOVE <steps>  - Move stepper motor"));
    Serial.println(F("  HOME          - Home the stepper motor (same as TILT_HOME)"));
    Serial.println(F("  TILT_HOME     - Home and move to level position"));
    Serial.println(F("  FILL_HOME     - Home without moving to level"));
    Serial.println(F("  STOP          - Stop motor movement"));
    Serial.println(F("  CALIBRATE     - Calibrate the system"));
    Serial.println(F("  HELP          - Show this help message"));
}

void level() {
    //Print out Instructions on the Serial Monitor at Start
    Serial.println("Turn off power to the motor");
    Serial.println("Place a level sensor on the Tilt Platform");
    Serial.println("Manually adjust the platform until level sensor reads 0 +/- 0.1 degrees");
    Serial.println("Toggle the Home Switch to start the test (5 second safety delay)");

    // stay in while loop until switch is read as a low
    while (digitalRead(HOME_SWITCH_PIN) == HIGH) {
        delay(10);
    }
    Serial.println("Switch Toggled --- LEVELED |||  Turn on power to the motor");
    isLevel = true;
    stepper.setCurrentPosition(0);  // Set level as current and safe position
    delay(5000);
}

void fillHome() {
    if (isEmergencyStopped) {
        Serial.println(F("ERROR: Homing rejected - emergency stop active"));
        return;
    }

    Serial.println(F("Starting fill home sequence..."));
    
    // Enable motor and set speeds
    digitalWrite(MOTOR_ENABLE_PIN, LOW);  // Enable motor
    stepper.setMaxSpeed(450);  // 3x faster
    stepper.setSpeed(MOTOR_CLEARING_SPEED * 3);  // Use positive speed for upward movement, 3x faster
    
    Serial.println(F("Moving up to find home switch..."));
    // Move up until home switch is hit
    while (digitalRead(HOME_SWITCH_PIN) == HIGH && !isEmergencyStopped) {
        stepper.runSpeed();
        delay(10);  // simulates debouncing
    }

    if (!isEmergencyStopped) {
        stepper.stop();  // Stop motor movement
        delay(1000);     // Wait 1 second after hitting switch

        // Clear the switch by moving down until switch is released
        Serial.println(F("Clearing home switch..."));
        while (digitalRead(HOME_SWITCH_PIN) == LOW && !isEmergencyStopped) {
            stepper.setSpeed(MOTOR_HOMING_SPEED * 3);  // Use negative speed for downward movement, 3x faster
            stepper.runSpeed();
            delay(5);  // debouncing
        }
        
        stepper.stop();
        delay(1000);  // Wait 1 second after clearing

        // Set current position as 0
        stepper.setCurrentPosition(0);
        isHomed = true;
        Serial.println(F("Fill home complete - Position set to 0"));
    } else {
        Serial.println(F("ERROR: Fill home interrupted by emergency stop"));
    }
}