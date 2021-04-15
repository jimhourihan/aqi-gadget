import cherrypy
import subprocess
import time
from multiprocessing import Queue
from string import Template
from aqi_util import *
from datetime import datetime
from cherrypy.process.plugins import BackgroundTask
import system_tools
import aqi_gadget_config

server_ip     = "127.0.0.1"
server_port   = 8081
server_name   = "localhost"
packet_buffer = []
max_packets   = 100

wificonf = Template("""
country=$COUNTRY
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="$NETWORK"
    psk="$PASSWORD"
}
""")

forwardhtml = Template("""
<html>
<body>
<script type="text/javascript">
    window.location.href = "$LOCATION";
</script>
</body>
</html>
""")

attachedblurb = """NOTE: Settings are disabled when using WiFi. To change settings plug the AQI gadget into a computer using the USB socket closer to the display. Be sure to use a micro USB cable which supports data not just power."""

statushtml = Template("""
<style>

  body {
      background: #bbbbbb;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 2vw;
      margin-top: 1em;
      margin-left: 2em;
      margin-right: 2em;
  }

  ::selection {
      background: lightgreen;
  }

  table {
      width: 100%;
  }

  td { padding: 5px; }

  label { font-weight: bold; }

  .fail {
      background-color: orange;
      font-weight: bold;
      text-align: center;
      font-size: 2.8vw;
      padding: 4px;
      border-radius: 2.8vw;
  }

  .slogan {
      font-size: 10pt;
      font-style: italic;
  }

</style>

<html>
  <head>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta http-equiv="Expires" content="0" />
  </head>
  <body>
    <h2>AQI Gadget Status</h2>

    <hr>

      <table>
        <th align="left">Networks</th>
        <tr>
          <td width="40%" align="right"> <label>WiFi:</label> </td>
          <td> $WIFISTATUS </td>
        </tr>
        <tr>
          <td width="40%"  align="right"> <label>USB Gadget Mode:</label> </td>
          <td> $GADGETSTATUS </td>
        </tr>
      </table>

    <hr>

      <table>
        <th align="left">Hardware</th>
        <tr>
          <td width="40%" align="right"> <label>Serial Number:</label> </td>
          <td> $SERIAL </td>
        </tr>
        <tr>
          <td width="40%"  align="right"> <label>Product:</label> </td>
          <td> $PRODUCT </td>
        </tr>
        <tr>
          <td width="40%"  align="right"> <label>Manufacturer:</label> </td>
          <td> $MANUFACTURER </td>
        </tr>
        <tr>
          <td width="40%"  align="right"> <label>Hostname Base:</label> </td>
          <td> $HOSTBASE </td>
        </tr>
        <tr>
          <td width="40%"  align="right"> <label>Config:</label> </td>
          <td> $HARDWARE </td>
        </tr>
      </table>

    <hr>
      <table>
        <th align="left">Software</th>
        <tr>
          <td width="40%" align="right"> <label>Version:</label> </td>
          <td> $RELEASE </td>
        </tr>
      </table>
    <hr>

  </body>
</html>
""")

