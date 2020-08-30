import digitalio
import board
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import aqi_util
import math

# Configuration for CS and DC pins for Raspberry Pi
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None
BAUDRATE = 64000000  # The pi can be very fast!
# Create the ST7789 display:
display = st7789.ST7789(
    board.SPI(),
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

backlight       = digitalio.DigitalInOut(board.D22)
buttonA         = digitalio.DigitalInOut(board.D23)
buttonB         = digitalio.DigitalInOut(board.D24)

backlight.switch_to_output()
buttonA.switch_to_input()
buttonB.switch_to_input()

backlight.value = True

#display.fill(color565(0, 255, 0))  # red

#font   = ImageFont.load_default()
bfont  = ImageFont.truetype('/home/pi/fonts/Roboto-Bold.ttf', 90)
tfont  = ImageFont.truetype('/home/pi/fonts/Roboto-Bold.ttf', 24)
width  = display.height # rotated
height = display.width
image  = Image.new('RGB', (width, height))
draw   = ImageDraw.Draw(image)

def draw_aqi (aqi, rgb, level, scale_name, delta):
    aqi_fg = (0, 0, 0)
    aqi_rgb = (int(rgb[0] * 255.0), int(rgb[1] * 255.0), int(rgb[2] * 255.0))
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

    if lum < 0.25:
        aqi_fg = (200, 200, 200)

    #print("draw_aqi", aqi, str(rgb))

    draw.rectangle([(0, 0), (width, height)], fill=aqi_rgb)
    s = draw.textsize(str(aqi), font=bfont)
    t = draw.textsize(scale_name, font=tfont)
    p = draw.textsize("+", font=bfont)
    w = draw.textsize(level, font=tfont)
    (sx, sy) = ((width - s[0]) / 2.0 - 10, (height - s[1]) / 2.0 - 20)
    (tx, ty) = (width - t[0] - 10, height - t[1] - 6)
    draw.text( (sx, sy), str(aqi), font=bfont, fill=aqi_fg)
    draw.text( (tx, ty), scale_name, font=tfont, fill=aqi_fg)
    draw.text( (10, ty), level, font=tfont, fill=aqi_fg)

    tsize = 22
    (x, y) = (width - tsize - 10, height / 2.0)
    if math.fabs(delta) > .05:
        if delta > 0:
            draw.polygon([(x,y), (x + tsize,y), (x + tsize/2.0, y - tsize/1.4)], fill=aqi_fg)
        else:
            draw.polygon([(x,y), (x + tsize,y), (x + tsize/2.0, y + tsize/1.4)], fill=aqi_fg)

    display.image(image, 90)

def draw_clear ():
    draw.rectangle([(0, 0), (width, height)], fill=(0, 0, 0))
    s = draw.textsize("OFF", font=bfont)
    (sx, sy) = ((width - s[0]) / 2.0 - 10, (height - s[1]) / 2.0 - 20)
    draw.text( (sx, sy), "OFF", font=bfont, fill=(100, 100, 100))
    display.image(image, 90)

def draw_packet (packet, scale="AQI"):
    ugm3 = packet[0]
    if scale == "LRAPA":
        ugm3 = aqi_util.LRAPA_correction(ugm3)
    elif scale == "AQandU":
        ugm3 = aqi_util.AQandU_correction(ugm3)
    raqi = aqi_util.aqi_from_concentration(packet[0])
    delta = packet[2]
    draw_aqi(raqi[0], raqi[2], raqi[1], scale, delta)

if __name__ == '__main__':
    draw_aqi(163, (1.0, 0.0, 0.0))

draw_clear()

