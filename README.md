# qbee-gpio

[![tests](https://github.com/gpajot/qbee-gpio/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/gpajot/qbee-gpio/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)
[![version](https://img.shields.io/pypi/v/qbee-gpio?label=stable)](https://pypi.org/project/qbee-gpio/)
[![python](https://img.shields.io/pypi/pyversions/qbee-gpio)](https://pypi.org/project/qbee-gpio/)

A python script to control an LCD and amplifier relay for use in an AirPlay and/or Spotify Connect Raspberry Pi server.

* Detect sound ouput and turn on the amplifier power supply.
* Get the track information and display it on an LCD.
* Auto turn off amplifier power supply and/or shutdown after set period of inactivity.

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

### Qbee

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
`CONFIG="/etc/qbee.yaml" ~/.local/bin/qbee ...`.
The default config will be located at `~/.qbee.yaml`.

See [all config options](./qbee_gpio/config.py)

### Setting up shairport-sync

You can follow instructions [here](https://github.com/mikebrady/shairport-sync/blob/master/BUILD.md). Here is what I used.

Install required packages:
```shell
sudo apt install --no-install-recommends build-essential git autoconf automake libtool \
    libpopt-dev libconfig-dev libasound2-dev avahi-daemon libavahi-client-dev libssl-dev libsoxr-dev
```

Install shairport-sync:
```shell
git clone https://github.com/mikebrady/shairport-sync.git
cd shairport-sync
autoreconf -fi
./configure --sysconfdir=/etc --with-alsa --with-soxr --with-avahi --with-ssl=openssl --with-systemd --with-metadata
make
make install
cd ../ && rm -rf shairport-sync
```

Edit `/etc/shairport-sync.conf` file, uncomment the metadata block to enable:
```
metadata =
{
        enabled = "yes";
        include_cover_art = "no";
        pipe_name = "/tmp/shairport-sync-metadata";
        pipe_timeout = 5000;
};
```

Enable to run on boot: `sudo systemctl enable shairport-sync --now`.

### Setting up Librespot

If [Raspotify](https://dtcooper.github.io/raspotify/) is available on your system, use it,
otherwise, you will need to compile [librespot](https://github.com/librespot-org/librespot/wiki).

For starting up automatically, create `/lib/systemd/system/librespot.service` file with (adjust users/paths):
```
[Unit]
Description=Librespot
After=sound.target
Requires=avahi-daemon.service
After=avahi-daemon.service
Wants=network-online.target
After=network.target network-online.target

[Service]
User=qbee
Group=qbee
EnvironmentFile=/etc/librespot.env
ExecStart=/usr/bin/librespot
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

The conf `/etc/librespot.env` should look like:
```shell
LIBRESPOT_NAME="Qbee"

LIBRESPOT_QUIET=

LIBRESPOT_ENABLE_VOLUME_NORMALISATION=
LIBRESPOT_BITRATE="320"
LIBRESPOT_BACKEND="alsa"
LIBRESPOT_INITIAL_VOLUME="40"

LIBRESPOT_ONEVENT="/usr/local/bin/librespot-pipe.sh"

QBEE_LIBRESPOT_METADATA_PIPE="/tmp/librespot-metadata"
```

You will also need to set up the script to pipe events to Qbee in `/usr/local/bin/librespot-pipe.sh` and make it executable:
```bash
#!/usr/bin/bash

# Expose track_changed librespot events in a named pipe.

# Only expose track changed events.
if [ "$PLAYER_EVENT" != 'track_changed' ]; then
  exit 0
fi
# Need a named pipe.
if [ "$QBEE_LIBRESPOT_METADATA_PIPE" == '' ]; then
  exit 0
fi
# It must already be opened for reading.
if ! [ -p "$QBEE_LIBRESPOT_METADATA_PIPE" ] ; then
  exit 0
fi
artist=$(printf '%s' "$ARTISTS" | base64)
album=$(printf '%s' "$ALBUM" | base64)
title=$(printf '%s' "$NAME" | base64)
printf 'artist:%s,album:%s,title:%s\t' "$artist" "$album" "$title" > "$QBEE_LIBRESPOT_METADATA_PIPE"
```

### Setting up Hifiberry DAC

Edit `/boot/config.txt` to add:
```
dtparam=audio=on
dtoverlay=hifiberry-dac
```

To disable the built-in sound card, edit `/etc/modprobe.d/raspi-blacklist.conf` to add:
```
blacklist snd_bcm2835
```

Edit `/etc/asound.conf` to set the default sound card for alsa, add:
```
defaults.pcm.card 0
defaults.ctl.card 0
```

### Disable Pi GPU

This should help give more power to the CPU, useful for older Pis.
Edit `/boot/config.txt` and add:
```
gpu_mem=16
disable_l2cache=0  # For pi 1 only
gpu_freq=250
```

### Full circuit diagram

<img title="Qbee wirings" src="./circuit.jpg">

The relay turns on the 24 VDC power supply, which powers the amplifier, the LCD backlight and a green status LED.
