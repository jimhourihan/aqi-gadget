import time
import board
import adafruit_dht

device = None

def init ():
    global device
    # Initial the dht device, with data pin connected to:
    device = adafruit_dht.DHT22(board.D18, use_pulseio=True)

def stop ():
    device.exit()

def read_packet ():
    global device
    try:
        temperature_c = device.temperature
        temperature_f = temperature_c * (9 / 5) + 32
        humidity = device.humidity
        return {
            "C" : temperature_c,
            "F" : temperature_f,
            "H" : humidity,
        } 
    except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
        print("WARNING: [dht]", error.args[0])
        return None
    except Exception as error:
        stop()
        print("ERROR: [dht] bail: ", str(error))
        return "FAIL"
