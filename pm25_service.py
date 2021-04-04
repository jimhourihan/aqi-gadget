#/usr/bin/env python3
#import serial
import time
import struct
import board
import math
import busio
import adafruit_pm25

# red 2
# black 3
# yellow 5

_emulate         = False
uart             = None
i2c              = None
pm25             = None
buffer           = []
last_sample_time = 0.0
avg_1m_pm25      = 0
avg_15s_pm25     = 0
avg_delta_pm25   = 0
avg_1m_pm100     = 0
avg_15s_pm100    = 0
avg_delta_pm100  = 0
pm25_buffer      = []
pm100_buffer     = []

def not_a_result (msg):
    return (0, 0, 0, msg)

def init (emulate=False, use_i2c=True):
    global _emulate
    global uart
    global i2c
    global pm25
    _emulate = emulate
    if not emulate:
        if use_i2c:
            import adafruit_pm25.i2c
            i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
            pm25 = adafruit_pm25.i2c.PM25_I2C(i2c, None)
        else:
            import serial
            import adafruit_pm25.uart
            uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)
            pm25 = adafruit_pm25.uart.PM25_UART(uart, None)
            
def stop ():
    global _emulate
    global uart
    global i2c
    global pm25
    if i2c:
        i2c.deinit()
    if uart:
        uart.close()

def emulate_read_packet ():
    global last_sample_time
    global avg_1m_pm25
    global avg_15s_pm25
    global avg_delta_pm25
    current_time = time.time()
    if last_sample_time == 0:
        last_sample_time = current_time
    t = current_time - last_sample_time
    s = math.sin(t / 7.0) * 0.5 + 0.5
    time.sleep(1.0)
    pm25 = s * 500.0
    avg_delta_pm25 = pm25 - avg_1m_pm25
    avg_1m_pm25 = pm25
    avg_15s_pm25 = pm25
    #return (pm25, avg_1m_pm25, avg_15s_pm25, avg_delta, current_time, "OK")
    return {
        "pm25" : pm25,
        "pm25_1m" : avg_1m_pm25,
        "pm100" : pm25,
        "pm100_1m" : avg_1m_pm25,
        "pm25_15s" : avg_15s_pm25,
        "pm25_delta" : avg_delta_pm25,
        "pm100_15s" : avg_15s_pm25,
        "pm100_delta" : avg_delta_pm25,
        "pm03_count" : 10,
        "pm05_count" : 20,
        "pm10_count" : 30,
        "pm25_count" : 40,
        "pm50_count" : 0,
        "pm100_count" : 0,
        "time" : current_time,
        "status" : "OK",
    }

def read_packet ():
    if _emulate:
        return emulate_read_packet()

    global buffer
    global avg_1m_pm25
    global avg_15s_pm25
    global pm25_buffer
    global pm100_buffer
    global last_sample_time
    global avg_delta_pm25

    elapsed = 0.0
    while elapsed < 1.0:
        sample_time = time.time()
        elapsed = sample_time - last_sample_time
        if elapsed < 2.3:
            # device may repeat data if under this limit
            time.sleep(2.3 - elapsed)
            elapsed = sample_time - last_sample_time

    aqdata = None

    while not aqdata:
        try:
            aqdata = pm25.read()
        except RuntimeError:
            pass
            #return not_a_result("Unable to read from sensor")

    pm25_std    = aqdata["pm25 standard"]
    pm25_env    = aqdata["pm25 env"]
    pm100_std   = aqdata["pm100 standard"]
    pm100_env   = aqdata["pm100 env"]
    pm03_count  = aqdata["particles 03um"]
    pm05_count  = aqdata["particles 05um"]
    pm10_count  = aqdata["particles 10um"]
    pm25_count  = aqdata["particles 25um"]
    pm50_count  = aqdata["particles 50um"]
    pm100_count = aqdata["particles 100um"]

    #if elapsed < 2.3:
    #    time.sleep(2.3 - elapsed)
    #else:
    last_sample_time = sample_time
    pm25_buffer.append((pm25_std, sample_time))
    pm100_buffer.append((pm100_std, sample_time))

    #while len(pm25_buffer) > 27:
    while len(pm25_buffer) > 6:
        pm25_buffer.pop(0)

    while len(pm100_buffer) > 6:
        pm100_buffer.pop(0)

    avg_1m_pm25 = 0
    avg_15s_pm25 = 0
    count = 0
    for (pm25_samp, time_samp) in reversed(pm25_buffer):
        avg_1m_pm25 += pm25_samp
        if count < 6:
            avg_15s_pm25 += pm25_samp
            count = count + 1
    avg_1m_pm25 /= len(pm25_buffer)
    avg_15s_pm25 /= count
    avg_delta_pm25 = pm25_std - avg_15s_pm25

    avg_1m_pm100 = 0
    avg_15s_pm100 = 0
    count = 0
    for (pm100_samp, time_samp) in reversed(pm100_buffer):
        avg_1m_pm100 += pm100_samp
        if count < 6:
            avg_15s_pm100 += pm100_samp
            count = count + 1
    avg_1m_pm100 /= len(pm100_buffer)
    avg_15s_pm100 /= count
    avg_delta_pm100 = pm100_std - avg_15s_pm100

    #print(str(pm25_buffer))

    buffer = buffer[32:]

    return {
        "pm25" : pm25_std,
        "pm25_env" : pm25_env,
        "pm100" : pm100_std,
        "pm100_env" : pm100_env,
        "pm03_count" : pm03_count,
        "pm05_count" : pm05_count,
        "pm10_count" : pm10_count,
        "pm25_count" : pm25_count,
        "pm50_count" : pm50_count,
        "pm100_count" : pm100_count,
        #"pm25_1m" : avg_1m_pm25,
        "pm25_15s" : avg_15s_pm25,
        "pm25_delta" : avg_delta_pm25,
        "pm100_15s" : avg_15s_pm100,
        "pm100_delta" : avg_delta_pm100,
        "time" : sample_time,
        "status" : "OK",
    }

if __name__ == '__main__':
    init()
    count = 0
    while True:
        time.sleep(1)
        p = read_packet()
        print(str(p))
        count = count + 1
        if count > 10:
            break
