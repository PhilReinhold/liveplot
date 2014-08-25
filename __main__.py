import sys

from PyQt4.QtGui import QApplication

from window import MainWindow


app = QApplication([])
win = MainWindow()
win.show()
sys.exit(app.exec_())