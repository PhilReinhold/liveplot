from PyQt4 import QtGui, QtCore
import warnings
import pyqtgraph as pg
import numpy as np
from pyqtgraph.dockarea import Dock

def get_widget(rank, name):
    return {
        1: CrosshairDock,
        2: CrossSectionDock,
        }[rank](name=name)

class CloseableDock(Dock):
    docklist = []
    def __init__(self, *args, **kwargs):
        super(CloseableDock, self).__init__(*args, **kwargs)
        style = QtGui.QStyleFactory().create("windows")
        close_icon = style.standardIcon(QtGui.QStyle.SP_TitleBarCloseButton)
        close_button = QtGui.QPushButton(close_icon, "", self)
        close_button.clicked.connect(self.close)
        close_button.setGeometry(0, 0, 20, 20)
        close_button.raise_()
        self.closeClicked = close_button.clicked

        max_icon = style.standardIcon(QtGui.QStyle.SP_TitleBarMaxButton)
        max_button = QtGui.QPushButton(max_icon, "", self)
        max_button.clicked.connect(self.maximize)
        max_button.setGeometry(20, 0, 20, 20)
        max_button.raise_()

        self.closed = False
        CloseableDock.docklist.append(self)

    def close(self):
        self.setParent(None)
        self.closed = True
        if hasattr(self, '_container'):
            if self._container is not self.area.topContainer:
                self._container.apoptose()

    def maximize(self):
        for d in CloseableDock.docklist:
            if d is not self and not d.closed:
                d.close()

class CrosshairPlotWidget(pg.PlotWidget):
    def __init__(self, parametric=False, *args, **kwargs):
        super(CrosshairPlotWidget, self).__init__(*args, **kwargs)
        self.scene().sigMouseClicked.connect(self.toggle_search)
        self.scene().sigMouseMoved.connect(self.handle_mouse_move)
        self.cross_section_enabled = False
        self.parametric = parametric
        self.search_mode = True
        self.label = None

    def toggle_search(self, mouse_event):
        if mouse_event.double():
            if self.cross_section_enabled:
                self.hide_cross_hair()
            else:
                self.add_cross_hair()
        elif self.cross_section_enabled:
            self.search_mode = not self.search_mode
            if self.search_mode:
                self.handle_mouse_move(mouse_event.scenePos())

    def handle_mouse_move(self, mouse_event):
        if self.cross_section_enabled and self.search_mode:
            item = self.getPlotItem()
            vb = item.getViewBox()
            view_coords = vb.mapSceneToView(mouse_event)
            view_x, view_y = view_coords.x(), view_coords.y()

            best_guesses = []
            for data_item in item.items:
                if isinstance(data_item, pg.PlotDataItem):
                    xdata, ydata = data_item.xData, data_item.yData
                    index_distance = lambda i: (xdata[i]-view_x)**2 + (ydata[i] - view_y)**2
                    if self.parametric:
                        index = min(range(len(xdata)), key=index_distance)
                    else:
                        index = min(np.searchsorted(xdata, view_x), len(xdata)-1)
                        if index and xdata[index] - view_x > view_x - xdata[index - 1]:
                            index -= 1
                    pt_x, pt_y = xdata[index], ydata[index]
                    best_guesses.append(((pt_x, pt_y), index_distance(index)))

            if not best_guesses:
                return

            (pt_x, pt_y), _ = min(best_guesses, key=lambda x: x[1])
            self.v_line.setPos(pt_x)
            self.h_line.setPos(pt_y)
            self.label.setText("x=%.2e, y=%.2e" % (pt_x, pt_y))

    def add_cross_hair(self):
        self.h_line = pg.InfiniteLine(angle=0, movable=False)
        self.v_line = pg.InfiniteLine(angle=90, movable=False)
        self.addItem(self.h_line, ignoreBounds=False)
        self.addItem(self.v_line, ignoreBounds=False)
        if self.label is None:
            self.label = pg.LabelItem(justify="right")
            self.getPlotItem().layout.addItem(self.label, 4, 1)
        self.x_cross_index = 0
        self.y_cross_index = 0
        self.cross_section_enabled = True

    def hide_cross_hair(self):
        self.removeItem(self.h_line)
        self.removeItem(self.v_line)
        self.cross_section_enabled = False

