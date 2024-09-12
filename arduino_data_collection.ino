#include <Wire.h>
#include <MPU6050.h>
#include <AccelStepper.h>

MPU6050 mpu;

// Stepper motor configuration
const int stepsPerRevolution = 200;  // Change this based on your stepper motor
const int dirPin = 2;
const int stepPin = 3;
AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);

void setup() {
  Serial.begin(115200);
  Wire.begin();
  mpu.initialize();

  // Stepper motor setup
  stepper.setMaxSpeed(1000);
  stepper.setAcceleration(500);
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.startsWith("GET_TILT")) {
      int16_t ax, ay, az;
      mpu.getAcceleration(&ax, &ay, &az);
      
      // Calculate tilt angle based on accelerometer data
      float tiltAngle = atan2(ay, sqrt(ax*ax + az*az)) * 180.0 / PI;
      
      Serial.print("TILT_ANGLE:");
      Serial.println(tiltAngle);
    }
    else if (command.startsWith("SET_ANGLE:")) {
      float targetAngle = command.substring(10).toFloat();
      
      // Calculate the number of steps to reach the target angle
      int targetSteps = (int)(targetAngle / 360.0 * stepsPerRevolution);
      
      stepper.moveTo(targetSteps);
      stepper.runToPosition();
      
      Serial.println("ANGLE_SET");
    }
  }
}