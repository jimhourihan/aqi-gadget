import aqi_gadget_config
import subprocess
import time
import signal
import sys
import os
import setproctitle
from multiprocessing import Process, Queue
import web_raw_data 
import aqi_util
import urllib.request
import systemd.daemon

stop_flag      = False
use_display    = aqi_gadget_config.use_mini_tft
use_env_sensor = aqi_gadget_config.use_dht_sensor or aqi_gadget_config.use_bme680_sensor
use_web_server = aqi_gadget_config.use_web_server

def check_usb_gadget ():
    if os.path.exists("/sys/kernel/config/usb_gadget/g1"):
        # its in gadget mode: turn off WIFI
        print("INFO: [aqi] USB gadget mode")
        os.system("ifconfig wlan0 down")

def signal_handler (sig, frame):
    global stop_flag
    print("INFO: [aqi] stop from signal")
    if stop_flag:
        sys.exit(-1)
    stop_flag = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def dht_loop (out_queue, control_queue):
    import dht_service
    dht_service.init()
    setproctitle.setproctitle("aqi: dht_loop")
    while control_queue.empty():
        p = dht_service.read_packet()
        if p:
            out_queue.put(p)
        elif isinstance(p, str):
            if p == "FAIL":
                print("ERROR: [aqi] dht failure")
                break
        else:
            pass
        time.sleep(1)
    dht_service.stop()

def bme680_loop (out_queue, control_queue):
    import bme680_service
    bme680_service.init()
    setproctitle.setproctitle("aqi: bme680_loop")
    while control_queue.empty():
        p = bme680_service.read_packet()
        if p:
            out_queue.put(p)
        elif isinstance(p, str):
            if p == "FAIL":
                print("ERROR: [aqi] bme680 failure")
                break
        else:
            pass
        time.sleep(1)
    bme680_service.stop()

def env_loop (out_queue, control_queue):
    print("INFO: [aqi] env sensor loop started")
    if aqi_gadget_config.use_dht_sensor:
        dht_loop(out_queue, control_queue)
    elif aqi_gadget_config.use_bme680_sensor:
        bme680_loop(out_queue, control_queue)
    else:
        print("ERROR: [aqi] misconfigured env sensor")
    print("INFO: [aqi] shutting down env sensor")

def pm25_loop (out_queue, control_queue):
    print("INFO: [aqi] pm sensor loop started")
    import pm25_service
    pm25_service.init(emulate=False, use_i2c=aqi_gadget_config.use_pm25_i2c)
    setproctitle.setproctitle("aqi: pm25_loop")
    while control_queue.empty():
        #(pm25, avg_pm25, sample_time, desc) = pm25_service.read_packet()
        p = pm25_service.read_packet()
        if p["status"] == "OK":
            out_queue.put(p)
        else:
            print("ERROR:[aqi] ", p["status"])
    pm25_service.stop()
    print("INFO: [aqi] shutting down pm sensor")

def display_loop (output_queue):
    print("INFO: [aqi] display loop started")
    import tft_display
    modes          = ["AQI", "NativeAQI", "HOST", "IP", "TEMP", "CPU"]
    mode_index     = 0
    stop           = False
    backlight_time = time.time()
    backlight      = True
    last_pm_packet = None

    tft_display.set_mode(modes[mode_index])
    tft_display.set_backlight(True)
    tft_display.draw_clear()

    setproctitle.setproctitle("aqi: display_loop")
    while not stop:
        pm_packet = None
        t = time.time()
        item = output_queue.get() ## blocks
        while not output_queue.empty() and isinstance(item, dict):
            item = output_queue.get()

        if backlight and (t - backlight_time) > 60.0:
            tft_display.set_backlight(False)
            tft_display.draw_clear()
            backlight = False
            
        if isinstance(item, dict):
            pm_packet = item
        elif isinstance(item, int):
            light = tft_display.backlight_state()
            if light:
                if item == 1:
                    mode_index = (mode_index + 1) % len(modes)
                    tft_display.set_mode(modes[mode_index])
                    backlight_time = t                          # reset backlight timer
                    pm_packet = last_pm_packet                        # immediately update
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
                
        if pm_packet == None or tft_display.backlight_state() == False:
            time.sleep(0.2)
            pass
        else:
            tft_display.draw_packet(pm_packet)
            last_pm_packet = pm_packet

    tft_display.draw_off()
    # eat any left over queued items
    while not output_queue.empty():
        item = output_queue.get()
    print("INFO: [aqi] shutting down display")

