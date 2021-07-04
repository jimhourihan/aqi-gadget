#/usr/bin/env python3
#
# This is a one off interface to the 50003ST PM25 sensor which includes
# temp, rh, and CH2O sensor. I have only had access to one of these and its
# RH sensor only ever varies by about 5% which makes me wonder if its
# broken.
#
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

def buffer_to_string (b):
    s = ""
    for byte in buffer:
        s += "{}0x{:02x}".format('' if len(s) == 0 else ' ', byte)
    return s

def init (emulate=False):
    global _emulate
    global uart
    _emulate = emulate
    if not emulate:
        uart = serial.Serial("/dev/serial0", baudrate=9600)
    return uart

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

def has_header (buf):
    return len(buf) > 3 and buffer[0:4] == [0x42, 0x4d, 0x00, 0x22]

def read_packet ():
    if _emulate:
        return emulate_read_packet()

    global buffer
    global avg_1m_pm25
    global avg_15s_pm25
    global pm25_buffer
    global last_sample_time
    global avg_delta
    sample_time = time.time()

    elapsed = 0.0
    while elapsed < 1.0:
        sample_time = time.time()
        elapsed = sample_time - last_sample_time
        if elapsed < 1.0:
            time.sleep(1.0)

    needs_data = True
    header = [0x42, 0x4d]

    while needs_data:
        try:
            data = uart.read(40)  # read up to 40 bytes
        except Exception as err:
            return not_a_result(str(err))

        data = list(data)
        buffer += data

        while len(buffer) > 0 and buffer[0] != header[0]:
            buffer.pop(0)

        if len(buffer) > 1 and buffer[1] != header[1]:
            buffer.pop(0)

        needs_data = len(buffer) < 40 or buffer[:len(header)] != header
        #if needs_data:
        #    print("buffer size {}: {}".format(len(buffer), buffer_to_string(buffer)))

    frame_len = struct.unpack(">H", bytes(buffer[2:4]))[0]
    if frame_len != 36:
        buffer = []
        return not_a_result("frame_len != 36 ({})".format(frame_len))

    try:
        frame = struct.unpack(">HHHHHHHHHHHHHHHHHH", bytes(buffer[4:40]))
    except:
        return not_a_result("exception when unpacking")

    pm10_std, pm25_std, pm100_std, pm10_env, \
        pm25_env, pm100_env, pm03_count, pm05_count, pm10_count, \
        pm25_count, pm50_count, pm100_count, \
        ch2o, tempC, rh, skip, codes, checksum = frame

    check = sum(buffer[0:38])

    if check != checksum:
        buffer = []
        return not_a_result("invalid checksum")

    ch2o = ch2o / 1000.0 # mg/m^3
    tempC = tempC / 10.0 # C
    rh = rh / 10.0 # %
        
    if elapsed < 2.3:
        # device may repeat data if under this limit
        pass
    else:
        last_sample_time = sample_time
        pm25_buffer.append((pm25_std, sample_time))

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

    buffer = buffer[38:]

    return {
        "pm25" : pm25_std,
        "pm25_env" : pm25_env,
        "pm03_count" : pm03_count,
        "pm05_count" : pm05_count,
        "pm10_count" : pm10_count,
        "pm25_count" : pm25_count,
        "pm50_count" : pm50_count,
        "pm100_count" : pm100_count,
        "pm25_1m" : avg_1m_pm25,
        "pm25_15s" : avg_15s_pm25,
        "pm25_delta" : avg_delta,
        "time" : sample_time,
        "C" : tempC,
        "F" : tempC * (9.0 / 5.0) + 32.0,
        "H" : rh,
        "CH2O" : ch2o,
        "status" : "OK",
    }


if __name__ == '__main__':
    init()
    while True:
        p = read_packet()
        print(str(p))
