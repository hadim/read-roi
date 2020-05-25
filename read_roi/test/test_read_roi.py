import os
import json

from unittest import TestCase
from nose.tools import nottest

import read_roi

root_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(root_dir, "data")


def load_data(name):
    return os.path.join(data_dir, name + ".roi")


def load_true_data(name):
    fname = os.path.join(data_dir, name + ".json")
    data = json.load(open(fname))
    true_name = list(data.keys())[0]
    if 'paths' in data[true_name]:
        # Convert segment nodes from list to tuples
        data[true_name]['paths'] = [
            [tuple(segment) for segment in path]
            for path in data[true_name]['paths']
        ]
    return data


@nottest
def test_roi_data(name, true_data):
    fname = load_data(name)
    data = read_roi.read_roi_file(fname)
    TestCase().assertDictEqual(data, true_data)


def test_read_roi_version():
    print(read_roi.__version__)


def test_point():
    true_data = {'point': {'n': 1,
                           'name': 'point',
                           'position': {'channel': 1, 'frame': 1, 'slice': 1},
                           'type': 'point',
                           'slices': [1],
                           'counters': [0],
                           'x': [68.0],
                           'y': [77.25]}}

    test_roi_data("point", true_data)


def test_line1():
    true_data = {'line1': {'draw_offset': False,
                           'name': 'line1',
                           'position': 0,
                           'type': 'line',
                           'width': 0,
                           'x1': 260.0,
                           'x2': 89.0,
                           'y1': 52.0,
                           'y2': 103.0}}

    test_roi_data("line1", true_data)


def test_line2():
    true_data = {'line2': {'draw_offset': False,
                           'name': 'line2',
                           'position': {'channel': 1, 'frame': 1, 'slice': 1},
                           'type': 'line',
                           'width': 0,
                           'x1': 100.5,
                           'x2': 132.5,
                           'y1': 158.5,
                           'y2': 156.5}}

    test_roi_data("line2", true_data)


def test_rois():
    names = [
        "composite-brush-donut",
        "composite-brush-yin-yang",
        "composite-oval-in-rect",
        "composite-rect-in-rect",
        "composite-two-ellipses",
        "composite-two-ovals",
        "ellipse",
        "ellipse-left",
        "ellipse-top",
        "freehand",
        "freeline",
        "multipoint",
        "oval",
        "oval-left",
        "oval-top",
        "point",
        "polygon",
        "polygon-left",
        "polygon-top",
        "polyline",
        "rectangle",
    ]
    for name in names:
        true_data = load_true_data(name)
        print(name)
        yield test_roi_data, name, true_data
