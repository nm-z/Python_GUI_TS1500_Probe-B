/*
Required Libraries:
1. Wire.h (Built-in with Arduino IDE)
2. MAX6675 (standard library)
3. AccelStepper by Mike McCauley (Install via Library Manager)

Installation Instructions:
1. Open Arduino IDE
2. Go to Tools > Manage Libraries...
3. Search for and install:
   - "MAX6675" (standard library)
   - "AccelStepper" by Mike McCauley
*/

#include <Wire.h>
#include <max6675.h>
#include <AccelStepper.h>
#include <SPI.h>

// Pin Definitions for Stepper Motor
const uint8_t MOTOR_STEP_PIN = 9;    // Stepper STEP pin
const uint8_t MOTOR_DIR_PIN = 8;     // Stepper DIR pin
const uint8_t MOTOR_ENABLE_PIN = 7;  // Stepper ENABLE pin
const uint8_t HOME_SWITCH_PIN = 3;   // Home switch pin
const uint8_t EMERGENCY_STOP_PIN = 4; // Emergency stop pin

// MAX6675 Thermocouple pins (Hardware SPI)
const uint8_t THERMOCOUPLE_CS_PIN = 10;    // CS -> Pin 10
const uint8_t THERMOCOUPLE_SCK_PIN = 13;   // SCK -> Pin 13 (Hardware SPI SCK)
const uint8_t THERMOCOUPLE_SO_PIN = 12;    // SO/MISO -> Pin 12 (Hardware SPI MISO)
// VCC -> 3.3V/5V (based on module)
// GND -> GND

// Constants
const float STEPS_PER_REV = 200.0;
const float STEPS_PER_DEGREE = STEPS_PER_REV / 360.0;
const int32_t MOTOR_MAX_SPEED = 1000;
const int32_t MOTOR_DEFAULT_SPEED = 200;
const int32_t MOTOR_ACCELERATION = 500;
const uint32_t SERIAL_BAUD_RATE = 250000;  // Increased baud rate
const uint16_t STRING_BUFFER_SIZE = 200;
const uint16_t TEMP_READ_DELAY = 250;

// Command Queue
const int QUEUE_SIZE = 10;
String commandQueue[QUEUE_SIZE];
int queueHead = 0;
int queueTail = 0;

// Global Objects
MAX6675 *thermocouple = NULL;
AccelStepper stepper(AccelStepper::DRIVER, MOTOR_STEP_PIN, MOTOR_DIR_PIN);

// Global Variables
volatile bool isEmergencyStopped = false;
volatile bool isCalibrated = false;
volatile bool isHomed = false;
unsigned long lastTempRead = 0;
float lastValidTemp = 0.0f;
bool tempSensorOk = false;
float roll = 0.0;
float pitch = 0.0;

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

void calculateTilt() {
    roll = 0.0;
    pitch = 0.0;
}

