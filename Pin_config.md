# MPU-6050 Wiring (Tilt)

| **MPU-6050 Pin** | **Arduino Pin**  | **Notes**                                                  |
| ---------------- | ---------------- | ---------------------------------------------------------- |
| **VCC**          | **Power - 3.3V** | Supply voltage to the MPU-6050. Ensure 3.3V compatibility. |
| **GND**          | **Power - GND**  | Ground connection.                                         |
| **SCL**          | **SCL Pin 21**   | I2C Clock line (SCL).                                      |
| **SDA**          | **SDA Pin 20**   | I2C Data line (SDA).                                       |



# MAX6675 Wiring (Temp)

| **MAX6675 Pin** | **Arduino ICSP Header** | **Notes**                                                      |
| --------------- | ----------------------- | -------------------------------------------------------------- |
| **GND**         | **ICSP Pin 6 - GND**    | Connect to Ground.                                             |
| **VCC**         | **ICSP Pin 2 - VCC**    | Connect to 3.3V or 5V (based on MAX6675 module compatibility). |
| **SO**          | **ICSP Pin 1 - MISO**   | SPI Data Out (Slave Out).                                      |
| **SCK**         | **ICSP Pin 3 - SCK**    | SPI Clock.                                                     |
| **CS**          | **PWM Pin 10**          | Chip Select (can be any digital pin).                          |
|                 |                         |                                                                |

