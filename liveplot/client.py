import warnings
import numpy as np
import logging
import zmq

__author__ = 'phil'

logging.root.setLevel(logging.DEBUG)

class LivePlotClient(object):
    def __init__(self, timeout=2000):
        ctx = zmq.Context()
        self.sock = ctx.socket(zmq.PUB)
        self.sock.connect('tcp://127.0.0.1:7755')
        self.is_connected = True
        self.timeout = timeout

    def send_to_plotter(self, meta, arr=None):
        if not self.is_connected:
            return
        if meta["name"] == None:
            meta["name"] = "*";
        if arr is not None:
            arrbytes = bytearray(arr)
            meta['arrsize'] = len(arrbytes)
            meta['dtype'] = str(arr.dtype)
            meta['shape'] = arr.shape
        else:
            meta['arrsize'] = 0
        self.sock.send_json(meta)
        if arr is not None:
            self.sock.send(arrbytes)

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
