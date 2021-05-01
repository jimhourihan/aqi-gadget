import digitalio
import sys
import board
from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789
import subprocess
import functools
import aqi_gadget_config
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

mode         = "AQI"
bfont        = ImageFont.truetype(ttf_file, 80)
tfont        = ImageFont.truetype(ttf_file, 22)
mfont        = None
width        = display.height # rotated
height       = display.width
fb_image     = Image.new('RGB', (width, height))
fb_draw      = ImageDraw.Draw(fb_image)
blank_image  = None
output_state = {} # combined packet


def small_font ():
    global mfont
    if mfont == None:
        mfont = ImageFont.truetype(ttf_file, 30)
    return mfont

def init_blank (blank_type = 'AQI'):
    global blank_image
    if blank_type == 'AQI':
        blank_image = Image.new('RGB', (width, height))
        blank_draw  = ImageDraw.Draw(blank_image)
        blank_draw.rectangle([(0, 0), (width, height)], fill=(0, 0, 0))
        s = blank_draw.textsize("AQI", font=bfont)
        (sx, sy) = ((width - s[0]) / 2.0, (height - s[1]) / 2.0)
        blank_draw.text( (sx, sy), "AQI", font=bfont, fill=(180, 180, 180))
    elif blank_type == 'usb':
        blank_image = Image.open('/home/pi/aqi-gadget/images/usb_icon.png')
    elif blank_type == 'wifi':
        blank_image = Image.open('/home/pi/aqi-gadget/images/wifi_icon.png')
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

def draw_single_value (out_draw, value, rgb, level, scale_name, delta=None):
    value_fg = (0, 0, 0)
    value_rgb = (int(rgb[0] * 255.0), int(rgb[1] * 255.0), int(rgb[2] * 255.0))
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]

    if lum < 0.25:
        value_fg = (200, 200, 200)

    out_draw.rectangle([(0, 0), (width, height)], fill=value_rgb)
    s = out_draw.textsize(str(value), font=bfont)
    t = out_draw.textsize(scale_name, font=tfont)
    p = out_draw.textsize("+", font=bfont)
    w = out_draw.textsize(level, font=tfont)

    small = s[0] > 235
    if small:
        s = out_draw.textsize(str(value), font=small_font())

    xmargin = 10 if delta != None else 0
    (sx, sy) = ((width - s[0]) / 2.0 - xmargin, (height - s[1]) / 2.0 - 20)
    (tx, ty) = (width - t[0] - 10, height - t[1] - 6)

    out_draw.text( (sx, sy), str(value), font=(mfont if small else bfont), fill=value_fg)
    out_draw.text( (tx, ty), scale_name, font=tfont, fill=value_fg)
    out_draw.text( (10, ty), level, font=tfont, fill=value_fg)

    tsize = 22
    (x, y) = (width - tsize - 10, height / 2.0)
    if delta != None and math.fabs(delta) > .05:
        if delta > 0:
            out_draw.polygon([(x,y), (x + tsize,y), (x + tsize/2.0, y - tsize/1.4)], fill=value_fg)
        else:
            out_draw.polygon([(x,y), (x + tsize,y), (x + tsize/2.0, y + tsize/1.4)], fill=value_fg)


