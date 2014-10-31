#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
:summary: Background script to control an amplifier and LCD character display from a Raspberry Pi.

The script listens for activity on the sound driver and powers the amp when playing sound from
shairport or mpd. The amplifier and LCD will be turned off after a preset time. When playing
from mpd, the script will also fetch and display the song/stream information.

CONFIGURATION VARIABLES:
- *_PIN: this should reflect the wiring of the GPIO pins, check this carefully
- AMP_OFF_DELAY: the time (s) after which the amp/lcd will be turned off after playback has stopped
- SOUND_PROCESSES: add any process needed here (value must match the process using the sound driver)
- SOUND_DRIVER_PATH: the path of the sound driver used
- AIRPLAY_FIFO_PATH: the path to the airplay fifo containing the current playing song

:author: Gabriel Pajot
:date: 2014-04-18
"""

import os
import RPi.GPIO as GPIO
import time
import subprocess
import re
import threading
import pyinotify
import unicodedata
import select
import logging

# GPIO pin configuration (BCM).
AMP_POWER_PIN = 4
LCD_POWER_PIN = 17
LCD_RS_PIN = 27
LCD_E_PIN = 18
LCD_D4_PIN = 25
LCD_D5_PIN = 24
LCD_D6_PIN = 23
LCD_D7_PIN = 22

# Delay to keep the amp on after use.
AMP_OFF_DELAY = 5 * 60

# Delay between which to check the CPU temperature.
TEMP_DELAY = 60 * 60
# Temp threshold to aim.
TEMP_THRESHOLD = 50

# Variables allowing to fetch information from sound output use.
SOUND_PROCESSES = {'AirPlay': 'shairport',
                   'MPD': 'mpd'}

# Sound driver path.
SOUND_DRIVER_PATH = '/dev/snd/pcmC0D0p'

# AirPlay fifo path.
AIRPLAY_FIFO_PATH = '/var/lib/shairport/now_playing'

# Initiate logger, DEBUG is used for pins, INFO for verbose logging and WARNING for important messages.
logger = None
LOGGER_LEVEL = logging.WARNING

def initiate_logger():
    global logger
    logger = logging.getLogger('gpio')
    hdlr = logging.FileHandler('/var/lib/gpio/qbee_gpio.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr) 
    logger.setLevel(LOGGER_LEVEL)
initiate_logger()


def log(level, *args):
    """
    Used for printing information on the logger while debugging.
    """

    getattr(logger, level)(''.join(map(str, args)))


def dec_busy(func):
    """
    Decorator to set the amp/lcd controller state to busy while executing function.
    """

    def wrapper(*args, **kwargs):
        args[0].busy = True
        output = func(*args, **kwargs)
        args[0].busy = False

        return output

    return wrapper


def dec_check_power(func):
    """
    Decorator to check for LCD power before doing function.
    """

    def wrapper(*args, **kwargs):
        tries = 0
        while not args[0].state and tries < args[0].POWER_TRIES:
            time.sleep(args[0].POWER_WAIT_TIME)
            tries += 1

        return func(*args, **kwargs)

    return wrapper


def dec_check_lines(func):
    """
    Decorator to check the currently displayed lines on the LCD to prevent rewriting on the screen.
    """

    def wrapper(*args, **kwargs):
        str_args = str(args) + str(kwargs)
        if args[0].lines != str_args:
            args[0].lines = str_args
            func(*args, **kwargs)

    return wrapper


def strip_accents(s):
    """
    Remove accents from unicode strings.
    """

    return ''.join(c for c in unicodedata.normalize('NFD', unicode(s, 'utf-8', errors='ignore'))
                   if unicodedata.category(c) != 'Mn')


def pin_output(pin, state):
    """
    Wrapper function used to debug pin states.
    """

    GPIO.output(pin, state)
    # log('debug', 'pin ',  pin, ', state ', state)


class AmpController(object):
    """
    Custom timer function used to control the power of the amp.
    """

    TEMP_CMD = 'cat /sys/class/thermal/thermal_zone0/temp'

    def __init__(self, func):

        self.event = threading.Event()
        # Function used to power off amp and LCD.
        self.func = func
        # Power state of the amp.
        self.state = False
        # Whether the amp controller is currently busy.
        self.busy = False
        # Need a separate thread for the off timer to be able to restart it.
        self.thread = None
        # Temperature monitoring thread, will run whenever amp is off.
        self.temperature_thread = None

        GPIO.setup(AMP_POWER_PIN, GPIO.OUT)
        pin_output(AMP_POWER_PIN, False)

        self._start_temp_monitor()

    @dec_busy
    def power(self, state):

        pin_output(AMP_POWER_PIN, state)
        log('info', 'Amp power:', state)
        self.state = state

    def start(self):
        """
        Start the timer.
        """

        # Initiate a new thread and start it.
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        """
        Start the timer, will be called by self.thread.
        """

        self.event.wait(AMP_OFF_DELAY)
        if not self.event.is_set():
            self.func(False)
            # Start the temperature monitor thread.
            self._start_temp_monitor()

    @dec_busy
    def stop(self):
        """
        Stop the timer. The threading event is used by both the power timeout and temp threads.
        """

        self.event.set()

        # Wait before the threads finish.
        if self.thread is not None:
            self.thread.join()
            self.thread = None
        if self.temperature_thread is not None:
            self.temperature_thread.join()
            self.temperature_thread = None

        # Reset the timer event.
        self.event.clear()

    def _start_temp_monitor(self):
        """
        Start the temperature monitoring thread.
        """

        self.temperature_thread = threading.Thread(target=self._run_temp_monitor)
        self.temperature_thread.start()
        log('info', 'starting temperature monitoring thread')

    def _run_temp_monitor(self):
        """
        Start the temperature monitoring thread, will be called by self.temperature_thread.
        """

        self.event.wait(TEMP_DELAY)
        if not self.event.is_set():
            self._check_temp()

    def _check_temp(self):
        """
        Check the temperature.
        """

        get_temp_cmd = subprocess.Popen(self.TEMP_CMD,
                                        shell=True, stdout=subprocess.PIPE)
        temp = int(get_temp_cmd.stdout.readlines()[0]) / 1000
        if temp >= TEMP_THRESHOLD and not self.state:
            log('warning', 'high temperature: ' + temp)
            self.power(True)
            self.start()
        elif not self.state:
            self._start_temp_monitor()


class LCDController(object):
    """
    Object responsible for controlling the LCD (power, text displayed).
    """

    # Character width of the LCD.
    LCD_WIDTH = 16

    # Line addresses for the LCD.
    LCD_LINES = (0x80, 0xC0)

    # Timing constants.
    E_PULSE_CHR = .000001
    E_DELAY_CHR = .000001
    # Delays must be longer for commands.
    E_PULSE_CMD = .001
    E_DELAY_CMD = .001

    # LCD mode, command or character byte.
    LCD_CHR = True
    LCD_CMD = False

    # Variables defining how long to wait before power comes up.
    POWER_WAIT_TIME = .005
    POWER_TRIES = 1000

    def __init__(self):

        # Power state of the LCD.
        self.state = False
        # Whether the LCD controler is currently busy.
        self.busy = False
        # Currently displayed lines.
        self.lines = None

        for pin in (LCD_POWER_PIN, LCD_E_PIN, LCD_RS_PIN, LCD_D4_PIN, LCD_D5_PIN, LCD_D6_PIN, LCD_D7_PIN):
            GPIO.setup(pin, GPIO.OUT)
            pin_output(pin, False)

    @dec_busy
    def power(self, state):
        """
        Turn on and Initialize the display or power off.
        """

        pin_output(LCD_POWER_PIN, state)
        log('info', 'LCD power:', state)
        self.state = state
        if not state:
            self.lines = None

        # Initialize the LCD.
        if state:
            for byte in (0x33, 0x32, 0x28, 0x0C, 0x06, 0x01):
                self._lcd_send_byte(byte, self.LCD_CMD)

    @staticmethod
    def _reset_data_pins():
        """
        Reset all data pins to low.
        """

        for pin in (LCD_D4_PIN, LCD_D5_PIN, LCD_D6_PIN, LCD_D7_PIN):
            pin_output(pin, False)

    @dec_busy
    @dec_check_lines
    @dec_check_power
    def lcd_send_string(self, line1='', line2=''):
        """
        Display a message on the LCD.
        """

        line1 = strip_accents(line1.strip()[:self.LCD_WIDTH]).center(self.LCD_WIDTH)
        line2 = strip_accents(line2.strip()[:self.LCD_WIDTH]).center(self.LCD_WIDTH)

        log('info', 'Display string:', line1, line2)
        for idx, line in enumerate((line1, line2)):
            self._lcd_send_byte(self.LCD_LINES[idx], self.LCD_CMD)
            for letter in line:
                self._lcd_send_byte(ord(letter), self.LCD_CHR)

    def _toggle_enable_pin(self, mode):
        """
        Toggle 'Enable' pin.
        """

        time.sleep(self.E_DELAY_CHR if mode else self.E_DELAY_CMD)
        pin_output(LCD_E_PIN, True)
        time.sleep(self.E_PULSE_CHR if mode else self.E_PULSE_CMD)
        pin_output(LCD_E_PIN, False)
        time.sleep(self.E_DELAY_CHR if mode else self.E_DELAY_CMD)

    def _lcd_send_byte(self, bits, mode):
        """
        Send bits to the display.
        """

        # Set the mode.
        if mode:
            pin_output(LCD_RS_PIN, mode)

        # High bits.
        for pin, bit in ((LCD_D4_PIN, 0x10), (LCD_D5_PIN, 0x20), (LCD_D6_PIN, 0x40), (LCD_D7_PIN, 0x80)):
            if bits & bit == bit:
                pin_output(pin, True)

        self._toggle_enable_pin(mode)
        self._reset_data_pins()

        # Low bits.
        for pin, bit in ((LCD_D4_PIN, 0x01), (LCD_D5_PIN, 0x02), (LCD_D6_PIN, 0x04), (LCD_D7_PIN, 0x08)):
            if bits & bit == bit:
                pin_output(pin, True)

        self._toggle_enable_pin(mode)
        self._reset_data_pins()

        if mode:
            pin_output(LCD_RS_PIN, False)


class DisplayThreadMPD(threading.Thread):
    """
    Thread that will periodically check for song change of MPD and update the LCD.
    """

    # Interval between which to check for song info and refresh display.
    DISPLAY_REFRESH_DELAY = 10

    def __init__(self, func, *args, **kwargs):

        super(DisplayThreadMPD, self).__init__(*args, **kwargs)

        self.func = func
        self.event = threading.Event()

        self.start()

    def run(self):
        """
        Loop while thread is active.
        """

        while not self.event.is_set():

            self.event.wait(self.DISPLAY_REFRESH_DELAY)

            if not self.event.is_set():
                self.func()

    def stop(self):
        """
        Stop the thread.
        """

        self.event.set()


class DisplayThreadAP(threading.Thread):
    """
    Thread that listens to song change for AirPlay and update the LCD.
    """

    # Timeout for polling.
    POLL_TIMEOUT = 1000

    # Regex for info parsing.
    RE_INFO = re.compile('artist=(.*?)title=(.*?)album=')

    def __init__(self, func, last_lines, *args, **kwargs):
        super(DisplayThreadAP, self).__init__(*args, **kwargs)

        self.func = func
        self.last_lines = last_lines
        self.event = threading.Event()
        # Display the last lines.
        self.func(self.last_lines)

        # Fifo poll init.
        self.poll = select.poll()
        fifo = os.open(AIRPLAY_FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
        self.poll.register(fifo, select.POLLIN)

        self.info = None

        self.start()

    def run(self):
        """
        Loop while thread is active.
        """

        while not self.event.is_set():

            self._read_info()

    def _read_info(self):
        """
        Read the info from fifo.
        """

        p = self.poll.poll(self.POLL_TIMEOUT)
        if p:
            # Get one char at a time.
            s = os.read(p[0][0], 1)
            if s:
                if self.info is not None:
                    self.info += s
                else:
                    self.info = s
            elif self.info is not None and not self.event.is_set():
                self._parse_info()
        elif self.info is not None and not self.event.is_set():
            self._parse_info()

    def _parse_info(self):
        """
        Parse current info and call func.
        """

        m = self.RE_INFO.search(self.info.replace('\n', ''))
        if m is not None:
            lines = list(m.groups())
            self.func(lines)
            # Replace like this to update the variable of SoundEventHandler.
            self.last_lines[0] = lines[0]
            self.last_lines[1] = lines[1]
        else:
            self.func()
        self.info = None

    def stop(self):
        """
        Stop the thread.
        """

        self.event.set()


class SoundEventHandler(pyinotify.ProcessEvent):
    """
    This object will handle events relating to sound output, as well as control the GPIO pins.
    """

    # How long to wait between different busy checks.
    BUSY_WAIT_TIME = .005

    # Get sound process command.
    SOUND_PROCESS_CMD = 'lsof ' + SOUND_DRIVER_PATH

    # MPD current song information.
    MPD_CURRENT_INFO = 'mpc current'

    def __init__(self, *args, **kwargs):
        """
        Initiate the watcher for the sound driver and initiate all controllers.
        """

        super(SoundEventHandler, self).__init__(*args, **kwargs)

        # Set up the watch manager.
        wm = pyinotify.WatchManager()
        mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_OPEN

        self.notifier = pyinotify.Notifier(wm, self)
        wm.add_watch(SOUND_DRIVER_PATH, mask)

        # Set up the GPIO pins and controllers.
        GPIO.setmode(GPIO.BCM)
        self.amp_controller = AmpController(self._power)
        self.lcd_controller = LCDController()

        # This holds the current process playing sound.
        self.sound_process = None

        # The display threads. These will get the song info and display them.
        self.display_thread_mpd = None
        self.display_thread_ap = None

        # Since the AirPlay info will not be fetched twice, we store the latest info here.
        self.ap_lines = ['AirPlay', '']

    def loop(self):
        """
        Start watching the sound driver for output.
        """

        self.notifier.loop()

    def _get_sound_processes(self):
        """
        Get the list of running sound processes.
        """

        processes = []

        get_sound_cmd = subprocess.Popen(self.SOUND_PROCESS_CMD,
                                         shell=True, stdout=subprocess.PIPE)

        sound_process_lines = get_sound_cmd.stdout.readlines()

        for process_line in sound_process_lines[1:]:
            for display_name, process in SOUND_PROCESSES.iteritems():
                if re.search(process, process_line) and process not in processes:
                    processes.append(display_name)

        if processes:
            self.sound_process = processes[0]
        else:
            self.sound_process = None

    def display_lines(self, lines=None):
        """
        Parse the current sound process into lines to display on the LCD and display them.
        """

        if lines is None:
            lines = ['', '']

            if self.sound_process is not None:
                if self.sound_process == 'MPD':
                    # Surround this with exception handling to at least be able to display something and power the amp.
                    try:
                        get_song_cmd = subprocess.Popen(self.MPD_CURRENT_INFO,
                                                        shell=True, stdout=subprocess.PIPE)
                        song_lines = get_song_cmd.stdout.readlines()
                        if song_lines:
                            song = song_lines[0].split(' - ')
                            if len(song) == 2:
                                lines = song
                            else:
                                # Radio or something else that was wrongly parsed.
                                lines[0] = song[0] if song else self.sound_process
                        else:
                            lines[0] = self.sound_process
                    except:
                        lines[0] = self.sound_process
                else:
                    lines[0] = self.sound_process

        # Display the running process on the lcd.
        while self.lcd_controller.busy:
            time.sleep(self.BUSY_WAIT_TIME)
        self.lcd_controller.lcd_send_string(*lines)

    def _power(self, state):
        """
        Power on/off the amp and the lcd.
        """

        self.amp_controller.power(state)
        self.lcd_controller.power(state)

    def _stop_display_threads(self, thread=None):
        """
        Stop the display threads if running.
        """

        if (thread == 'mpd' or thread is None) and self.display_thread_mpd is not None:
            log('info', 'stopping display_thread_mpd')
            self.display_thread_mpd.stop()
            self.display_thread_mpd.join()
            self.display_thread_mpd = None
        elif (thread == 'ap' or thread is None) and self.display_thread_ap is not None:
            log('info', 'stopping display_thread_ap')
            self.display_thread_ap.stop()
            self.display_thread_ap.join()
            self.display_thread_ap = None

    def process_default(self, event):
        """
        Generic method to process OPEN and CLOSE events.
        """

        while self.amp_controller.busy or self.lcd_controller.busy:
            time.sleep(self.BUSY_WAIT_TIME)

        self._get_sound_processes()

        if self.sound_process is not None:

            # Turn on amp and LCD if not already on.

            if not self.amp_controller.state:
                self.amp_controller.power(True)
            else:
                # Stop the turn off timer if amp already on or temperature monitoring thread.
                self.amp_controller.stop()

            if not self.lcd_controller.state:
                self.lcd_controller.power(True)

            # Start or stop the display thread depending on sound source.
            if self.sound_process == 'MPD':
                self._stop_display_threads('ap')
                # Display the proper lines on LCD.
                self.display_lines()
                if self.display_thread_mpd is None:
                    self.display_thread_mpd = DisplayThreadMPD(func=self.display_lines)
                    log('info', 'starting display_thread_mpd')
            elif self.sound_process == 'AirPlay':
                self._stop_display_threads('mpd')
                if self.display_thread_ap is None:
                    self.display_thread_ap = DisplayThreadAP(func=self.display_lines, last_lines=self.ap_lines)
                    log('info', 'starting display_thread_ap')
            else:
                self._stop_display_threads()

        else:
            # Stop display threads if running, start the turn off timer for the amp and clear the LCD.
            self._stop_display_threads()
            self.amp_controller.start()
            self.display_lines()

    def cancel(self):
        """
        Stop the process event and cleanup.
        """

        self._stop_display_threads()
        self.amp_controller.stop()
        GPIO.cleanup()


if __name__ == '__main__':
    log('warning', 'starting script')

    sound_event_handler = SoundEventHandler()

    try:
        # Listen for sound driver activity.
        sound_event_handler.loop()
    finally:
        sound_event_handler.cancel()
