import board
import busio
import adafruit_bme680

i2c = None
sensor = None

def init ():
    global i2c
    global sensor
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)

def read_packet ():
    tempC = sensor.temperature
    gas = sensor.gas
    h = sensor.humidity
    mbars = sensor.pressure
    return {
        "C" : tempC,
        "F" : tempC * 1.8 + 32.0,
        "H" : h,
        "hPa" : mbars,
        "Gas" : gas
    }

def stop ():
    pass
