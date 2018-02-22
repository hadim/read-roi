import os
from unittest import TestCase

import read_roi

root_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(root_dir, "data")


def load_data(name):
    return os.path.join(data_dir, name + ".roi")


def test_read_roi_version():
    ""
    print(read_roi.__version__)


def test_point():
    ""
    true_data = {'point': {'n': 1,
                           'name': 'point',
                           'position': {'channel': 1, 'frame': 1, 'slice': 1},
                           'type': 'freeroi',
                           'x': [68],
                           'y': [77]}}

    fname = load_data("point")
    data = read_roi.read_roi_file(fname)
    TestCase().assertDictEqual(data, true_data)
