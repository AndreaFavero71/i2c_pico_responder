"""
Andrea Favero 08/03/2025

Micropython Class for Raspberry Pi Pico (RP2040 and RP2350).

This Class:
- determines if running on RP2040 or RP2350, and stores it in a instance variable.
- it stores a list with four mem16 addresses for the I2C data fields.
- it stores a mem16 address for a halt flag, used by core0 to stop core1.

Notes:
- mem16 DMA is used for inter-cores communication.
- used mem16 addresses are at very end of the SRAM.
- RP2040 and RP2350 differ in SRAM size.


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


from shared_memory import SharedMemory
import uos

class SharedVariables:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    
    def _init(self):
        print("Uploading shared_variables ...")

        self.rp = self._check_micro()
        if self.rp == "RP2040":
            base_address = 0x20041FE0   # RP2040 SRAM upper memory
        elif self.rp == "RP2350":
            base_address = 0x2007FFE0   # RP2350 SRAM upper memory

        # pins used at RP2040-ZERO / RP2350-ZERO
        self.I2C0_SDA_PIN = 0           # I2C0 SDA pin
        self.I2C0_SCL_PIN = 1           # I2C0 SCL pin
        
        # define fixed memory locations for dataframe fields (max 4 fields)
        self.HALT_FLAG_ADR = base_address
        self.FIELD_ADRS = [base_address + i * 2 for i in range(1, 5)]  # create a list with fields mem16 adressed

        # flag used to stop core1 task
        self.halt = SharedMemory(self.HALT_FLAG_ADR)
        self.halt.write(0)              # 0 = run, 1 = halt

        # create SharedMemory objects for the data fields
        self.fields = [SharedMemory(addr) for addr in self.FIELD_ADRS]

        # initialize memory locations for the data fields
        for field in self.fields:
            field.write(0)              # Set initial value to 0
    
    
    def _check_micro(self):
        # detect RP2040 or RP2350
        machine_info = uos.uname().machine.lower()
        if "rp2040" in machine_info:
            rp = "RP2040"
        elif "rp2350" in machine_info:
            rp = "RP2350"
        else:
            raise RuntimeError("Unknown microcontroller")
        print(f"Detected {rp}")
        return rp



shared_variables = SharedVariables()

