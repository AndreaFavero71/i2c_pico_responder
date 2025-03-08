from machine import mem32, Pin

class I2CResponder:
    """Implementation of a (polled) Raspberry Pico I2C Responder.

    NOTE: This module uses I2C Controller/Responder nomenclature per
          https://www.eetimes.com/its-time-for-ieee-to-retire-master-slave/

    I2C Responder support is not yet present in Pico micropython (as of MicroPython v1.14).

    This class implements a polled I2C responder by accessing the Pico registers directly.
    The implementation is largely built upon the work of danjperron as posted in:
        https://www.raspberrypi.org/forums/viewtopic.php?f=146&t=302978&sid=164b1038e60b43a22d1af6b6ba69f6ae

    """
    VERSION = "1.0.1"
    # modified for RP2350 (by Andrea Favero 20250308)
    

    # Register access method control flags
    REG_ACCESS_METHOD_RW = 0x0000
    REG_ACCESS_METHOD_XOR = 0x1000
    REG_ACCESS_METHOD_SET = 0x2000
    REG_ACCESS_METHOD_CLR = 0x3000

    # Register address offsets
    IC_CON = 0x00
    IC_TAR = 0x04
    IC_SAR = 0x08
    IC_DATA_CMD = 0x10
    IC_RAW_INTR_STAT = 0x34
    IC_RX_TL = 0x38
    IC_TX_TL = 0x3C
    IC_CLR_INTR = 0x40
    IC_CLR_RD_REQ = 0x50
    IC_CLR_TX_ABRT = 0x54
    IC_ENABLE = 0x6C
    IC_STATUS = 0x70
    IC_RXFLR = 0x78
    IC_TX_ABRT_SOURCE = 0x80

    # GPIO Register block size (i.e.) per GPIO
    GPIO_REGISTER_BLOCK_SIZE = 8

    # GPIO Register offsets within a GPIO Block
    GPIOxCTRL = 0x04

    # Register bit definitions
    IC_STATUS__RFNE = 0x08  # Receive FIFO Not Empty
    IC_RXFLR__RXFLR = 0x1f  # Receive FIFO Level
    IC_ENABLE__DISABLE = 0x0
    IC_ENABLE__ENABLE = 0x01
    IC_SAR__IC_SAR = 0x1FF  # Responder address
    IC_CLR_TX_ABRT__CLR_TX_ABRT = 0x01
    IC_RAW_INTR_STAT__RD_REQ = 0x20
    IC_CON__CONTROLLER_MODE = 0x01
    IC_CON__IC_10BITADDR_RESPONDER = 0x08
    IC_CON__IC_RESPONDER_DISABLE = 0x40
    GPIOxCTRL__FUNCSEL = 0x1F
    GPIOxCTRL__FUNCSEL__I2C = 0x03

    def write_reg(self, register_offset, data, method=0):
        """Write Pico register."""
        mem32[self.i2c_base | method | register_offset] = data

    def set_reg(self, register_offset, data):
        """Set bits in Pico register."""
        self.write_reg(register_offset, data, method=self.REG_ACCESS_METHOD_SET)

    def clr_reg(self, register_offset, data):
        """Clear bits in Pico register."""
        self.write_reg(register_offset, data, method=self.REG_ACCESS_METHOD_CLR)

    def __init__(self, i2c_device_id=0, sda_gpio=0, scl_gpio=1, responder_address=0x41, rp='RP2040'):
        """Initialize.

        Args:
            i2c_device_id (int, optional): The internal Pico I2C device to use (0 or 1).
            sda_gpio (int, optional): The gpio number of the pin to use for SDA.
            scl_gpio (int, optional): The gpio number of the pin to use for SCL.
            responder_address (int, optional): The I2C address to assign to this Responder.
            rp (string, optional): Microcontroller core architectur ('2040' or '2350').
        """
        
        print("Uploading i2c_responder ...")
        
        if rp == 'RP2040':
            # RP2040 Register base addresses
            self.I2C0_BASE = 0x40044000
            self.I2C1_BASE = 0x40048000
            self.IO_BANK0_BASE = 0x40014000
        elif rp == 'RP2350':
            # RP2350 Register base addresses
            self.I2C0_BASE = 0x40090000
            self.I2C1_BASE = 0x40098000
            self.IO_BANK0_BASE = 0x40028000
        else:
            print("\n\nRP type not recognized at i2c_responder init\n\n")
        
        # GPIO with pull-up setting: Only necessary for RP2350 but it does not harm RP2040
        self.sda_pin = Pin(sda_gpio, Pin.IN, Pin.PULL_UP)  # configure SDA with pull-up
        self.scl_pin = Pin(scl_gpio, Pin.IN, Pin.PULL_UP)  # configure SCL with pull-up
        
        self.responder_address = responder_address
        self.i2c_device_id = i2c_device_id
        self.i2c_base = self.I2C0_BASE if i2c_device_id == 0 else self.I2C1_BASE
        
        # disable I2C engine while initializing it
        self.write_reg(self.IC_ENABLE, self.IC_ENABLE__DISABLE)
        
        # clear Responder address bits
        self.clr_reg(self.IC_SAR, self.IC_SAR__IC_SAR)
        
        # Set Responder address
        self.set_reg(self.IC_SAR, self.responder_address & self.IC_SAR__IC_SAR)
        
        # clear 10 Bit addressing bit (i.e. enable 7 bit addressing)
        # clear CONTROLLER bit (i.e. we are a Responder)
        # clear RESPONDER_DISABLE bit (i.e. we are a Responder)
        self.clr_reg(
            self.IC_CON,
            (
                self.IC_CON__CONTROLLER_MODE
                | self.IC_CON__IC_10BITADDR_RESPONDER
                | self.IC_CON__IC_RESPONDER_DISABLE
            ),
        )
        
        # configure SDA and SCL for I2C function
        mem32[self.IO_BANK0_BASE | self.GPIOxCTRL | (sda_gpio * 8)] = self.GPIOxCTRL__FUNCSEL__I2C
        mem32[self.IO_BANK0_BASE | self.GPIOxCTRL | (scl_gpio * 8)] = self.GPIOxCTRL__FUNCSEL__I2C

        # enable i2c engine
        self.set_reg(self.IC_ENABLE, self.IC_ENABLE__ENABLE)
        
    
    def read_is_pending(self):
        """Return True if the Controller has issued an I2C READ command.

        If this function returns True then the Controller has issued an
        I2C READ, which means that its I2C engine is currently blocking
        waiting for us to respond with the requested I2C READ data.
        """
        status = mem32[self.i2c_base | self.IC_RAW_INTR_STAT] & self.IC_RAW_INTR_STAT__RD_REQ
        return bool(status)

    
    def put_read_data(self, data):
        """Issue requested I2C READ data to the requesting Controller.

        This function should be called to return the requested I2C READ
        data when read_is_pending() returns True.

        Args:
            data (int): A byte value to send.
        """
        # reset flag
        self.clr_reg(self.IC_CLR_TX_ABRT, self.IC_CLR_TX_ABRT__CLR_TX_ABRT)
        status = mem32[self.i2c_base | self.IC_CLR_RD_REQ]
        mem32[self.i2c_base | self.IC_DATA_CMD] = data & 0xFF


    def write_data_is_available(self):
        """Check whether incoming (I2C WRITE) data is available.

        Returns:
            True if data is available, False otherwise.
        """
        # get IC_STATUS
        status = mem32[self.i2c_base | self.IC_STATUS]
        # check RFNE (Receive FIFO not empty)
        if status & self.IC_STATUS__RFNE:
            # There is data in the Zx FIFO
            return True
        # the Rx FIFO is empty
        return False


    def write_data_bytes_available(self):
        """Determine number of bytes received.

        Returns:
            Number of bytes (at least) that can be read without blocking.
        """
        # check RXFLR (Receive FIFO level register)
        status = mem32[self.i2c_base | self.IC_RXFLR]
        return int(status & self.IC_RXFLR__RXFLR)


    def get_write_data(self, max_size=1):
        """Get incoming (I2C WRITE) data.

        Will return bytes from the Rx FIFO, if present, up to the requested size.

        Args:
            max_size (int): The maximum number of bytes to fetch.
        Returns:
            A list containing 0 to max_size bytes.
        """
        data = []
        while len(data) < max_size and self.write_data_is_available():
            data.append(mem32[self.i2c_base | self.IC_DATA_CMD] & 0xFF)
        return data

