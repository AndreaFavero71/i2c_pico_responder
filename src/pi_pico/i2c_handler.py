"""
Andrea Favero 08/03/2025

Micropython code for Raspberry Pi Pico (RP2040 and RP2350).

This Class:
- gets instantiated in core1 of the Pico.
- it uses mem16 DMA for inter-cores communication.
- it keeps checking for I2C arrival.
- every new 8bits received are added to previous and checked if completing a dataframe.
- dataframe is analyzed for STX, 16bits field(s), escape characters, checksum and ETX.
- when data is requested, 8 bits are returned: 1 (ok) or 0 (checksum error) or 2 (dataframe uncomplete).



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


from shared_variables import shared_variables
from i2c_responder import I2CResponder

class I2CHandler:
    
    def __init__(self,  rp='RP2040', i2c_id=0x41, fields=1, led_type='led', printout=False):
        print("Uploading i2c_handler ...")
        print("i2c_address:", hex(i2c_id))
        
        # SCA and SCL pins are defined at shared_variables (all boards the same). Change them here if needed
        sda_pin = shared_variables.I2C0_SDA_PIN
        scl_pin = shared_variables.I2C0_SCL_PIN
        
        # instantiate the I2C responder
        self.s_i2c = I2CResponder(rp = rp, i2c_device_id=0, sda_gpio=sda_pin, scl_gpio=scl_pin, responder_address=i2c_id)
        
        # number of data fields per I2C exchange
        self.df_fields = fields                        # number of (16bits) fields per dataframe (max 4)
        print(f"Number of fields: {self.df_fields}") # feedback is printed to the terminal
        self.max_buffer = 2 + 4 * self.df_fields       # max buffer size
        self.raw_data = bytearray()                    # bytearray storing bytes arriving at the i2C
        
        # library import for the onboard led
        if led_type == 'rgb_led':                      # case led == 'rgb_led'
            from rgb_led import rgb_led as led         # import the Class for the rgb led
        elif led_type == 'led':                        # case led == 'led'
            from led import led                        # import the library for the normal led
        else:                                          # else case
            print("The led type is undefined")         # feedback is printed to the terminal
        self.led = led                                 # instance variable of the led object
            

        self.printout = printout                       # instance printout
    
    

    def calculate_checksum(self, data):
        """ Returns the checksum of the received data, as module of 256."""
        return sum(data) & 0xFF
    
    
    
    def _process_received_data(self, df_fields, max_buffer):
        """
        Analyze the raw_data and return the clean_data.
        This means finding the STX header character (0x02) and the 
        the ETX terminator character (0x03).
        The \ escape character (0x5c) :
        - is used in front of the stx, etx when these are part of the data.
        - is usedin front of the escape character itself, when nreppresenting a value
        - it must be removed for proper data interpretation and checksum calculation.
        """
        
        raw_data = self.raw_data                       # local variable from instance variable
        
        if len(raw_data) < 2 + 2 * df_fields:          # case to little data
            return [], False                           # returns empty data and False checksum
        
        data = []                                      # empty list to store the arriving bits
        checksum_result = False                        # checksum_result is initially set False
        start = None                                   # start is the STX index in raw_data, initially set on None
        i = 0                                          # iterator index
        while i < len(raw_data):                       # iterating though the raw_data
            byte = raw_data[i]                         # byte at the i index position
            prev_byte = raw_data[i - 1] if i > 0 else None  # byte in previous index position
            if byte == 0x02 and prev_byte != 0x5C:     # case the byte equals to stx and not escape in front
                start = i                              # dataframe-start index (STX index location in raw_data)
            elif byte == 0x03 and start is not None:   # case the byte equals to ETX and STX not None
                is_escaped = prev_byte == 0x5C         # bool of previous byte being an escape character
                double_escape = is_escaped and i > 1 and raw_data[i - 2] == 0x5C # bool of prev two bytes == escape character
                
                if not is_escaped or double_escape:    # case index i is not following 1 or 2 escapes
                    stop = i                           # dataframe-end index (ETX index location in raw_data)
                    if i == len(raw_data) - 2 and raw_data[i + 1] == 0x03: # case EXT is followed by a second ETX
                        stop += 1                      # dataframe-end index takes the second ETX
                    if stop > start + 2 * df_fields:   # case dataframe has enough data
                        clean_data = self._escapes_removal(raw_data, start, stop) # removing escape characters
                        data, checksum_result = self._validate_data(clean_data, df_fields)   # validating data
                        break                          # end of the while loop
            i += 1                                     # move to next byte index
        return data, checksum_result                   # interpreted data and checksum result are returned
    
    
    
    
    def _escapes_removal(self, raw_data, start, stop):
        """
        Process data between STX and ETX, handling escape sequences.
        The escape character is used in front of:
            ETX (0x02, decimal 2)
            STX (0x03, decimal 3)
            Escape (0x5c, decimal 92).
        """ 

        clean_data = bytearray()                       # bytearray for dataframe purged from STX, ETX and escapes characters
        escape_next = False                            # checksum_result is set False
        
        idx = start                                    # iteration start at the raw_data index where STX was found 
        while idx <= stop:                             # iteration until raw_data index where ETX was found
            byte = raw_data[idx]                       # byte at idx index location
            if escape_next:                            # case escape_next is True
                clean_data.append(byte)                # byte is appended to clean_data
                escape_next = False                    # case escape_next is set False
            
            elif byte == 0x5C:                         # case of escape character at idx raw_data index location
                if idx + 1 <= stop and raw_data[idx + 1] == 0x5C: # case escape is followed by another escape
                    clean_data.append(0x5C)            # one escape is appended
                    idx += 1                           # index is increased (to slip the second escape)
                else:                                  # case escape is not followed by another escape
                    escape_next = True                 # escape_next is set True (skip this escape)
            else:                                      # case byte is not an escape
                clean_data.append(byte)                # byte is appended to clean_data
            idx += 1                                   # move to the next byte
        return clean_data                              # return the clean_data
        
    
    
    def _validate_data(self, clean_data, df_fields):
        """
        The clean_data is a dataframe of bytes: STX + n * fields (2 bytes each) + checksum + ETX
        The n fields are calculated from the relative bytes.
        The checksum is retrieved from the clean_data.
        The checksum is calculated (it refers to the STX + the n * fields, ETX is excluded).
        The calculated checksum is confronted with the one received, and a boolean returned.
        """

        data = []                                      # empty list storing interpreted data from dataframe
        checksum_result = False                        # checksum_result is set False
        
        if len(clean_data) < 3 + 2 * df_fields:        # case clean_data has too little data
            self.led.fast_flash_red(ticks=20)          # short flashing of red led
            if self.printout:                          # case printout is True
                print("Incomplete message:", list(self.raw_data), list(clean_data))  # feedback is printed to the terminal
            return data, checksum_result               # return empty data and False checksum
        
        for i in range(0, 2 * df_fields, 2):           # iteration over the even byte 
            value = (clean_data[i+1] << 8) | clean_data[i+2]  # generate a 16bit value out of 2 bytes
            data.append(value)                         # interpreted value is appended
        checksum = clean_data[-2]                      # received chacksum (8 bits) retrieved from clean_data
        
        # case the checksum calculated on received (and interpreted) data equals the one received
        if self.calculate_checksum(clean_data[:-2]) == checksum:
            checksum_result = True                     # local flag is set True
            self.led.fast_flash_blue(ticks=10)         # very short flashing of blue led
         
        # case the calculated checksum differs from the one received                                
        else:
            if self.printout:                          # case printout is True
                print("Checksum error")                # feedback is printed to the terminal
            self.led.fast_flash_red(ticks=20)          # short flashing of red led
        
        return data, checksum_result
    
    
    
    def _read_i2c_data(self, byte, df_fields, max_buffer):
        """
        Receives one byte at the time, and feeds the raw_data list.
        For every byte received, it calls the function that checks if a complete dataframe is formed.
        In case a correct dataframe is found, the led is shortly turned on/off.
        """
        raw_data = self.raw_data                       # local variable from instace variable
        data = []                                      # list to store the interpreted data
        
        raw_data.append(byte)                          # the recived byte is appended to the raw_data list
        data, checksum_result = self._process_received_data(df_fields, max_buffer) # checks if a complete dataframe
        
        if checksum_result:                            # case of correct checksum
            self.raw_data = bytearray()                # self.raw_data is 'cleaned'
        else:                                          # case of incorrect checksum
            if len(raw_data) > max_buffer:             # case of local raw_data is longher than max_buffer
                self.raw_data = raw_data[1:]           # older byte sliced out, remaining assigned to instance variable
        
        return data, checksum_result                   # data and checksum fals are returned
    
    
    
    def run(self):
        """
        This is essentially the main function of this Class.
        It keeps checking whether there is data arrival or request at i2c.
        If there is data arrival, it checks it: If it's the completion of a dataframe, mem16 variables are updated.
        If there is data request, it reply with 3 possible bytes:
            0 if the last received data completed a dataframe with not correct checksum
            1 if the last received data completed a dataframe with correct checksum
            2 if there is no data received yet or data is too short
        """
        s_i2c = self.s_i2c                             # local object of the i2c instance  
        df_fields = self.df_fields                     # local variable from instace variable of number of fields in dataframe
        max_buffer = self.max_buffer                   # local variable from instace variable of max bytes in buffer
        fields = shared_variables.fields               # local variable of fields
        printout = self.printout                       # local variable to print some data to the terminal (only for debug purpose)
    
        data = []                                      # empty list to be populated with data received at i2c
        check_ok = False                               # flag for coherent i2c data receival is initially set False
       
        
        while True:                                    # infinite loop
            
            if shared_variables.halt.read():           # case the shared_variables.halt variable is set True
                print("shared_variables.halt.read() at i2c_handler.run():", shared_variables.halt.read())
                break                                  # infinite loop is interrupted
            
            if s_i2c.write_data_is_available():        # case there is data at the i2c arrival buffer
                data, check_ok = self._read_i2c_data(s_i2c.get_write_data()[0], df_fields, max_buffer)  # byte is read and analyzed
                
                if check_ok and len(data) > 0:         # case the received data reppresent a complete dataframe
                    if printout:                       # case printout is set True
                        print("Received data:", data)  # feedbaclk is printed to the terminal
                    
                    for i in range(df_fields):         # iteration over the number of fields
                        fields[i].write(data[i])       # updated value at the specific data sharing memory location  


            elif s_i2c.read_is_pending():                   # case there is i2c data request    
                if len(data)>0:                             # case there is data from previous i2c data arrival
                    if check_ok:                            # case the check_ok is True (checksum ok on received data)
                        self.s_i2c.put_read_data(1 & 0xff)  # 1 is returned to I2C (1 means checksum is ok)
                    else:                                   # case the check_ok is False (checksum not ok on received data)
                        self.s_i2c.put_read_data(0 & 0xff)  # 0 is returned to I2C (0 means checksum is not correct)
                        if printout:                        # case printout is set True
                            print("Checksum error")         # feedback is printed to the terminal
                else:                                       # case there is no data from previous i2c data arrival
                    self.s_i2c.put_read_data(2 & 0xff)      # 2 is returned to I2C (no data received yet) 
                    if printout:                            # case printout is set True
                        print("Uncomplete data:", data)     # feedback is printed to the terminal

