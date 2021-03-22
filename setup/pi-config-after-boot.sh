#!/bin/sh

#raspi-config nonint do_change_hostname aqi-gadget
apt update
apt upgrade -y
apt install dnsmasq -y
# Do these if you're not using lite
#apt-get remove --purge "libreoffice*" -y
#apt-get purge wolfram-engine -y
apt autoremove -y

# move the 100MB image file into place and decompress it
mv storage.fat32.dmg.gz /
gunzip /storage.fat32.dmg.gz

cat > /boot/aqi-gadget-info <<EOF
serial_number 000
product AQI Gadget
manufacturer Absolute Garbage
hostname_base aqi-gadget
config otg wifi adafruit_minitft adafruit_PMSA003I adafruit_BME680
EOF

SNUM=`awk '{ if ($1 == "serial_number") print $2 }' /boot/aqi-gadget-info`
HNAME=$HNAME-$SNUM

cat >> /etc/modules <<EOF
i2c-dev
EOF

cat > /etc/network/interfaces.d/usb0 <<EOF
auto usb0
iface usb0 inet static
      address 10.10.10.1
      netmask 255.255.255.0
EOF

cat > /etc/dnsmasq.d/usb <<EOF
interface=usb0
listen-address=10.10.10.1
dhcp-range=10.10.10.1,10.10.10.3,255.255.255.0,1h
dhcp-option=3
leasefile-ro
EOF

# NOTE: appending
cat >> /etc/dhcpcd.conf <<EOF
denyinterfaces usb0
noipv4ll
EOF


cat > /boot/make-usb-gadget <<EOF
#!/bin/sh
# go to configfs directory for USB gadgets

SN=`awk '{ if ($1 == "serial_number") print $2 }' /boot/aqi-gadget-info`
PROD=`awk '{ if ($1 == "product") for (i=2;i<=NF;i++) printf "%s", $i OFS; }' /boot/aqi-gadget-info`
MANU=`awk '{ if ($1 == "manufacturer") for (i=2;i<=NF;i++) printf "%s", $i OFS; }' /boot/aqi-gadget-info`
HNAME=`awk '{ if ($1 == "hostname_base") print $2 }' /boot/aqi-gadget-info`
CURRENTNAME=`hostname`
TARGETNAME=$HNAME-$SN

if [ "$CURRENTNAME" = "$TARGETNAME" ]; then
   HOSTNAME_UPDATE=NO
else
   HOSTNAME_UPDATE=YES
   echo $TARGETNAME > /etc/hostname
   sed --in-place=bak "s/$CURRENTNAME/$TARGETNAME/" /etc/hosts
fi

cd /sys/kernel/config/usb_gadget

# create gadget directory and enter it
mkdir g1
cd g1

# USB ids
echo 0x1d6b > idVendor
echo 0x104 > idProduct

# USB strings, optional
mkdir strings/0x409 # US English, others rarely seen
echo $MANU > strings/0x409/manufacturer
echo $PROD > strings/0x409/product
echo $SN > strings/0x409/serialnumber

# create the (only) configuration
mkdir configs/c.1 # dot and number mandatory

# create the ethernet function
mkdir functions/ecm.usb0 
echo 32:71:15:18:ff:7a > functions/ecm.usb0/host_addr
echo 32:71:15:18:ff:7b > functions/ecm.usb0/dev_addr

# create mass_storage function
mkdir functions/mass_storage.0
echo 1 > functions/mass_storage.0/ro
echo 1 > functions/mass_storage.0/removable
echo /storage.fat32.dmg > functions/mass_storage.0/lun.0/file

# assign function to configuration
ln -s functions/ecm.usb0/ configs/c.1/
ln -s functions/mass_storage.0/ configs/c.1/

# bind!
udevadm settle -t 5 || :
ls /sys/class/udc > UDC 
ifup usb0

cd /home/pi/aqi-gadget
./display_connection.py 

ST=`cat /sys/devices/platform/soc/20980000.usb/udc/20980000.usb/state`
if [ "$ST" = "not attached" ]; then
    ifconfig usb0 down
else
    ifconfig wlan0 down
fi
EOF

chmod +x /boot/make-usb-gadget

cat > /etc/systemd/system/create-usb-gadgets.service <<EOF
[Unit]
Description=Create USB gadgets

[Service]
Type=oneshot
ExecStart=/boot/make-usb-gadget
StandardInput=tty
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now dnsmasq
systemctl enable create-usb-gadgets

# install required code for aqi-gadget
apt install python3-pip -y
apt install python3-pil -y
apt install python3-numpy -y
apt install libopenjp2-7-dev libtiff-dev -y
pip3 install --upgrade --force-reinstall spidev
pip3 install RPi.GPIO
pip3 install serial setproctitle systemd 
pip3 install Adafruit-Blinka Adafruit-PlatformDetect Adafruit-PureIO
pip3 install adafruit-circuitpython-bme680 adafruit-circuitpython-busdevice adafruit-circuitpython-pm25 adafruit-circuitpython-rgb-display
pip3 install CherryPy
pip3 install pillow numpy

# ro sdcard setup
apt-get remove --purge triggerhappy logrotate dphys-swapfile -y
apt autoremove -y

# create the gadget and set the new hostname
echo "Needs Reboot"