settingshtml = Template("""
<style>

  body {
      background: #bbbbbb;
      font-family: Arial, Helvetica, sans-serif;
      font-size: 2vw;
      margin-top: 1em;
      margin-left: 2em;
      margin-right: 2em;
  }

  ::selection {
      background: lightgreen;
  }

  table {
      font-size: 1.7vw;
      width: 100%;
  }

  td { padding: 5px; }

  label { font-weight: bold; }

  input { font-size: 1.7vw; }
  button { font-size: 1.7vw; }
  select { font-size: 1.7vw; }
  option { font-size: 1.7vw; }

  .slogan {
      font-size: 10pt;
      font-style: italic;
  }

</style>

<html>
  <head>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
    <meta http-equiv="Pragma" content="no-cache" />
    <meta http-equiv="Expires" content="0" />
  </head>
  <body>
    <h2>AQI Gadget Settings</h2>
$BLURB
    <hr>

    <form id="wifi">
      <table>
        <th align="left">WiFi</th>
        <tr>
          <td width="40%" align="right">
            <label>Country:</label>
          </td>
          <td>
            <input $ENABLED list="cclist" type="text" name="ccode" id="ccode" autocomplete="off" value=$CCVALUE><br>
            <datalist id="cclist">
              <option value="US">
              <option value="IN">
            </datalist>
          </td>
          <td>
          </td>
        </tr>
        <tr>
          <td width="40%"  align="right">
            <!-- Don't put "Network Name" in the label: safari will add a contacts drop-down !!-->
            <label>Network:</label>
          </td>
          <td>
            <input $ENABLED list="netlist" type="text" name="network" id="network" autocomplete="off" value=$NETWORKVALUE><br>
            <datalist id="netlist">
              $NETLIST
            </datalist>
          </td>
          <td align="left">
          </td>
        </tr>
        <tr>
          <td width="40%"  align="right">
            <label>Password:</label>
          </td>
          <td>
            <input $ENABLED type="password" name="password" id="password" value="">
          </td>
          <td align="left">
            <button $ENABLED type="submit" form="wifi" formaction="$HERE/set-wifi">Restart</button>
          </td>
        </tr>
      </table>
    </form>

    <hr>

    <form id="general">
      <table>
        <th align="left">General</th>
        <tr>
          <td width="40%" align="right">
            <label>Sensor Calibration:</label><br>
          </td>
          <td>
            <select $ENABLED name="aqifunc" id="aqifunc" value="$AQIFUNC">
                $AQIFUNCLIST
            </select><br>
          </td>
          <td>
          </td>
        </tr>
        <tr>
          <td width="40%" align="right">
            <label>AQI Type:</label><br>
          </td>
          <td>
            <select $ENABLED name="aqitype" id="aqitype" value="$AQITYPE">
                $AQITYPELIST
            </select><br>
          </td>
          <td>
          </td>
        </tr>
        <tr>
          <td width="40%" align="right">
            <label>Temperature Units:</label>
          </td>
          <td>
            <select $ENABLED name="temp" id="temp">
                $TEMPUNITSLIST
            </select>
          </td>
        </tr>
        <tr>
          <td width="40%" align="right">
            <label>Temp Offset (Celcius):</label>
          </td>
          <td>
            <input $ENABLED type="text" name="offset" id="offset" value="$TEMPOFFSET">
          </td>
          <td>
            <button $ENABLED type="submit" form="general" formaction="$HERE/set_general">Save</button>
          </td>
        </tr>
      </table>
    </form>

    <hr>


    <form id="expert">
      <table>
        <th align="left">Expert</th>
        <tr>
          <td width="40%" align="right">
            <label>Display Modes:</label>
          </td>
          <td>
            <textarea $ENABLED name="modes" id="modes" rows="8"> $MODES </textarea>
          </td>
          <td>
            <button $ENABLED type="submit" form="expert" formaction="$HERE/set_expert">Save</button>
            <button $ENABLED type="submit" form="expert" formaction="$HERE/restore_expert">Restore
                    Defaults</button>
          </td>
        </tr>
      </table>
    </form>

    <br>
    <div class="slogan">
    An Absolute Garbage Product (2021)
    </div>

  </body>
</html>
 
""")

