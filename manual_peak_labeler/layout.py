#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from pyqtgraph          import LayoutWidget, ImageView, PlotItem, ImageItem, ViewBox
from pyqtgraph.Qt       import QtWidgets
from pyqtgraph.dockarea import DockArea, Dock

class MainLayout(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.area      = DockArea()
        self.dock_dict = self.config_dock()

        self.btn_prev_img, self.btn_next_img = self.config_button_img()

        # Update images in child's class
        self.viewer_img = self.config_image()

        ## self.graphview  = self.config_graphview()

        return None


    def config_dock(self):
        # Define Docks in main window...
        setup_dict = {
            "ImgQry"       : (500, 300),
            "ImgQryButton" : (1, 1),
        }

        # Instantiate docks...
        dock_dict = {}
        for k, v in setup_dict.items(): dock_dict[k] = Dock(k, size = v)

        # Config layout...
        self.area.addDock(dock_dict["ImgQry"]      , "left")
        self.area.addDock(dock_dict["ImgQryButton"], "bottom", dock_dict["ImgQry"])

        # Hide titles...
        for v in dock_dict.values(): v.hideTitleBar()

        return dock_dict


    def config_status_img(self):
        # Biolerplate code to start widget config
        wdgt = LayoutWidget()

        # Set up label...
        label = QtWidgets.QLabel("XXXX")

        wdgt.addWidget(label, row = 0, col = 0)
        self.dock_dict["ImgQryStatus"].addWidget(wdgt)

        return label


    def config_button_img(self):
        ''' Dock of ImgQry displays one image, three buttons, and one status.
        '''
        # Biolerplate code to start widget config
        wdgt = LayoutWidget()

        # Set up buttons...
        btn_prev  = QtWidgets.QPushButton('Prev')
        btn_next  = QtWidgets.QPushButton('Next')

        wdgt.addWidget(btn_prev , row = 0, col = 0)
        wdgt.addWidget(btn_next , row = 0, col = 1)

        self.dock_dict["ImgQryButton"].addWidget(wdgt)

        return btn_prev, btn_next


    def config_image(self):
        ''' Display image.
        '''
        # Biolerplate code to start widget config
        wdgt = ImageView(view = PlotItem())

        self.dock_dict["ImgQry"].addWidget(wdgt)

        return wdgt
