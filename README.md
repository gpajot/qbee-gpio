# qbee-gpio

[![tests](https://github.com/gpajot/qbee-gpio/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/gpajot/qbee-gpio/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)
[![PyPi](https://img.shields.io/pypi/v/qbee-gpio?label=stable)](https://pypi.org/project/qbee-gpio/)
[![python](https://img.shields.io/pypi/pyversions/qbee-gpio)](https://pypi.org/project/qbee-gpio/)

A python script to control an LCD and amplifier relay for use in an AirPlay and/or Spotify Connect Raspberry Pi server.

* Detect sound ouput and turn on the amplifier power supply.
* Get the track information and display it on an LCD.
* Auto turn off amplifier power supply and/or shutdown after set period of inactivity.

Additional documentation:

* [Setting up shairport-sync](./docs/shairport-sync.md)
* [Setting up librespot](./docs/librespot.md)
* [My hardware](./docs/hardware.md)

## Installation

```shell
sudo python -m pip install qbee-gpio
````

For first time usage:
```shell
qbee --init-config
```
then change what you need in `~/.qbee.yaml`.

## Usage

```shell
qbee
```

Pass a `-v` flag for verbose logging.

## Detailed setup

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
ExecStart=/usr/local/bin/qbee
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```
Enable to run on boot: `sudo systemctl enable qbee --now`.

Optionally, specify a `CONFIG` env variable when running the script:
`CONFIG="/etc/qbee.yaml" qbee ...`.
The default config will be located at `~/.qbee.yaml`.

See [all config options](./qbee_gpio/config.py)