datahtml = Template("""
<style>

body { 
    background-color: $BG; 
    margin: 0px 0px 0px 0px;
    padding: 0px 0px 0px 0px;
    font-family: Arial, Helvetica, sans-serif;
}

  table { 
    width: 100%; 
  }
  td { font-size: 3vw; }
  th { 
    color: #FFFFBB;
    font-size: 3vw;
    padding-top: 2.5vw;
    padding-bottom: 2.5vw; 
  }

  .count { color: white; }
  .barlabel { color: white;}

  .clabel { text-align: right; font-size: 6vw; }
  .cvalue { text-align: left; font-size: 6vw; font-weight: bold; padding-left: 2vw;}
  .bigcvalue { text-align: center; font-size: 12vw; font-weight: bold; padding-left: 2vw; white-space: nowrap; }

  .graph {
      background: #888888;
      padding: 2vw;
      margin-top: 5vw;
      margin-left: 1.5%;
      width: 93%;
  }

.bar1 { padding: 1vw; font-size: 6vw; width: $BAR1%; background: black; color: white; }
.bar2 { padding: 1vw; font-size: 6vw; width: $BAR2%; background: black; color: white; } 
.bar3 { padding: 1vw; font-size: 6vw; width: $BAR3%; background: black; color: white; } 
.bar4 { padding: 1vw; font-size: 6vw; width: $BAR4%; background: black; color: white; }
.bar5 { padding: 1vw; font-size: 6vw; width: $BAR5%; background: black; color: white; }
.bar6 { padding: 1vw; font-size: 6vw; width: $BAR6%; background: black; color: white; }

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
  margin-top: 2vw;
}

.regularfont {
  font-family: Arial, Helvetica, sans-serif;
  font-size: 3vw;
  margin-bottom: 2vw;
}

.button0 {
  background-color: $BGCOLOR0;
  border: 1px solid grey;
  border-radius: 8px;
  color: black;
  width: 100%;
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
  width: 100%;
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
  width: 100%;
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
  width: 100%;
  margin: 0px 0px;
  text-align: center;
  text-decoration: none;
  display: inline-block;
  font-size: 5vw;
  cursor: pointer;
}

</style>
<meta http-equiv="refresh" content="$REFRESH">
<body>
  <html>
    <table style="width=100%;">
    <colgroup>
          <col width="25%">
          <col width="25%">
          <col width="25%">
          <col width="25%">
    </colgroup>
    <tr>
    <td>
        <a href="http://$HOST/$TARGET0?refresh=$REFRESH" class="button0"><div class="boldfont">$VALUE0</div><div class="regularfont">$LABEL0</div></a>
    </td>
    <td>
        <a href="http://$HOST/$TARGET1?refresh=$REFRESH" class="button1"><div class="boldfont">$VALUE1</div><div class="regularfont">$LABEL1</div></a>
    </td>
    <td>
        <a href="http://$HOST/$TARGET2?refresh=$REFRESH" class="button2"><div class="boldfont">$VALUE2</div><div class="regularfont">$LABEL2</div></a>
    </td>
    <td>
        <a href="http://$HOST/$TARGET3?refresh=$REFRESH" class="button3"><div class="boldfont">$VALUE3</div><div class="regularfont">$LABEL3</div></a>
    </td>
    </tr></table>
""")

aqipart = Template("""
    <div class="centered">
        <center> <div class="bignum">$MAINVALUE</div> </center>
        <center> <div class="desc">$DESC</div> </center>
        <center> <div class="subdesc">$MAINLABEL | $MACHINE</div> </center>
        <center> <div class="time">$TIME</div> </center>
    </div>
""")

