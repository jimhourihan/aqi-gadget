import board
import busio
import time
import adafruit_bme680
import aqi_gadget_config

i2c = None
sensor = None

def init ():
    global i2c
    global sensor
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)

def read_packet ():
    # this is what I'm guessing the RH correction is based on the
    # tempurature correction:
    #
    #       RH_corrected = RH * (1.0 / 2^(offset / 11.0))
    #
    # Wikipedia says RH would 1/2 for every 11C increase in temp.  The
    # adafruit sensor seems to need a -3.7C offset if its floating in the
    # air (not touching anything)
    #
    offsetC = aqi_gadget_config.temp_offset_celsius
    tempC = sensor.temperature + offsetC
    h_factor = 1.0 / (2.0 ** (offsetC / 11.0))
    gas = sensor.gas
    h = sensor.humidity * h_factor
    mbars = sensor.pressure
    return {
        "C" : tempC,
        "F" : tempC * 1.8 + 32.0,
        "H" : h,
        "hPa" : mbars,
        "Gas" : gas,
        "time" : time.time()
    }

def stop ():
    pass
