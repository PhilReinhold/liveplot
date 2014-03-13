import inspect
from PyQt4.QtGui import QApplication, QMainWindow, QWidget, QVBoxLayout, QSpinBox, QHBoxLayout, QLabel, QPushButton, \
    QPlainTextEdit
import numpy as np
import sys
from liveplot import LivePlotClient
import time

def test_plot_y(t):
    for i in range(100):
        xs = np.linspace(0, 10, 100) + i / 2.
        arr = np.sin(xs)
        c.plot_y('scrolling sine', arr, start_step=(xs[0], xs[1]-xs[0]))
        time.sleep(t)

def test_plot_xy(t):
    xs = np.linspace(-1, 1, 100)
    for mu in xs:
        ys = np.exp((-(xs - mu)**2)/.1)
        c.plot_xy('travelling packet', xs, ys)
        time.sleep(t)

def test_append_y(t):
    xs = np.linspace(0, 6, 100)
    for val in np.exp(xs):
        c.append_y('appending exp', val, start_step=(xs[0], xs[1]-xs[0]))
        time.sleep(t)

def test_plot_xy_parametric(t):
    for i in range(100):
       ts = np.linspace(0, 20, 300) + i/20.
       xs = ts**2 * np.sin(ts)
       ys = ts**2 * np.cos(ts)
       c.plot_xy('rotating spiral', xs, ys)
       time.sleep(t)

def test_append_xy(t):
    c.clear('spiral out')
    ts = np.linspace(0, 20, 300)
    xs = ts**2 * np.sin(ts)
    ys = ts**2 * np.cos(ts)
    for x, y in zip(xs, ys):
        c.append_xy('spiral out', x, y)
        time.sleep(t)

def test_plot_z(t):
    xs, ys = np.mgrid[-100:100, -100:100]/20.
    rs = np.sqrt(xs**2 + ys**2)
    for i in range(100):
        c.plot_z('sinc', np.sinc(rs + i/20.), extent=((-5, 5), (-10, 10)))
        time.sleep(t)

def test_append_z(t):
    c.clear('appending sinc')
    xs, ys = np.mgrid[-100:100, -100:100]/20.
    rs = np.sqrt(xs**2 + ys**2)
    zs = np.sinc(rs)
    for i in range(200):
        c.append_z('appending sinc', zs[:,i])
        time.sleep(t)

class TestWindow(QWidget):
    def __init__(self):
        super(TestWindow, self).__init__()
        layout = QHBoxLayout(self)
        button_layout = QVBoxLayout()
        time_layout = QHBoxLayout()
        time_spin = QSpinBox()
        time_spin.setValue(50)
        time_spin.setRange(0, 1000)
        time_layout.addWidget(QLabel("Sleep Time (ms)"))
        time_layout.addWidget(time_spin)
        button_layout.addLayout(time_layout)

        tests = {
            'plot y': test_plot_y,
            'plot xy': test_plot_xy,
            'plot parametric': test_plot_xy_parametric,
            'plot z': test_plot_z,
            'append y': test_append_y,
            'append xy': test_append_xy,
            'append z': test_append_z,
        }
        all_button = QPushButton("Run All Tests")
        button_layout.addWidget(all_button)
        fn_text_widget = QPlainTextEdit()
        fn_text_widget.setMinimumWidth(500)

        def make_runner(fn):
            def runner():
                fn_text_widget.setPlainText(inspect.getsource(fn))
                QApplication.instance().processEvents()
                fn(time_spin.value()/1000.)
            return runner

        for name, fn in tests.items():
            button = QPushButton(name)
            button.clicked.connect(make_runner(fn))
            all_button.clicked.connect(make_runner(fn))
            button_layout.addWidget(button)

        layout.addLayout(button_layout)
        layout.addWidget(fn_text_widget)

if __name__ == "__main__":
    app = QApplication([])
    c = LivePlotClient()
    win = TestWindow()
    win.show()
    sys.exit(app.exec_())
