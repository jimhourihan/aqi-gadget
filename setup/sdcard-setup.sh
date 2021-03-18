#!/bin/sh

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

# run this in /boot on the machine you burned the ssd card on
# (before the first boot on the pi zero)
echo "Where is the SD card /boot directory mounted? (e.g. /Volumes/boot on MacOS)"
read -p "Path to /boot: " boot_path

if [ -d "$boot_path" ]; then
    cp pi-config-after-boot.sh $boot_path
    cp storage.fat32.dmg.gz $boot_path
    cd $boot_path
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

replaceAppend(config.txt, '#dtparam=i2c_arm=on', 'dtparam=i2c_arm=on')
replaceAppend(config.txt, '#dtparam=spi=on', 'dtparam=spi=on')
cat >> config.txt <<EOF
dtoverlay=dwc2
enable_uart=1
EOF

cat cmdline.txt | sed "s/rootwait/modules-load=dwc2,libcomposite rootwait/" > new_cmdline.txt
mv new_cmdline.txt cmdline.txt

