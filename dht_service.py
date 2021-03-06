import time
import board
import adafruit_dht
import aqi_gadget_config
import time

device = None

def init ():
    global device
    # Initial the dht device, with data pin connected to:
    device = adafruit_dht.DHT22(board.D18, use_pulseio=True)
    return device

def stop ():
    global device
    device.exit()

def read_packet ():
    global device
    try:
        offsetC = aqi_gadget_config.temp_offset_celsius
        temperature_c = device.temperature + offsetC
        temperature_f = temperature_c * (9 / 5) + 32
        h_factor = 1.0 / (2.0 ** (offsetC / 11.0))
        humidity = device.humidity * h_factor
        return {
            "C" : temperature_c,
            "F" : temperature_f,
            "H" : humidity,
            "time" : time.time(),
        } 
    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print("WARNING: [dht]", error.args[0])
        return None
    except Exception as error:
        stop()
        print("ERROR: [dht] bail: ", str(error))
        return "FAIL"
