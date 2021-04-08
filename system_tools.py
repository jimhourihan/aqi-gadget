import subprocess
import time

class WriteCapability:
    """A Context Manager that switches the file system to RW
    does something then returns it to RO
    """

    def __init__ (self):
        pass

    def __enter__ (self):
        subprocess.run('sudo mount -o remount,rw / ; sudo mount -o remount,rw /boot', shell=True)
        return self

    def __exit__ (self, *args):
        subprocess.run('sudo mount -o remount,ro / ; sudo mount -o remount,ro /boot', shell=True)
        return self

def write_capability ():
    return WriteCapability()

def check_usb_gadget_attached ():
    with open("/sys/devices/platform/soc/20980000.usb/udc/20980000.usb/state", 'r') as file:
        state = str(file.readline()).rstrip()
        return state != "not attached"

def system_sync_all ():
    subprocess.run('sudo /usr/bin/bash -c "sync; echo 3 > /proc/sys/vm/drop_caches"', shell=True)


def system_wifi_info ():
    # get wpa_supplicant info 
    cmd       = 'sudo cat /etc/wpa_supplicant/wpa_supplicant.conf'
    blob      = subprocess.check_output(cmd, shell=True).decode("utf-8")
    lines     = blob.splitlines()
    country   = list(filter(lambda x: "country=" == x[:8], lines))[0][8:]
    network   = list(filter(lambda x: "ssid=" in x, lines))[0].split(sep='"')[1]
    # not reporting the password on purpose
    return (country, network)

def get_release_from_pi_home ():
    cmd  = """cd ~pi;file * "-F " | awk '{ if ($2 == "directory") print($1) }'"""
    blob = subprocess.check_output(cmd, shell=True).decode("utf-8")
    return blob.strip()

def system_gadget_info ():
    # /boot/aqi-gadget-info contents
    info_dict = {
        "serial_number" : "000",
        "product" : "X",
        "manufacturer" : "Absolute Garbage",
        "hostname_base" : "x",
        "config" : "nada",
        "release" : "unknown",
    }
    with open('/boot/aqi-gadget-info', 'r') as file:
        blob = file.read()
        for line in blob.split('\n'):
            words = line.split()
            if len(words) > 0:
                info_dict[words[0]] = " ".join(words[1:])

    if info_dict['release'] == 'unknown':
        # fall back to literal release untar dir
        info_dict['release'] = get_release_from_pi_home()

    return info_dict

def system_network_status ():
    cmd       = 'ifconfig'
    blob      = subprocess.check_output(cmd, shell=True).decode("utf-8")
    entries   = blob.split('\n\n')
    networks  = {}
    for n in entries:
        words = n.split(' ')
        name = None
        ip4address = None
        ip6address = None
        if words[0] == 'usb0:':
            name = "USB"
        elif words[0] == 'wlan0:':
            name = "WIFI"
        if "inet" in words:
            i = words.index("inet")
            ip4address = words[i+1]
        if "inet6" in words:
            i = words.index("inet6")
            ip6address = words[i+1]
        if name:
            networks[name] = (ip4address, ip6address)
    if "WIFI" in networks:
        cmd     = 'iwconfig wlan0'
        blob    = subprocess.check_output(cmd, shell=True).decode("utf-8")
        entries = blob.split()
        (ip4, ip6) = networks['WIFI']
        try:
            lindex  = entries.index('Link')
            sindex  = entries.index('Signal')
            quality = entries[lindex + 1]
            signal  = entries[sindex + 1] + entries[sindex + 2]
            ssid    = ""
            for word in entries:
                if "ESSID:" in word:
                    ssid = word.split('"')[1]
                    break
            networks['WIFI'] = (ip4, ip6, ssid, quality, signal)
        except Exception:
            (_, ssid) = system_wifi_info()
            networks['WIFI'] = (ip4, ip6, ssid, None, None)
    return networks
            
def system_wifi_scan ():
    import wifi
    attached  = check_usb_gadget_attached()
    if attached:
        # make sure wlan0 is up (for usb attached mode)
        subprocess.run('sudo ifconfig wlan0 up', shell=True)
        time.sleep(0.5)
    # calling sudo gets around needing to be root
    scanloop = 0
    while scanloop < 10:
        # attempt to scan, keep trying while sleeping every sec
        try:
            cmd       = 'sudo iwlist wlan0 scan'
            blob      = subprocess.check_output(cmd, shell=True).decode("utf-8")
            celltexts = blob.split("Cell")
            cells     = []
            for text in celltexts:
                c = wifi.Cell.from_string(text)
                if c.ssid:
                    cells.append(c)
            cells.sort(key=lambda x: -x.signal if x.signal else 0)
            return cells
        except Exception:
            # wlan0 might not be ready yet
            time.sleep(1.0)
            scanloop += 1
    return []

def get_host_info ():
    cmd  = 'hostname ; hostname -I'
    lines = subprocess.check_output(cmd, shell=True).decode('utf-8').splitlines()
    return (lines[0].strip(), lines[1].strip().split())