def event_loop (control_queue, event_queue):
    print("INFO: [aqi] event loop started")
    import tft_buttons
    setproctitle.setproctitle("aqi: event_loop")
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

    setproctitle.setproctitle("aqi: pm25 process")
    pm25_queue         = Queue()
    pm25_control_queue = Queue()
    pm25_process       = Process(target=pm25_loop,
                                 name="pm25_loop",
                                 args=(pm25_queue, pm25_control_queue))
    pm25_process.start()

    disp_output_queue  = None
    disp_process       = None

    event_control_queue = None
    event_event_queue   = None
    event_process       = None

    web_command_queue = None
    web_data_queue    = None
    web_process       = None

    if use_web_server:
        setproctitle.setproctitle("aqi: web process")
        web_command_queue = Queue()
        web_data_queue    = Queue()
        web_process       = Process(target=web_raw_data.start,
                                    name="web_server",
                                    args = (web_command_queue,
                                            web_data_queue,
                                            ipaddress,
                                            80 if root else 8080,
                                            machine))
        web_process.start()

    if use_display:
        setproctitle.setproctitle("aqi: display process")
        disp_output_queue  = Queue()
        disp_process       = Process(target=display_loop,
                                     name="display_loop",
                                     args=(disp_output_queue,))
        disp_process.start()

        setproctitle.setproctitle("aqi: event process")
        event_control_queue = Queue()
        event_event_queue   = Queue()
        event_process       = Process(target=event_loop,
                                      name="event_loop",
                                      args=(event_control_queue, event_event_queue))
        event_process.start()

    env_queue         = None
    env_control_queue = None
    env_process       = None

    if use_env_sensor:
        setproctitle.setproctitle("aqi: env process")
        env_queue         = Queue()
        env_control_queue = Queue()
        env_process       = Process(target=env_loop,
                                    name="env_loop",
                                    args=(env_queue, env_control_queue))
        env_process.start()

    pm_packet = None
    if root:
        systemd.daemon.notify(systemd.daemon.Notification.READY)

    control_queues = filter(None, [env_control_queue, event_control_queue,
                                   disp_output_queue, pm25_control_queue,
                                   web_data_queue])

    processes = filter(None, [env_process, event_process, disp_process,
                              pm25_process, web_process])

    setproctitle.setproctitle("aqi: main")
    while not stop_flag:
        if use_display and not event_event_queue.empty():
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

        pm_packet = None
        env_packet = None

        if pm25_queue and not pm25_queue.empty():
            pm_packet = pm25_queue.get() ## blocks

        if env_queue and not env_queue.empty():
            env_packet = env_queue.get()

        try:
            if use_display and pm_packet:
                disp_output_queue.put(pm_packet, block=False)
        except:
            pass

        if use_web_server:
            if pm_packet != None:
                web_data_queue.put(pm_packet)
            if env_packet != None:
                web_data_queue.put(env_packet)

        if pm_packet == None and env_packet == None:
            time.sleep(.1)

    # SHUTDOWN
    for q in control_queues:
        q.put("STOP")

    while event_event_queue and not event_event_queue.empty():
        e = event_event_queue.get()

    while not pm25_queue.empty():
        p = pm25_queue.get()

    for p in processes:
        print("INFO: [aqi] joining", p.name)
        p.join(10)
        if p.is_alive():
            print("WARNING: [aqi]", p.name, "not responding, calling terminate()")
            p.terminate()
        print("INFO: [aqi] joined", p.name)

check_usb_gadget()
run()
