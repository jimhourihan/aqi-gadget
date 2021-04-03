import configparser
import os, os.path

# which components are being used
use_web_server      = True
use_mini_tft        = True
use_pm25_i2c        = True
use_dht_sensor      = False
use_bme680_sensor   = True
use_fahrenheit      = True

# aqi function
aqi_function = 'EPA'

# aqi type ('US' or 'IN')
aqi_type = 'US'

# env sensor temp offset for dht/bme680/etc
#temp_offset_celsius = -3.5
temp_offset_celsius = -1.5

# seconds before screen times out. backlight is expensive
screen_blank_secs   = 600

# Polling a bme680 causes heating. Internet recommends 1m
env_polling_secs    = 15

# default display modes
default_display_modes = [["EPA_AQI25", "EPA_AQI10", "TEMP", "RHUM"],
                         "EPA_AQI25", "EPA_AQI10", "RAW25", "RAW10",
                         "TEMP", "RHUM", "MBARS", "GAS", "HOST", "IP"]

display_modes = default_display_modes

def read_config_file ():
    global use_web_server
    global use_mini_tft
    global use_pm25_i2c
    global use_dht_sensor
    global use_bme680_sensor
    global use_fahrenheit
    global temp_offset_celsius
    global screen_blank_secs
    global env_polling_secs
    global aqi_function
    global aqi_type
    if not os.path.exists('/boot/aqi_gadget_config.ini'):
        return
    config = configparser.ConfigParser()
    config.read('/boot/aqi_gadget_config.ini')
    if 'DISPLAY' in config:
        global display_modes
        display = config['DISPLAY']
        m = display.get('modes', str(display_modes))
        display_modes = eval(m)
    if 'SYSTEMS' in config:
        systems = config['SYSTEMS']
        use_web_server = systems.getboolean('web_server', False)
        use_mini_tft = systems.getboolean('mini_tft', False)
        use_pm25_i2c = systems.getboolean('pm25_i2c', False)
        use_dht_sensor = systems.getboolean('dht', False)
        use_bme680_sensor = systems.getboolean('bme680', False)
    if 'GENERAL' in config:
        general = config['GENERAL']
        aqi_function = general.get('aqi_function', 'EPA')
        aqi_type = general.get('aqi_type', 'US')
        use_fahrenheit = general.get('temp_units', 'C') == 'F'
        temp_offset_celsius = general.getfloat('temp_offset_in_C', -1.5)
        env_polling_secs = general.getfloat('env_polling_secs', 600)

def write_config_file ():
    config = configparser.ConfigParser()
    config['GENERAL'] = {
        "aqi_function" : aqi_function,
        "aqi_type" : aqi_type,
        "temp_units" : 'F' if use_fahrenheit else 'C',
        "temp_offset_in_C" : str(temp_offset_celsius),
        "env_polling_secs" : str(env_polling_secs),
    }
    config['SYSTEMS'] = {
        "web_server" : "1" if use_web_server else "0",
        "mini_tft" : "1" if use_mini_tft else "0",
        "pm25_i2c" : "1" if use_pm25_i2c else "0",
        "dht" : "1" if use_dht_sensor else "0",
        "bme680" : "1" if use_bme680_sensor else "0",
    }
    config['DISPLAY'] = {
        "modes" : str(display_modes),
    }
    with open("/boot/aqi_gadget_config.ini", "w") as file:
        config.write(file)

read_config_file()
