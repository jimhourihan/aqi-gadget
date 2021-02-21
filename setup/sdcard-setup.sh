#!/bin/sh

# run this in /boot on the machine you burned the ssd card on
# (before the first boot on the pi zero)
echo "Where is the SD card /boot directory mounted? (e.g. /Volumes/boot on MacOS)"
read -p "Path to /boot: " boot_path

if [ -f $boot_path ]; then
    cd boot_path
else
    echo "ERROR: $boot_path does not exist"
    exit -1
fi

echo "INFO: enabling SSH"
touch ssh

echo "Default local WIFI to connect to (can be changed later)"
read -p "Wireless Network Name: " wireless_name
read -p "Wireless Network Password: " wireless_passwd

cat > wpa_supplicant.conf <<EOF
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="$wireless_name"
    psk="$wireless_passwd"
}
EOF

echo "INFO: UART is enabled"
cat >> config.txt <<EOF
dtoverlay=dwc2
enable_uart=1
EOF

cat cmdline.txt | sed "s/rootwait/rootwait modules-load=dwc2,libcomposite/" > new_cmdline.txt
mv new_cmdline.txt cmdline.txt
