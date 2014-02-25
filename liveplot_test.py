import numpy as np
from client import LivePlotClient
import time

c = LivePlotClient()

for i in range(100):
   arr = np.sin(np.linspace(0, 10, 100) + i/2.)
   c.plot_y('scrolling sine', arr)
   time.sleep(.05)

xs = np.linspace(-1, 1, 100)
for mu in xs:
    ys = np.exp((-(xs - mu)**2)/.1)
    c.plot_xy('travelling packet', xs, ys)
    time.sleep(.05)

for val in np.exp(np.linspace(0, 6, 100)):
    c.append_y('appending exp', val)
    time.sleep(.05)

for i in range(100):
   ts = np.linspace(0, 20, 300) + i/20.
   xs = ts**2 * np.sin(ts)
   ys = ts**2 * np.cos(ts)
   c.plot_xy('rotating spiral', xs, ys)
   time.sleep(.05)

c.clear('spiral out')
for x, y in zip(xs, ys):
    c.append_xy('spiral out', x, y)
    time.sleep(.05)

xs, ys = np.mgrid[-100:100, -100:100]/20.
rs = np.sqrt(xs**2 + ys**2)
for i in range(100):
    c.plot_z('sinc', np.sinc(rs + i/20.), extent=((-5, 5), (-10, 10)))
    time.sleep(.05)