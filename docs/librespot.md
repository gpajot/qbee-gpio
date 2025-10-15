# Setting up Librespot

See https://hub.docker.com/r/giof71/librespot, this is what I am using:

```shell
docker run -d --name librespot \
    --network host \
    --device /dev/snd \
    -e DEVICE_NAME=Qbee \
    -e QUIET=y \
    -e ENABLE_VOLUME_NORMALISATION=y \
    -e BITRATE=320 \
    -e BACKEND=alsa \
    -e DEVICE=hw:CARD=sndrpihifiberry,DEV=0 \
    -e INITIAL_VOLUME=60 \
    -e ONEVENT_COMMAND=/opt/qbee/on-event.bash \
    -v "$HOME/librespot/scripts:/opt/qbee:ro" \
    -v "$HOME/librespot/metadata:/run/qbee:ro" \
    --restart always \
    giof71/librespot:latest
```

You will also need to set up the script to pipe events to Qbee in `$HOME/librespot/scripts/on-event.bash` and make it executable:

```bash
#!/usr/bin/bash
set -o errexit
# Expose track_changed librespot events in a named pipe.
PIPE="/run/qbee/metadata"
# Only expose track changed events.
if [ "$PLAYER_EVENT" != 'track_changed' ]; then
  exit 0
fi
# It must be a named pipe.
if ! [ -p "$PIPE" ]; then
  exit 0
fi
artists=$(printf '%s' "$ARTISTS" | base64)
album=$(printf '%s' "$ALBUM" | base64)
title=$(printf '%s' "$NAME" | base64)
printf 'artists:%s,album:%s,title:%s\t' "$artists" "$album" "$title" > "$PIPE"
```
