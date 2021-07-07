import time
import board
import adafruit_scd30
import aqi_gadget_config

i2c        = None
sensor     = None
start_time = None
buffer     = []

def init ():
    global i2c
    global sensor
    i2c = board.I2C()   # uses board.SCL and board.SDA
    sensor = adafruit_scd30.SCD30(i2c)
    start_time = time.time()
    return sensor

def set_pressure (hPa):
    try:
        sensor.ambient_pressure = hPa
    except AttributeError as err:
        print("ERROR:", str(err))
    except:
        print("ERROR: setting ambient_pressure in scd30")

def read_packet ():
    global i2c
    global sensor
    global start_time
    global buffer

    t        = time.time()
    offsetC  = aqi_gadget_config.temp_offset_celsius
    tempC    = sensor.temperature + offsetC
    h_factor = 1.0 / (2.0 ** (offsetC / 11.0))
    h        = sensor.relative_humidity * h_factor

    co2 = sensor.CO2
    buffer.append(co2)
    if len(buffer) > 24:
        buffer.pop(0)
    bsize = len(buffer)
    avg_1m = sum(buffer) / bsize if bsize > 0 else 0

    return {
        "C" : tempC,
        "F" : tempC * 1.8 + 32.0,
        "H" : h,
        "time" : t,
        "CO2" : co2,
        "CO2_delta" : (co2 - avg_1m),
        "CO2_1m" : avg_1m,
    }

def stop ():
    pass

if __name__ == '__main__':
    init()
    while True:
        # since the measurement interval is long (2+ seconds) we check for new data before reading
        # the values, to ensure current readings.
        if sensor.data_available:
            print("Data Available!")
            print("CO2:", sensor.CO2, "PPM")
            print("Temperature:", sensor.temperature, "degrees C")
            print("Humidity:", sensor.relative_humidity, "%%rH")
            print("")
        time.sleep(0.5)

