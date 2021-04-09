<TeXmacs|1.99.12>

<style|manual>

<\body>
  <section|Basic Operation>

  <\with|par-mode|center>
  </with>

  <\itemize-dot>
    <item><strong|Use the \PA\Q USB port for normal operation>. Any USB cable
    that fits will power the device from this port. You can plug it into any
    USB port (computer, car, phone battery, usb wall charger) to power the
    device.

    <item><strong|Use the \PB\Q USB port to change the settings>. Make sure
    to use a proper USB Data Cable so the device can talk to the computer.
    Cables that recharge portable or bicycle lights are typically power only
    so those won't work but will power the device just like port \PA\Q.

    <\itemize-minus>
      <item>When attached you will see the \PAQI Gadget\Q disk drive on your
      computer.

      <item>Open the README.html file to navigate to settings, the manual, or
      see the current AQI.

      <item>You can change WiFi settings, the country you're in (as long as
      its the US or India) and the temperature units.
    </itemize-minus>
  </itemize-dot>

  <\itemize-dot>
    <item>It can take up to one minute for the device to start working after
    you plug it in.

    <item><strong|To power off the device simply unplug it>. When using port
    \PB\Q your computer might want you to eject the disk drive first.

    <item>It takes up to 10 minutes or so for the device to become accurate.
    Before that time readings will be less accurate and may vary.

    \;
  </itemize-dot>

  <section|The Display>

  <\itemize-dot>
    <item>The display can show you various readings but most importantly it
    will show you the current AQI for the country in settings. For the US
    this is the <em|US EPA Air Quality Index>. For India it is the Indian
    <em|National Air Quality Index>.

    <item>The upper button will switch between display modes. The default
    display modes are:

    <\itemize-minus>
      <item>AQI

      <item>2x2 display of AQI, Temperature (Celcius or Farenheit), Relative
      Humidity (Percentage), and Particle Concentration.

      <item>2x2 display of Gadet hostname, IP address, AQI Index Name,
      Particle Calibration.
    </itemize-minus>

    <item>The display will turn itself off after a certain amount of time.
    You can turn it on again by pressing one of the buttons.
  </itemize-dot>

  <section|Web Interface>

  <\itemize-dot>
    <item>When using port \PA\Q to power the device, WiFi is active, and the
    device is set up with the network and password, you can visit its website
    at the URL: <samp|http://aqi-gadget-XXX.local> \V where <samp|XXX> is the
    serial number of your device (for example 001). You can see the device
    name on its display. Alternately you can use its IP address directly
    (also indicated on the display) such as: <samp|http://192.168.0.232> for
    example.

    <item>When port \PB\Q is used you can get to the website using either
    <samp|http://aqi-gadget-XXX.local> as above or with the exact address
    which is: <samp|http://10.10.10.1>. That address is hard coded and will
    not change. You can only access the device via the computer its plugged
    into when using port \PB\Q.

    <item>The web interface is best viewed on a phone or tablet when not in
    landscape mode but it also works from a computer's web browser.
  </itemize-dot>

  <section|Typical Use Cases>

  <\itemize-dot>
    <item>Testing interior and/or exterior air quality during wild fires.

    <item>Get a baseline for polution in your house or car.

    <item>Determine the efficacy of your car's air filter. (It probably sucks
    during a wild fire.)

    <item>Find our when you need to turn on/off your house air filtere.

    <item>Find our which rooms in your house have the best air quality. This
    can change dramatically during a wild fire.
  </itemize-dot>

  <section|Caveats>

  <\itemize-dot>
    <item>I've tried to make this thing as accurate as possible but there are
    no guarantees. You can test it against other AQI monitors on the internet
    like <inactive|<hlink| https://www.purpleair.com|>> to guage its accuracy
    in your area. In the case of purple air: set reporting for \PUS EPA PM2.5
    AQI\Q and \PUS EPA\Q for wood smoke or \PNone\Q for non-wood smoke (this
    applies in the US only).

    <item>The most fragile parts of the device are the particle sensor (the
    blue box on the bottom) and the SD Card. The most likely failure will be
    the particle sensor. Either way if you want it fixed just contact me. You
    can tell the particle sensor is wigging out if the AQI readings start
    dramatically fluctuating for no good reason consistantly. Occasionally it
    will fluctuate because something happened to it like a nat or very tiny
    spider went in there. Try blowing hard on its fan to see if you can
    dislodge any beastie which may have taken up residence.

    <item>The particle sensor is designed to detect PM2.5 particles or
    smaller (2.5 micometers). These are the most important particle sizes for
    pollution and wood smoke. It will extrapolate to particles up to PM10 (10
    micrometers) but I don't believe its accurate for that range. PM10
    particles are reported on the total particle count page of the website
    and on the graph.\ 

    <item>If your finger covers the particle sensor fan or touches it and it
    stops: just move your finger and forget about it.
  </itemize-dot>

  <section|Hacking>

  <\itemize-dot>
    <item>The AQI Gadget is a Raspberry Pi Zero W connected to two main
    components from Adafruit. All of the software is available at:
    <inactive|<hlink|https://github.com/jimhourihan/aqi-gadget|>>. Links to
    the particle sensor and BME680 (environment sensors) are available there
    as well.

    <item>Your AQI Gadget is constructed of the finest Blu Tac (basically
    playdoh) and rubber bands that you can find on Amazon. The wood is from
    some game that we lost most of the pieces to. The reason the small PCB is
    located at the end of the wood stick and buffered by some styrofoam is to
    insulate it against heat and infrared radiation from the Raspberry Pi
    Zero.\ 

    The product design probably makes Steve Jobs very sad in whatever plane
    of existence he currently inhabits and I'm sorry about that.

    If it falls apart just use more rubber bands and/or Blue Tac or tell me
    and I'll gladly come over with some super glue.

    <item>SSH is enabled on the device. You can login to the gadget from your
    computer like so:

    <\shell-code>
      ssh pi@aqi-gadget-XXX.local
    </shell-code>

    where XXX indicates your serial number. Alternately you can substitute in
    the IP address directly. When attached to port \PB\Q the IP address is
    always 10.10.10.1. In WiFi mode you should find the IP address on the
    display or use your router's Wifi clients list.

    The password is \Praspberry\Q. If you are worried about the NSA getting
    into your device change the password. It won't help but you'll feel
    better. (Note: you have to switch to read-write mode before doing so).

    <item>The device is in read-only mode. In the <strong|pi> user's shell
    you can type <shell|rw> to change into read-write mode and <shell|ro> to
    change back to read-only. Always reset to read-only mode before
    unplugging the device. Read-only mode prevents requiring a \Pclean
    shutdown\Q of the raspberry pi.

    <item>One fun thing you can do is just take it apart, remove the garbage
    that holds it together and replace it with something reasonable.
  </itemize-dot>

  <section|Trivia>

  Of all the crap I've made this is one of the few that Rosa actively
  complimented me on and used frequently. Hopefully you get some good use out
  of it.
</body>

<initial|<\collection>
</collection>>

<\references>
  <\collection>
    <associate|auto-1|<tuple|1|?>>
    <associate|auto-2|<tuple|2|?>>
    <associate|auto-3|<tuple|3|?>>
    <associate|auto-4|<tuple|4|?>>
    <associate|auto-5|<tuple|5|?>>
    <associate|auto-6|<tuple|6|?>>
    <associate|auto-7|<tuple|7|?>>
  </collection>
</references>

<\auxiliary>
  <\collection>
    <\associate|toc>
      1<space|2spc>Basic Operation <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-1>

      2<space|2spc>The Display <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-2>

      3<space|2spc>Web Interface <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-3>

      4<space|2spc>Typical Use Cases <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-4>

      5<space|2spc>Caveats <datoms|<macro|x|<repeat|<arg|x>|<with|font-series|medium|<with|font-size|1|<space|0.2fn>.<space|0.2fn>>>>>|<htab|5mm>>
      <no-break><pageref|auto-5>
    </associate>
  </collection>
</auxiliary>