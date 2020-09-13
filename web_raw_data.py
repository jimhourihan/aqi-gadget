import cherrypy
import subprocess
from multiprocessing import Queue
from string import Template
from aqi_util import *
from datetime import datetime
from cherrypy.process.plugins import BackgroundTask

server_ip   = "127.0.0.1"
server_port = 8081
server_name = "localhost"

envhtml = Template("""
<style>
.centered {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translateX(-50%) translateY(-50%);
}
.desc {
    color: $FG;
    font-size: 14vw;
    font-family: Arial, Helvetica, sans-serif;
    font-weight: bold;
}
.time {
    color: $FG;
    font-size: 3.5vw;
    font-family: Arial, Helvetica, sans-serif;
}
</style>
<meta http-equiv="refresh" content="$REFRESH">
<body style="background-color: $BG">
  <html>
    <div class="centered">
        <center> <div class="desc">$TEMPF°F</div></center>
        <center> <div class="desc">$TEMPC°C</div></center>
<br>
        <center> <div class="desc">$HUMIDITY%</div> </center>
        <center> <div class="time">$TIME</div> </center>
    </div>
  </html>
</body>
""")

aqihtml = Template("""
<style>
.centered {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translateX(-50%) translateY(-50%);
}

.bignum {
    color: $FG;
    font-size: 30vw;
    font-family: Arial, Helvetica, sans-serif;
    font-weight: bold;
}

.desc {
    color: $FG;
    font-size: 8vw;
    font-family: Arial, Helvetica, sans-serif;
    font-weight: bold;
}

.subdesc {
    color: $FG;
    font-size: 5vw;
    font-family: Arial, Helvetica, sans-serif;
    font-weight: bold;
}

.time {
    color: $FG;
    font-size: 3.5vw;
    font-family: Arial, Helvetica, sans-serif;
}

.boldfont {
  font-family: Arial, Helvetica, sans-serif;
  font-weight: bold;
}

.regularfont {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 3vw;
}

.button0 {
  background-color: $BGCOLOR0;
  border: 1px solid grey;
  border-radius: 8px;
  color: black;
  width: 23.5%;
  padding: 1% 0px;
  margin: 0px 0px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 5vw;
  cursor: pointer;
}

.button1 {
  background-color: $BGCOLOR1;
  border: 1px solid grey;
  border-radius: 8px;
  color: black;
  width: 23.5%;
  padding: 1% 0px;
  margin: 0px 0px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 5vw;
  cursor: pointer;
}

.button2 {
  background-color: $BGCOLOR2;
  border: 1px solid grey;
  border-radius: 8px;
  color: black;
  width: 23.5%;
  padding: 1% 0px;
  margin: 0px 0px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 5vw;
  cursor: pointer;
}

.button3 {
  background-color: $BGCOLOR3;
  border: 1px solid grey;
  border-radius: 8px;
  color: black;
  width: 23.5%;
  padding: 1% 0px;
  margin: 0px 0px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 5vw;
  cursor: pointer;
}

</style>
<meta http-equiv="refresh" content="$REFRESH">
<body style="background-color: $BG">
  <html>
    <a href="http://$HOST/$TARGET0?refresh=$REFRESH" class="button0"><div class="boldfont">$VALUE0</div><div class="regularfont">$LABEL0</div></a>
    <a href="http://$HOST/$TARGET1?refresh=$REFRESH" class="button1"><div class="boldfont">$VALUE1</div><div class="regularfont">$LABEL1</div></a>
    <a href="http://$HOST/$TARGET2?refresh=$REFRESH" class="button2"><div class="boldfont">$VALUE2</div><div class="regularfont">$LABEL2</div></a>
    <a href="http://$HOST/$TARGET3?refresh=$REFRESH" class="button3"><div class="boldfont">$VALUE3</div><div class="regularfont">$LABEL3</div></a>


    <div class="centered">
        <center> <div class="bignum">$MAINVALUE</div> </center>
        <center> <div class="desc">$DESC</div> </center>
        <center> <div class="subdesc">$MAINLABEL | $MACHINE</div> </center>
        <center> <div class="time">$TIME</div> </center>
    </div>
  </html>
</body>
""")

def to_html_color (rgb):
    nums = [rgb[0] * 255.0, rgb[1] * 255.0, rgb[2] * 255.0]
    return '#' + ''.join('{:02X}'.format(int(a)) for a in nums)

