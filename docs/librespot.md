# Setting up Librespot

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
