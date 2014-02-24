liveplot.py
===========

![](http://github.com/PhilReinhold/liveplot/master/screenshot.png)

Requirements
------------
- Numpy
- [PyQt4](http://www.riverbankcomputing.com/software/pyqt/download)
- [pyqtgraph](http://www.pyqtgraph.org)

Basic Usage
-----------

Put the liveplot directory in your path somewhere and start the window

    python -m liveplot

Then open a client and plot
```python
from liveplot import LivePlotClient
import numpy as np
plotter = LivePlotClient()
xs = np.linspace(0, 10, 100)
plotter.plot_xy('my test data', xs, np.sin(xs))
```

See more examples with the test suite, `liveplot_test.py`. Several methods of
plotting are supported, including cumulative, parametric, and 2D.

GUI Features
------------
- Double click on plots to bring up cross-hair marker
- Cross-hair displays cross-section cuts for image plots
- Restore closed plots by double-clicking the name in the plot list

To Do
-----
- Appending method for image plots
- Record history with updating plot
- Context menu for toggling cross-hairs, image histogram
- Keep plots hidden while updating
- Permanently delete plots
