import board
import busio
import time
import adafruit_bme680
import aqi_gadget_config

i2c = None
sensor = None
start_time = None

def init ():
    global i2c
    global sensor
    global start_time
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)
    start_time = time.time()

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
    global start_time

    t        = time.time()
    offsetC  = aqi_gadget_config.temp_offset_celsius
    tempC    = sensor.temperature + offsetC
    h_factor = 1.0 / (2.0 ** (offsetC / 11.0))
    gas      = sensor.gas
    h        = sensor.humidity * h_factor
    mbars    = sensor.pressure

    d = time.time() - start_time
    if d < 300:
        # too early if under 5 mins after start up
        gas = "{} min wait".format(int(5 - d/60) + 1)

    #print("{:.1f}".format(t - start_time), gas, "{:.1f}".format(h), "{:.1f}".format(tempC), "{:.1f}".format(mbars), sep=',')

    return {
        "C" : tempC,
        "F" : tempC * 1.8 + 32.0,
        "H" : h,
        "hPa" : mbars,
        "Gas" : gas,
        "time" : t
    }

def stop ():
    pass