graphpart = Template("""

    <div class="graph">
      <table>
        
        <colgroup>
          <col width="7.5%">
          <col width="85%">
          <col width="7.5%">
        </colgroup>

        <tr>
          <th>Diameter</th>
          <th>Percentage</th>
          <th>Count</th>
        </tr>

        <tr>
          <td><span class="barlabel">0.3&#160;µm</span></td>
          <td><div class="bar1">&#160;</div></td>
          <td><span class="count">$COUNT1</span></td>
        </tr>

        <tr>
          <td><span class="barlabel">0.5&#160;µm</span></td>
          <td><div class="bar2">&#160;</div></td>
          <td><span class="count">$COUNT2</span></td>
        </tr>

        <tr>
          <td><span class="barlabel">1.0&#160;µm</span></td>
          <td><div class="bar3">&#160;</div></td>
          <td><span class="count">$COUNT3</span></td>
        </tr>

        <tr>
          <td><span class="barlabel">2.5&#160;µm</span></td>
          <td><div class="bar4">&#160;</div></td>
          <td><span class="count">$COUNT4</span></td>
        </tr>

        <tr>
          <td><span class="barlabel">5.0&#160;µm</span></td>
          <td><div class="bar5">&#160;</div></td>
          <td><span class="count">$COUNT5</span></td>
        </tr>

        <tr>
          <td><span class="barlabel">10.0&#160;µm</span></td>
          <td><div class="bar6">&#160;</div></td>
          <td><span class="count">$COUNT6</span></td>
        </tr>

      </table>

    </div>

<br>
<br>

    <table style="font-size: 6vw;">
        <colgroup>
          <col width="50%">
          <col width="50%">
        </colgroup>
        <tr> 
            <td><div class="clabel">Total Count:</div></td>
            <td><div class="cvalue">$PCOUNT</div></td>
        </tr> 
        <tr> 
            <td><div class="clabel">Avg Diameter:</div></td>
            <td><div class="cvalue">$AVGD µm</div></td>
        </tr> 
    </table>
""")

envpart = Template("""

<div class="centered">
  <table style="font-size: 6vw; font-family: Arial, Helvetica, sans-serif;">
        <colgroup>
          <col width="100%">
        </colgroup>
        <tr> <td><div class="bigcvalue">$TEMPERATUREC</div></td> </tr> 
        <tr> <td><div class="bigcvalue">$TEMPERATUREF</div></td> </tr> 
        <tr> <td><div class="bigcvalue">$HUMIDITY</div></td> </tr> 
        <tr> <td><div class="bigcvalue">$PRESSURE</div></td> </tr> 
        <tr> <td><div class="bigcvalue">$GAS</div></td> </tr> 
    </table>
</div>
  
""")

suffixhtml = Template("""
<!--
    <table style="width=100%;position: fixed; bottom: 0px;">
    <colgroup>
          <col width="50%">
          <col width="50%">
    </colgroup>
    <tr>
    <td>
        <a href="http://$HOST/$TARGET0?refresh=$REFRESH" class="button0"><div class="boldfont">Settings</div><div class="regularfont">.</div></a>
    </td>
    <td>
        <a href="http://$HOST/$TARGET1?refresh=$REFRESH" class="button1"><div class="boldfont">Status</div><div class="regularfont">.</div></a>
    </td>
    </tr></table>
-->
  </html>
</body>
""")

def to_html_color (rgb):
    nums = [rgb[0] * 255.0, rgb[1] * 255.0, rgb[2] * 255.0]
    return '#' + ''.join('{:02X}'.format(int(a)) for a in nums)

