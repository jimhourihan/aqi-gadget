#!/usr/bin/env python3
import digitalio
import sys
import board
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789
from PIL import Image

# Configuration for CS and DC pins for Raspberry Pi
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None
BAUDRATE = 64000000  # The pi can be very fast!
# Create the ST7789 display:
display = st7789.ST7789( board.SPI(),
                         cs=cs_pin,
                         dc=dc_pin,
                         rst=reset_pin,
                         baudrate=BAUDRATE,
                         width=135,
                         height=240,
                         x_offset=53,
                         y_offset=40)

backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = 1

def check_usb_gadget_attached ():
    with open("/sys/devices/platform/soc/20980000.usb/udc/20980000.usb/state", 'r') as file:
        state = str(file.readline()).strip()
        return state != "not attached"

image = Image.open('images/usb_icon.png') if check_usb_gadget_attached() else Image.open('images/wifi_icon.png')
display.image(image, 90)
