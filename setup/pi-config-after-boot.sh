#!/bin/sh
if [ $(id -u) -ne 0 ]; then
	echo "Must be run as root."
	echo "Try 'sudo bash $0'"
	exit 1
fi

cd /boot
tarfile=$(echo aqi-gadget-release-*.tar.gz)
tarfile_base="${tarfile%%.*}"
echo Using $tarfile

# Given a filename, a regex pattern to match and a replacement string:
# Replace string if found, else no change.
# (# $1 = filename, $2 = pattern to match, $3 = replacement)
replace() {
	grep $2 $1 >/dev/null
	if [ $? -eq 0 ]; then
		# Pattern found; replace in file
		sed -i "s/$2/$3/g" $1 >/dev/null
	fi
}

# Given a filename, a regex pattern to match and a replacement string:
# If found, perform replacement, else append file w/replacement on new line.
replaceAppend() {
	grep $2 $1 >/dev/null
	if [ $? -eq 0 ]; then
		# Pattern found; replace in file
		sed -i "s/$2/$3/g" $1 >/dev/null
	else
		# Not found; append on new line (silently)
		echo $3 | sudo tee -a $1 >/dev/null
	fi
}

# Given a filename, a regex pattern to match and a string:
# If found, no change, else append file with string on new line.
append1() {
	grep $2 $1 >/dev/null
	if [ $? -ne 0 ]; then
		# Not found; append on new line (silently)
		echo $3 | sudo tee -a $1 >/dev/null
	fi
}

# Given a filename, a regex pattern to match and a string:
# If found, no change, else append space + string to last line --
# this is used for the single-line /boot/cmdline.txt file.
append2() {
	grep $2 $1 >/dev/null
	if [ $? -ne 0 ]; then
		# Not found; insert in file before EOF
		sed -i "s/\'/ $3/g" $1 >/dev/null
	fi
}

#raspi-config nonint do_change_hostname aqi-gadget
apt update
apt upgrade -y
apt install dnsmasq -y
apt-get install busybox-syslogd -y
apt-get remove --purge rsyslog -y
apt-get remove -y --purge triggerhappy logrotate dphys-swapfile fake-hwclock
apt-get -y autoremove --purge

cat > /boot/aqi-gadget-info <<EOF
serial_number 000
product AQI Gadget
manufacturer Absolute Garbage
hostname_base aqi-gadget
config otg wifi adafruit_minitft adafruit_PMSA003I adafruit_BME680
release $tarfile_base
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
pip3 install wifi serial setproctitle systemd 
pip3 install Adafruit-Blinka Adafruit-PlatformDetect Adafruit-PureIO
pip3 install adafruit-circuitpython-bme680 adafruit-circuitpython-busdevice adafruit-circuitpython-pm25 adafruit-circuitpython-rgb-display
pip3 install CherryPy pillow numpy

# ro sdcard setup
# Replace log management with busybox (use logread if needed)
# Installing ntp and busybox-syslogd...
apt-get -y install ntp busybox-syslogd; dpkg --purge rsyslog

# Add fastboot, noswap and/or ro to end of /boot/cmdline.txt
append2 /boot/cmdline.txt fastboot fastboot
append2 /boot/cmdline.txt noswap noswap
append2 /boot/cmdline.txt ro^o^t ro

# Move /var/spool to /tmp
rm -rf /var/spool
ln -s /tmp /var/spool

# Make SSH work
replaceAppend /etc/ssh/sshd_config "^.*UsePrivilegeSeparation.*$" "UsePrivilegeSeparation no"

# Change spool permissions in var.conf (rondie/Margaret fix)
replace /usr/lib/tmpfiles.d/var.conf "spool\s*0755" "spool 1777"

# Move dhcpd.resolv.conf to tmpfs
touch /tmp/dhcpcd.resolv.conf
rm /etc/resolv.conf
ln -s /tmp/dhcpcd.resolv.conf /etc/resolv.conf

# Make edits to fstab
# make / ro
# tmpfs /var/log tmpfs nodev,nosuid 0 0
# tmpfs /var/tmp tmpfs nodev,nosuid 0 0
# tmpfs /tmp     tmpfs nodev,nosuid 0 0
replace /etc/fstab "vfat\s*defaults\s" "vfat    defaults,ro "
replace /etc/fstab "ext4\s*defaults,noatime\s" "ext4    defaults,noatime,ro "
append1 /etc/fstab "/var/log" "tmpfs /var/log tmpfs nodev,nosuid 0 0"
append1 /etc/fstab "/var/tmp" "tmpfs /var/tmp tmpfs nodev,nosuid 0 0"
append1 /etc/fstab "\s/tmp"   "tmpfs /tmp    tmpfs nodev,nosuid 0 0"

# random seed
rm /var/lib/systemd/random-seed
ln -s /tmp/random-seed /var/lib/systemd/random-seed
cat >> /lib/systemd/system/systemd-random-seed.service <<EOF 
ExecStartPre=/bin/echo "" >/tmp/random-seed
EOF

cat >> ~pi/.bashrc <<EOF
set_bash_prompt() {
    fs_mode=\$(mount | sed -n -e "s/^\/dev\/.* on \/ .*(\(r[w|o]\).*/\1/p")
    PS1='\[\033[01;32m\]\u@\h\${fs_mode:+(\$fs_mode)}\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\] > '
}
alias ro='sudo mount -o remount,ro / ; sudo mount -o remount,ro /boot'
alias rw='sudo mount -o remount,rw / ; sudo mount -o remount,rw /boot'
alias start='sudo systemctl start aqi.service'
alias stop='sudo systemctl stop aqi.service'
alias status='sudo systemctl status aqi.service'
PROMPT_COMMAND=set_bash_prompt
EOF

chown pi:pi ~pi/.bashrc

mv $tarfile ~pi/
cd ~pi
tar -xvzf $tarfile
cd "${tarfile:0:-7}" 
bash install.sh
cd ~pi
chown -R pi:pi *

echo "Set up complete -- file system will be read-only"
echo "Edit aqi-gadget-info and reboot"

