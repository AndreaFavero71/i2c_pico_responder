# Micropython I2C communication: Raspberry Pi Pico as Responder.
At the moment of writing, there isn't an I2C library to use RP2040 or RP2350 microprocessors as I2C Responders.<br>

This code builds on existing one ([see aknowledgements](https://github.com/AndreaFavero71/i2c_pico_responder?tab=readme-ov-file#acknowledgements)), by:
- extending this functionality to RP2350 microprocessors.<br>
- realizing a dataframe contruction with checksum, for data validation by the Responder.<br>
<br><br><br>


## Showcasing video:
Objective:
- Send two 16-bit data packages, via I2C, to different Pico boards.<br>
- Data sent and received is printed to the screen, for video purpose.<br>
   
https://youtu.be/zCGxnThmF0I
[![Watch the Demo](/images/title2.jpg)](https://youtu.be/zCGxnThmF0I)


#### Showcase test setup:
1. Controller: Raspberry Pi Zero 2.<br>
2. Responders: Raspberry Pi Pico, RP2040-Zero and RP2350-Zero.<br>
3. Onboard LED flashes at every correct data receival (via the camera the RGB led appears toggling at low frequency, while for humans it appears contantly ON).<br>
    - for boards with onboard RGB led, it will blink blue for positive data receival and red for errors.
    - for the other boards, the led will just blink.
4. Connections (for video recording only):
    - RPi Zero 2 connected via WiFi.<br>
    - Picos connected via USB.<br>
5. I2C Bus:
   - 4.7kΩ pull-up resistors on SDA & SCL.<br>
   - 470Ω series resistors on SDA & SCL (at Raspberry Pi Zero).<br>
<br><br><br>


## Dataframe:
- The Controntroller sends a predefined number of 16-bit data fields to the Receiver.
- The data fields are encapsulated in dataframes, with a checksum for validation at the receiver.<br>
- Dataframe structure: STX + Field1 + ... + Checksum + ETX (max 4 fields).<br>
- Escape character is added to the dataframe to differentiate STX and ETX used as terminators from when used as data (deciam 2 and 3 respectively).
- Escape character is also used to differentiate itself when used as data (decimal 92).
- The responder returns an 8-bit response:
    - 0 if the checksum differs from the one received.<br>
    - 1 if the checksum is correct.<br>
    - 2 if the dataframe is uncomplete.<br>
<br><br><br>


## Speed:
Data exchange speed depends on number of fields and number of devices; as rule of thumb it takes ca 5ms per device, when 2 fields.<br>
The bottleneck is the dataframe analysis (in MicroPython) for data validation.<br>
This is certainly not fast, but it's fast enough for the project I'm working on and I'd expect fat enough for many robotics applications.<br>
<br><br><br>


## Installation:
1. Connections:
    - Connect the same GND to all boards.<br>
    - Pico SDA and SCL GPIO pins must be pulled up to 3V3 (not 5V !) via external resistors (4k7); Pico I2C hasn't internal pull-up.<br> 
    - Suggested using serie resistors (470ohm) at Raspberry Pi Zero 2 SDA and SCL GPIOs: This will limit current drainage when the Pico's GPIOs aren't set as input (high impedence). Lesson learning after getting 2 Raspberry Pi Zero misteriously dying, pattern interrupted by addig these serie resistors.<br>
2. Copy all the files from `/i2c_pico_responder/tree/main/src/pi_pico` folder to a folder in your Raspberry Pi Pico.<br>
3. Copy the file `/i2c_pico_responder/tree/main/src/i2c_pi_zero_controller.py` to a folder in your Raspberry Pi Zero 2 (or other board).<br>
4. Power up the Raspberry Pi Pico boards; The main.py file will be automatically executed.<br>
5. Enable the I2C at raspberry Pi Zero (sudo raspi-config, Interfacing Options, I2C, select Yes to enable I2C, then reboot)
6. Run the i2c_pi_zero_controller.py script at Raspberry Pi Zero 2.<br>
7. For max I2C speed, at Raspberry Pi Zero 2, edit the /boot/config.txt file, uncomment row `dtparam=i2c_arm_baudrate=100000` and set it `400000`.<br>
<br><br><br>


## Notes:
Feel free to use and change the code to your need; Please feedback in case of improvements proposals.<br>
Of course, using this code is at your own risk :blush: .<br>
<br><br><br>


## Acknowledgements:
The implementation is largely built upon the work of danjperron as posted in:
https://www.raspberrypi.org/forums/viewtopic.php?f=146&t=302978&sid=164b1038e60b43a22d1af6b6ba69f6ae.<br>
The i2c_responder.py file is essentially the one published by Eric Moyer at GitHub: https://github.com/epmoyer/I2CResponder.<br>
