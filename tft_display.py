import digitalio
import sys
import board
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789
import subprocess
import functools
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import aqi_util
import math

ttf_file = "/home/pi/aqi-gadget/Roboto-Bold.ttf"

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

mode        = "AQI"
bfont       = ImageFont.truetype(ttf_file, 90)
tfont       = ImageFont.truetype(ttf_file, 24)
mfont       = None
width       = display.height # rotated
height      = display.width
image       = Image.new('RGB', (width, height))
draw        = ImageDraw.Draw(image)
blank_image = Image.new('RGB', (width, height))

def init_blank ():
    blank_draw  = ImageDraw.Draw(blank_image)
    blank_draw.rectangle([(0, 0), (width, height)], fill=(0, 0, 0))
    s = blank_draw.textsize("AQI", font=bfont)
    (sx, sy) = ((width - s[0]) / 2.0, (height - s[1]) / 2.0)
    blank_draw.text( (sx, sy), "AQI", font=bfont, fill=(180, 180, 180))
    display.image(blank_image, 90)
    backlight.value = True

def draw_off ():
    blank_draw  = ImageDraw.Draw(blank_image)
    blank_draw.rectangle([(0, 0), (width, height)], fill=(0, 0, 0))
    s = blank_draw.textsize("OFF", font=bfont)
    (sx, sy) = ((width - s[0]) / 2.0, (height - s[1]) / 2.0)
    blank_draw.text( (sx, sy), "OFF", font=bfont, fill=(255, 255, 0))
    display.image(blank_image, 90)
    backlight.value = True

def set_backlight (b):
    backlight.value = b

def backlight_state ():
    return backlight.value

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

def draw_message (title, msg):
    global mfont
    if mfont == None:
        mfont = ImageFont.truetype(ttf_file, 30)
    draw.rectangle([(0, 0), (width, height)], fill=(0, 0, 0))
    ms = draw.textsize(msg, font=mfont)
    ts = draw.textsize(title, font=tfont)
    (mx, my) = ((width - ms[0]) / 2.0, (height - ms[1]) / 2.0)
    (tx, ty) = ((width - ts[0]) / 2.0, my - ts[1] - 6)
    draw.text( (mx, my), msg, font=mfont, fill=(255, 255, 255) )
    draw.text( (tx, ty), title, font=tfont, fill=(150, 150, 150) )
    display.image(image, 90)

def draw_clear ():
    display.image(blank_image, 90)

def set_mode (m):
    global mode
    mode = m

hostinfo = None

def get_host_info ():
    global hostinfo
    if hostinfo == None:
        cmd  = 'hostname ; hostname -I'
        lines = subprocess.check_output(cmd, shell=True).decode('utf-8').splitlines()
        hostinfo = (lines[0].strip(), lines[1].strip())
    if hostinfo[1] == "":
        hostinfo = (hostinfo[0], "NOT CONNECTED")
    return hostinfo

def get_temperature ():
    cmd  = 'vcgencmd measure_temp'
    blob = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return blob.split('=')[1].strip()

def get_cpu_info ():
    cmd       = 'ps -eo pcpu,rss --no-headers | grep -E -v "    0"'
    blob      = subprocess.check_output(cmd, shell=True).decode("utf-8")
    usages    = list(map(lambda x: float(x.split()[0]), blob.splitlines()))
    cpu_total = functools.reduce(lambda x, y: x + y, usages)
    cpu_max   = max(usages)
    cmd2      = 'cat /proc/cpuinfo'
    lines     = subprocess.check_output(cmd2, shell=True).decode("utf-8").splitlines()
    procs     = filter(lambda x: "processor" == x[:9], lines)
    num_procs = float(len(list(procs)))
    return (int(cpu_total / num_procs), int(cpu_max), int(num_procs))

def draw_packet (packet):
    global mode
    converter = None
    if mode == "AQI":
        converter = lambda x: aqi_util.EPA_correction(x, 60.0)
    elif mode == "NativeAQI":
        converter = lambda x: x

    if converter:
        raqi = aqi_util.aqi_from_concentration(converter(packet["pm25_15s"]))
        delta = packet["pm25_delta"]
        draw_aqi(raqi[0], raqi[2], raqi[1], mode, delta)
    elif mode == "IP":
        draw_message("IP Address", get_host_info()[1])
    elif mode == "HOST":
        draw_message("Hostname", get_host_info()[0])
    elif mode == "TEMP":
        draw_message("Tempurature", get_temperature())
    elif mode == "CPU":
        info = get_cpu_info()
        draw_message(str(info[2]) + " Cores", str(info[0]) + "% | " + str(info[1]) + "%")
    else:
        draw_clear()

if __name__ == '__main__':
    draw_aqi(163, (1.0, 0.0, 0.0), "Sure", "test", 0.0)

init_blank()


