# QBee gpio controller

A python script to control an LCD and amplifier relay for use in an AirPlay Raspberry Pi server.

* Detect sound ouput and turn on the amplifier power supply.
* Get the track information and display it on an LCD (using a fifo pipe exposed by [shairport-sync](https://github.com/mikebrady/shairport-sync)).
* Auto turn off amplifier power supply and/or shutdown after set period of inactivity.


## Usage

`python -m pip install --user qbee-gpio`

For first time usage: `~/.local/bin/qbee --init-config` then change what you need in `.qbee.yaml`.

For starting up automatically, create `/etc/systemd/system/qbee.service` file with (adjust users/paths):
```
[Unit]
Description=Qbee
After=network-online.target
StartLimitIntervalSec=500
StartLimitBurst=5

[Service]
User=qbee
Group=qbee
ExecStart=/home/qbee/.local/bin/qbee
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```
Then run:
```shell
sudo systemctl enable qbee
sudo systemctl start qbee
```
