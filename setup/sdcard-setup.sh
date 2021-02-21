#!/bin/sh

# run this in /boot on the machine you burned the ssd card on
# (before the first boot on the pi zero)
#cd /Volumes/boot

touch ssh

echo "Set up Pi Zero W /boot configuration for AQI Gadget"
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

cat >> config.txt <<EOF
dtoverlay=dwc2
enable_uart=1
EOF

cat cmdline.txt | sed "s/rootwait/rootwait modules-load=dwc2,g_ether/" > new_cmdline.txt
mv new_cmdline.txt cmdline.txt
