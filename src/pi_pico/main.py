"""
Andrea Favero 08/03/2025

Micropython code for Raspberry Pi Pico (RP2040 and RP2350).

It demonstrates MicroPython implementation:
- to use RP2040 and RP2350 biards as I2C responders.
- to send up to four 16bits fields in dataframe with checksum validation.
- the data exchange frequency depends on number of fields and number of devices; as
rule of thumb it takes ca 5ms per 2 fields per device.

The implementation is largely built upon the work of danjperron as posted in:
https://www.raspberrypi.org/forums/viewtopic.php?f=146&t=302978&sid=164b1038e60b43a22d1af6b6ba69f6ae
and published by Eric Moyer at GitHub: https://github.com/epmoyer/I2CResponder

My addition relates to extending the functionality to RP2350 and the
dataframe contruction with checksum (data validation from the Responder).



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


from machine import Timer, Pin                     # RP specific modules
import _thread, time                               # micropython modules

# variables to manually set, on each Responder
rgb_led = False                                    # flag to set True is the omboard led is rgb
printout = True                                    # flag to enable the prints to the Shell
i2c_id = 0x41                                      # I2C address for this board
df_fields = 2                                      # number of data fields per I2C transaction (note: max 4. Set same value at i2c Master)


def print_title():
    print("\n"*10)
    print("#"*75)
    print("#", " "*71, "#")
    print("#", " "*2, "Raspberry Pi Zero2 (Controller)  <--I2C--|-->  RP2040 (Responder)"," "*2, "#")
    print("#", " "*43, "|-->  RP2350 (Responder)"," "*2, "#")
    print("#", " "*71, "#")
    print("#"*75, "\n")



def import_libraries(rgb_led=False):
    """
    Function to import libraries, after an initial 'wasting' period.
    The blinking led entertains during this 'waiting' period; This alows enough
    time for Thonny to connect and for the user to interrupt the code.
    Remaing libraries are then imported.
    """
    print("Waiting time to eventually stop the code before further imports ...\n")
    
    led_ret = False                                # led_ret is set False
    if rgb_led:                                    # case rgb_led is True
        from rgb_led import rgb_led as led         # singleton for RGB led handling
    else:                                          # case rgb_led is False
        from led import led                        # singleton for led handling
    
    # wasting time, allowing Thonny to connect and eventually stopping the RP2040 / RP2350
    led_ret = led.heart_beat(n=10, delay=1)        # led flashes (10 x color if RGB) 
    while not led_ret:                             # case led_ret is False
        time. sleep(0.1)                           # sleep some little time
    
    from shared_variables import shared_variables  # Singleton for global variables
    from i2c_handler import I2CHandler             # Class with the i2c data handling
    
    return shared_variables, I2CHandler            # return the libraries



def core1(rp, i2c_id, fields, rgb_led):
    """ Funtion with imports and function for core1."""
    # create the singleton instance of the I2CHandler class
    led = 'rgb_led' if rgb_led else 'led'          # local led type to pass to the i2c Class
    i2c = I2CHandler(rp = rp, i2c_id = i2c_id, fields = df_fields, led_type = led, printout = printout)
    i2c.run()                                      # calls the I2C infinite loop



def stop_code():
    """Function to stop core1 and interrupts."""
    if 'shared_variables' in locals():             # case shared_variables has been imported
        print("Stopping Core 1...")                # feedback is printed to the terminal
        shared_variables.halt.write(1)             # flag stopping the core1 tasks is written to the mem16 address
    import gc                                      # importing garbage collector library
    gc.collect()                                   # cleaning the memory
    time.sleep(0.5)                                # give core1 time to stop safely
    print("Closing the program ...\n\n")           # feedback is printed to the terminal
    


try:
    print_title()                                  # print the title to the Shell                     
    shared_variables, I2CHandler = import_libraries(rgb_led)  # import libraries, while setting the onboard led type 
    rp_type = shared_variables.rp                  # the microprocessor RP type is retrieved from the shared_variables
    _thread.start_new_thread(core1, (rp_type, i2c_id, df_fields, rgb_led,)) # new thread with callback to core1 function

    while True:                                    # infinite loop
        time.sleep(0.1)                            # sleep for another little while

except KeyboardInterrupt:                          # keyboard interrupts
    print("\n\nCtrl+C detected!")                  # feedback is printed to the terminal
    
except Exception as e:                             # error 
    print(f"\nAn error occured: {e}")              # feedback is printed to the terminal

finally:                                           # closing the try loop
    stop_code()                                    # stop_code is called
