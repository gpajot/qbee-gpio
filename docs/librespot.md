# Setting up Librespot

See https://hub.docker.com/r/giof71/librespot, this is what I am using:

```shell
docker run -d \
  --name librespot \
  --restart always \
  --network host \
  -e ALSA_CARD=sndrpihifiberry \
  -e DEVICE_NAME=Qbee \
  -e QUIET=y \
  -e ENABLE_VOLUME_NORMALISATION=y \
  -e BITRATE=320 \
  -e BACKEND=alsa \
  -e INITIAL_VOLUME=60 \
  -e ONEVENT_COMMAND=/opt/librespot/on-event.bash \
  --device /dev/snd \
  -v ~/librespot:/opt/librespot:ro \
  --user $(stat -c '%u:%g' ~) \
  --group-add $(stat -c '%g' /dev/snd/timer) \
  giof71/librespot:latest
```

You will also need to set up the script to send events to Qbee in `~/librespot/on-event.bash` and make it executable:

```bash
#!/bin/bash
set -o errexit

if [ "$PLAYER_EVENT" = 'track_changed' ]; then
  printf 'librespot:artists:%s,album:%s,title:%s' "${ARTISTS//$'\n'/, }" "$ALBUM" "$NAME" >/dev/udp/127.0.0.1/8000
elif [ "$PLAYER_EVENT" = 'playing' ]; then
  echo -n "librespot:playing" >/dev/udp/127.0.0.1/8000
elif [ "$PLAYER_EVENT" = 'paused' ]; then
  echo -n "librespot:stopped" >/dev/udp/127.0.0.1/8000
elif [ "$PLAYER_EVENT" = 'session_connected' ]; then
  echo -n "librespot:user:unknown" >/dev/udp/127.0.0.1/8000
elif [ "$PLAYER_EVENT" = 'session_disconnected' ]; then
  echo -n "librespot:user:" >/dev/udp/127.0.0.1/8000
fi
```
