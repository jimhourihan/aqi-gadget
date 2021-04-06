#!/bin/sh
# unzip in ~pi

ln -s $PWD ../aqi-gadget
python3 -m compileall .
zcat setup/storage.fat32.dmg.gz > /boot/storage.fat32.dmg
cp setup/make-usb-gadget /boot
chmod +x /boot/make-usb-gadget
cp aqi_gadget_config.ini /boot
cp aqi.service /lib/systemd/system
systemctl enable aqi.service
systemctl start aqi.service

echo Installed as:
cat /boot/aqi_gadget_config.ini
echo EDIT SERIAL NUMBER
