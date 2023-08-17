#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import numpy as np
import skimage.measure as sm
import psana

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)

    return None




def hex_to_rgb(hex_string):
    # Convert the hex string to an integer
    hex_int = int(hex_string[hex_string.find('#')+1:], 16)

    # Extract the red, green, and blue values
    red = (hex_int >> 16) & 0xFF
    green = (hex_int >> 8) & 0xFF
    blue = hex_int & 0xFF

    # Return a list of the RGB values
    return [red, green, blue]




def read_log(file):
    '''Return all lines in the user supplied parameter file without comments.
    ''' 
    # Retrieve key-value information...
    kw_kv     = "KV - " 
    kv_dict   = {}

    # Retrieve data information...
    kw_data   = "DATA - " 
    data_dict = {}
    with open(file,'r') as fh: 
        for line in fh.readlines():
            # Collect kv information...
            if kw_kv in line:
                info = line[line.rfind(kw_kv) + len(kw_kv):]
                k, v = info.split(":", maxsplit = 1)
                if not k in kv_dict: kv_dict[k.strip()] = v.strip()

            # Collect data information...
            if kw_data in line:
                info = line[line.rfind(kw_data) + len(kw_data):]
                k = info.strip().split(",")

                # Remove contents after colon...
                k[1:] = [ i[:i.rfind(":")].strip() for i in k[1:] ]

                # Convert list to tuple...
                k = tuple(k)

                if not k in data_dict: data_dict[k] = True

    ret_dict = { "kv" : kv_dict, "data" : tuple(data_dict.keys()) }

    return ret_dict




class PerfMetric:
    def __init__(self, res_dict):
        self.res_dict = res_dict


    def reduce_confusion(self, label):
        ''' Given a label, reduce multiclass confusion matrix to binary
            confusion matrix.
        '''
        res_dict    = self.res_dict
        labels      = res_dict.keys()
        labels_rest = [ i for i in labels if not i == label ]

        # Early return if non-exist label is passed in...
        if not label in labels: 
            print(f"label {label} doesn't exist!!!")
            return None

        # Obtain true positive...
        tp = len(res_dict[label][label])
        fp = sum( [ len(res_dict[label][i]) for i in labels_rest ] )
        tn = sum( sum( len(res_dict[i][j]) for j in labels_rest ) for i in labels_rest )
        fn = sum( [ len(res_dict[i][label]) for i in labels_rest ] )

        return tp, fp, tn, fn


    def get_metrics(self, label):
        # Early return if non-exist label is passed in...
        confusion = self.reduce_confusion(label)
        if confusion is None: return None

        # Calculate metrics...
        tp, fp, tn, fn = confusion
        assert tp + fn > 0, "The result about one category is still missing, please work on more tests!!!"
        assert tn + fp > 0, "The result about one category is still missing, please work on more tests!!!"

        accuracy    = (tp + tn) / (tp + tn + fp + fn)
        precision   = tp / (tp + fp)
        recall      = tp / (tp + fn)
        specificity = tn / (tn + fp) if tn + fp > 0 else None
        f1_inv      = (1 / precision + 1 / recall)
        f1          = 2 / f1_inv

        return accuracy, precision, recall, specificity, f1




def downsample(assem, bin_row=2, bin_col=2, mask=None):
    """ Downsample an SPI image.  
        Adopted from https://github.com/chuckie82/DeepProjection/blob/master/DeepProjection/utils.py
    """
    if mask is None:
        combinedMask = np.ones_like(assem)
    else:
        combinedMask = mask
    downCalib  = sm.block_reduce(assem       , block_size=(bin_row, bin_col), func=np.sum)
    downWeight = sm.block_reduce(combinedMask, block_size=(bin_row, bin_col), func=np.sum)
    warr       = np.zeros_like(downCalib, dtype='float32')
    ind        = np.where(downWeight > 0)
    warr[ind]  = downCalib[ind] / downWeight[ind]

    return warr




class PsanaImg:
    """
    It serves as an image accessing layer based on the data management system
    psana in LCLS.  
    """

    def __init__(self, exp, run, mode, detector_name):

        # Biolerplate code to access an image
        # Set up data source
        self.datasource_id = f"exp={exp}:run={run}:{mode}"
        self.datasource    = psana.DataSource( self.datasource_id )
        self.run_current   = next(self.datasource.runs())
        self.timestamps    = self.run_current.times()

        # Set up detector
        self.detector = psana.Detector(detector_name)


    def get(self, event_num, multipanel = None, mode = "image"):
        # Fetch the timestamp according to event number...
        timestamp = self.timestamps[int(event_num)]

        # Access each event based on timestamp...
        event = self.run_current.event(timestamp)

        # Only three modes are supported...
        assert mode in ("raw", "image", "calib"), f"Mode {mode} is not allowed!!!  Only 'raw' or 'image' are supported."

        # Fetch image data based on timestamp from detector...
        read = { "image" : self.detector.image,
                 "calib" : self.detector.calib }
        img = read[mode](event) if multipanel is None else read[mode](event, multipanel)

        return img




def apply_mask(data, mask, mask_value = np.nan):
    """ 
    Return masked data.

    Args:
        data: numpy.ndarray with the shape of (B, H, W).·
              - B: batch of images.
              - H: height of an image.
              - W: width of an image.

        mask: numpy.ndarray with the shape of (B, H, W).·

    Returns:
        data_masked: numpy.ndarray.
    """ 
    # Mask unwanted pixels with np.nan...
    data_masked = np.where(mask, data, mask_value)

    return data_masked
