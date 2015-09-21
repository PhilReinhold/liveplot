import atexit
import os
import json
import logging
import signal
import widgets
import numpy as np
from PyQt4.QtCore import QSharedMemory, QSize
from PyQt4.QtGui import QMainWindow, QApplication, QStandardItem, QDockWidget, QStandardItemModel, QListView, QAction, \
    QIcon
from PyQt4.QtNetwork import QLocalServer
from PyQt4.Qt import Qt as QtConst
from pyqtgraph.dockarea import DockArea

logging.root.setLevel(logging.WARNING)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Liveplot")
        self.setWindowIcon(QIcon('icon.ico'))
        self.dockarea = DockArea()
        self.setCentralWidget(self.dockarea)
        self.namelist = NameList(self)
        self.addDockWidget(QtConst.LeftDockWidgetArea, self.namelist)
        self.server = QLocalServer()
        self.server.removeServer('LivePlot')
        self.server.listen('LivePlot')
        self.server.newConnection.connect(self.accept)
        self.bytes = bytearray()
        self.target_size = 0
        self.meta = None
        self.insert_dock_right = True
        self.conns = []
        self.shared_mems = []
        signal.signal(signal.SIGINT, self.close)


    def close(self, sig=None, frame=None):
        print 'closing'
        for conn in self.conns:
            conn.close()
        for shm in self.shared_mems:
            shm.detach()
        QApplication.instance().exit()


    def accept(self):
        logging.debug('connection accepted')
        conn = self.server.nextPendingConnection()
        conn.waitForReadyRead()
        key = str(conn.read(36))
        memory = QSharedMemory()
        memory.setKey(key)
        memory.attach()
        logging.debug('attached to memory %s with size %s'%(key, memory.size()))
        atexit.register(memory.detach)
        self.conns.append(conn)
        self.shared_mems.append(memory)
        conn.readyRead.connect(lambda: self.read_from(conn, memory))
        conn.disconnected.connect(memory.detach)
        conn.write('ok')

    # noinspection PyNoneFunctionAssignment
    def read_from(self, conn, memory):
        logging.debug('reading data')
        self.meta = json.loads(conn.read(200))
        if self.meta['arrsize'] != 0:
            memory.lock()
            ba = memory.data()[0:self.meta['arrsize']]
            arr = np.frombuffer(buffer(ba))
            memory.unlock()
            conn.write('ok')
            arr = arr.reshape(self.meta['shape']).copy()
        else:
            arr = None
        self.do_operation(arr)
        if conn.bytesAvailable():
            self.read_from(conn, memory)

    #     if not self.target_size:
    #         self.meta = conn._socket.recv_json()
    #         self.target_size = self.meta['arrsize']
    #     if self.target_size > 0:
    #         n = self.target_size - len(self.bytes)
    #         data = bytearray(conn.read(n))
    #         self.bytes.extend(data)
    #     if len(self.bytes) == self.target_size:
    #         self.process_bytes()
    #     if conn.bytesAvailable():
    #         self.read_from(conn)
    #
    # def process_bytes(self):
    #     self.target_size = 0
    #     if len(self.bytes) > 0:
    #         arr = np.frombuffer(buffer(self.bytes), dtype=self.meta['dtype'])
    #         try:
    #             arr.resize(self.meta['shape'])
    #         except ValueError:
    #             arr = arr.reshape(self.meta['shape'])
    #     else:
    #         arr = None
    #     self.bytes = bytearray()
    #     self.do_operation(arr)

    def do_operation(self, arr=None):
        def clear(name):
            self.namelist[name].clear()

        def close(name):
            self.namelist[name].close()

        def remove(name):
            del self.namelist[name]

        meta = self.meta
        operation = meta['operation']
        name = meta['name']

        if name in self.namelist:
            pw = self.namelist[name]
            if pw.closed:
                pw.closed = False
                self.dockarea.addDock(pw)

        elif name == "*":
            if operation == 'clear':
                map(clear, self.namelist.keys())
            elif operation == 'close':
                map(close, self.namelist.keys())
            elif operation == 'remove':
                map(remove, self.namelist.keys())
            return
        else:
            if operation in ('clear', 'close', 'remove'):
                return
            pw = self.add_new_plot(meta['rank'], name)

        if operation == 'clear':
            pw.clear()
        elif operation == 'close':
            pw.close()
        elif operation == 'remove':
            del self.namelist[name]

        elif operation == 'plot_y':
            start_step = meta['start_step']
            label = meta['label']
            if start_step is not None:
                x0, dx = start_step
                nx = len(arr)
                xs = np.linspace(x0, x0 + (nx - 1)*dx, nx)
                pw.plot(xs, arr, name=label)
            else:
                pw.plot(arr, name=label)
        elif operation == 'plot_xy':
            label = meta['label']
            pw.plot(arr[0], arr[1], parametric=True, name=label)
        elif operation == 'plot_z':
            start_step = meta['start_step']
            if start_step is not None:
                (x0, dx), (y0, dy) = start_step
                pw.setImage(arr, pos=(x0, y0), scale=(dx, dy))
            else:
                pw.setImage(arr)
        elif operation == 'append_y':
            label = meta['label']
            xs, ys = pw.get_data(label)
            new_ys = list(ys)
            new_ys.append(meta['value'])
            start_step = meta['start_step']
            if start_step is not None:
                x0, dx = start_step
                nx = len(new_ys)
                xs = np.linspace(x0, x0 + (nx - 1)*dx, nx)
                pw.plot(xs, new_ys, name=label)
            else:
                pw.plot(new_ys, name=label)
        elif operation == 'append_xy':
            label = meta['label']
            xs, ys = pw.get_data(label)
            xn, yn = meta['value']
            new_xs = list(xs)
            new_xs.append(xn)
            new_ys = list(ys)
            new_ys.append(yn)
            pw.plot(new_xs, new_ys, parametric=True, name=label)

        elif operation == 'append_z':
            image = pw.get_data()
            if image is None:
                image = np.array([arr])
            else:
                try:
                    image = np.vstack((image, [arr]))
                except ValueError:
                    image = np.array([arr])
            start_step = meta['start_step']
            if start_step is not None:
                (x0, dx), (y0, dy) = start_step
                pw.setImage(image, pos=(x0, y0), scale=(dx, dy))
            else:
                pw.setImage(image)

        elif operation == 'label':
            pw.setTitle(meta['value'])

    def add_new_plot(self, rank, name):
        pw = widgets.get_widget(rank, name)
        self.add_plot(pw)
        self.namelist[name] = pw
        return pw

    def add_plot(self, pw):
        self.insert_dock_right = not self.insert_dock_right
        self.dockarea.addDock(pw, position=['bottom', 'right'][self.insert_dock_right])

    def sizeHint(self):
        return QSize(1000, 600)


