/*
  Arduino Data Collection for MPU6050 Tilt Sensor

  This sketch communicates with a Python GUI to collect tilt angle data from an MPU6050 sensor.
  It supports the following serial commands:

  - GET_TILT: Retrieves the current tilt angle from the MPU6050 sensor.
    Returns: TILT_ANGLE:<angle>

  - CALIBRATE: Sets the current orientation as the baseline (flat) position.
    Returns: CALIBRATED when the calibration is complete.

  Dependencies:
  - Wire library
  - MPU6050 library by Jeff Rowberg: https://github.com/jrowberg/i2cdevlib/tree/master/Arduino/MPU6050
*/

#include <Wire.h>
#include <MPU6050.h>

MPU6050 mpu;

// Stepper motor configuration (commented out)
// const int stepsPerRevolution = 200;  // Change this based on your stepper motor
// const int dirPin = 2;
// const int stepPin = 3;
// AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);

float baselineAngle = 0;

// Define scale factors
const float ACCEL_SCALE_FACTOR = 8192.0; // Scale factor for accelerometer (4g range)
const float GYRO_SCALE_FACTOR = 65.5;    // Scale factor for gyroscope (500 degrees/s range)

// Define accelerometer and gyroscope offsets
// Leave as float to be able to assign new values during calibration
float ACCEL_X_OFFSET = 0.15;
float ACCEL_Y_OFFSET = -0.148;
float ACCEL_Z_OFFSET = -2.176;
float GYRO_X_OFFSET = 99.0;
float GYRO_Y_OFFSET = 96.0;
float GYRO_Z_OFFSET = -92.0;

void setup() {
  Serial.begin(115200);
  Wire.begin();
  mpu.initialize();

  // Set accelerometer and gyroscope ranges
  mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_4);
  mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_500);

  // Stepper motor setup (commented out)
  // stepper.setMaxSpeed(1000);
  // stepper.setAcceleration(500);
}

void loop() {
  // Send XYZ axis data at 5 readings per second
  static unsigned long lastReadingTime = 0;
  if (millis() - lastReadingTime >= 200) {  // 200ms delay for 5 readings per second
    int16_t ax, ay, az, gx, gy, gz;
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    
    // Scale the raw readings
    float scaledAx = ax / ACCEL_SCALE_FACTOR;
    float scaledAy = ay / ACCEL_SCALE_FACTOR;
    float scaledAz = az / ACCEL_SCALE_FACTOR;
    float scaledGx = gx / GYRO_SCALE_FACTOR;
    float scaledGy = gy / GYRO_SCALE_FACTOR;
    float scaledGz = gz / GYRO_SCALE_FACTOR;
    
    // Apply offsets
    float adjustedAx = scaledAx - ACCEL_X_OFFSET;
    float adjustedAy = scaledAy - ACCEL_Y_OFFSET;
    float adjustedAz = scaledAz - ACCEL_Z_OFFSET;
    float adjustedGx = scaledGx - GYRO_X_OFFSET;
    float adjustedGy = scaledGy - GYRO_Y_OFFSET;
    float adjustedGz = scaledGz - GYRO_Z_OFFSET;
    
    Serial.print("XYZ:");
    Serial.print(adjustedAx);
    Serial.print(",");
    Serial.print(adjustedAy);
    Serial.print(",");
    Serial.print(adjustedAz);
    Serial.print(",");
    Serial.print(adjustedGx);
    Serial.print(",");
    Serial.print(adjustedGy);
    Serial.print(",");
    Serial.println(adjustedGz);

    lastReadingTime = millis();
  }

  // Check for incoming commands
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "GET_ACCEL") {
      // Already sending XYZ data, no need to respond to this command
    }
    else if (command == "GET_TILT") {
      int16_t ax, ay, az;
      mpu.getAcceleration(&ax, &ay, &az);
      
      // Calculate tilt angle based on accelerometer data
      float tiltAngle = atan2(ay, sqrt(ax*ax + az*az)) * 180.0 / PI;
      
      // Subtract the baseline angle to get the calibrated tilt angle
      float calibratedAngle = tiltAngle - baselineAngle;
      
      Serial.print("TILT_ANGLE:");
      Serial.println(calibratedAngle);
    }
    // Stepper motor commands (commented out)
    // else if (command.startsWith("SET_ANGLE:")) {
    //   float targetAngle = command.substring(10).toFloat();
    //   
    //   // Calculate the number of steps to reach the target angle
    //   int targetSteps = (int)(targetAngle / 360.0 * stepsPerRevolution);
    //   
    //   stepper.moveTo(targetSteps);
    //   stepper.runToPosition();
    //   
    //   Serial.println("ANGLE_SET");
    // }
    else if (command.startsWith("CALIBRATE")) {
      performCalibration();
    }
  }
}

/**
 * @brief Collects and averages sensor readings over a calibration period to determine offsets.
 * 
 * This function gathers gyroscope and accelerometer data for a specified duration,
 * calculates the average values, and updates the offset variables to calibrate the sensor.
 * It ensures more stable and accurate sensor readings by accounting for inherent biases.
 */
void performCalibration() {
    unsigned long startTime = millis();
    const unsigned long calibrationDuration = 10000; // 10 seconds
    int numReadings = 0;
    long sumGx = 0, sumGy = 0, sumGz = 0;
    long sumAx = 0, sumAy = 0, sumAz = 0;

    while (millis() - startTime < calibrationDuration) {
        int16_t ax, ay, az, gx, gy, gz;
        mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
        sumGx += gx;
        sumGy += gy;
        sumGz += gz;
        sumAx += ax;
        sumAy += ay;
        sumAz += az;
        numReadings++;
        delay(20); // 50 readings per second
    }

    // Error handling: Ensure that at least one reading was taken
    if (numReadings > 0) {
        // Calculate average offsets with scale factors
        GYRO_X_OFFSET = (sumGx / (float)numReadings) / GYRO_SCALE_FACTOR;
        GYRO_Y_OFFSET = (sumGy / (float)numReadings) / GYRO_SCALE_FACTOR;
        GYRO_Z_OFFSET = (sumGz / (float)numReadings) / GYRO_SCALE_FACTOR;
        ACCEL_X_OFFSET = (sumAx / (float)numReadings) / ACCEL_SCALE_FACTOR;
        ACCEL_Y_OFFSET = (sumAy / (float)numReadings) / ACCEL_SCALE_FACTOR;
        ACCEL_Z_OFFSET = (sumAz / (float)numReadings) / ACCEL_SCALE_FACTOR - 1.0;

        Serial.println("CALIBRATED");
    } else {
        Serial.println("CALIBRATION_FAILED: No readings collected.");
    }
}