class CrosshairDock(CloseableDock):
    def __init__(self, **kwargs):
        self.plot_widget = CrosshairPlotWidget()
        self.plot_widget.addLegend()
        kwargs['widget'] = self.plot_widget
        super(CrosshairDock, self).__init__(**kwargs)
        self.avail_colors = [(255,0,0), (0,0,255), (0,255,0), (255,255,255)]
        self.used_colors = {}
        self.curves = {}

    def plot(self, *args, **kwargs):
        self.plot_widget.parametric = kwargs.pop('parametric', False)
        name = kwargs.get('name', '')
        if name in self.curves:
            kwargs['pen'] = self.used_colors[name]
            self.curves[name].setData(*args, **kwargs)
        else:
            kwargs['pen'] = self.used_colors[name] = self.avail_colors.pop()
            self.curves[name] = self.plot_widget.plot(*args, **kwargs)

    def clear(self):
        self.plot_widget.clear()

    def get_data(self, label):
        if label in self.curves:
            return self.curves[label].getData()
        else:
            return [], []

    def redraw(self):
        xs_ys = []
        for name in self.curves:
            xs_ys.append((name,) + self.get_data(name))
        self.clear()
        for name, xs, ys in xs_ys:
            self.plot(xs, ys, name=name)

    def setTitle(self, text):
        self.plot_widget.setTitle(text)