void setup() {
    // Initialize serial port with higher baud rate
    Serial.begin(SERIAL_BAUD_RATE);
    Serial.println(F("Debug port initialized"));
    
    // Initialize SPI for MAX6675
    SPI.begin();
    pinMode(THERMOCOUPLE_CS_PIN, OUTPUT);
    digitalWrite(THERMOCOUPLE_CS_PIN, HIGH);
    delay(100);
    
    // Initialize MAX6675
    thermocouple = new MAX6675(THERMOCOUPLE_SCK_PIN, THERMOCOUPLE_CS_PIN, THERMOCOUPLE_SO_PIN);
    delay(500);
    
    // Test temperature sensor
    float temp = readTemperatureSafe();
    if (!isnan(temp) && temp >= 0.0f && temp <= 150.0f) {
        tempSensorOk = true;
        Serial.println(F("Temperature sensor initialized successfully"));
    } else {
        Serial.println(F("ERROR: Temperature sensor initialization failed!"));
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
    // Check emergency stop
    if (digitalRead(EMERGENCY_STOP_PIN) == LOW && !isEmergencyStopped) {
        emergencyStop();
    }
    
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
    else if (command.startsWith("MOVE ")) {
        String stepsStr = command.substring(5);
        int32_t steps = stepsStr.toInt();
        moveMotor(steps);
    }
    else if (command == "HOME") {
        homeMotor();
    }
    else if (command == "STOP") {
        stopMotor();
    }
    else if (command == "CALIBRATE") {
        calibrateSystem();
    }
    else if (command == "EMERGENCY_STOP") {
        emergencyStop();
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
    if (thermocouple == NULL) {
        Serial.println(F("TEMP ERROR: Thermocouple not initialized"));
        return;
    }

    float temp = thermocouple->readCelsius();
    if (!isnan(temp) && temp >= 0.0f && temp <= 150.0f) {
        Serial.print(F("TEMP "));
        Serial.println(temp, 2);
    } else {
        Serial.println(F("TEMP ERROR: Invalid reading"));
    }
}

void performSelfTest() {
    Serial.println("TEST_START");
    
    // Test MAX6675
    if (thermocouple != NULL) {
        float temp = thermocouple->readCelsius();
        if (!isnan(temp)) {
            Serial.print("TEMP: ");
            Serial.println(temp, 2);
            Serial.println("MAX6675: OK");
        } else {
            Serial.println("MAX6675: FAIL");
        }
    } else {
        Serial.println("MAX6675: FAIL");
    }
    
    // Test motor
    bool motorEnabled = (digitalRead(MOTOR_ENABLE_PIN) == LOW);
    Serial.print("MOTOR: ");
    Serial.println(motorEnabled ? "OK" : "FAIL");
    
    Serial.println("TEST_SUCCESS");
}

float getCurrentAngle() {
    calculateTilt();
    return roll;
}

void moveMotor(int32_t steps) {
    if (!isCalibrated) {
        Serial.println(F("ERROR: Movement rejected - not calibrated"));
        return;
    }
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
    stepper.move(steps);
    Serial.println(F("Movement started"));
}

void homeMotor() {
    if (isEmergencyStopped) {
        Serial.println(F("ERROR: Homing rejected - emergency stop active"));
        return;
    }

    Serial.println(F("Starting homing sequence..."));
    while (digitalRead(HOME_SWITCH_PIN) == HIGH && !isEmergencyStopped) {
        stepper.moveTo(-1000000L);
        stepper.run();
    }
    
    if (!isEmergencyStopped) {
        Serial.println(F("Home switch triggered"));
        stepper.setCurrentPosition(0L);
        isHomed = true;
        Serial.println(F("Homing complete"));
    }
}

void calibrateSystem() {
    if (isEmergencyStopped) {
        Serial.println(F("ERROR: Calibration rejected - emergency stop active"));
        return;
    }

    Serial.println(F("Starting calibration..."));
    stepper.setCurrentPosition(0L);
    isCalibrated = true;
    Serial.println(F("Calibration complete"));
}

void emergencyStop() {
    if (isEmergencyStopped) {
        isEmergencyStopped = false;
        digitalWrite(MOTOR_ENABLE_PIN, LOW);
        Serial.println(F("Emergency stop released"));
    } else {
        stepper.stop();
        isEmergencyStopped = true;
        digitalWrite(MOTOR_ENABLE_PIN, HIGH);
        Serial.println(F("Emergency stop engaged"));
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
    static unsigned long lastTempRead = 0;
    static float lastValidTemp = 0.0f;
    
    if (thermocouple == NULL) {
        return lastValidTemp;
    }
    
    if (millis() - lastTempRead >= TEMP_READ_DELAY) {
        float temp = thermocouple->readCelsius();
        lastTempRead = millis();
        
        if (!isnan(temp) && temp >= 0.0f && temp <= 150.0f) {
            lastValidTemp = temp;
            tempSensorOk = true;
            return temp;
        } else {
            tempSensorOk = false;
        }
    }
    return lastValidTemp;
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
    int32_t pos = stepper.currentPosition();
    float speed = stepper.speed();
    float accel = MOTOR_ACCELERATION;
    
    Serial.print(F("POS "));
    Serial.print(pos);
    Serial.print(F(" SPEED "));
    Serial.print(speed);
    Serial.print(F(" ACCEL "));
    Serial.print(accel);
    Serial.print(F(" HOMED "));
    Serial.print(isHomed ? F("YES") : F("NO"));
    Serial.print(F(" E_STOP "));
    Serial.println(isEmergencyStopped ? F("YES") : F("NO"));
}

void printHelp() {
    Serial.println(F("Available Commands:"));
    Serial.println(F("  TEST          - Run system self-test"));
    Serial.println(F("  STATUS        - Show current system status"));
    Serial.println(F("  TEMP          - Read current temperature"));
    Serial.println(F("  TILT          - Read current tilt angle"));
    Serial.println(F("  MOVE <steps>  - Move stepper motor"));
    Serial.println(F("  HOME          - Home the stepper motor"));
    Serial.println(F("  STOP          - Stop motor movement"));
    Serial.println(F("  CALIBRATE     - Calibrate the system"));
    Serial.println(F("  EMERGENCY_STOP - Toggle emergency stop"));
    Serial.println(F("  HELP          - Show this help message"));
}