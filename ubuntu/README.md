# Service 
Install Hue DMX as service on Ubuntu 20+

## prepare
1. Copy hue-dmx.service to /etc/systemd/system
2. Replace {script path} in hue-dmx.service
3. Set correct user name and group in hue-dmx.service

## use
```bash
sudo systemctl start hue-dmx
sudo systemctl enable hue-dmx
sudo systemctl status hue-dmx.service
```


