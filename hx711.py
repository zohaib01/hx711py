import RPi.GPIO as GPIO
import time
import numpy  # sudo apt-get python-numpy

class HX711:
    def __init__(self, dout, pd_sck, gain=128):
        self.PD_SCK = pd_sck
        self.DOUT = dout

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PD_SCK, GPIO.OUT)
        GPIO.setup(self.DOUT, GPIO.IN)

        self.GAIN = 0

        # The value returned by the hx711 that corresponds to your reference
        # unit AFTER dividing by the SCALE.
        self.REFERENCE_UNIT_A = 1
        self.REFERENCE_UNIT_B = 1
        self.REFERENCE_UNIT = self.REFERENCE_UNIT_A

        self.OFFSET_A = 1
        self.OFFSET_B = 1
        self.OFFSET = self.OFFSET_A
        self.lastVal = long(0)

        self.LSByte = [2, -1, -1]
        self.MSByte = [0, 3, 1]

        self.MSBit = [0, 8, 1]
        self.LSBit = [7, -1, -1]

        self.byte_range_values = self.LSByte
        self.bit_range_values = self.MSBit

        self.set_gain(gain)

        time.sleep(1)

    def is_ready(self):
        return GPIO.input(self.DOUT) == 0

    def set_gain(self, gain):
        if gain is 128:
            self.GAIN = 1
        elif gain is 64:
            self.GAIN = 3
        elif gain is 32:
            self.GAIN = 2

        GPIO.output(self.PD_SCK, False)
        self.read()

    def createBoolList(self, size=8):
        ret = []
        for i in range(size):
            ret.append(False)
        return ret

    def read(self):
        while not self.is_ready():
            #print("WAITING")
            pass

        dataBits = [self.createBoolList(), self.createBoolList(), self.createBoolList()]
        dataBytes = [0x0] * 4

        for j in range(self.byte_range_values[0], self.byte_range_values[1], self.byte_range_values[2]):
            for i in range(self.bit_range_values[0], self.bit_range_values[1], self.bit_range_values[2]):
                GPIO.output(self.PD_SCK, True)
                dataBits[j][i] = GPIO.input(self.DOUT)
                GPIO.output(self.PD_SCK, False)
            dataBytes[j] = numpy.packbits(numpy.uint8(dataBits[j]))

        #set channel and gain factor for next reading
        for i in range(self.GAIN):
            GPIO.output(self.PD_SCK, True)
            GPIO.output(self.PD_SCK, False)

        #check for all 1
        #if all(item is True for item in dataBits[0]):
        #    return long(self.lastVal)

        dataBytes[2] ^= 0x80

        return dataBytes

    def get_binary_string(self):
        binary_format = "{0:b}"
        np_arr8 = self.read_np_arr8()
        binary_string = ""
        for i in range(4):
            # binary_segment = binary_format.format(np_arr8[i])
            binary_segment = format(np_arr8[i], '#010b')
            binary_string += binary_segment + " "
        return binary_string

    def get_np_arr8_string(self):
        np_arr8 = self.read_np_arr8()
        np_arr8_string = "[";
        comma = ", "
        for i in range(4):
            if i is 3:
                comma = ""
            np_arr8_string += str(np_arr8[i]) + comma
        np_arr8_string += "]";

        return np_arr8_string

    def read_np_arr8(self):
        dataBytes = self.read()
        np_arr8 = numpy.uint8(dataBytes)

        return np_arr8

    def read_long(self):
        np_arr8 = self.read_np_arr8()
        np_arr32 = np_arr8.view('uint32')
        self.lastVal = np_arr32

        return long(self.lastVal)

    def read_average(self, times=3):
        values = long(0)
        for i in range(times):
            values += self.read_long()

        return values / times

    # A median-based read method, might help when getting random value spikes
    # for unknown or CPU-related reasons
    def read_median(self, times=3):
        values = list()
        for i in range(times):
            values.append(self.read_long())

        return numpy.median(values)

    # Compatibility function, uses channel A version
    def get_value(self, times=3):
        return self.get_value_A(times)

    def get_value_A(self, times=3):
        return self.read_average(times) - self.OFFSET_A

    def get_value_B(self, times=3):
        # for channel B, we need to set_gain(32)
        gain = self.GAIN
        self.set_gain(32)
        value = self.read_average(times) - self.OFFSET_B
        self.set_gain(gain)
        return value

    # Compatibility function, uses channel A version
    def get_weight(self, times=3):
        return self.get_weight_A(times)

    def get_weight_A(self, times=3):
        value = self.get_value_A(times)
        value = value / self.REFERENCE_UNIT_A
        return value

    def get_weight_B(self, times=3):
        value = self.get_value_B(times)
        value = value / self.REFERENCE_UNIT_B
        return value

    # Sets tare for channel A for compatibility purposes
    def tare(self, times=15):
        self.tare_A(times)

    def tare_A(self, times=15):
        # Backup REFERENCE_UNIT value
        reference_unit = self.REFERENCE_UNIT_A
        self.set_reference_unit_A(1)

        value = self.read_median(times)
        self.set_offset_A(value)

        self.set_reference_unit_A(reference_unit)

    def tare_B(self, times=15):
        # Backup REFERENCE_UNIT value
        reference_unit = self.REFERENCE_UNIT_B
        self.set_reference_unit_B(1)

        # for channel B, we need to set_gain(32)
        gain = self.GAIN
        self.set_gain(32)

        value = self.read_median(times)
        self.set_offset_B(value)

        self.set_gain(gain)
        self.set_reference_unit_B(reference_unit)

    def set_reading_format(self, byte_format="LSB", bit_format="MSB"):
        if byte_format == "LSB":
            self.byte_range_values = self.LSByte
        elif byte_format == "MSB":
            self.byte_range_values = self.MSByte

        if bit_format == "LSB":
            self.bit_range_values = self.LSBit
        elif bit_format == "MSB":
            self.bit_range_values = self.MSBit

    # sets offset for channel A for compatibility reasons
    def set_offset(self, offset):
        self.set_offset_A(offset)

    def set_offset_A(self, offset):
        self.OFFSET_A = offset
        self.OFFSET = offset

    def set_offset_B(self, offset):
        self.OFFSET_B = offset

    # sets reference unit for channel A for compatibility reasons
    def set_reference_unit(self, reference_unit):
        self.set_reference_unit_A(reference_unit)

    def set_reference_unit_A(self, reference_unit):
        self.REFERENCE_UNIT_A = reference_unit
        self.REFERENCE_UNIT = reference_unit

    def set_reference_unit_B(self, reference_unit):
        self.REFERENCE_UNIT_B = reference_unit

    # HX711 datasheet states that setting the PDA_CLOCK pin on high for >60 microseconds would power off the chip.
    # I used 100 microseconds, just in case.
    # I've found it is good practice to reset the hx711 if it wasn't used for more than a few seconds.
    def power_down(self):
        GPIO.output(self.PD_SCK, False)
        GPIO.output(self.PD_SCK, True)
        time.sleep(0.0001)

    def power_up(self):
        GPIO.output(self.PD_SCK, False)
        time.sleep(0.0001)

    def reset(self):
        self.power_down()
        self.power_up()
