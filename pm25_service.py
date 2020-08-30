#/usr/bin/env python3
import serial
import time
import struct
import math

# red 2
# black 3
# yellow 5

_emulate         = False
uart             = None
buffer           = []
last_sample_time = 0.0
avg_1m_pm25      = 0
avg_15s_pm25     = 0
avg_delta        = 0
pm25_buffer      = []

def not_a_result (msg):
    return (0, 0, 0, msg)

def init (emulate=False):
    global _emulate
    global uart
    _emulate = emulate
    if not emulate:
        uart = serial.Serial("/dev/serial0", baudrate=9600)

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
    return (pm25, avg_1m_pm25, avg_15s_pm25, avg_delta, current_time, "OK")

def read_packet ():
    if _emulate:
        return emulate_read_packet()

    global buffer
    global avg_1m_pm25
    global avg_15s_pm25
    global pm25_buffer
    global last_sample_time
    global avg_delta
    data = uart.read(32)  # read up to 32 bytes
    data = list(data)
    sample_time = time.time()

    buffer += data

    while buffer and buffer[0] != 0x42:
        buffer.pop(0)

    if len(buffer) > 200:
        buffer = []  # avoid an overrun if all bad data
    if len(buffer) < 32:
        return not_a_result("len buffer < 32")

    if buffer[1] != 0x4d:
        buffer.pop(0)
        return not_a_result("buffer[1] != 0x4d")

    frame_len = struct.unpack(">H", bytes(buffer[2:4]))[0]
    if frame_len != 28:
        buffer = []
        return not_a_result("frame_len != 28")

    try:
        frame = struct.unpack(">HHHHHHHHHHHHHH", bytes(buffer[4:]))
    except:
        return not_a_result("exception when unpacking")

    pm10_standard, pm25_standard, pm100_standard, pm10_env, \
        pm25_env, pm100_env, particles_03um, particles_05um, particles_10um, \
        particles_25um, particles_50um, particles_100um, skip, checksum = frame

    check = sum(buffer[0:30])

    if check != checksum:
        buffer = []
        return not_a_result("invalid checksum")
        

    elapsed = sample_time - last_sample_time
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

    return (pm25_env, avg_1m_pm25, avg_15s_pm25, avg_delta, sample_time, "OK")

if __name__ == '__main__':
    init()
    while True:
        p = read_packet()
        print(str(p))
