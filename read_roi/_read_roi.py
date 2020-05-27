import os
import struct
import zipfile
import logging

__all__ = ['read_roi_file', 'read_roi_zip']


class UnrecognizedRoiType(Exception):
    pass


OFFSET = dict(VERSION_OFFSET=4,
              TYPE=6,
              TOP=8,
              LEFT=10,
              BOTTOM=12,
              RIGHT=14,
              N_COORDINATES=16,
              X1=18,
              Y1=22,
              X2=26,
              Y2=30,
              XD=18,
              YD=22,
              WIDTHD=26,
              HEIGHTD=30,
              STROKE_WIDTH=34,
              SHAPE_ROI_SIZE=36,
              STROKE_COLOR=40,
              FILL_COLOR=44,
              SUBTYPE=48,
              OPTIONS=50,
              ARROW_STYLE=52,
              ELLIPSE_ASPECT_RATIO=52,
              ARROW_HEAD_SIZE=53,
              ROUNDED_RECT_ARC_SIZE=54,
              POSITION=56,
              HEADER2_OFFSET=60,
              COORDINATES=64)

ROI_TYPE = dict(polygon=0,
                rect=1,
                oval=2,
                line=3,
                freeline=4,
                polyline=5,
                noRoi=6,
                freehand=7,
                traced=8,
                angle=9,
                point=10)

OPTIONS = dict(SPLINE_FIT=1,
               DOUBLE_HEADED=2,
               OUTLINE=4,
               OVERLAY_LABELS=8,
               OVERLAY_NAMES=16,
               OVERLAY_BACKGROUNDS=32,
               OVERLAY_BOLD=64,
               SUB_PIXEL_RESOLUTION=128,
               DRAW_OFFSET=256)

HEADER_OFFSET = dict(C_POSITION=4,
                     Z_POSITION=8,
                     T_POSITION=12,
                     NAME_OFFSET=16,
                     NAME_LENGTH=20,
                     OVERLAY_LABEL_COLOR=24,
                     OVERLAY_FONT_SIZE=28,
                     AVAILABLE_BYTE1=30,
                     IMAGE_OPACITY=31,
                     IMAGE_SIZE=32,
                     FLOAT_STROKE_WIDTH=36,
                     ROI_PROPS_OFFSET=40,
                     ROI_PROPS_LENGTH=44,
                     COUNTERS_OFFSET=48)

SUBTYPES = dict(TEXT=1,
                ARROW=2,
                ELLIPSE=3,
                IMAGE=4)

# https://docs.oracle.com/javase/6/docs/api/constant-values.html#java.awt.geom.PathIterator
PATHITERATOR_TYPES = dict(SEG_MOVETO=0,
                          SEG_LINETO=1,
                          SEG_QUADTO=2,
                          SEG_CUBICTO=3,
                          SEG_CLOSE=4)


def get_byte(data, base):
    if isinstance(base, int):
        return data[base]
    elif isinstance(base, list):
        return [data[b] for b in base]


def get_uint16(data, base):
    b0 = data[base]
    b1 = data[base + 1]
    n = (b0 << 8) + b1
    return n


def get_int16(data, base):
    n = get_uint16(data, base)
    if n >= 32768:  # 2**15
        n -= 65536  # 2**16
    return n


def get_maybe_int16(data, base, thr=65036):
    """
    Load data which might be int16 or uint16.
    """
    n = get_uint16(data, base)
    if thr < 32768:
        raise ValueError(
            "Threshold for distinguishing between int16 and uint16 must be"
            " at least 2^15 = 32768, but {} was given.".format(thr)
        )
    if n >= thr:
        # Convert to uint16
        n -= 65536  # 2**16
    return n


def get_uint32(data, base):
    b0 = data[base]
    b1 = data[base + 1]
    b2 = data[base + 2]
    b3 = data[base + 3]
    n = ((b0 << 24) + (b1 << 16) + (b2 << 8) + b3)
    return n


def get_float(data, base):
    s = struct.pack('I', get_uint32(data, base))
    return struct.unpack('f', s)[0]


def get_counter(data, base):
    """
    See setCounters() / getCounters() methods in IJ source, ij/gui/PointRoi.java.
    """

    b0 = data[base]
    b1 = data[base + 1]
    b2 = data[base + 2]
    b3 = data[base + 3]

    counter = b3
    position = (b1 << 8) + b2

    return counter, position