class NameList(QDockWidget):
    def __init__(self, window):
        super(NameList, self).__init__('Current Plots')
        self.namelist_model = QStandardItemModel()
        self.namelist_view = QListView()
        self.namelist_view.setModel(self.namelist_model)
        self.setWidget(self.namelist_view)
        self.window = window
        self.plot_dict = {}

        self.namelist_view.doubleClicked.connect(self.activate_item)
        self.namelist_view.setContextMenuPolicy(QtConst.ActionsContextMenu)
        delete_action = QAction("Delete Selected", self.namelist_view)
        delete_action.triggered.connect(self.delete_item)
        self.namelist_view.addAction(delete_action)

    def activate_item(self, index):
        item = self.namelist_model.itemFromIndex(index)
        plot = self.plot_dict[str(item.text())]
        if plot.closed:
            plot.closed = False
            self.window.add_plot(plot)

    def delete_item(self):
        index = self.namelist_view.currentIndex()
        item = self.namelist_model.itemFromIndex(index)
        del self[str(item.text())]

    def __getitem__(self, item):
        return self.plot_dict[item]

    def __setitem__(self, name, plot):
        model = QStandardItem(name)
        model.setEditable(False)
        self.namelist_model.appendRow(model)
        self.plot_dict[name] = plot

    def __contains__(self, value):
        return value in self.plot_dict

    def __delitem__(self, name):
        self.namelist_model.removeRow(self.namelist_model.findItems(name)[0].index().row())
        self.plot_dict[name].close()
        del self.plot_dict[name]

    def keys(self):
        return self.plot_dict.keys();


def main():
    if os.name == 'nt':
        import ctypes
        myappid = 'philreinhold.liveplot'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
