import board
import busio
import time
import adafruit_hts221
import aqi_gadget_config

i2c = None
sensor = None
start_time = None

def init ():
    global i2c
    global sensor
    global start_time
    i2c = board.I2C()
    sensor = adafruit_hts221.HTS221(i2c) 
    start_time = time.time()
    return sensor

def read_packet ():
    #       RH_corrected = RH * (1.0 / 2^(offset / 11.0))
    global start_time

    t        = time.time()
    offsetC  = aqi_gadget_config.temp_offset_celsius
    tempC    = sensor.temperature + offsetC
    h_factor = 1.0 / (2.0 ** (offsetC / 11.0))
    h        = sensor.relative_humidity * h_factor

    return {
        "C" : tempC,
        "F" : tempC * 1.8 + 32.0,
        "H" : h,
        "hPa" : 1013.0,
        "Gas" : "",
        "time" : t
    }

def stop ():
    pass