class CrossSectionDock(CloseableDock):
    def __init__(self, trace_size=80, **kwargs):
        self.plot_item = view = pg.PlotItem(labels=kwargs.pop('labels', None))
        self.img_view = kwargs['widget'] = pg.ImageView(view=view)
        view.setAspectLocked(lock=False)
        self.ui = self.img_view.ui
        self.imageItem = self.img_view.imageItem
        super(CrossSectionDock, self).__init__(**kwargs)
        self.closeClicked.connect(self.hide_cross_section)
        self.cross_section_enabled = False
        self.search_mode = False
        self.signals_connected = False
        self.set_histogram(False)
        histogram_action = QtGui.QAction('Histogram', self)
        histogram_action.setCheckable(True)
        histogram_action.triggered.connect(self.set_histogram)
        self.img_view.scene.contextMenu.append(histogram_action)

        self.autolevels_action = QtGui.QAction('Autoscale Levels', self)
        self.autolevels_action.setCheckable(True)
        self.autolevels_action.setChecked(True)
        self.autolevels_action.triggered.connect(self.redraw)
        self.ui.histogram.item.sigLevelChangeFinished.connect(lambda: self.autolevels_action.setChecked(False))
        self.img_view.scene.contextMenu.append(self.autolevels_action)

        self.clear_action = QtGui.QAction('Clear Contents', self)
        self.clear_action.triggered.connect(self.clear)
        self.img_view.scene.contextMenu.append(self.clear_action)

        self.ui.histogram.gradient.loadPreset('thermal')
        try:
            self.connect_signal()
        except RuntimeError:
            warnings.warn('Scene not set up, cross section signals not connected')

        self.y_cross_index = 0
        self.h_cross_section_widget = CrosshairPlotWidget()
        self.h_cross_dock = CloseableDock(name='x trace', widget=self.h_cross_section_widget, area=self.area)
        self.h_cross_section_widget.add_cross_hair()
        self.h_cross_section_widget.search_mode = False
        self.h_cross_section_widget_data = self.h_cross_section_widget.plot([0,0])

        self.x_cross_index = 0
        self.v_cross_section_widget = CrosshairPlotWidget()
        self.v_cross_dock = CloseableDock(name='y trace', widget=self.v_cross_section_widget, area=self.area)
        self.v_cross_section_widget.add_cross_hair()
        self.v_cross_section_widget.search_mode = False
        self.v_cross_section_widget_data = self.v_cross_section_widget.plot([0,0])

    def setLabels(self, xlabel="X", ylabel="Y", zlabel="Z"):
        print self.h_cross_dock.label
        self.plot_item.setLabels(bottom=(xlabel,), left=(ylabel,))
        self.h_cross_section_widget.plotItem.setLabels(bottom=xlabel, left=zlabel)
        self.v_cross_section_widget.plotItem.setLabels(bottom=ylabel, left=zlabel)
        self.ui.histogram.item.axis.setLabel(text=zlabel)

    def setImage(self, *args, **kwargs):
        if 'pos' in kwargs:
            self._x0, self._y0 = kwargs['pos']
        else:
            self._x0, self._y0 = 0, 0
        if 'scale' in kwargs:
            self._xscale, self._yscale = kwargs['scale']
        else:
            self._xscale, self._yscale = 1, 1

        autorange = self.img_view.getView().vb.autoRangeEnabled()[0]
        kwargs['autoRange'] = autorange
        self.img_view.setImage(*args, **kwargs)
        self.img_view.getView().vb.enableAutoRange(enable=autorange)

        self.update_cross_section()

    def setTitle(self, text):
        self.plot_item.setTitle(text)

    def redraw(self):
        self.setImage(self.img_view.imageItem.image)

    def get_data(self):
        img = self.img_view.imageItem.image
        if img is not None and img.shape != (1, 1):
            return img
        else:
            return None

    def clear(self):
        self.img_view.setImage(np.array([[0]]))
        self.plot_item.enableAutoRange()

    def toggle_cross_section(self):
        if self.cross_section_enabled:
            self.hide_cross_section()
        else:
            self.add_cross_section()

    def set_histogram(self, visible):
        self.ui.histogram.setVisible(visible)
        self.ui.roiBtn.setVisible(visible)
        self.ui.normGroup.setVisible(visible)
        self.ui.menuBtn.setVisible(visible)

    def add_cross_section(self):
        if self.imageItem.image is not None:
            (min_x, max_x), (min_y, max_y) = self.imageItem.getViewBox().viewRange()
            mid_x, mid_y = (max_x + min_x)/2., (max_y + min_y)/2.
        else:
            mid_x, mid_y = 0, 0
        self.h_line = pg.InfiniteLine(pos=mid_y, angle=0, movable=False)
        self.v_line = pg.InfiniteLine(pos=mid_x, angle=90, movable=False)
        self.plot_item.addItem(self.h_line, ignoreBounds=False)
        self.plot_item.addItem(self.v_line, ignoreBounds=False)
        self.x_cross_index = 0
        self.y_cross_index = 0
        self.cross_section_enabled = True
        self.text_item = pg.LabelItem(justify="right")
        #self.img_view.ui.gridLayout.addWidget(self.text_item, 2, 1, 1, 2)
        #self.img_view.ui.graphicsView.addItem(self.text_item)#, 2, 1)
        self.plot_item.layout.addItem(self.text_item, 4, 1)
        #self.cs_layout.addItem(self.label, 2, 1) #TODO: Find a way of displaying this label
        self.search_mode = True

        self.area.addDock(self.h_cross_dock)
        self.area.addDock(self.v_cross_dock, position='right', relativeTo=self.h_cross_dock)
        self.cross_section_enabled = True

    def hide_cross_section(self):
        if self.cross_section_enabled:
            self.plot_item.removeItem(self.h_line)
            self.plot_item.removeItem(self.v_line)
            self.img_view.ui.graphicsView.removeItem(self.text_item)
            self.cross_section_enabled = False

            self.h_cross_dock.close()
            self.v_cross_dock.close()

    def connect_signal(self):
        """This can only be run after the item has been embedded in a scene"""
        if self.signals_connected:
            warnings.warn("")
        if self.imageItem.scene() is None:
            raise RuntimeError('Signal can only be connected after it has been embedded in a scene.')
        self.imageItem.scene().sigMouseClicked.connect(self.toggle_search)
        self.imageItem.scene().sigMouseMoved.connect(self.handle_mouse_move)
        self.img_view.timeLine.sigPositionChanged.connect(self.update_cross_section)
        self.signals_connected = True

    def toggle_search(self, mouse_event):
        if mouse_event.double():
            self.toggle_cross_section()
        elif self.cross_section_enabled:
            self.search_mode = not self.search_mode
            if self.search_mode:
                self.handle_mouse_move(mouse_event.scenePos())

    def handle_mouse_move(self, mouse_event):
        if self.cross_section_enabled and self.search_mode:
            view_coords = self.imageItem.getViewBox().mapSceneToView(mouse_event)
            view_x, view_y = view_coords.x(), view_coords.y()
            item_coords = self.imageItem.mapFromScene(mouse_event)
            item_x, item_y = item_coords.x(), item_coords.y()
            max_x, max_y = self.imageItem.image.shape
            if item_x < 0 or item_x > max_x or item_y < 0 or item_y > max_y:
                return
            self.v_line.setPos(view_x)
            self.h_line.setPos(view_y)
            #(min_view_x, max_view_x), (min_view_y, max_view_y) = self.imageItem.getViewBox().viewRange()
            self.x_cross_index = max(min(int(item_x), max_x-1), 0)
            self.y_cross_index = max(min(int(item_y), max_y-1), 0)
            z_val = self.imageItem.image[self.x_cross_index, self.y_cross_index]
            self.update_cross_section()
            self.text_item.setText("x=%.2e, y=%.2e, z=%.2e" % (view_x, view_y, z_val))

    def update_cross_section(self):
        nx, ny = self.imageItem.image.shape
        x0, y0, xscale, yscale = self._x0, self._y0, self._xscale, self._yscale
        xdata = np.linspace(x0, x0+(xscale*(nx-1)), nx)
        ydata = np.linspace(y0, y0+(yscale*(ny-1)), ny)
        zval = self.imageItem.image[self.x_cross_index, self.y_cross_index]
        self.h_cross_section_widget_data.setData(xdata, self.imageItem.image[:, self.y_cross_index])
        self.h_cross_section_widget.v_line.setPos(xdata[self.x_cross_index])
        self.h_cross_section_widget.h_line.setPos(zval)
        self.v_cross_section_widget_data.setData(ydata, self.imageItem.image[self.x_cross_index, :])
        self.v_cross_section_widget.v_line.setPos(ydata[self.y_cross_index])
        self.v_cross_section_widget.h_line.setPos(zval)

class MoviePlotDock(CrossSectionDock):
    def __init__(self, array, *args, **kwargs):
        super(MoviePlotDock, self).__init__(*args, **kwargs)
        self.setImage(array)
        self.tpts = len(array)
        play_button = QtGui.QPushButton("Play")
        stop_button = QtGui.QPushButton("Stop")
        stop_button.hide()
        self.addWidget(play_button)
        self.addWidget(stop_button)
        self.play_timer = QtCore.QTimer()
        self.play_timer.setInterval(50)
        self.play_timer.timeout.connect(self.increment)
        play_button.clicked.connect(self.play_timer.start)
        play_button.clicked.connect(play_button.hide)
        play_button.clicked.connect(stop_button.show)
        stop_button.clicked.connect(self.play_timer.stop)
        stop_button.clicked.connect(play_button.show)
        stop_button.clicked.connect(stop_button.hide)

    def increment(self):
        self.img_view.setCurrentIndex((self.img_view.currentIndex + 1) % self.tpts)