def get_point_counters(data, hdr2Offset, n_coordinates, size):
    if hdr2Offset == 0:
        return None

    offset = get_uint32(data, hdr2Offset + HEADER_OFFSET['COUNTERS_OFFSET'])
    if offset == 0:
        return None

    if offset + n_coordinates * 4 > size:
        return None

    counters = []
    positions = []
    for i in range(0, n_coordinates):
        cnt, position = get_counter(data, offset + i * 4)
        counters.append(cnt)
        positions.append(position)

    return counters, positions


def pathiterator2paths(shape_array):
    """
    Converts a shape array in PathIterator notation to polygon (or curved)
    paths.

    Parameters
    ----------
    shape_array : list of floats
        paths encoded in `java.awt.geom.PathIterator` format. Each segment
        within the path begins with a header value,

            0 : Move operation
            1 : Line segment
            2 : Quadratic segment
            3 : Cubic segment
            4 : Terminate path

        followed by a number of values describing the path along the segment
        to the next node. In the case of a termination operation, the current
        path ends, whilst for a move operation a new path begins with a new
        node described whose co-ordinate is given by the next two value in
        `shape_array`.

    Returns
    -------
    paths : list of lists of tuples
        The `segements` output contains a list of path paths. Each path
        is a list of points along the path. In its simplest form, each tuple
        in the list has length two, corresponding to a nodes along a polygon
        shape. Tuples of length 4 or 6 correspond to quadratic and cubic paths
        (respectively) from the previous node.
        ImageJ ROIs are only known to output linear segments (even with
        ellipses with subpixel precision enabled), so it is expected that all
        segments along the path should be length two tuples containing only the
        co-ordinates of the next point on the polygonal path.

    Notes
    -----
    Based on the ShapeRoi constructor "from an array of variable length path
    segments" and `makeShapeFromArray`, as found in:
    https://imagej.nih.gov/ij/developer/source/ij/gui/ShapeRoi.java.html
    With further reference to its `PathIterator` dependency, as found in:
    https://docs.oracle.com/javase/6/docs/api/constant-values.html#java.awt.geom.PathIterator
    """
    paths = []
    path = None
    i = 0
    while i < len(shape_array):
        segmentType = shape_array[i]
        if segmentType == PATHITERATOR_TYPES["SEG_MOVETO"]:
            # Move to
            if path is not None:
                paths.append(path)
            # Start a new segment with a node at this point
            path = []
            nCoords = 2
        elif segmentType == PATHITERATOR_TYPES["SEG_LINETO"]:
            # Line to next point
            nCoords = 2
        elif segmentType == PATHITERATOR_TYPES["SEG_QUADTO"]:
            # Quadratic curve to next point
            nCoords = 4
        elif segmentType == PATHITERATOR_TYPES["SEG_CUBICTO"]:
            # Cubic curve to next point
            nCoords = 6
        elif segmentType == PATHITERATOR_TYPES["SEG_CLOSE"]:
            # Segment close
            paths.append(path)
            path = None
            i += 1
            continue
        if path is None:
            raise ValueError("A path must begin with a move operation.")
        path.append(tuple(shape_array[i + 1 : i + 1 + nCoords]))
        i += 1 + nCoords
    return paths


