"""
Andrea Favero 08/03/2025

Micropython code for Raspberry Pi Zero 2.
It demonstrates how to use a Pi Zero 2 as I2C Controller.

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


from smbus2 import SMBus
import time, random, subprocess

# variable to manually set
df_fields = 2                  # number of 16-bit fields in dataframe, max 4
runs = 200                     # limits the test to a number of runs
timeout_mins = 3               # timeout in minutes


def scan_i2c_devices():
    """Scans the I2C bus via the bash command 'i2cdetect -y -1' """
    try:
        result = subprocess.run(["i2cdetect", "-y", "1"], capture_output=True, text=True, check=True)
        output_lines = result.stdout.splitlines()  # split output into lines

        detected_devices = []

        for line in output_lines[1:]:         # skip the header line
            parts = line.split()              # split line into columns
            if not parts:
                continue

            row_prefix = parts[0].strip(":")  # remove colon from row descriptor

            for col_index, value in enumerate(parts[1:]):  # skip row label
                if value != "--":
                    # convert row/column index to I2C address
                    detected_devices.append(int(row_prefix, 16) + col_index)

        devices = {}
        device_labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        print()
        for i, addr in enumerate(detected_devices):
            devices[device_labels[i]] = addr
            print(f"Device found {device_labels[i]}:", hex(addr))
        print()
        return devices

    except subprocess.CalledProcessError as e:
        print("Error running i2cdetect:", e)
        return {}


def calculate_checksum(dataframe):
    return sum(dataframe) & 0xFF


def escape_data(dataframe):
    escaped_data = []
    for byte in dataframe:
        if byte in [0x02, 0x03, 0x5C]:  # STX, ETX, and backslash
            escaped_data.append(0x5C)   # escape character
        escaped_data.append(byte)
    return escaped_data


def send_data(dataframe, dev, adr):
    data_frame = [stx]                                       # data_frame list with the STX
    for value in dataframe:                                  # iterating over the values in data
        field_bytes = value.to_bytes(2, byteorder='big')     # convert value to bytes
        data_frame.extend(field_bytes)                       # bytes of value are added to the data_frame

    checksum = calculate_checksum(data_frame)                # calculate checksum (including STX, excluding ETX)
    data_frame.append(checksum)                              # append checksum and ETX to the data frame
    escaped_data_frame = escape_data(data_frame)[1:] + [etx] # add escapes characters

    try:
        bus.write_i2c_block_data(adr, 0, escaped_data_frame) # send data frame over I2C)
    except TimeoutError as e:
        print(f"I2C Timeout Error on device {dev}: {e}")
    except Exception as e:
        print(f"I2C Error on device {dev}: {e}")
        escaped_data_frame = []

    return escaped_data_frame



def read_data(dev, adr):
    try:
        return bus.read_byte(adr)
    except TimeoutError as e:
        print(f"I2C Timeout Error on device {dev}: {e}")
    except Exception as e:
        print(f"I2C Error on device {dev}: {e}") 
    return None 


def stop_code():
    if bus:
        try:
            bus.close()            # close the I2C bus
        except Exception as e:
            print(f"Error closing I2C bus: {e}")



# other variables
stx = 0x02                         # STX (Start of Text)
etx = 0x03                         # ETX (End of Text)
ok_runs = 0                        # counter for positive dataframe transmissions
errors = 0                         # counter for the errors occurrence
stop_test = False                  # flag to stop the code after number or runs
    
try:                               # tentative approach
    bus = SMBus(1)                 # I2C bus is initialized
    devices = scan_i2c_devices()   # scans for devices in I2C bus

    # manually restricting devices
#     devices = {'A': 0x41}

    number_of_devs = len(devices)  # number of devices
    if number_of_devs == 0:
        print("Quiting the code as no devices found in the I2C bus")
        stop_code()
        exit(0)

    print(f"Sending {runs} dataframes (of {df_fields} fields each) to the devices ...")

    timeout_s = 60 * timeout_mins              # timeout in seconds
    t_start = time.time()                      # time reference for timing purpose

    while time.time() - t_start < timeout_s:   # loops until timeout

        if stop_test:                          # case stop_test is True
            break                              # while loop is interrupted

        data = [random.randrange(0, 65535) for _ in range(df_fields)]  # generate random fields

        device_reply = 0                       # device_reply is zeroed at every run
        print()
        for device, address in devices.items():           # iterates over the devices in dict
            print(f"Send data to device {device}: {data}")
            data_sent = send_data(data, device, address)  # call the data sending function
            device_return = read_data(device, address)    # devive is inquired to get (8bit) return

            if device_return == 1:             # case device returns 1 (all ok)
                device_reply += 1              # device_reply counter is increased
            elif device_return == 0:           # case device returns 0 (checksum error)
                errors += 1                    # errors counter is increase
                print(device, "error")         # feedback is printed to terminal
            elif device_return == 2:           # case device returns 2 (dataframe lenght error)
                errors += 1                    # errors counter is increase
                print(device, "checksum error")  # feedback is printed to terminal
            else:                              # other cases
                val = device_return            # returned value is assigned to local variable (just as example)

        if device_reply == number_of_devs:     # case all devices replied positively
            ok_runs += 1                       # ok_runs counter is increased

        if ok_runs >= runs or errors >= runs:  # case one of the counters equals the runs value
            elapsed_time = round(time.time() - t_start, 3)
            print(f"\nTotal of {ok_runs} positive datasets sent in {elapsed_time} secs")
            print(f"Total errors: {errors}\n")
            stop_test = True


except KeyboardInterrupt:
    print("\nCtrl+C detected!")

except Exception as e:
    print(f"\nAn errorsor occured: {e}")

finally:
    stop_code()

