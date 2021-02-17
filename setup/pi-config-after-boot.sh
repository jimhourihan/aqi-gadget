#!/bin/sh

apt update
apt upgrade
apt install dnsmasq -y
# Do these if you're not using lite
#apt-get remove --purge "libreoffice*" -y
#apt-get purge wolfram-engine -y
apt autoremove -y

cat > /etc/modprobe.d/g_ether.conf <<EOF
options g_ether use_eem=0 host_addr=02:ed:c8:f7:75:15 dev_addr=02:ed:dc:eb:6d:a1
EOF

cat >> /etc/network/interfaces <<EOF
auto usb0
iface usb0 inet static
      address 10.10.10.1
      netmask 255.255.255.0
EOF

cat >> /etc/dnsmasq.conf <<EOF
listen-address=10.10.10.1
dhcp-range=10.10.10.1,10.10.10.3,255.255.255.0,1h
dhcp-option=3
EOF

echo noipv4ll >> /etc/dhcpcd.conf

systemctl enable --now dnsmasq

