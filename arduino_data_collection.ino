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
    
    Serial.print("XYZ:");
    Serial.print(ax);
    Serial.print(",");
    Serial.print(ay);
    Serial.print(",");
    Serial.print(az);
    Serial.print(",");
    Serial.print(gx);
    Serial.print(",");
    Serial.print(gy);
    Serial.print(",");
    Serial.println(gz);

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
      int16_t ax, ay, az;
      mpu.getAcceleration(&ax, &ay, &az);
      
      // Calculate the baseline angle when the sensor is flat
      baselineAngle = atan2(ay, sqrt(ax*ax + az*az)) * 180.0 / PI;
      
      Serial.println("CALIBRATED");
    }
  }
}