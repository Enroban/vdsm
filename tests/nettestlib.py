# Copyright 2015 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

import errno
import fcntl
import os
import platform
import signal
import struct
from multiprocessing import Process

from nose.plugins.skip import SkipTest

from vdsm.constants import EXT_BRCTL, EXT_TC
from vdsm.netlink import monitor
from vdsm.utils import execCmd, random_iface_name

EXT_IP = "/sbin/ip"


class ExecError(RuntimeError):
    def __init__(self, msg, out, err):
        super(ExecError, self).__init__(msg)
        self.out = out
        self.err = err


def check_call(cmd):
    rc, out, err = execCmd(cmd, raw=True)
    if rc != 0:
        raise ExecError(
            'Command %s returned non-zero exit status %s.' % (cmd, rc),
            out, err)


class Interface():

    def __init__(self, prefix='vdsm-'):
        self.devName = random_iface_name(prefix)

    def _ifUp(self):
        check_call([EXT_IP, "link", "set", self.devName, "up"])

    def _ifDown(self):
        with monitor.Monitor(groups=('link',), timeout=2) as mon:
            check_call([EXT_IP, "link", "set", self.devName, "down"])
            for event in mon:
                if (event.get('name') == self.devName and
                        event.get('state') == 'down'):
                    return

    def __str__(self):
        return "<{0} {1!r}>".format(self.__class__.__name__, self.devName)


class Bridge(Interface):

    def addDevice(self):
        check_call([EXT_BRCTL, 'addbr', self.devName])
        # learning interval is different on different kernels, so set it
        # explicit for 2.x kernels
        if os.uname()[2].startswith("2"):
            check_call([EXT_BRCTL, 'setfd', self.devName, '0'])
            check_call([EXT_BRCTL, 'setageing', self.devName, '0'])
        self._ifUp()

    def delDevice(self):
        self._ifDown()
        check_call([EXT_BRCTL, 'delbr', self.devName])

    def addIf(self, dev):
        check_call([EXT_BRCTL, 'addif', self.devName, dev])


def _listenOnDevice(fd, icmp):
    while True:
        packet = os.read(fd, 2048)
        # check if it is an IP packet
        if (packet[12:14] == chr(0x08) + chr(0x00)):
            if packet == icmp:
                return


class Tap(Interface):

    _IFF_TAP = 0x0002
    _IFF_NO_PI = 0x1000
    arch = platform.machine()
    if arch == 'x86_64':
        _TUNSETIFF = 0x400454ca
    elif arch == 'ppc64':
        _TUNSETIFF = 0x800454ca
    else:
        raise SkipTest("Unsupported Architecture %s" % arch)

    _deviceListener = None

    def addDevice(self):
        self._cloneDevice = open('/dev/net/tun', 'r+b')
        ifr = struct.pack('16sH', self.devName, self._IFF_TAP |
                          self._IFF_NO_PI)
        fcntl.ioctl(self._cloneDevice, self._TUNSETIFF, ifr)
        self._ifUp()

    def delDevice(self):
        self._ifDown()
        self._cloneDevice.close()

    def startListener(self, icmp):
        self._deviceListener = Process(target=_listenOnDevice,
                                       args=(self._cloneDevice.fileno(), icmp))
        self._deviceListener.start()

    def isListenerAlive(self):
        if self._deviceListener:
            return self._deviceListener.is_alive()
        else:
            return False

    def stopListener(self):
        if self._deviceListener:
            os.kill(self._deviceListener.pid, signal.SIGKILL)
            self._deviceListener.join()

    def writeToDevice(self, icmp):
        os.write(self._cloneDevice.fileno(), icmp)


def checkDependencies():
    dev = Bridge()
    try:
        dev.addDevice()
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise SkipTest("Cannot run %r: %s\nDo you have bridge-utils "
                           "installed?" % (EXT_BRCTL, e))
        raise

    try:
        check_call([EXT_TC, 'qdisc', 'add', 'dev', dev.devName, 'ingress'])
    except ExecError as e:
        raise SkipTest("%r has failed: %s\nDo you have Traffic Control kernel "
                       "modules installed?" % (EXT_TC, e.err))
    finally:
        dev.delDevice()
