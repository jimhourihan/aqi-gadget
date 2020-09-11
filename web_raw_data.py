import cherrypy
import subprocess
from multiprocessing import Queue
from string import Template
import aqi_util
from datetime import datetime
from cherrypy.process.plugins import BackgroundTask

server_ip   = "127.0.0.1"
server_port = 8081

html = Template("""
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

.aqibutton {
  background-color: $AQICOLOR;
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

.lrapabutton {
  background-color: $LRAPACOLOR;
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

.aqandubutton {
  background-color: $AQANDUCOLOR;
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

.conbutton {
  background-color: $CONCOLOR;
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
    <a href="http://$HOST/aqi" class="aqibutton"><div class="boldfont">$BAQI</div><div class="regularfont">AQI</div></a>
    <a href="http://$HOST/lrapa" class="lrapabutton"><div class="boldfont">$BLRAPA</div><div class="regularfont">LRAPA</div></a>
    <a href="http://$HOST/aqandu" class="aqandubutton"><div class="boldfont">$BAQANDU</div><div class="regularfont">AQandU</div></a>
    <a href="http://$HOST/concentration" class="conbutton"><div class="boldfont">$BCON</div><div class="regularfont">µg/m<sup>3</sup></div></a>


    <div class="centered">
        <center> <div class="bignum">$AQI</div> </center>
        <center> <div class="desc">$DESC</div> </center>
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
        self.value = None

    def read_queue (self):
        while not self.data_queue.empty():
            self.value = self.data_queue.get()

    @cherrypy.expose
    def raw (self):
        val = self.value
        return str(val)

    def big_aqi (self, convert_func, c, refresh=100000):
        aqi = aqi_util.aqi_from_concentration(convert_func(c))
        b_aqi = aqi_util.aqi_from_concentration(c)[0]
        b_lrapa = aqi_util.aqi_from_concentration(aqi_util.LRAPA_correction(c))[0]
        b_aqandu = aqi_util.aqi_from_concentration(aqi_util.AQandU_correction(c))[0]
        b_con = c
        b_aqi_rgb = aqi_util.rgb_shade_from_aqi(b_aqi)
        b_lrapa_rgb = aqi_util.rgb_shade_from_aqi(b_lrapa)
        b_aqandu_rgb = aqi_util.rgb_shade_from_aqi(b_aqandu)
        b_con_rgb = (.7, .7, .7)
        rgb = aqi[2]
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        bg = to_html_color(rgb)
        fg = to_html_color( (0, 0, 0) if lum > .25 else (.8, .8, .8) )
        now = datetime.now()
        h = server_ip + ":" + str(server_port)
        return html.substitute(AQI=str(aqi[0]),
                               BAQI=str(b_aqi),
                               BLRAPA=str(b_lrapa),
                               BAQANDU=str(b_aqandu),
                               BCON=str(int(b_con)),
                               AQICOLOR=to_html_color(b_aqi_rgb),
                               LRAPACOLOR=to_html_color(b_lrapa_rgb),
                               AQANDUCOLOR=to_html_color(b_aqandu_rgb),
                               CONCOLOR=to_html_color(b_con_rgb),
                               BG=bg,
                               FG=fg,
                               HOST=h,
                               DESC=aqi[1],
                               TIME=now.ctime(),
                               REFRESH=str(refresh))

    @cherrypy.expose
    def index (self):
        return self.aqi()

    def show_aqi (self, convert_func, refresh):
        val = self.value
        if val:
            return self.big_aqi(convert_func, val[2], refresh)
        else:
            return html.substitute(AQI="OFF",
                                   REFRESH="10000",
                                   BG="black",
                                   FG="white",
                                   DESC="")

    @cherrypy.expose
    def aqi (self, refresh=100000):
        return self.show_aqi(lambda x: x, refresh)

    @cherrypy.expose
    def lrapa (self, refresh=100000):
        return self.show_aqi(aqi_util.LRAPA_correction, refresh)

    @cherrypy.expose
    def aqandu (self, refresh=100000):
        return self.show_aqi(aqi_util.AQandU_correction, refresh)

    @cherrypy.expose
    def concentration (self, refresh=100000):
        return "CONCENTRATION"

    @cherrypy.expose
    def web_shutdown (self, key="blah"):
        if key == "blah":
            print("INFO: [aqi] shutting down raw web server")
            cherrypy.engine.exit()

    @cherrypy.expose
    def display (self):
        self.ask_queue.put("TOGGLE_DISPLAY")
        return "TOGGLE_DISPLAY"

def get_host_info ():
    cmd  = 'hostname ; hostname -I'
    lines = subprocess.check_output(cmd, shell=True).decode('utf-8').splitlines()
    return (lines[0].strip(), lines[1].strip())


def start (ask_queue, data_queue, host=None, port=None):
    global server_ip
    global server_port
    cherrypy.log.screen = False
    if host == None:
        (machine, ipaddress) = get_host_info()
        host = ipaddress
    if port == None:
        port = 8081
    server_ip = host
    server_port = port
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

    print("INFO: [aqi] web server starting: ", str(config))
    cherrypy.quickstart(server, '/', config)
    print("INFO: [aqi] web server finished")

if __name__ == '__main__':
    start(None, None)