def extract_basic_roi_data(data):
    size = len(data)
    code = '>'

    magic = get_byte(data, list(range(4)))
    magic = "".join([chr(c) for c in magic])

    # TODO: raise error if magic != 'Iout'
    version = get_uint16(data, OFFSET['VERSION_OFFSET'])
    roi_type = get_byte(data, OFFSET['TYPE'])
    subtype = get_uint16(data, OFFSET['SUBTYPE'])

    # Note that top, bottom, left, and right may be signed integers
    top = get_maybe_int16(data, OFFSET['TOP'])
    left = get_maybe_int16(data, OFFSET['LEFT'])
    if top >= 0:
        bottom = get_uint16(data, OFFSET['BOTTOM'])
    else:
        bottom = get_maybe_int16(data, OFFSET['BOTTOM'])
    if left >= 0:
        right = get_uint16(data, OFFSET['RIGHT'])
    else:
        right = get_maybe_int16(data, OFFSET['RIGHT'])
    width = right - left
    height = bottom - top

    n_coordinates = get_uint16(data, OFFSET['N_COORDINATES'])
    options = get_uint16(data, OFFSET['OPTIONS'])
    position = get_uint32(data, OFFSET['POSITION'])
    hdr2Offset = get_uint32(data, OFFSET['HEADER2_OFFSET'])

    logging.debug("n_coordinates: {}".format(n_coordinates))
    logging.debug("position: {}".format(position))
    logging.debug("options: {}".format(options))

    sub_pixel_resolution = (options == OPTIONS['SUB_PIXEL_RESOLUTION']) and version >= 222
    draw_offset = sub_pixel_resolution and (options == OPTIONS['DRAW_OFFSET'])
    sub_pixel_rect = version >= 223 and sub_pixel_resolution and (
        roi_type == ROI_TYPE['rect'] or roi_type == ROI_TYPE['oval'])

    logging.debug("sub_pixel_resolution: {}".format(sub_pixel_resolution))
    logging.debug("draw_offset: {}".format(draw_offset))
    logging.debug("sub_pixel_rect: {}".format(sub_pixel_rect))

    # Untested
    if sub_pixel_rect:
        xd = get_float(data, OFFSET['XD'])
        yd = get_float(data, OFFSET['YD'])
        widthd = get_float(data, OFFSET['WIDTHD'])
        heightd = get_float(data, OFFSET['HEIGHTD'])
        logging.debug("Entering in sub_pixel_rect")

    # Untested
    if hdr2Offset > 0 and hdr2Offset + HEADER_OFFSET['IMAGE_SIZE'] + 4 <= size:
        channel = get_uint32(data, hdr2Offset + HEADER_OFFSET['C_POSITION'])
        slice = get_uint32(data, hdr2Offset + HEADER_OFFSET['Z_POSITION'])
        frame = get_uint32(data, hdr2Offset + HEADER_OFFSET['T_POSITION'])
        overlayLabelColor = get_uint32(data, hdr2Offset + HEADER_OFFSET['OVERLAY_LABEL_COLOR'])
        overlayFontSize = get_uint16(data, hdr2Offset + HEADER_OFFSET['OVERLAY_FONT_SIZE'])
        imageOpacity = get_byte(data, hdr2Offset + HEADER_OFFSET['IMAGE_OPACITY'])
        imageSize = get_uint32(data, hdr2Offset + HEADER_OFFSET['IMAGE_SIZE'])
        logging.debug("Entering in hdr2Offset")

    roi_props = (hdr2Offset, n_coordinates, roi_type, channel, slice, frame, position, version, subtype, size)

    shape_roi_size = get_uint32(data, OFFSET['SHAPE_ROI_SIZE'])
    is_composite = shape_roi_size > 0

    if is_composite:
        roi = {'type': 'composite'}

        # Add bounding box rectangle details
        if sub_pixel_rect:
            roi.update(dict(left=xd, top=yd, width=widthd, height=heightd))
        else:
            roi.update(dict(left=left, top=top, width=width, height=height))

        # Load path iterator shape array and decode it into paths
        base = OFFSET['COORDINATES']
        shape_array = [get_float(data, base + i * 4) for i in range(shape_roi_size)]
        roi['paths'] = pathiterator2paths(shape_array)

        # NB: Handling position of roi is implemented in read_roi_file

        if version >= 218:
            # Not implemented
            # Read stroke width, stroke color and fill color
            pass
        if version >= 224:
            # Not implemented
            # Get ROI properties
            pass

        return roi, roi_props

    if roi_type == ROI_TYPE['rect']:
        roi = {'type': 'rectangle'}

        if sub_pixel_rect:
            roi.update(dict(left=xd, top=yd, width=widthd, height=heightd))
        else:
            roi.update(dict(left=left, top=top, width=width, height=height))

        roi['arc_size'] = get_uint16(data, OFFSET['ROUNDED_RECT_ARC_SIZE'])

        return roi, roi_props

    elif roi_type == ROI_TYPE['oval']:
        roi = {'type': 'oval'}

        if sub_pixel_rect:
            roi.update(dict(left=xd, top=yd, width=widthd, height=heightd))
        else:
            roi.update(dict(left=left, top=top, width=width, height=height))

        return roi, roi_props

    elif roi_type == ROI_TYPE['line']:
        roi = {'type': 'line'}

        x1 = get_float(data, OFFSET['X1'])
        y1 = get_float(data, OFFSET['Y1'])
        x2 = get_float(data, OFFSET['X2'])
        y2 = get_float(data, OFFSET['Y2'])

        if subtype == SUBTYPES['ARROW']:
            # Not implemented
            pass
        else:
            roi.update(dict(x1=x1, x2=x2, y1=y1, y2=y2))
            roi['draw_offset'] = draw_offset

        strokeWidth = get_uint16(data, OFFSET['STROKE_WIDTH'])
        roi.update(dict(width=strokeWidth))

        return roi, roi_props

    elif roi_type in [ROI_TYPE[t] for t in ["polygon", "freehand", "traced", "polyline", "freeline", "angle", "point"]]:
        x = []
        y = []

        if sub_pixel_resolution:
            base1 = OFFSET['COORDINATES'] + 4 * n_coordinates
            base2 = base1 + 4 * n_coordinates
            for i in range(n_coordinates):
                x.append(get_float(data, base1 + i * 4))
                y.append(get_float(data, base2 + i * 4))
        else:
            base1 = OFFSET['COORDINATES']
            base2 = base1 + 2 * n_coordinates
            for i in range(n_coordinates):
                xtmp = get_uint16(data, base1 + i * 2)
                ytmp = get_uint16(data, base2 + i * 2)
                x.append(left + xtmp)
                y.append(top + ytmp)


        if roi_type == ROI_TYPE['point']:
            roi = {'type': 'point'}
            roi.update(dict(x=x, y=y, n=n_coordinates))
            return roi, roi_props

        if roi_type == ROI_TYPE['polygon']:
            roi = {'type': 'polygon'}

        elif roi_type == ROI_TYPE['freehand']:
            roi = {'type': 'freehand'}
            if subtype == SUBTYPES['ELLIPSE']:
                ex1 = get_float(data, OFFSET['X1'])
                ey1 = get_float(data, OFFSET['Y1'])
                ex2 = get_float(data, OFFSET['X2'])
                ey2 = get_float(data, OFFSET['Y2'])
                roi['aspect_ratio'] = get_float(
                    data, OFFSET['ELLIPSE_ASPECT_RATIO'])
                roi.update(dict(ex1=ex1, ey1=ey1, ex2=ex2, ey2=ey2))

                return roi, roi_props

        elif roi_type == ROI_TYPE['traced']:
            roi = {'type': 'traced'}

        elif roi_type == ROI_TYPE['polyline']:
            roi = {'type': 'polyline'}

        elif roi_type == ROI_TYPE['freeline']:
            roi = {'type': 'freeline'}

        elif roi_type == ROI_TYPE['angle']:
            roi = {'type': 'angle'}

        else:
            roi = {'type': 'freeroi'}

        roi.update(dict(x=x, y=y, n=n_coordinates))

        strokeWidth = get_uint16(data, OFFSET['STROKE_WIDTH'])
        roi.update(dict(width=strokeWidth))

        return roi, roi_props
    else:
        raise UnrecognizedRoiType("Unrecognized ROI specifier: %d" % (roi_type, ))


