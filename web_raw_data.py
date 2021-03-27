import cherrypy
import subprocess
import time
from multiprocessing import Queue
from string import Template
from aqi_util import *
from datetime import datetime
from cherrypy.process.plugins import BackgroundTask

server_ip     = "127.0.0.1"
server_port   = 8081
server_name   = "localhost"
packet_buffer = []
max_packets   = 100

settingshtml = Template("""
<style>

  body {
      background: #bbbbbb;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 3vw;
      margin-top: 1em;
      margin-left: 2em;
      margin-right: 2em;
  }

  ::selection {
      background: cornsilk;
  }

  table {
      width: 80%;
      font-size: 2.5vw;
  }

  input { font-size: 2.5vw; }
  button { font-size: 2.5vw; }
  select { font-size: 2.5vw; }
  option { font-size: 2.5vw; }

  .slogan {
      font-size: 10pt;
      font-style: italic;
  }

</style>

<html>
  <body>
    <h2>AQI Gadget Settings</h2>

    <hr>

    <form id="wifi">
      <table>
        <th align="left">WiFi</th>
        <tr>
          <td width="40%"  align="right">
            <label>Network Name:</label><br>
          </td>
          <td>
            <input type="text" name="network" id="network" value=""><br>
          </td>
          <td align="left">
          </td>
        </tr>
        <tr>
          <td width="40%"  align="right">
            <label>Password:</label>
          </td>
          <td>
            <input type="text" name="password" id="password" value="">
          </td>
          <td align="left">
            <button type="submit" form="wifi"
                    formaction="http://aqi-gadget-001.local:8080/set-wifi">Save</button>
          </td>
        </tr>
      </table>
    </form>

    <hr>

    <form id="other">
    <table>
        <th align="left">Localization</th>
        <tr>
            <td width="40%" align="right">
              <label>Country:</label>
            </td>
            <td>
              <select name="country" id="country">
                <option value="US">US</option>
                <option value="IN">India</option>
              </select>
            </td>
            <td>
        </tr>
        
        <tr>
            <td width="40%" align="right">
              <label>Temperature Units:</label>
            </td>
            <td>
              <select name="temp" id="temp">
                <option value="C">Celcius</option>
                <option value="F">Farenheit</option>
              </select>
            </td>
        </tr>
    </table>

    <br>

      <table>
        <th align="left">Calibration</th>
        <tr>
          <td width="40%" align="right">
            <label>Particle Type:</label><br>
          </td>
          <td>
            <select name="particle" id="particle">
              <option value="wood">Wood Smoke (EPA)</option>
              <option value="standard">Industrial / Vehicle</option>
            </select><br>
          </td>
          <td>
          </td>
        </tr>
        <tr>
          <td width="40%" align="right">
            <label>Temperature Offset:</label>
          </td>
          <td>
            <input type="text" name="offset" id="offset" value="-1.5">
          </td>
          <td>
            <button type="submit" form="other"
                    formaction="http://aqi-gadget-001.local:8080/set_general">Save</button>
          </td>
        </tr>
      </table>
    </form>

    <hr>

    <br>
    <div class="slogan">
    Another Fine Product of Cheez Grits (TM)
    </div>

  </body>
</html>
""")

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
                if "pm25" in v:
                    self.pm_value = v
                else:
                    self.env_value = v

    @cherrypy.expose
    def settings (self):
        return settingshtml.substitute({})

    @cherrypy.expose
    def set_wifi (self, network="network", password="password"):
        print("INFO: set_wifi:", network, password)
        return "OK"

    @cherrypy.expose
    def set_general (self, country="US", temp="F", particle="wood", offset="-1.5"):
        print("INFO: set_general:", country, temp, particle, offset)
        return "OK"

    @cherrypy.expose
    def raw (self):
        val = {**self.env_value, **self.pm_value}
        return str(val)

    @cherrypy.expose
    def env (self, refresh=10000):
        t = self.env_value["time"]
        F = "{:.1f}".format(self.env_value["F"])
        C = "{:.1f}".format(self.env_value["C"])
        H = "{:.1f}".format(self.env_value["H"])

        keys = {
            "FG" : "black",
            "BG" : "#aaaaaa",
            "TEMPF" : F,
            "TEMPC" : C,
            "HUMIDITY" : H,
            "TIME" : time.ctime(t),
            "REFRESH" : str(refresh),
        }
        return envhtml.substitute(keys)

    def big_aqi (self, other_keys):

        c          = self.pm_value["pm25_15s"]
        h          = self.env_value["H"]
        t          = self.pm_value["time"]
        aqi        = aqi_from_concentration(EPA_25_correction(c, h), 2.5, "US")
        b_aqi      = aqi_from_concentration(c, 2.5, "US")[0]
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
            "VALUE0" : aqi_from_concentration(EPA_25_correction(c, self.env_value["H"]), 2.5, "US"),
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
            #"TIME" : now.ctime(),
            "TIME" : time.ctime(t),
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
        c = self.pm_value["pm25_15s"]
        h = self.env_value["H"]
        epa = aqi_from_concentration(EPA_25_correction(c, h), 2.5, "US")
        native = aqi_from_concentration(c, 2.5, "US")
        rgb = epa[2]
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        bg = to_html_color(rgb)
        fg = to_html_color( (0, 0, 0) if lum > .25 else (.8, .8, .8) )
        keys = {
            "MAINVALUE" : str(epa[0]),
            "MAINLABEL" : "US EPA AQI",
            "DESC" : epa[1],
            "REFRESH" : refresh,
            "VALUE0" : str(native[0]),
            "LABEL0" : "Native AQI",
            "TARGET0" : "native",
            "BGCOLOR0" : to_html_color(native[2]),
            "VALUE1" : int(EPA_25_correction(c, h)),
        }
        return self.big_aqi(keys)

    @cherrypy.expose
    def native (self, refresh=100000):
        c = self.pm_value["pm25_15s"]
        h = self.env_value["H"]
        epa = aqi_from_concentration(EPA_25_correction(c, h), 2.5, "US")
        native = aqi_from_concentration(c, 2.5, "US")
        rgb = native[2]
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        bg = to_html_color(rgb)
        fg = to_html_color( (0, 0, 0) if lum > .25 else (.8, .8, .8) )
        keys = {
            "MAINVALUE" : str(native[0]),
            "MAINLABEL" : "Native AQI",
            "BG" : bg,
            "FG" : fg,
            "DESC" : native[1],
            "REFRESH" : refresh,
            "VALUE0" : str(epa[0]),
            "LABEL0" : "US EPA AQI",
            "TARGET0" : "epa",
            "BGCOLOR0" : to_html_color(epa[2]),
            "VALUE1" : int(c),
        }
        return self.big_aqi(keys)

    @cherrypy.expose
    def display (self):
        self.ask_queue.put("TOGGLE_DISPLAY")
        return "TOGGLE_DISPLAY"

def get_host_info ():
    cmd  = 'hostname ; hostname -I'
    lines = subprocess.check_output(cmd, shell=True).decode('utf-8').splitlines()
    return (lines[0].strip(), lines[1].strip().split())

def start (ask_queue, data_queue, host=None, port=None, name=None):
    global server_ip
    global server_port
    global server_name
    import setproctitle
    setproctitle.setproctitle("aqi: web server")
    (machine, ipaddresses) = get_host_info()
    cherrypy.log.screen = False
    if host == None:
        host = ipaddress[0]
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
