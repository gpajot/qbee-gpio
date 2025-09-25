# Setting up shairport-sync

You can follow instructions [here](https://github.com/mikebrady/shairport-sync/blob/master/BUILD.md).
Here is what I used:

Install required packages:
```shell
sudo apt install --no-install-recommends build-essential git autoconf automake libtool \
    libpopt-dev libconfig-dev libasound2-dev avahi-daemon libavahi-client-dev libssl-dev libsoxr-dev
```

Install shairport-sync:
```shell
git clone https://github.com/mikebrady/shairport-sync.git --depth 1
cd shairport-sync
autoreconf -fi
./configure --sysconfdir=/etc --with-alsa --with-soxr --with-avahi --with-ssl=openssl --with-systemd --with-metadata
make
sudo make install
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

Enable to run on boot: `sudo systemctl enable shairport-sync.service --now`.
