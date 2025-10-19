# Setting up shairport-sync

See https://hub.docker.com/r/mikebrady/shairport-sync, this is what I am using:

```shell
docker run -d \
  --name shairport \
  --restart always \
  --network host \
  --cap-add=SYS_NICE \
  -e ALSA_CARD=sndrpihifiberry \
  --device /dev/snd \
  -v ~/shairport:/etc/shairport:ro \
  mikebrady/shairport-sync:latest \
  --configfile=/etc/shairport/shairport-sync.conf
```

You will also need to set up the config in `~/shairport/shairport-sync.conf`:

```
general =
{
  name = "Qbee";
  default_airplay_volume = -20.0;
};
metadata =
{
  enabled = "yes";
  include_cover_art = "no";
  socket_address = "127.0.0.1";
  socket_port = 8000;
};
```
