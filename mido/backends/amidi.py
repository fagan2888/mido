"""Mido amidi backend

Very experimental backend using amidi to access the ALSA rawmidi
interface.

Todo:

* implement non-blocking receive (thread and queue?)
* use parser instead of from_hex()
* default port name
* do sysex messages work?
* starting amidi for every message sent is costly
"""
import os
import subprocess
from ..messages import Message
from ._common import ParserQueue, PortMethods, InputMethods, OutputMethods
"""
Dir Device    Name
IO  hw:1,0,0  UM-1 MIDI 1
IO  hw:2,0,0  nanoKONTROL2 MIDI 1
IO  hw:2,0,0  MPK mini MIDI 1
"""

def get_devices():
    devices = []

    lines = os.popen('amidi -l').read().splitlines()
    for line in lines[1:]:
        mode, device, name = line.strip().split(None, 2)

        devices.append({
            'name': name.strip(),
            'device': device,
            'is_input': 'I' in mode,
            'is_output': 'O' in mode,
            })

    return devices


def _get_device(name, mode):
    for dev in get_devices():
        if name == dev['name'] and dev[mode]:
            return dev
    else:
        raise IOError('unknown port {!r}'.format(name))


class Input(PortMethods, InputMethods):
    def __init__(self, name=None, **kwargs):
        self.name = name
        self.closed = False

        self._inproc = None
        
        dev = _get_device(self.name, 'is_input')
        self._inproc = subprocess.Popen(['amidi', '-d',
                                         '-p', dev['device']],
                                        stdout=subprocess.PIPE)
       

    def _receive(self, block=True): 
        while True:
            line = self._inproc.stdout.readline().strip()
            if line:
                return Message.from_hex(line.decode('ascii'))

    def close(self):
        if not self.closed:
            if self._inproc:
                self._inproc.kill()
                self._inproc = None
            self.closed = True


class Output(PortMethods, OutputMethods):
    def __init__(self, name=None, autoreset=False, **kwargs):
        self.name = name
        self.autoreset = autoreset
        self.closed = False

        self._dev = _get_device(self.name, 'is_output')

    def send(self, msg):
        proc = subprocess.Popen(['amidi', '--send-hex', msg.hex(),
                                 '-p', self._dev['device']])
        proc.wait()

    def close(self):
        if not self.closed:
            if self.autoreset:
                self.reset()

            self.closed = True