def create_option_list (opts, selected):
    s = ""
    for (value, label) in opts:
        s += '<option value="{}" {}>{}</option>'.format(value,
                                                        'selected="selected"' if value == selected else '',
                                                        label)
    return s

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
    def internal_forward_to (self, location):
        global server_ip
        global server_port
        keys = {
            "LOCATION" : "http://{}:{}/{}".format(server_ip, server_port, location),
        }
        return forwardhtml.substitute(keys)

    @cherrypy.expose
    def status (self):
        global server_ip
        global server_port
        wifi = 'OFF'
        usb = 'Not Attached'
        networks = system_tools.system_network_status()
        if 'WIFI' in networks:
            x = networks['WIFI']
            if x[4]:
                wifi = "Connected to {2} at {0} / {1}<br>{3}<br>{4}".format(*x)
            else:
                wifi = '<a href="http://{}:{}/settings"><div class="fail">⚠ Unable to Connect to "{}"</div></href>'.format(server_ip, server_port, x[2])
        if 'USB' in networks:
            x = networks['USB']
            usb = "Attached with address {} or {}".format(*x)

        ginfo = system_tools.system_gadget_info()

        keys = {
            "WIFISTATUS" : wifi,
            "GADGETSTATUS" : usb,
            "SERIAL" : ginfo["serial_number"],
            "PRODUCT" : ginfo["product"],
            "MANUFACTURER" : ginfo["manufacturer"],
            "HOSTBASE" : ginfo['hostname_base'],
            "HARDWARE" : ginfo['config'],
            "RELEASE" : ginfo['release']
        }
        return statushtml.substitute(keys)


    @cherrypy.expose
    def settings (self):
        import wifi
        wifi_settings = system_tools.system_wifi_info()
        cells = system_tools.system_wifi_scan()
        netlist = []

        for c in cells:
            netlist.append('<option value="{}">'.format(c.ssid))

        aqifunc_options = [("EPA", "Wood Smoke (EPA)"),
                           ("Native", "Not Wood Smoke (Native)")]

        aqitype_options = [("US", "US EPA Air Quality Index"),
                           ("IN", "Indian CPCB National Air Quality Index")]

        tempunit_options = [("F", "Farenheit"),
                            ("C", "Celcius")]

        attached = system_tools.check_usb_gadget_attached()

        keys = {
            "HERE" : "http://{}:{}".format(server_ip, server_port),
            "BLURB" : attachedblurb if not attached else "",
            "CCVALUE" : wifi_settings[0],
            "ENABLED" : "" if attached else "disabled",
            "NETWORKVALUE" : wifi_settings[1],
            "NETLIST" : str.join('', netlist),
            "MODES" : str(aqi_gadget_config.display_modes),
            "AQIFUNC" : aqi_gadget_config.aqi_function,
            "AQITYPE" : aqi_gadget_config.aqi_type,
            "AQIFUNCLIST" : create_option_list(aqifunc_options, aqi_gadget_config.aqi_function),
            "AQITYPELIST" : create_option_list(aqitype_options, aqi_gadget_config.aqi_type),
            "TEMPUNITSLIST" : create_option_list(tempunit_options, 'F' if aqi_gadget_config.use_fahrenheit else 'C'),
            "TEMPOFFSET" : str(aqi_gadget_config.temp_offset_celsius),
        }
        return settingshtml.substitute(keys)

    @cherrypy.expose
    def setup (self):
        return self.internal_forward_to("settings")

    @cherrypy.expose
    def set_wifi (self, ccode="US", network="network", password="password"):
        print("INFO: set_wifi:", ccode, network, password)
        keys = {
            "COUNTRY" : ccode,
            "NETWORK" : network,
            "PASSWORD" : password,
        }
        conf = wificonf.substitute(keys)
        tempfile = "/tmp/wpa_supplicant.conf"
        wpafile = "/etc/wpa_supplicant/wpa_supplicant.conf"
        with system_tools.write_capability() as capability:
            with open(tempfile, "w") as file:
                file.write(conf)
            # move it to /etc/wpa_supplicant/wpa_supplicant.conf as root
            subprocess.run("sudo mv {} {}".format(tempfile, wpafile), shell=True)
            subprocess.run("sudo chmod 600 {}".format(wpafile), shell=True)
            system_tools.system_sync_all()
            subprocess.run("sudo wpa_supplicant -B -i wlan0 -c {} -D wext".format(wpafile), shell=True)
        # sync file system
        subprocess.run("sudo nohup reboot&", shell=True)
        return "<pre>RESTARTING...</pre>"

    @cherrypy.expose
    def set_general (self, temp="F", aqifunc="wood", aqitype="US", offset="-1.5"):
        aqi_gadget_config.use_fahrenheit = temp == 'F'
        aqi_gadget_config.aqi_function = aqifunc
        aqi_gadget_config.aqi_type = aqitype
        aqi_gadget_config.temp_offset_celsius = offset
        with system_tools.write_capability() as capability:
            aqi_gadget_config.write_config_file()
        return self.internal_forward_to("settings")

    @cherrypy.expose
    def set_expert (self, modes=""):
        aqi_gadget_config.display_modes = eval(modes)
        with system_tools.write_capability() as capability:
            aqi_gadget_config.write_config_file()
        return self.internal_forward_to("settings")

    @cherrypy.expose
    def restore_expert (self, modes=""):
        aqi_gadget_config.display_modes = aqi_gadget_config.default_display_modes
        with system_tools.write_capability() as capability:
            aqi_gadget_config.write_config_file()
        return self.internal_forward_to("settings")

    @cherrypy.expose
    def raw (self):
        val = {**self.env_value, **self.pm_value}
        return str(val)

    def big_env (self, other_keys):
        c          = self.pm_value["pm25_15s"]
        count03    = self.pm_value["pm03_count"]
        count05    = self.pm_value["pm05_count"]
        count10    = self.pm_value["pm10_count"]
        count25    = self.pm_value["pm25_count"]
        tcount     = count03 + count05 + count10 + count25
        ncount03   = count03 / tcount # normalized
        ncount05   = count05 / tcount
        ncount10   = count10 / tcount
        ncount25   = count25 / tcount
        avgD       = ncount03 * 0.3 + ncount05 * 0.5 + ncount10 * 1.0 + ncount25 * 2.5
        count      = tcount if tcount < 1000 else str(int(tcount/1000.0)) + "k"
        h          = self.env_value["H"]
        correction = aqi_correction_func(aqi_gadget_config.aqi_function)
        ccorrected = correction(c, h)
        aqi        = aqi_from_concentration(ccorrected, 2.5, aqi_gadget_config.aqi_type)
        b_temp     = self.env_value['F' if aqi_gadget_config.use_fahrenheit else 'C']
        b_hum      = h
        b_con      = c
        b_temp_rgb = (1, .8, .8)
        b_hum_rgb  = (.8, .8, 1.0)
        b_con_rgb  = (.85, .85, .85)
        rgb        = aqi[2]
        port       = server_ip + ":" + str(server_port)
        machine    = server_name

        t = self.env_value["time"]
        C = "{:.1f}°C".format(self.env_value["C"])
        F = "{:.1f}°F".format(self.env_value["F"])
        H = "{:.1f}% RH".format(self.env_value["H"])
        P = "{:.1f} mbars".format(self.env_value["hPa"])
        gas = self.env_value["Gas"]
        G = "" if type(gas) == str else "{:.1f} Ω".format(gas)

        keys = {
            "VALUE0" : "{:.1f}".format(ccorrected) if ccorrected < 10.0 else "{:.0f}".format(ccorrected),
            "VALUE1" : count,
            "VALUE2" : str(aqi[0]),
            "VALUE3" : "-",
            "LABEL0" : "µg/m<sup>3</sup>",
            "LABEL1" : "{:.1f}µm Avg".format(avgD),
            "LABEL2" : "AQI",
            "LABEL3" : "-",
            "TARGET0" : "graph",
            "TARGET1" : "graph",
            "TARGET2" : "aqi",
            "TARGET3" : "env",
            "BGCOLOR0" : to_html_color(b_con_rgb),
            "BGCOLOR1" : to_html_color(b_con_rgb),
            "BGCOLOR2" : to_html_color(rgb),
            "BGCOLOR3" : to_html_color(b_con_rgb),
            "BAR1" : "",
            "BAR2" : "",
            "BAR3" : "",
            "BAR4" : "",
            "BAR5" : "",
            "BAR6" : "",
            "FG" : "black",
            "BG" : "#bbbbbb",
            "TEMPERATUREC" : C,
            "TEMPERATUREF" : F,
            "HUMIDITY" : H,
            "PRESSURE" : P,
            "GAS" : G,
            "TIME" : time.ctime(t),
            "HOST" : port,
            "MACHINE" : machine,
            "REFRESH" : "10000",
        }

        keys = {**keys, **other_keys}
        html0 = datahtml.substitute(keys)
        htmlc = envpart.substitute(keys)
        html1 = suffixhtml.substitute(keys)
        return html0 + htmlc + html1

    def big_aqi (self, other_keys):
        c          = self.pm_value["pm25_15s"]
        count03    = self.pm_value["pm03_count"]
        count05    = self.pm_value["pm05_count"]
        count10    = self.pm_value["pm10_count"]
        count25    = self.pm_value["pm25_count"]
        tcount     = count03 + count05 + count10 + count25
        ncount03   = count03 / tcount # normalized
        ncount05   = count05 / tcount
        ncount10   = count10 / tcount
        ncount25   = count25 / tcount
        avgD       = ncount03 * 0.3 + ncount05 * 0.5 + ncount10 * 1.0 + ncount25 * 2.5
        count      = tcount if tcount < 1000 else str(int(tcount/1000.0)) + "k"
        h          = self.env_value["H"]
        t          = self.pm_value["time"]
        correction = aqi_correction_func(aqi_gadget_config.aqi_function)
        ccorrected = correction(c, h)
        aqi        = aqi_from_concentration(ccorrected, 2.5, aqi_gadget_config.aqi_type)
        b_temp     = self.env_value['F' if aqi_gadget_config.use_fahrenheit else 'C']
        b_hum      = h
        b_con      = c
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
            "MAINVALUE" : str(aqi[0]),
            "MAINLABEL" : "{} {} AQI".format(aqi_gadget_config.aqi_type, aqi_gadget_config.aqi_function),
            "VALUE0" : "{:.1f}".format(ccorrected) if ccorrected < 10.0 else "{:.0f}".format(ccorrected),
            "VALUE1" : count,
            "VALUE2" : "{:.1f}°".format(b_temp),
            "VALUE3" : "{:.0f}%".format(b_hum),
            "LABEL0" : "µg/m<sup>3</sup>",
            "LABEL1" : "{:.1f}µm Avg".format(avgD),
            "LABEL2" : "Temp. {}".format('F' if aqi_gadget_config.use_fahrenheit else 'C'),
            "LABEL3" : "Humidity",
            "TARGET0" : "graph",
            "TARGET1" : "graph",
            "TARGET2" : "env",
            "TARGET3" : "env",
            "BGCOLOR0" : to_html_color(b_con_rgb),
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
            "BAR1" : "",
            "BAR2" : "",
            "BAR3" : "",
            "BAR4" : "",
            "BAR5" : "",
            "BAR6" : "",
        }

        keys = {**keys, **other_keys}
        html0 = datahtml.substitute(keys)
        htmlc = aqipart.substitute(keys)
        html1 = suffixhtml.substitute(keys)
        return html0 + htmlc + html1

    def big_graph (self, other_keys):
        c          = self.pm_value["pm25_15s"]
        count03    = self.pm_value["pm03_count"]
        count05    = self.pm_value["pm05_count"]
        count10    = self.pm_value["pm10_count"]
        count25    = self.pm_value["pm25_count"]
        count50    = self.pm_value["pm50_count"]
        count100    = self.pm_value["pm100_count"]
        tcount     = count03 + count05 + count10 + count25 + count50 + count100
        ncount03   = count03 / tcount # normalized
        ncount05   = count05 / tcount
        ncount10   = count10 / tcount
        ncount25   = count25 / tcount
        ncount50   = count50 / tcount
        ncount100  = count100 / tcount
        avgD       = ncount03 * 0.3 + ncount05 * 0.5 + ncount10 * 1.0 + ncount25 * 2.5 + ncount50 * 5.0 + ncount100 * 10.0
        h          = self.env_value["H"]
        t          = self.pm_value["time"]
        correction = aqi_correction_func(aqi_gadget_config.aqi_function)
        ccorrected = correction(c, h)
        aqi        = aqi_from_concentration(ccorrected, 2.5, aqi_gadget_config.aqi_type)
        b_temp     = self.env_value['F' if aqi_gadget_config.use_fahrenheit else 'C']
        b_hum      = h
        b_con      = c
        b_temp_rgb = (1, .8, .8)
        b_hum_rgb  = (.8, .8, 1.0)
        rgb        = aqi[2]
        lum        = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        bg         = to_html_color(rgb)
        now        = datetime.now()
        port       = server_ip + ":" + str(server_port)
        machine    = server_name

        keys = {
            "PCOUNT" : tcount,
            "AVGD" : "{:.2f}".format(avgD),
            "BAR1" : "{:.0f}".format(ncount03 * 100.0),
            "BAR2" : "{:.0f}".format(ncount05 * 100.0),
            "BAR3" : "{:.0f}".format(ncount10 * 100.0),
            "BAR4" : "{:.0f}".format(ncount25 * 100.0),
            "BAR5" : "{:.0f}".format(ncount50 * 100.0),
            "BAR6" : "{:.0f}".format(ncount100 * 100.0),
            "COUNT1" : count03,
            "COUNT2" : count05,
            "COUNT3" : count10,
            "COUNT4" : count25,
            "COUNT5" : count50,
            "COUNT6" : count100,
            "VALUE0" : "{:.1f}".format(ccorrected) if ccorrected < 10.0 else "{:.0f}".format(ccorrected),
            "VALUE1" : str(aqi[0]),
            "VALUE2" : "{:.1f}°".format(b_temp),
            "VALUE3" : "{:.0f}%".format(b_hum),
            "LABEL0" : "µg/m<sup>3</sup>",
            "LABEL1" : "AQI",
            "LABEL2" : "Temp. {}".format('F' if aqi_gadget_config.use_fahrenheit else 'C'),
            "LABEL3" : "Humidity",
            "TARGET0" : "aqi",
            "TARGET1" : "aqi",
            "TARGET2" : "env",
            "TARGET3" : "env",
            "BGCOLOR0" : to_html_color((0.85, 0.85, 0.85)),
            "BGCOLOR1" : bg,
            "BGCOLOR2" : to_html_color(b_temp_rgb),
            "BGCOLOR3" : to_html_color(b_hum_rgb),
            "BG" : to_html_color((.85, .85, .85)),
            "FG" : "black",
            "HOST" : port,
            "MACHINE" : machine,
            "DESC" : aqi[1],
            #"TIME" : now.ctime(),
            "TIME" : time.ctime(t),
            "REFRESH" : str(10000),
        }

        keys = {**keys, **other_keys}
        html0 = datahtml.substitute(keys)
        htmlc = graphpart.substitute(keys)
        html1 = suffixhtml.substitute(keys)
        return html0 + htmlc + html1

    @cherrypy.expose
    def index (self):
        return self.aqi(refresh=10)

    @cherrypy.expose
    def graph (self, refresh=1000000):
        keys = {"REFRESH" : str(refresh)}
        return self.big_graph(keys)

    @cherrypy.expose
    def aqi (self, refresh=100000):
        keys = {"REFRESH" : str(refresh)}
        return self.big_aqi(keys)

    @cherrypy.expose
    def env (self, refresh=10000):
        keys = {"REFRESH" : str(refresh)}
        return self.big_env(keys)

    @cherrypy.expose
    def manual (self, refresh=100000):
        return "NOT YET, SORRY"

    @cherrypy.expose
    def display (self):
        self.ask_queue.put("TOGGLE_DISPLAY")
        return "TOGGLE_DISPLAY"

def start (ask_queue, data_queue, host=None, port=None, name=None):
    global server_ip
    global server_port
    global server_name
    import setproctitle
    setproctitle.setproctitle("aqi: web server")
    (machine, ipaddresses) = system_tools.get_host_info()
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
