#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import h5py
import yaml
import numpy as np
import random
from datetime import datetime

from .utils  import set_seed, apply_mask

class DataManager:
    def __init__(self):
        super().__init__()

        # Internal variables...
        self.img_state_dict = {}

        self.timestamp = self.get_timestamp()

        self.state_random = [random.getstate(), np.random.get_state()]

        return None


    def get_timestamp(self):
        now = datetime.now()
        timestamp = now.strftime("%Y_%m%d_%H%M_%S")

        return timestamp


    def save_random_state(self):
        self.state_random = (random.getstate(), np.random.get_state())

        return None


    def set_random_state(self):
        state_random, state_numpy = self.state_random
        random.setstate(state_random)
        np.random.set_state(state_numpy)

        return None




class PeakNetData(DataManager):
    """
    [DRAFT]
    PeakNet Data (PND) are produced by PeakNet by converting peak information
    in stream files into a tensor/ndarray.

    Tensor shape: (N, 2, H, W)
    - N: The number of data points that have been selected.
    - 2: It refers to a pair of an image and its corresponding label.
    - H, W: The height and width of both the image and its corresponding label.  

    Main tasks of this class:
    - Offers `get_img` function that returns a data point tensor with the shape
      (2, H, W).
    - Offers an interface that allows users to modify the label tensor with the
      shape (1, H, W).  The label tensor only supports integer type.

    YAML
    - CXI 0
      - EVENT 0
      - EVENT 1
    - CXI 1
      - EVENT 0
      - EVENT 1
    """

    def __init__(self, config_data):
        super().__init__()

        # Imported variables...
        self.path_yaml     = getattr(config_data, 'path_yaml'    , None)
        self.username      = getattr(config_data, 'username'     , None)
        self.seed          = getattr(config_data, 'seed'         , None)
        self.layer_manager = getattr(config_data, 'layer_manager', None)

        if self.layer_manager is None:
            layer_metadata = {
                0 : {'name' : 'background' , 'color' : '#FFFFFF'},
                1 : {'name' : 'peak'       , 'color' : '#FF0000'},
                2 : {'name' : 'do not pred', 'color' : '#0000FF'},
                3 : {'name' : 'bad pixel'  , 'color' : '#00FF00'},
            }
            layer_order  = [0, 1, 2, 3]
            layer_active = 1
            self.layer_manager = { 'layer_metadata' : layer_metadata,
                                   'layer_order'    : layer_order,
                                   'layer_active'   : layer_active, }

        # Load the YAML file
        with open(self.path_yaml, 'r') as fh:
            config = yaml.safe_load(fh)
        path_cxi_list = config['cxi']

        # Define the keys used below...
        CXI_KEY = {
            "num_peaks" : "/entry_1/result_1/nPeaks",
            "peak_y"    : "/entry_1/result_1/peakYPosRaw",
            "peak_x"    : "/entry_1/result_1/peakXPosRaw",
            "data"      : "/entry_1/data_1/data",
            "mask"      : "/entry_1/data_1/mask",
            "segmask"   : "/entry_1/data_1/segmask",
        }

        # Open all cxi files and track their status...
        cxi_dict = {}
        for path_cxi in path_cxi_list:
            # Open a new file???
            if path_cxi not in cxi_dict:
                cxi_dict[path_cxi] = {
                    "file_handle" : h5py.File(path_cxi, 'r+'),
                    "is_open"     : True,
                }

        # Build an entire idx list...
        idx_list = []
        for path_cxi, cxi in cxi_dict.items():
            fh = cxi["file_handle"]
            k  = CXI_KEY["num_peaks"]
            num_event = fh.get(k)[()]
            for event_idx in range(len(num_event)):
                idx_list.append((path_cxi, event_idx, fh))


        # Internal variables...
        self.cxi_dict      = cxi_dict
        self.CXI_KEY       = CXI_KEY
        self.path_cxi_list = path_cxi_list
        self.idx_list      = idx_list
        self.buffer_dict   = {}

        set_seed(self.seed)

        return None


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


    def close(self):
        for path_cxi, cxi in self.cxi_dict.items():
            is_open = cxi.get("is_open")
            if is_open:
                cxi.get("file_handle").close()
                cxi["is_open"] = False
                print(f"{path_cxi} is closed.")


    def get_img(self, idx):
        path_cxi, event_idx, fh = self.idx_list[idx]

        buffer_key = (path_cxi, event_idx)
        if not buffer_key in self.buffer_dict:
            # Obtain the image...
            k   = self.CXI_KEY["data"]
            img = fh.get(k)[event_idx]

            # Obtain the bad pixel mask...
            k    = self.CXI_KEY['mask']
            mask = fh.get(k)
            mask = mask[event_idx] if mask.ndim == 3 else mask[()]

            # Apply mask...
            img = apply_mask(img, 1 - mask, mask_value = 0)

            # Obtain the segmask...
            k       = self.CXI_KEY["segmask"]
            segmask = fh.get(k)[event_idx]

            self.buffer_dict[buffer_key] = (img, segmask)

        img, segmask = self.buffer_dict[buffer_key]

        # Save random state...
        # Might not be useful for this labeler
        if not idx in self.img_state_dict:
            self.save_random_state()
            self.img_state_dict[idx] = self.state_random
        else:
            self.state_random = self.img_state_dict[idx]
            self.set_random_state()

        return img[None,], segmask[None,]


    def update_segmask(self, idx, new_segmask):
        path_cxi, event_idx, fh = self.idx_list[idx]

        # Obtain the segmask...
        k = self.CXI_KEY["segmask"]

        # Update the content in segmask with caution...
        try:
            fh.get(k)[event_idx] = new_segmask[0]    # [0] : (1, H, W) -> (H, W)

            # Flush it to disk now...
            fh.flush()

            # Clean the buffer...
            self.buffer_dict = {}

            print(f"The new segmask for event {event_idx} is saved.")

        except Exception as e:
            print(f"Oops!!! Errors occurs while saving the new segmask for event {event_idx}.")