class RawDataServer (object):
    "Raw PM25 data server"

    def __init__ (self, ask_queue, data_queue):
        self.ask_queue = ask_queue
        self.data_queue = data_queue
        self.pm_value = None
        self.env_value = {"F" : 70.5, "C" : 21.4, "H" : 60.6}

    def read_queue (self):
        while not self.data_queue.empty():
            v = self.data_queue.get()
            if isinstance(v, str):
                if v == "STOP":
                    print("INFO: [aqi] shutting down web server")
                    cherrypy.engine.exit()
            elif isinstance(v, dict):
                self.env_value = v
            else:
                self.pm_value = v

    @cherrypy.expose
    def raw (self):
        val = self.pm_value
        return str(val)

    @cherrypy.expose
    def env (self):
        now = datetime.now()

        F = str(self.env_value["F"])
        C = str(self.env_value["C"])
        H = str(self.env_value["H"])

        keys = {
            "FG" : "black",
            "BG" : "#aaaaaa",
            "TEMPF" : F,
            "TEMPC" : C,
            "HUMIDITY" : H,
            "TIME" : now.ctime(),
            "REFRESH" : "10",
        }
        return envhtml.substitute(keys)

    def big_aqi (self, other_keys):

        c          = self.pm_value[2]
        h          = self.env_value["H"]
        aqi        = aqi_from_concentration(EPA_correction(c, h))
        b_aqi      = aqi_from_concentration(c)[0]
        b_temp     = self.env_value["F"]
        b_hum      = h
        b_con      = c
        b_aqi_rgb  = rgb_shade_from_aqi(b_aqi)
        b_temp_rgb = (1, .8, .8)
        b_hum_rgb  = (.8, .8, 1.0)
        b_con_rgb  = (.85, .85, .85)
        rgb        = aqi[2]
        lum        = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        bg         = to_html_color(rgb)
        fg         = to_html_color( (0, 0, 0) if lum > .25 else (.8, .8, .8) )
        now        = datetime.now()
        port       = server_ip + ":" + str(server_port)
        machine    = server_name

        keys = {
            "MAINVALUE" : aqi[0],
            "MAINLABEL" : "Native AQI",
            "VALUE0" : aqi_from_concentration(EPA_correction(c, self.env_value["H"])),
            "VALUE1" : "{:.0f}".format(b_con),
            "VALUE2" : "{:.1f}°".format(b_temp),
            "VALUE3" : "{:.0f}%".format(b_hum),
            "LABEL0" : "Native",
            "LABEL1" : "µg/m<sup>3</sup>",
            "LABEL2" : "Temp. F",
            "LABEL3" : "Humidity",
            "TARGET0" : "native",
            "TARGET1" : "concentration",
            "TARGET2" : "env",
            "TARGET3" : "env",
            "BGCOLOR0" : to_html_color(b_aqi_rgb),
            "BGCOLOR1" : to_html_color(b_con_rgb),
            "BGCOLOR2" : to_html_color(b_temp_rgb),
            "BGCOLOR3" : to_html_color(b_hum_rgb),
            "BG" : bg,
            "FG" : fg,
            "HOST" : port,
            "MACHINE" : machine,
            "DESC" : aqi[1],
            "TIME" : now.ctime(),
            "REFRESH" : str(10000),
        }

        return aqihtml.substitute({**keys, **other_keys})

    @cherrypy.expose
    def index (self):
        return self.aqi(refresh=10)

    @cherrypy.expose
    def aqi (self, refresh=100000):
        return self.epa(refresh)

    @cherrypy.expose
    def epa (self, refresh=100000):
        c = self.pm_value[2]
        h = self.env_value["H"]
        aqi = aqi_from_concentration(EPA_correction(c, h))
        native = aqi_from_concentration(c)
        keys = {
            "MAINVALUE" : str(aqi[0]),
            "MAINLABEL" : "EPA AQI",
            "DESC" : aqi[1],
            "REFRESH" : refresh,
            "VALUE0" : str(native[0]),
            "LABEL0" : "Native AQI",
            "TARGET0" : "native",
            "VALUE1" : int(EPA_correction(c, h)),
            "BGCOLOR0" : to_html_color(native[2]),
        }
        return self.big_aqi(keys)

    @cherrypy.expose
    def native (self, refresh=100000):
        c = self.pm_value[2]
        h = self.env_value["H"]
        aqi = aqi_from_concentration(EPA_correction(c, h))
        native = aqi_from_concentration(c)
        keys = {
            "MAINVALUE" : str(native[0]),
            "MAINLABEL" : "Native AQI",
            "DESC" : native[1],
            "REFRESH" : refresh,
            "VALUE0" : str(aqi[0]),
            "LABEL0" : "EPA AQI",
            "TARGET0" : "epa",
            "VALUE1" : int(c),
            "BGCOLOR0" : to_html_color(aqi[2]),
        }
        return self.big_aqi(keys)

    @cherrypy.expose
    def display (self):
        self.ask_queue.put("TOGGLE_DISPLAY")
        return "TOGGLE_DISPLAY"

def get_host_info ():
    cmd  = 'hostname ; hostname -I'
    lines = subprocess.check_output(cmd, shell=True).decode('utf-8').splitlines()
    return (lines[0].strip(), lines[1].strip())


def start (ask_queue, data_queue, host=None, port=None, name=None):
    global server_ip
    global server_port
    global server_name
    (machine, ipaddress) = get_host_info()
    cherrypy.log.screen = False
    if host == None:
        host = ipaddress
    if port == None:
        port = 8080
    if name == None:
        name = "localhost"
    server_ip = host
    server_port = port
    server_name = name
    config = {
        'global': {
            'server.socket_host' : server_ip,
            'server.socket_port' : server_port,
            'log.access_file'    : '',
            'log.error_file'     : '',
        }
    }

    server = RawDataServer(ask_queue, data_queue)
    task = BackgroundTask(interval = 1, function = server.read_queue, args = [], bus = cherrypy.engine)
    task.start()

    print("INFO: [aqi] web server starting: {}:{}".format(server_ip, server_port))
    cherrypy.quickstart(server, '/', config)
    print("INFO: [aqi] web server finished")

if __name__ == '__main__':
    start(None, None)
