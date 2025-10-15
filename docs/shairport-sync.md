# Setting up shairport-sync

See https://hub.docker.com/r/mikebrady/shairport-sync, this is what I am using:

```shell
docker run -d --name shairport \
    --cap-add=SYS_NICE \
    --network host \
    --device /dev/snd \
    -v "$HOME/shairport:/run/qbee:ro" \
    --restart always \
    mikebrady/shairport-sync \
    --name=Qbee \
    --metadata-enable \
    --metadata-pipename=/run/qbee/metadata \
    -- \
    -d hw:CARD=sndrpihifiberry,DEV=0 
```