def read_roi_file(fpath):
    """
    """

    if isinstance(fpath, zipfile.ZipExtFile):
        data = fpath.read()
        name = os.path.splitext(os.path.basename(fpath.name))[0]
    elif isinstance(fpath, str):
        fp = open(fpath, 'rb')
        data = fp.read()
        fp.close()
        name = os.path.splitext(os.path.basename(fpath))[0]
    else:
        logging.error("Can't read {}".format(fpath))
        return None

    logging.debug("Read ROI for \"{}\"".format(name))

    roi, (hdr2Offset, n_coordinates, roi_type, channel, slice, frame, position, version, subtype, size) = extract_basic_roi_data(data)
    roi['name'] = name

    if version >= 218:
        # Not implemented
        # Read stroke width, stroke color and fill color
        pass

    if version >= 218 and subtype == SUBTYPES['TEXT']:
        # Not implemented
        # Read test ROI
        pass

    if version >= 218 and subtype == SUBTYPES['IMAGE']:
        # Not implemented
        # Get image ROI
        pass

    if version >= 224:
        # Not implemented
        # Get ROI properties
        pass

    if version >= 227 and roi['type'] == 'point':
        # Get "point counters" (includes a "counter" and a "position" (slice, i.e. z position)
        tmp = get_point_counters(data, hdr2Offset, n_coordinates, size)
        if tmp is not None:
            counters, positions = tmp
            if counters:
                roi.update(dict(counters=counters, slices=positions))

    roi['position'] = position
    if channel > 0 or slice > 0 or frame > 0:
        roi['position'] = dict(channel=channel, slice=slice, frame=frame)

    return {name: roi}


def read_roi_zip(zip_path):
    """
    """
    from collections import OrderedDict
    rois = OrderedDict()
    zf = zipfile.ZipFile(zip_path)
    for n in zf.namelist():
        rois.update(read_roi_file(zf.open(n)))
    return rois
