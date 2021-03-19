#!/bin/sh
#!/bin/sh
# unzip in ~pi

ln -s $PWD ../aqi-gadget
sudo cp aqi.service /lib/systemd/system
sudo systemctl enable aqi.service
