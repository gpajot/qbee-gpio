QBee gpio controller
===========

A python script to control an LCD display and relay for use in an AirPlay and/or MPD Raspberry Pi server. Check here for more information on the project: [http://www.instructables.com/id/QBee-AirPlay-MPD-integrated-speaker-Raspberry-Pi-s](http://www.instructables.com/id/QBee-AirPlay-MPD-integrated-speaker-Raspberry-Pi-s).

## Dependencies

* Pyinotify: [http://github.com/seb-m/pyinotify](http://github.com/seb-m/pyinotify)

Optional:
* Shairport (AirPlay): [https://github.com/abrasive/shairport](https://github.com/abrasive/shairport)
* Music Player Daemon: [http://www.musicpd.org](http://www.musicpd.org)
* Or any other music player

## Features

* Detect sound ouput and turn on the amplifier power supply.
* Get the track information and display it on a 16-pin LCD (currenlty works for Shairport and MPD).
* Regularly check temperature and turn on power supply to start the fan.
* Auto turn off amplifier power supply after set period of inactivity.
