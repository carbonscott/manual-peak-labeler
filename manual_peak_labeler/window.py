#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import pickle
import numpy as np

from .utils import hex_to_rgb

import pyqtgraph as pg

from pyqtgraph    import LabelItem, ImageItem, SignalProxy, PolyLineROI, GraphicsLayoutWidget
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

class Window(QtWidgets.QMainWindow):
    def __init__(self, layout, data_manager):
        super().__init__()

        self.createAction()
        self.createMenuBar()
        self.connectAction()

        self.layout       = layout
        self.data_manager = data_manager

        self.timestamp = self.data_manager.timestamp
        self.username  = self.data_manager.username

        self.num_img = len(self.data_manager.idx_list)

        self.idx_img = 0

        self.setupButtonFunction()
        self.setupButtonShortcut()
        self.setupShortcut()

        self.two_click_pos_list = []
        self.pen_click_pos_list = []
        self.img   = None
        self.label = None
        self.unsaved_label = {}

        self.uses_roi_eraser = False
        self.label_item = ImageItem(None)
        self.roi_item   = PolyLineROI(self.pen_click_pos_list, closed=True)
        self.layout.viewer_img.getView().addItem(self.label_item)
        self.layout.viewer_img.getView().addItem(self.roi_item)

        self.layer_panel = { 'wgt' : None, 'panel' : None }

        self.requires_overlay = True
        self.uses_auto_range = True

        self.proxy_click = None
        self.proxy_moved = None

        self.fetchMousePosition()

        self.dispImg()

        return None


    def closeEvent(self, event):
        QtWidgets.QApplication.closeAllWindows()
        event.accept()


    def setupShortcut(self):
        QtWidgets.QShortcut(QtCore.Qt.Key_R    , self, self.selectActiveLayerDialog)
        QtWidgets.QShortcut(QtCore.Qt.Key_V    , self, self.showLayerPanel)
        QtWidgets.QShortcut(QtCore.Qt.Key_D    , self, self.switchToROILabelMode)
        QtWidgets.QShortcut(QtCore.Qt.Key_E    , self, self.switchToROIEraserMode)
        QtWidgets.QShortcut(QtCore.Qt.Key_Z    , self, self.undoPrevNode)
        QtWidgets.QShortcut(QtCore.Qt.Key_C    , self, self.connectNodes)
        QtWidgets.QShortcut(QtCore.Qt.Key_F    , self, self.switchToPointLabelMode)
        QtWidgets.QShortcut(QtCore.Qt.Key_B    , self, self.switchToRecLabelMode)
        QtWidgets.QShortcut(QtCore.Qt.Key_Space, self, self.switchOffMouseMode)
        QtWidgets.QShortcut(QtCore.Qt.Key_S    , self, self.switchOffOverlay)
        QtWidgets.QShortcut(QtCore.Qt.Key_A    , self, self.resetRange)
        QtWidgets.QShortcut(QtCore.Qt.Key_T    , self, self.toggleAutoRange)


    def showLayerPanel(self):
        if self.layer_panel['wgt'] is None:
            wgt = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout()

            # Add the tree widget to the new window
            tree = pg.DataTreeWidget()
            layout.addWidget(tree)

            self.layer_panel['wgt'] = wgt
            self.layer_panel['panel'] = tree

            wgt.setLayout(layout)
            wgt.resize(600, 600)

        layer_metadata = self.data_manager.layer_manager['layer_metadata']
        self.layer_panel['panel'].setData(layer_metadata)

        iterator = QtWidgets.QTreeWidgetItemIterator(self.layer_panel['panel'])
        while iterator.value():
            item = iterator.value()
            key   = item.text(0)
            value = item.text(2)
            if key == 'color': item.setBackground(2, QtGui.QColor(value))
            iterator += 1

        self.layer_panel['wgt'].show()


    def resetRange(self):
        self.dispImg(requires_refresh_img = True, requires_refresh_layers = False)


    def toggleAutoRange(self):
        self.uses_auto_range = not self.uses_auto_range
        print(f"Auto range: {self.uses_auto_range}")


    def switchOffOverlay(self):
        if self.requires_overlay:
            # Overlay label...
            label = self.label
            empty_mask = np.zeros(label.shape[-2:] + (4, ), dtype = 'uint8')
            self.label_item.setImage(empty_mask, levels = [0, 128])
            self.requires_overlay = False
        else:
            self.dispImg(requires_refresh_img = False)
            self.requires_overlay = True


    def fetchMousePosition(self):
        self.proxy_moved = SignalProxy(self.layout.viewer_img.getView().scene().sigMouseMoved, rateLimit = 30, slot = self.mouseMovedToDisplayPosition)


    def mouseMovedToDisplayPosition(self, event):
        if self.layout.viewer_img.getView().sceneBoundingRect().contains(event[0]):
            mouse_pos = self.layout.viewer_img.getView().vb.mapSceneToView(event[0])

            x_pos = mouse_pos.x()
            y_pos = mouse_pos.y()
            x = int(x_pos)
            y = int(y_pos)

            img = self.img[0]

            size_x, size_y = img.shape
            x = min(max(x, 0), size_x - 1)
            y = min(max(y, 0), size_y - 1)

            self.layout.viewer_img.getView().setTitle(f"Sequence number: {self.idx_img}/{self.num_img - 1}  |  ({x_pos:6.2f}, {y_pos:6.2f}, {img[x, y]:12.6f})")


    def switchOffMouseMode(self):
        self.proxy_click = None


    def switchToPointLabelMode(self):
        self.proxy_click = SignalProxy(self.layout.viewer_img.getView().scene().sigMouseClicked, slot = self.mouseClickedToLabel)


    def switchToRecLabelMode(self):
        self.proxy_click = SignalProxy(self.layout.viewer_img.getView().scene().sigMouseClicked, slot = self.mouseClickedToLabelRange)


    def switchToROILabelMode(self):
        ## self.roi_code = 1
        self.uses_roi_eraser = False    # [COMPRIMISED SOLUION]
        self.proxy_click = SignalProxy(self.layout.viewer_img.getView().scene().sigMouseClicked, slot = self.mouseClickedToLabelROI)


    def switchToROIEraserMode(self):
        self.uses_roi_eraser = True
        self.proxy_click = SignalProxy(self.layout.viewer_img.getView().scene().sigMouseClicked, slot = self.mouseClickedToLabelROI)


    def mouseClickedToLabel(self, event):
        mouse_pos = self.layout.viewer_img.getView().vb.mapSceneToView(event[0].scenePos())

        x = int(mouse_pos.x())
        y = int(mouse_pos.y())

        label = self.label    # (1, H, W)
        layer_active = self.data_manager.layer_manager['layer_active']
        size_x, size_y = label.shape[-2:]
        if x < size_x and y < size_y:
            label[0, x, y] = 0 if label[0, x, y] == layer_active else layer_active

        self.dispImg(requires_refresh_img = False, requires_refresh_layers = True)


    def mouseClickedToLabelRange(self, event):
        mouse_pos = self.layout.viewer_img.getView().vb.mapSceneToView(event[0].scenePos())

        x = int(mouse_pos.x())
        y = int(mouse_pos.y())

        self.two_click_pos_list.append((x, y))

        if len(self.two_click_pos_list) == 2:
            (x_0, y_0), (x_1, y_1) = self.two_click_pos_list

            label = self.label    # (1, H, W)
            layer_active = self.data_manager.layer_manager['layer_active']
            size_x, size_y = label.shape[-2:]

            x_0 = min(max(x_0, 0), size_x - 1)
            x_1 = min(max(x_1, 0), size_x - 1)
            y_0 = min(max(y_0, 0), size_y - 1)
            y_1 = min(max(y_1, 0), size_y - 1)

            x_b, x_e = sorted([x_0, x_1])
            y_b, y_e = sorted([y_0, y_1])

            label_selected    = label[0, x_b:x_e+1, y_b:y_e+1]
            label_selected[:] = layer_active if np.all(label_selected == 0) == True else 0
            label[0, x_b:x_e+1, y_b:y_e+1] = label_selected

            self.dispImg(requires_refresh_img = False, requires_refresh_layers = True)
            self.two_click_pos_list = []


    def mouseClickedToLabelROI(self, event):
        mouse_pos = self.layout.viewer_img.getView().vb.mapSceneToView(event[0].scenePos())

        x = mouse_pos.x()
        y = mouse_pos.y()

        self.pen_click_pos_list.append((x, y))

        if len(self.pen_click_pos_list) > 0:
            self.layout.viewer_img.getView().removeItem(self.roi_item)
            self.roi_item = PolyLineROI(self.pen_click_pos_list, closed=False)
            self.layout.viewer_img.getView().addItem(self.roi_item)


    def undoPrevNode(self):
        if len(self.pen_click_pos_list) > 0: _ = self.pen_click_pos_list.pop()

        self.layout.viewer_img.getView().removeItem(self.roi_item)
        self.roi_item = PolyLineROI(self.pen_click_pos_list, closed=False)
        self.layout.viewer_img.getView().addItem(self.roi_item)


    def connectNodes(self):
        if len(self.pen_click_pos_list) < 3: 
            self.pen_click_pos_list = []
            return None

        # Connect the starting and end nodes...
        self.pen_click_pos_list.append(self.pen_click_pos_list[0])

        # Plot the polygon again...
        self.layout.viewer_img.getView().removeItem(self.roi_item)
        self.roi_item = PolyLineROI(self.pen_click_pos_list, closed=False)
        self.layout.viewer_img.getView().addItem(self.roi_item)

        # Fetch image, label and mask...
        label = self.label
        layer_active = self.data_manager.layer_manager['layer_active']

        # Fetch the right ROI...
        # Shape: (1, H, W);  Value: integers

        # Find the values and coordinates of the ROI...
        # mask is an array of 0 or 1
        canvas = np.ones(label.shape[-2:], dtype = 'int8')
        roi_patch, coords = self.roi_item.getArrayRegion(canvas, self.layout.viewer_img.getImageItem(), returnMappedCoords = True)
        roi_patch = roi_patch.astype(bool)

        ## from PyQt5.QtCore import pyqtRemoveInputHook, pyqtRestoreInputHook
        ## pyqtRemoveInputHook()
        ## ## pyqtRequestInputHook()  # Restore
        ## import pdb; pdb.set_trace()

        # Assign bool values to the ROI area of the label...
        # Shape of coords: (2, H_patch, W_patch)
        idx_y, idx_x = coords
        idx_y -= 0.5
        idx_x -= 0.5
        idx_y, idx_x = np.round(coords).astype(int)

        size_y, size_x = label.shape[-2:]
        idx_y = np.minimum(np.maximum(idx_y, 0), size_y - 1)
        idx_x = np.minimum(np.maximum(idx_x, 0), size_x - 1)

        # !!! FUTURE IDEA !!! 
        # Use the 0th-dim for saving multiple labels
        ## roi[0][idx_y, idx_x] = np.logical_or (roi[0][idx_y, idx_x], layer_active * roi_patch) if not self.uses_roi_eraser else \
        ##                        np.logical_and(roi[0][idx_y, idx_x], 1 - roi_patch)
        ## label[0][idx_y, idx_x] = layer_active

        label_patch = label[0][idx_y, idx_x]
        label_patch[roi_patch] = layer_active if not self.uses_roi_eraser else 0
        label[0][idx_y, idx_x] = label_patch

        self.dispImg(requires_refresh_img = False, requires_refresh_layers = True)

        self.layout.viewer_img.getView().removeItem(self.roi_item)
        self.pen_click_pos_list = []


    def config(self):
        self.setCentralWidget(self.layout.area)
        self.resize(700, 700)
        self.setWindowTitle(f"X-ray Diffraction Image Labeler")

        return None


    def setupButtonFunction(self):
        self.layout.btn_next_img.clicked.connect(self.nextImg)
        self.layout.btn_prev_img.clicked.connect(self.prevImg)

        return None


    def setupButtonShortcut(self):
        # w/ buttons
        self.layout.btn_next_img.setShortcut("N")
        self.layout.btn_prev_img.setShortcut("P")

        # w/o buttons
        QtWidgets.QShortcut(QtCore.Qt.Key_G, self, self.goEventDialog)

        return None


    ###############
    ### DIPSLAY ###
    ###############
    def refresh_layers(self):
        # Turn label into a layer of shape (1, H, W, 4)...
        # The type is uint8 for pyqt visualization purpose
        label  = self.label
        layers = np.zeros(label.shape + (4, ), dtype = 'uint8')

        # Color them based on layer encoding in the layer metadata...
        for encode in self.data_manager.layer_manager['layer_order']:
            metadata = self.data_manager.layer_manager['layer_metadata'][encode]
            color_hex = metadata['color']

            if color_hex == '#FFFFFF': continue

            r, g, b = hex_to_rgb(color_hex)

            layers[:, :, :, 0][label == encode] = r
            layers[:, :, :, 1][label == encode] = g
            layers[:, :, :, 2][label == encode] = b
            layers[:, :, :, 3][label == encode] = 100

        self.label_item.setImage(layers[0], levels = [0, 128])


    def dispImg(self, requires_refresh_img = True, requires_refresh_layers = True):
        # Let idx_img bound within reasonable range....
        self.idx_img = min(max(0, self.idx_img), self.num_img - 1)

        img, label = self.data_manager.get_img(self.idx_img)
        self.img = img
        self.label = label

        vmin = np.mean(img)
        vmax = vmin + 8 * np.std(img)
        ## print(vmin, vmax)
        levels = [vmin, vmax]

        if requires_refresh_img:
            # Display images...
            self.layout.viewer_img.setImage(img[0], levels = levels, autoRange = self.uses_auto_range)

        if requires_refresh_layers: self.refresh_layers()

        # Display title...
        self.layout.viewer_img.getView().setTitle(f"Sequence number: {self.idx_img}/{self.num_img - 1}")

        return None


    ##################
    ### NAVIGATION ###
    ##################
    def nextImg(self):
        # Support rollover...
        idx_next = self.idx_img + 1
        self.idx_img = idx_next if idx_next < self.num_img else 0

        self.dispImg()

        return None


    def prevImg(self):
        idx_img_current = self.idx_img

        # Support rollover...
        idx_prev = self.idx_img - 1
        self.idx_img = idx_prev if -1 < idx_prev else self.num_img - 1

        # Update image only when next/prev event is found???
        if idx_img_current != self.idx_img:
            self.dispImg()

        return None


    ################
    ### MENU BAR ###
    ################
    def saveStateDialog(self):
        path_pickle, is_ok = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File', f'{self.timestamp}.pickle')

        if is_ok:
            obj_to_save = ( self.data_manager.layer_manager,
                            self.data_manager.state_random,
                            self.idx_img,
                            self.timestamp )

            with open(path_pickle, 'wb') as fh:
                pickle.dump(obj_to_save, fh, protocol = pickle.HIGHEST_PROTOCOL)

            print(f"{path_pickle} saved")

        return None


    def loadStateDialog(self):
        path_pickle = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File')[0]

        if os.path.exists(path_pickle):
            with open(path_pickle, 'rb') as fh:
                obj_saved = pickle.load(fh)
                self.data_manager.layer_manager = obj_saved[0]
                self.data_manager.state_random  = obj_saved[1]
                self.idx_img                    = obj_saved[2]
                self.timestamp                  = obj_saved[3]

            self.dispImg()
            self.num_img = len(self.data_manager.idx_list)

        return None


    # [DEV]
    def saveDataDialog(self):

        is_confirmed = QtWidgets.QMessageBox.question(
            self,
            "Save Segmask",
            "Are you sure you want to save the label to cxi?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if is_confirmed == QtWidgets.QMessageBox.Yes:
            self.data_manager.save_buffered_segmask()
            self.dispImg()

        return None


    def selectActiveLayerDialog(self):
        idx, is_ok = QtWidgets.QInputDialog.getText(self, "Activate label", "Activate label")

        if is_ok and int(idx) in self.data_manager.layer_manager['layer_metadata']:
            self.data_manager.layer_manager['layer_active']= int(idx)

        return None


    def goEventDialog(self):
        idx, is_ok = QtWidgets.QInputDialog.getText(self, "Enter the event number to go", "Enter the event number to go")

        if is_ok:
            self.idx_img = int(idx)

            # Bound idx within a reasonable range
            self.idx_img = min(max(0, self.idx_img), self.num_img - 1)

            self.dispImg()

        return None


    def createMenuBar(self):
        menuBar = self.menuBar()

        # File menu
        fileMenu = QtWidgets.QMenu("&File", self)
        menuBar.addMenu(fileMenu)

        fileMenu.addAction(self.loadAction)
        fileMenu.addAction(self.saveAction)
        ## fileMenu.addAction(self.loadDataAction)
        fileMenu.addAction(self.saveDataAction)

        # Go menu
        goMenu = QtWidgets.QMenu("&Go", self)
        menuBar.addMenu(goMenu)

        goMenu.addAction(self.goAction)

        return None


    def createAction(self):
        self.loadAction = QtWidgets.QAction(self)
        self.loadAction.setText("&Load State")

        self.saveAction = QtWidgets.QAction(self)
        self.saveAction.setText("&Save State")

        self.loadDataAction = QtWidgets.QAction(self)
        self.loadDataAction.setText("&Load Data")

        self.saveDataAction = QtWidgets.QAction(self)
        self.saveDataAction.setText("&Save Segmask")

        self.goAction = QtWidgets.QAction(self)
        self.goAction.setText("&Event")

        return None


    def connectAction(self):
        self.loadAction.triggered.connect(self.loadStateDialog)
        self.saveAction.triggered.connect(self.saveStateDialog)
        ## self.loadDataAction.triggered.connect(self.loadDataDialog)
        self.saveDataAction.triggered.connect(self.saveDataDialog)

        self.goAction.triggered.connect(self.goEventDialog)

        return None
