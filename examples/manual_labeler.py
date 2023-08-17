#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from pyqtgraph.Qt import QtWidgets

from manual_peak_labeler.layout import MainLayout
from manual_peak_labeler.window import Window
from manual_peak_labeler.data   import PeakNetData

import socket

def run(config_data):
    # Main event loop
    app = QtWidgets.QApplication([])

    # Layout
    layout = MainLayout()

    # Data
    with PeakNetData(config_data) as data_manager:
        # Window
        win = Window(layout, data_manager)
        win.config()
        win.show()

        sys.exit(app.exec_())


class ConfigData:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        for k, v in kwargs.items(): setattr(self, k, v)

config_data = ConfigData( path_yaml = "/reg/data/ana03/scratch/cwang31/pf/manual_label.cxic00318_run0123.yaml",
                          username  = os.environ.get('USER'),
                          seed      = 0, )

run(config_data)
