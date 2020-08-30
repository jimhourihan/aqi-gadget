import subprocess
import time
import signal
import sys
from multiprocessing import Process, Queue
import web_raw_data 
import aqi_util
import urllib.request

break_signal = False

def signal_handler (sig, frame):
    global break_signal
    print("INFO: break signal")
    if break_signal:
        sys.exit(-1)
    break_signal = True

signal.signal(signal.SIGINT, signal_handler)

def pm25_loop (out_queue, control_queue):
    import pm25_service
    pm25_service.init(emulate=False)
    while control_queue.empty():
        #(pm25, avg_pm25, sample_time, desc) = pm25_service.read_packet()
        p = pm25_service.read_packet()
        if p[-1] == "OK":
            out_queue.put(p)
        else:
            print("ERROR:", p[-1])
    print("INFO: shutting down sensor")

def display_loop (output_queue):
    import tft_display
    stop = False
    while not stop:
        packet = None
        while not output_queue.empty():
            item = output_queue.get() ## blocks
            if isinstance(item, tuple):
                packet = item
            elif isinstance(item, str):
                if item == "STOP":
                    print("INFO: shutting down display")
                    stop = True
                    break
            else:
                pass
                
        if packet == None:
            time.sleep(0.1)
        else:
            tft_display.draw_packet(packet, scale="AQI")
    tft_display.draw_clear()

def run ():
    global break_signal

    (machine, ipaddress) = web_raw_data.get_host_info()

    pm25_queue         = Queue()
    pm25_control_queue = Queue()
    pm25_process       = Process(target=pm25_loop, args=(pm25_queue, pm25_control_queue))
    pm25_process.start()

    web_ask_queue  = Queue()
    web_data_queue = Queue()
    web_process    = Process(target=web_raw_data.start,
                             args=(web_ask_queue, web_data_queue, ipaddress, 8081))
    web_process.start()

    disp_output_queue  = Queue()
    disp_process       = Process(target=display_loop, args=(disp_output_queue,))
    disp_process.start()

    packet = None

    while not break_signal:
        packet = pm25_queue.get() ## blocks
        try:
            disp_output_queue.put(packet, block=False)
        except:
            pass
        if not web_ask_queue.empty() and packet != None:
            while not web_ask_queue.empty():
                web_ask_queue.get()
            web_data_queue.put(packet)

    # SHUTDOWN
    web_data_queue.put("STOP")
    disp_output_queue.put("STOP")
    pm25_control_queue.put("STOP")
    try:
        with urllib.request.urlopen('http://{0}:8081/shutdown'.format(ipaddress)) as response:
            html = response.read()
    except:
        print("EXCEPTION")
        pass

    web_process.join()
    pm25_process.join()
    disp_process.join()

run()
