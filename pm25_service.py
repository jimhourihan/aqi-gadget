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
avg_delta        = 0
pm25_buffer      = []

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
            i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
            pm25 = adafruit_pm25.PM25_I2C(i2c, None)
        else:
            import serial
            uart = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=0.25)
            pm25 = adafruit_pm25.PM25_UART(uart, None)
            
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
    global avg_delta
    current_time = time.time()
    if last_sample_time == 0:
        last_sample_time = current_time
    t = current_time - last_sample_time
    s = math.sin(t / 7.0) * 0.5 + 0.5
    time.sleep(0.5)
    pm25 = s * 200.0
    avg_delta = pm25 - avg_1m_pm25
    avg_1m_pm25 = pm25
    avg_15s_pm25 = pm25
    #return (pm25, avg_1m_pm25, avg_15s_pm25, avg_delta, current_time, "OK")
    return {
        "pm25" : pm25,
        "pm25_1m" : avg_1m_pm25,
        "pm25_15s" : avg_15s_pm25,
        "pm25_delta" : avg_delta,
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
    global last_sample_time
    global avg_delta

    elapsed = 0.0
    while elapsed < 1.0:
        sample_time = time.time()
        elapsed = sample_time - last_sample_time
        if elapsed < 1.0:
            time.sleep(1.0)

    aqdata = None

    while not aqdata:
        try:
            aqdata = pm25.read()
        except RuntimeError:
            pass
            #return not_a_result("Unable to read from sensor")

    pm25_env = aqdata["pm25 standard"]

    if elapsed < 2.3:
        # device may repeat data if under this limit
        pass
    else:
        last_sample_time = sample_time
        pm25_buffer.append((pm25_env, sample_time))

        while len(pm25_buffer) > 27:
            pm25_buffer.pop(0)

        last_avg = avg_1m_pm25
        avg_1m_pm25 = 0
        avg_15s_pm25 = 0
        count = 0
        for (pm25_samp, time_samp) in pm25_buffer:
            avg_1m_pm25 += pm25_samp
            if count < 6:
                avg_15s_pm25 += pm25_samp
                count = count + 1
        avg_1m_pm25 /= len(pm25_buffer)
        avg_15s_pm25 /= count
        avg_delta = (avg_1m_pm25 - last_avg) / elapsed

    buffer = buffer[32:]

    return {
        "pm25" : pm25_env,
        "pm25_1m" : avg_1m_pm25,
        "pm25_15s" : avg_15s_pm25,
        "pm25_delta" : avg_delta,
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
