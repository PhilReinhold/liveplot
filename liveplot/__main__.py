from PyQt4.QtGui import QApplication
from window import MainWindow
import sys

app = QApplication([])
win = MainWindow()
win.show()
sys.exit(app.exec_())