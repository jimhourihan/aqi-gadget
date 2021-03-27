# which components are being used
use_web_server      = True
use_mini_tft        = True
use_pm25_i2c        = True
use_dht_sensor      = False
use_bme680_sensor   = True
use_fahrenheit      = True

# env sensor temp offset for dht/bme680/etc
#temp_offset_celsius = -3.5
temp_offset_celsius = -1.5

# seconds before screen times out. backlight is expensive
screen_blank_secs   = 600

# Polling a bme680 causes heating. Internet recommends 1m
env_polling_secs    = 15
