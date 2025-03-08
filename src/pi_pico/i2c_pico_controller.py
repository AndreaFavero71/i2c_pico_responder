"""
Andrea Favero 08/03/2025

Micropython code for Raspberry Pi Pico (RP2040 and RP2350).
It demonstrates how to use a Pi Pico as I2C Controller.

This Class:
- it scans the I2C bus and makes a dict with detected devices.
- it sends datafarames to each device.
- dataframes are based on a (manually) defined number of 16bits fields.
- each dataframe includes STX, 16bits field(s), escape characters, checksum and ETX.
- the 16bits field(s) is a randome 16bits integer.
- after sendig a dataframe, it inquires the device if dataframe is correctly received.
- it sends a predefined number of dataframes and stops. 



MIT License

Copyright (c) 2025 Andrea Favero

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


from machine import I2C, Pin
import time, struct, random
import random


# variable to be manually set
df_fields = 2      # number of 16-bit fields in dataframe, max 4
runs = 1000        # limit the test to a number of runs
timeout_mins = 3   # timeout in minutes


# Define I2C parameters (use I2C0 or I2C1 based on your wiring)
i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq =100000)

print("Scanning for I2C devices...")
devs = i2c.scan()  # Scan for devices

devices = {}
device_labels = 'ABCDEFGHIJKLMNO'
if devs:
    print("I2C devices found:")
    for i, addr in enumerate(devs):
        devices[device_labels[i]] = addr
        print(f"  0x{addr:02X}")  # Print address in hexadecimal format
else:
    print("No I2C devices found.")

# manual entering of the device(s) and related address(es)
# devices = {'A': 0x42}  # RP2040-devices and related I2C addresses

# number of devices is assigned to number_of_devs variable
number_of_devs = len(devices)


def calculate_checksum(dataframe):
    return sum(dataframe) & 0xFF

def escape_data(dataframe):
    escaped_data = []
    for byte in dataframe:
        if byte in [0x02, 0x03, 0x5C]:  # STX, ETX, and backslash
            escaped_data.append(0x5C)   # Escape character
        escaped_data.append(byte)
    return escaped_data

def send_data(dataframe, dev, adr):
    data_frame = [stx]
    for value in dataframe:
        field_bytes = value.to_bytes(2, 'big')
        data_frame.extend(field_bytes)
    
    checksum = calculate_checksum(data_frame)
    data_frame.append(checksum)
    escaped_data_frame = escape_data(data_frame)[1:] + [etx]
    
    try:
        i2c.writeto(adr, bytes(escaped_data_frame))
    except OSError as e:
        print(f"I2C write error on device {dev}: {e}")
        escaped_data_frame = []
    return escaped_data_frame

def read_data(dev, adr):
    try:
        return i2c.readfrom(adr, 1)[0]  # Read 1 byte
    except OSError as e:
        print(f"I2C read error on device {dev}: {e}")
        return -1


# other variables
stop_test = False  # stop flag
stx = 0x02                       # start of Text
etx = 0x03                       # end of Text
ok_runs = 0                      # successful transmissions counter is zeroed
errors = 0                       # errors counter is zeroed
timeout_s = 60 * timeout_mins    # calculated timeout in seconds
t_start_s = time.time()          # time reference for seconds
t_start_ms = time.ticks_ms()     # time reference for milliseconds                 


try:
    while time.time() - t_start_s < timeout_s:            # while loop until timeout
        if stop_test:                                     # case all the target runs are made
            break                                         # while loop is interrupted
        
        data = [random.randint(0, 65535) for _ in range(df_fields)] # list with random 16bits values
        device_reply = 0                                  # 0 (= bad data trasmission) is assigned to device_reply 
        
        for device, address in devices.items():           # iteration over the devices
            data_sent = send_data(data, device, address)  # (the same) data is sent
            device_return = read_data(device, address)    # device is inquired
            
            if device_return == 1:                        # case positive data receival from Responder
                device_reply += 1                         # device_reply counter is increased by 1
            elif device_return == 0:                      # case of wrong checksum at Responder
                errors += 1                               # errors counter is increased by 1
                print(device, "checksum error")           # feedback is printed to the Terminal
            elif device_return == 2:                      # case of uncomplete data at Responder
                errors += 1                               # errors counter is increased by 1
                print(device, "dataframe length error")   # feedback is printed to the Terminal
            
        if device_reply == number_of_devs:                # case positive data receival by all devices
            ok_runs += 1                                  # ok_runs counter is increased by 1
        
        if ok_runs >= runs or errors >= runs:             # case ok_runs or errors equal the target runs
            elapsed = time.ticks_diff(time.ticks_ms(), t_start_ms) / 1000
            print(f"\nTotal {ok_runs} positive datasets sent in {elapsed:.3f} secs")
            print(f"Total errors: {errors}")
            print(f"Data sharing frequency: {int(runs / elapsed)} Hz\n")
            stop_test = True

except KeyboardInterrupt:
    print("\nCtrl+C detected!")
except Exception as e:
    print(f"\nAn error occurred: {e}")
finally:
    del(i2c)