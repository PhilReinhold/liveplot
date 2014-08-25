import atexit
import json
import uuid
import warnings
import numpy as np
import logging
from PyQt4.QtNetwork import QLocalSocket
from PyQt4.QtCore import QCoreApplication, QSharedMemory

__author__ = 'phil'

logging.root.setLevel(logging.WARNING)

class LivePlotClient(object):
    def __init__(self, timeout=2000, size=2**20):
        self.app = QCoreApplication.instance()
        if self.app is None:
            self.app = QCoreApplication([])
        self.sock = QLocalSocket()
        self.sock.connectToServer("LivePlot")
        if not self.sock.waitForConnected():
            raise EnvironmentError("Couldn't find LivePlotter instance")
        self.sock.disconnected.connect(self.disconnect_received)

        key = str(uuid.uuid4())
        self.shared_mem = QSharedMemory(key)
        if not self.shared_mem.create(size):
            raise Exception("Couldn't create shared memory %s" % self.shared_mem.errorString())
        logging.debug('Memory created with key %s and size %s' % (key, self.shared_mem.size()))
        self.sock.write(key)
        self.sock.waitForBytesWritten()

        self.is_connected = True
        self.timeout = timeout

        atexit.register(self.close)

    def close(self):
        self.shared_mem.detach()

    def send_to_plotter(self, meta, arr=None):
        if not self.is_connected:
            return

        if meta["name"] is None:
            meta["name"] = "*";
        if arr is not None:
            arrbytes = bytearray(arr)
            arrsize = len(arrbytes)
            if arrsize > self.shared_mem.size():
                raise ValueError("Array too big %s > %s" % (arrsize, self.shared_mem.size()))
            meta['arrsize'] = arrsize
            meta['dtype'] = str(arr.dtype)
            meta['shape'] = arr.shape
        else:
            meta['arrsize'] = 0
        meta_bytes = json.dumps(meta).ljust(200)
        if len(meta_bytes) > 200:
            raise ValueError("meta object is too large (> 200 char)")

        if arr is None:
            self.sock.write(meta_bytes)
        else:
            if not self.sock.bytesAvailable():
                self.sock.waitForReadyRead()
            self.sock.read(2)
            self.shared_mem.lock()
            self.sock.write(meta_bytes)
            region = self.shared_mem.data()
            region[:arrsize] = arrbytes
            self.shared_mem.unlock()

    def plot_y(self, name, arr, extent=None, start_step=None):
        arr = np.array(arr)
        if extent is not None and start_step is not None:
            raise ValueError('extent and start_step provide the same info and are thus mutually exclusive')
        if extent is not None:
            x0, x1 = extent
            nx = len(arr)
            start_step = x0, float(x1 - x0)/nx
        meta = {
            'name': name,
            'operation':'plot_y',
            'start_step': start_step,
            'rank': 1,
        }
        self.send_to_plotter(meta, arr)

    def plot_z(self, name, arr, extent=None, start_step=None):
        '''
        extent is ((initial x, final x), (initial y, final y))
        start_step is ((initial x, delta x), (initial_y, final_y))
        '''
        arr = np.array(arr)
        if extent is not None and start_step is not None:
            raise ValueError('extent and start_step provide the same info and are thus mutually exclusive')
        if extent is not None:
            (x0, x1), (y0, y1) = extent
            nx, ny = arr.shape
            start_step = (x0, float(x1 - x0)/nx), (y0, float(y1 - y0)/ny)
        meta = {
            'name': name,
            'operation':'plot_z',
            'rank': 2,
            'start_step': start_step,
        }
        self.send_to_plotter(meta, arr)

    def plot_xy(self, name, xs, ys):
        arr = np.array([xs, ys])
        meta = {
            'name': name,
            'operation':'plot_xy',
            'rank': 1,
        }
        self.send_to_plotter(meta, np.array([xs, ys]))

    def append_y(self, name, point, start_step=None):
        self.send_to_plotter({
            'name': name,
            'operation': 'append_y',
            'value': point,
            'start_step': start_step,
            'rank': 1,
        })

    def append_xy(self, name, x, y):
        self.send_to_plotter({
            'name': name,
            'operation': 'append_xy',
            'value': (x, y),
            'rank': 1,
        })

    def append_z(self, name, arr, start_step=None):
        arr = np.array(arr)
        meta = {
            'name': name,
            'operation':'append_z',
            'rank': 2,
            'start_step': start_step,
            }
        self.send_to_plotter(meta, arr)

    def clear(self, name=None):
        self.send_to_plotter({
            'name': name,
            'operation': 'clear'
        })

    def hide(self, name=None):
        self.send_to_plotter({
            'name': name,
            'operation': 'close'
        })

    def remove(self, name=None):
        self.send_to_plotter({
            'name': name,
            'operation': 'remove'
        })

    def disconnect_received(self):
            self.is_connected = False
            warnings.warn('Disconnected from LivePlotter server, plotting has been disabled')
