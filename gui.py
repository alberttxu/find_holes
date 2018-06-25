#!/usr/bin/env python3
import sys
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtWidgets import (QApplication, QWidget, QMainWindow, QAction,
                             QHBoxLayout, QVBoxLayout, QGridLayout,
                             QLabel, QScrollArea, QPushButton, QFileDialog,
                             QCheckBox, QSlider, QLineEdit, QRubberBand)
from PyQt5.QtGui import QPixmap, QKeySequence
from search import find_holes


class ImageViewer(QScrollArea):

    def __init__(self, filename=''):
        super().__init__()
        self.initUI(filename)

    def initUI(self, filename):
        self.zoomScale = 1
        self.pixmap = QPixmap(filename)
        self.originalCopy = self.pixmap
        self.currCopy = self.pixmap
        # QPixmap needs label to resize
        self.label = QLabel(self)
        self.label.setPixmap(self.pixmap)
        self.label.resize(self.label.sizeHint())
        self.setWidget(self.label)

    def loadPicture(self, img, fromMenu=True):
        self.zoomScale = 1
        if type(img) == str:
            self.pixmap.load(img)
        elif type(img) == QPixmap:
            self.pixmap = img
        else:
            raise TypeError("ImageViewer can't load img of type %s" % type(img))
        # original copy for scaling & cropping
        if fromMenu:
            self.originalCopy = self.pixmap
        self.currCopy = self.pixmap
        self.label.setPixmap(self.pixmap)
        self.label.resize(self.pixmap.size())

    def _refresh(self): # used in zoomIn/Out
        self.pixmap = self.currCopy.scaled(
                                     self.zoomScale * self.currCopy.size(),
                                     aspectRatioMode=Qt.KeepAspectRatio)
        self.label.setPixmap(self.pixmap)
        self.label.resize(self.pixmap.size())

    def zoomIn(self):
        self.zoomScale += 0.1
        self._refresh()

    def zoomOut(self):
        self.zoomScale -= 0.1
        self._refresh()


class ImageViewerCrop(ImageViewer):

    def __init__(self, filename=''):
        super().__init__(filename)

    def mousePressEvent(self, eventQMouseEvent):
        self.originQPoint = eventQMouseEvent.pos()
        self.rband = QRubberBand(QRubberBand.Rectangle, self)
        self.rband.setGeometry(QRect(self.originQPoint, QSize()))
        self.rband.show()

    def mouseMoveEvent(self, eventQMouseEvent):
        # unnormalized QRect can have negative width/height
        self.rband.setGeometry(
                            QRect(2*self.originQPoint - eventQMouseEvent.pos(),
                                  eventQMouseEvent.pos()).normalized())

    def mouseReleaseEvent(self, eventQMouseEvent):
        self.rband.hide()
        currentQRect = self.rband.geometry()
        # calculate X and Y position in original image
        X = self.horizontalScrollBar().value() + currentQRect.x()
        X = int(X / self.zoomScale)
        Y = self.verticalScrollBar().value() + currentQRect.y()
        Y = int(Y / self.zoomScale)
        origScaleCropWidth = int(currentQRect.width() / self.zoomScale)
        origScaleCropHeight = int(currentQRect.height() / self.zoomScale)
        # save crop
        cropQPixmap = self.originalCopy.copy(QRect(X, Y, origScaleCropWidth,
                                                         origScaleCropHeight))
        self.parentWidget().sidebar.crop_template.loadPicture(cropQPixmap)


class Sidebar(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.width = 230
        self.setFixedWidth(self.width)

        # widgets
        self.crop_template = ImageViewer()
        self.crop_template.setFixedHeight(200)
        cbBlurTemp = QCheckBox('Blur template')
        cbBlurImg  = QCheckBox('Blur image')
        buttonAutoDoc = QPushButton('Generate autodoc file')
        buttonAutoDoc.resize(buttonAutoDoc.sizeHint())
        buttonPrintCoord = QPushButton('Print Coordinates')
        buttonPrintCoord.resize(buttonPrintCoord.sizeHint())
        self.slider = QSlider(Qt.Horizontal)
        self.sldPrec = 3
        self.slider.setMaximum(10**self.sldPrec)
        self.slider.valueChanged.connect(self._setThreshDisp)
        self.threshDisp = QLineEdit()
        self.threshDisp.returnPressed.connect(
                          lambda: self._setSliderValue(self.threshDisp.text()))
        buttonSearch = QPushButton('Search')
        buttonSearch.clicked.connect(self.matchTemplate)

        # layout
        vlay = QVBoxLayout()
        vlay.addWidget(self.crop_template)
        vlay.addWidget(cbBlurTemp)
        vlay.addWidget(cbBlurImg)
        vlay.addWidget(QLabel())
        vlay.addWidget(QLabel('Threshold'))
        threshold = QGridLayout()
        threshold.addWidget(self.slider, 0, 0, 1, 1)
        threshold.addWidget(self.threshDisp, 1, 0, 1, 1)
        threshold.addWidget(buttonSearch)
        threshold.addWidget(QLabel())
        vlay.addLayout(threshold)
        vlay.addWidget(buttonAutoDoc)
        vlay.addWidget(buttonPrintCoord)
        vlay.addStretch(1)
        self.setLayout(vlay)

    def _setThreshDisp(self, i: int):
        self.threshDisp.setText("{:.{}f}".format(i / 10**self.sldPrec,
                                                 self.sldPrec))

    def _setSliderValue(self, s: str):
        try:
            self.slider.setValue(int(10**self.sldPrec * float(s)))
        except ValueError:
            pass

    def matchTemplate(self):
        print(self.crop_template.pixmap.size())
        coords, qpixmap = find_holes(self.parentWidget().viewer.originalCopy,
                                    self.crop_template.pixmap)
        print(coords)
        self.parentWidget().viewer.loadPicture(qpixmap, fromMenu=False)


class MainWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.sidebar = Sidebar()
        self.viewer = ImageViewerCrop()

        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.addWidget(self.sidebar, 1, 0, 1, 1)
        self.grid.addWidget(self.viewer, 1, 1, 5, 5)
        self.setLayout(self.grid)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.root = MainWidget()
        self.setCentralWidget(self.root)
        self.statusBar()
        self.initUI()

    def initUI(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        viewMenu = menubar.addMenu('View')

        openFile = QAction("Open File", self)
        openFile.setShortcut("Ctrl+O")
        openFile.setStatusTip("Open new File")
        openFile.triggered.connect(self.openFileDialog)
        fileMenu.addAction(openFile)

        zoomIn = QAction("Zoom In", self)
        zoomIn.setShortcut(Qt.Key_Equal)
        zoomIn.triggered.connect(self.root.viewer.zoomIn)
        zoomOut = QAction("Zoom Out", self)
        zoomOut.setShortcut(Qt.Key_Minus)
        zoomOut.triggered.connect(self.root.viewer.zoomOut)
        viewMenu.addAction(zoomIn)
        viewMenu.addAction(zoomOut)

        self.setGeometry(300, 300, 1000, 1000)
        self.setWindowTitle('Title')
        self.show()

    def openFileDialog(self):
        filename = QFileDialog.getOpenFileName(self, 'Open File')[0]

        print(filename)
        if filename:
            self.root.viewer.loadPicture(filename)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
