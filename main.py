import subprocess
import time
import signal
import sys
import os
from multiprocessing import Process, Queue
import web_raw_data 
import aqi_util
import urllib.request
import systemd.daemon

stop_flag = False

def signal_handler (sig, frame):
    global stop_flag
    print("INFO: [aqi] stop from signal")
    if stop_flag:
        sys.exit(-1)
    stop_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def pm25_loop (out_queue, control_queue):
    print("INFO: [aqi] sensor loop started")
    import pm25_service
    pm25_service.init(emulate=False)
    while control_queue.empty():
        #(pm25, avg_pm25, sample_time, desc) = pm25_service.read_packet()
        p = pm25_service.read_packet()
        if p[-1] == "OK":
            out_queue.put(p)
        else:
            print("ERROR:[aqi] ", p[-1])
    print("INFO: [aqi] shutting down sensor")

def display_loop (output_queue):
    print("INFO: [aqi] display loop started")
    import tft_display
    modes          = ["AQI", "LRAPA", "AQandU", "HOST", "IP", "TEMP", "CPU"]
    mode_index     = 0
    stop           = False
    backlight_time = time.time()
    backlight      = True
    last_packet    = None

    tft_display.set_mode(modes[mode_index])
    tft_display.set_backlight(True)
    tft_display.draw_clear()

    while not stop:
        packet = None
        t = time.time()
        item = output_queue.get() ## blocks
        while not output_queue.empty() and isinstance(item, tuple):
            item = output_queue.get()

        if backlight and (t - backlight_time) > 60.0:
            tft_display.set_backlight(False)
            tft_display.draw_clear()
            backlight = False
            
        if isinstance(item, tuple):
            packet = item
        elif isinstance(item, int):
            light = tft_display.backlight_state()
            if light:
                if item == 1:
                    mode_index = (mode_index + 1) % len(modes)
                    tft_display.set_mode(modes[mode_index])
                    backlight_time = t                          # reset backlight timer
                    packet = last_packet                        # immediately update
                elif item == 2 or item == 16:
                    tft_display.set_backlight(False)
                    backlight = False
            else:
                if item > 0:
                    tft_display.set_backlight(True)
                    backlight_time = t
                    backlight = True
        elif isinstance(item, str):
            if item == "STOP":
                stop = True
                break
        else:
            pass
                
        if packet == None or tft_display.backlight_state() == False:
            pass
        else:
            tft_display.draw_packet(packet)
            last_packet = packet

    tft_display.draw_off()
    print("INFO: [aqi] shutting down display")

def event_loop (control_queue, event_queue):
    print("INFO: [aqi] event loop started")
    import tft_buttons
    while control_queue.empty():
        s = tft_buttons.event()
        if s:
            event_queue.put(s)
        time.sleep(.2)
    print("INFO: [aqi] shutting down event loop")

def run ():
    global stop_flag

    root = (os.getuid() == 0)

    (machine, ipaddress) = web_raw_data.get_host_info()

    pm25_queue         = Queue()
    pm25_control_queue = Queue()
    pm25_process       = Process(target=pm25_loop, args=(pm25_queue, pm25_control_queue))
    pm25_process.start()

    web_ask_queue  = Queue()
    web_data_queue = Queue()
    web_process    = Process(target=web_raw_data.start,
                             args=(web_ask_queue,
                                   web_data_queue,
                                   ipaddress,
                                   80 if root else 8081))
    web_process.start()

    disp_output_queue  = Queue()
    disp_process       = Process(target=display_loop, args=(disp_output_queue,))
    disp_process.start()

    event_control_queue = Queue()
    event_event_queue   = Queue()
    event_process       = Process(target=event_loop, args=(event_control_queue, event_event_queue))
    event_process.start()

    packet = None
    if root:
        systemd.daemon.notify(systemd.daemon.Notification.READY)

    while not stop_flag:
        if not event_event_queue.empty():
            e = event_event_queue.get()
            if e == 3:
                stop_flag = True
                try:
                    if root:
                        subprocess.check_output('shutdown now', shell=True)
                except:
                    print("WARNING: shutdown raised exception")
                break;
            else:
                disp_output_queue.put(e)

        packet = pm25_queue.get() ## blocks

        try:
            disp_output_queue.put(packet, block=False)
        except:
            pass

        if not web_ask_queue.empty() and packet != None:
            while not web_ask_queue.empty():
                a = web_ask_queue.get()
                if isinstance(a, str):
                    if a == "TOGGLE_DISPLAY":
                        disp_output_queue.put(16)
            web_data_queue.put(packet)

    # SHUTDOWN
    web_data_queue.put("STOP")
    event_control_queue.put("STOP")
    disp_output_queue.put("STOP")
    pm25_control_queue.put("STOP")
    try:
        with urllib.request.urlopen('http://{0}:8081/web_shutdown'.format(ipaddress)) as response:
            html = response.read()
    except:
        print("[aqi] EXCEPTION")
        pass

    web_process.join()
    pm25_process.join()
    disp_process.join()
    event_process.join()

run()
