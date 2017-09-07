#/bin/bash
hostn=$(cat /etc/hostname)
echo "Enter new hostname: "
read newhost
sudo mkdir -p /media/backup
sudo sed -i "s/$hostn/$newhost/g" /etc/hosts
sudo sed -i "s/$hostn/$newhost/g" /etc/hostname
sudo rm -rf /var/lib/dhcp/dhcpd.leases~
sudo sh -c 'echo "" > /var/lib/dhcp/dhcpd.leases'
echo "Your new hostname is $newhost"
sudo reboot
