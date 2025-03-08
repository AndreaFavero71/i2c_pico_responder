"""
Andrea Favero 08/03/2025

Micropython Class for Raspberry Pi Pico with onboard normal led.
Examples of boards: Raspberry Pi Pico, Raspberry Pi Pico 2.

Note: This code references to led colors, for compatibility with i2c_handler.py,
as the latest uses different colors when the onboard led is of RGB type.



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


from machine import Pin
import _thread, time

class Led:
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            print("Uploading led ...")
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    
    def _init(self):
        self._lock = _thread.allocate_lock()
        self.LED_ONBOARD_PIN = 25                              # onboard LED pin
        self.led_onboard = Pin(self.LED_ONBOARD_PIN, Pin.OUT)  # GPIO pin


    def flash(self, times=1, time_s=0.01):
        # slash the led
        with self._lock:
            for _ in range(times):
                self.led_onboard.value(1)
                time.sleep(time_s)
                self.led_onboard.value(0)
                time.sleep(time_s)
    
    
    def fast_flash_red(self, ticks=1):
        self.led_onboard.value(1)
        for i in range(ticks):
            continue
        self.led_onboard.value(0)
        
    
    def fast_flash_green(self, ticks=1):
        self.led_onboard.value(1)
        for i in range(ticks):
            continue
        self.led_onboard.value(0)
    
    
    def fast_flash_blue(self, ticks=1):
        self.led_onboard.value(1)
        for i in range(ticks):
            continue
        self.led_onboard.value(0)


    def heart_beat(self, n=10, delay=0):
        self.flash(times=n, time_s=0.05)
        time.sleep(delay/2)
        self.flash(times=n, time_s=0.05)
        time.sleep(delay/2)
        self.flash(times=n, time_s=0.05)
        return True

    
    


led = Led()