def draw_graph (out_draw, rgb, packet):
    value_fg = (0, 0, 0)
    value_rgb = (int(rgb[0] * 255.0), int(rgb[1] * 255.0), int(rgb[2] * 255.0))
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    rw = 16

    if lum < 0.25:
        value_fg = (200, 200, 200)

    out_draw.rectangle([(0, 0), (width, height)], fill=value_rgb)

    t = out_draw.textsize("μg", font=tfont)
    xmargin = 10 
    (tx, ty) = (width - t[0] - 10, height - t[1] - 6)
    #out_draw.text( (tx, ty), "μg", font=tfont, fill=value_fg)

    vlist = []
    total = 0
    count = 0
    for n in ['03', '05', '10', '25', '50', '100']:
        k = "pm{}_count".format(n)
        v = packet[k]
        a = int(n) / 10.0
        vlist.append(v)
        total += a * v
        count += v

    avg_rad = total / count

    for i in range(0, len(vlist)):
        v = vlist[i]
        pcent = v / count
        x0 = xmargin + i * rw
        y0 = ty
        x1 = x0 + rw - 2
        y1 = y0 - pcent * (ty - 10)
        out_draw.rectangle([(x0, y0), (x1, y1)], fill=value_fg)
            
    if count > 999999:
        tcount = str(count // 1000000) + "M"
    elif count > 999:
        tcount = str(count // 1000) + "k"
    else:
        tcount = str(count)

    trad = "{:0.2f}μm".format(avg_rad)

    sfont = small_font()
    tcount_size = out_draw.textsize(tcount, font=sfont)
    trad_size = out_draw.textsize(trad, font=sfont)

    w2 = width // 2
    h2 = height // 2

    #out_draw.rectangle([(w2, 0), (w2+2, height)], fill=value_fg)

    x0 = (w2 - tcount_size[0]) // 2 + w2
    y0 = h2 - tcount_size[1] - xmargin
    out_draw.text( (x0, y0), tcount, font=sfont, fill=value_fg)

    out_draw.rectangle([(w2 + xmargin, h2-2), (width - xmargin, h2)], fill=value_fg)

    x0 = (w2 - trad_size[0]) // 2 + w2
    y0 = h2 + xmargin // 2
    out_draw.text( (x0, y0), trad, font=sfont, fill=value_fg)

def draw_message (out_draw, title, msg):
    global mfont
    if mfont == None:
        mfont = ImageFont.truetype(ttf_file, 30)
    out_draw.rectangle([(0, 0), (width, height)], fill=(0, 0, 0))
    ms = out_draw.textsize(msg, font=mfont)
    ts = out_draw.textsize(title, font=tfont)
    (mx, my) = ((width - ms[0]) / 2.0, (height - ms[1]) / 2.0)
    (tx, ty) = ((width - ts[0]) / 2.0, my - ts[1] - 6)
    out_draw.text( (mx, my), msg, font=mfont, fill=(255, 255, 255) )
    out_draw.text( (tx, ty), title, font=tfont, fill=(150, 150, 150) )

def draw_clear ():
    if blank_image:
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

def draw_packet_into (mode, packet, draw_obj, image_obj):
    converter = None

    if mode == 'AQI' or mode[:4] == 'AQI ':
        parts = mode.split()
        psize = '*' if len(parts) < 2 else parts[1]
        aqitype = '*' if len(parts) < 3 else parts[2]
        aqifunc = '*' if len(parts) < 4 else parts[3]
        (name, key1, key2) = ("2.5µm", "pm25_15s", "pm25_delta")
        co = aqitype
        if psize == '25' or psize == '*':
            pass
        elif psize == '100':
            (name, key1, key2) = ("10µm", "pm100_15s", "pm100_delta")
        if co == '*':
            co = aqi_gadget_config.aqi_type
        if aqifunc == '*':
            aqifunc = aqi_gadget_config.aqi_function
        converter = aqi_util.aqi_correction_func(aqifunc)
                
    if converter:
        (aqi, level, rgb) = aqi_util.aqi_from_concentration(converter(packet[key1], packet["H"]), psize, co)
        delta = packet[key2]
        if len(level) > 14:
            level = level[:14]
        draw_single_value(draw_obj, aqi, rgb, level, name, delta)

    elif mode == "RAW25":
        aqifunc = aqi_gadget_config.aqi_function
        converter = aqi_util.aqi_correction_func(aqifunc)
        c = converter(packet["pm25_15s"], packet["H"])
        v = ("{:.0f}" if c >= 10.0 else "{:.1f}").format(c)
        delta = packet["pm25_delta"]
        draw_single_value(draw_obj, v, (.20, .20, .20), "pm2.5 Conc", "µg/m^3", delta)

    elif mode == "RAW100":
        c = packet["pm100_15s"]
        v = ("{:.0f}" if c >= 10.0 else "{:.1f}").format(c)
        delta = packet["pm100_delta"]
        draw_single_value(draw_obj, v, (.20, .20, .20), "pm10 Conc", "µg/m^3", delta)

    elif mode == "MBARS":
        v = "{:.0f}".format(packet["hPa"])
        draw_single_value(draw_obj, v, (.70, .85, 1.00), "Pressure", "mbar", None)

    elif mode == "IP":
        draw_message(draw_obj, "IP Address", get_host_info()[1])

    elif mode == "HOST":
        draw_message(draw_obj, "Hostname", get_host_info()[0])

    elif mode == "AQITYPE":
        draw_message(draw_obj, "AQI Type", aqi_util.aqi_type_description[aqi_gadget_config.aqi_type])

    elif mode == "AQIFUNC":
        draw_message(draw_obj, "PM25 Calibration", aqi_gadget_config.aqi_function)

    elif mode == "TEMP":
        units = "F" if aqi_gadget_config.use_fahrenheit else "C"
        v = "{:.0f}°".format(packet[units])
        draw_single_value(draw_obj, v, (.75, .75, .75), "Temp", units) 

    elif mode == "RHUM":
        rh = packet["H"]
        v = "{:.0f}%".format(rh)
        off = rh / 100.0 * 0.25
        draw_single_value(draw_obj, v, (.75, .75 + off, .75 + off), "Humidity", "Rel")

    elif mode == "GAS":
        ohms = packet["Gas"]
        rh   = packet["H"]
        v = None
        if type(ohms) == str:
            v = ohms
        else:
            #iaq  = math.log(ohms) + 0.04 * rh
            iaq  = ohms / 1000.0
            v    = "{:.0f}".format(iaq)
        draw_single_value(draw_obj, v, (0.0, 0.0, 1.0), "Gas", "IAQ")

    elif mode == "CPU":
        info = get_cpu_info()
        draw_message(draw_obj, str(info[2]) + " Cores", str(info[0]) + "% | " + str(info[1]) + "%")

    elif mode == "GRAPH":
        draw_graph(draw_obj, (.1, .1, .1), packet)

    elif type(mode) == type([]) and len(mode) == 4:
        # top left
        draw_packet_into (mode[0], packet, draw_obj, image_obj)
        tl_image = image_obj.resize((width//2, height//2), Image.BOX)

        # bot left
        draw_packet_into (mode[1], packet, draw_obj, image_obj)
        bl_image = image_obj.resize((width//2, height//2), Image.BOX)

        # top right
        draw_packet_into (mode[2], packet, draw_obj, image_obj)
        tr_image = image_obj.resize((width//2, height//2), Image.BOX)

        # bot right
        draw_packet_into (mode[3], packet, draw_obj, image_obj)
        br_image = image_obj.resize((width//2, height//2), Image.BOX)

        # comp
        image_obj.paste(tl_image, (0,0))
        image_obj.paste(bl_image, (0,height//2))
        image_obj.paste(tr_image, (width//2,0))
        image_obj.paste(br_image, (width//2,height//2))
    else:
        pass

def draw_packet (mode, packet):
    global output_state
    output_state.update(packet)
    draw_packet_into (mode, output_state, fb_draw, fb_image)
    display.image(fb_image, 90)

if __name__ == '__main__':
    draw_single_value(fb_draw, 163, (1.0, 0.0, 0.0), "Sure", "test", 0.0)
    display.image(fb_image, 90)



