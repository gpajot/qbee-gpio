# qbee-gpio

[![tests](https://github.com/gpajot/qbee-gpio/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/gpajot/qbee-gpio/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)
[![DockerHub](https://img.shields.io/docker/v/gpajot/qbee-gpio/latest)](https://hub.docker.com/r/gpajot/qbee-gpio)

A docker image to control an LCD and amplifier relay for use in an AirPlay and/or Spotify Connect Raspberry Pi server.

* Detect sound output and turn on the amplifier power supply.
* Get the track information and display it on an LCD.
* Auto turn off amplifier power supply after set period of inactivity.

Additional documentation:

* [Setting up shairport-sync](./docs/shairport-sync.md)
* [Setting up librespot](./docs/librespot.md)
* [My hardware](./docs/hardware.md)

## Running

```shell
docker run -d --name qbee \
  --network host \
  --device=/dev/gpiomem \
  -v $CONFIG_DIR:/app/config:ro \
  --restart always \
  gpajot/qbee-gpio
```

This expects a config file located at `$CONFIG_DIR/conf.yaml`.
See [all config options](./qbee_gpio/config.py)
