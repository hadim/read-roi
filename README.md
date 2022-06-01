# read-roi

[![PyPI version](https://img.shields.io/pypi/v/read-roi.svg?maxAge=2591000)](https://pypi.org/project/read-roi/)
[![Build Status](https://travis-ci.com/hadim/read-roi.svg?branch=master)](https://travis-ci.com/hadim/read-roi)
[![codecov](https://codecov.io/gh/hadim/read-roi/branch/master/graph/badge.svg)](https://codecov.io/gh/hadim/read-roi)

Read ROI files .zip or .roi generated with ImageJ. Code is largely inspired from : http://rsb.info.nih.gov/ij/developer/source/ij/io/RoiDecoder.java.html

## Functions

```python
from read_roi import read_roi_file
from read_roi import read_roi_zip

roi = read_roi_file(roi_file_path)

# or

rois = read_roi_zip(roi_zip_path)
```

## Note

- Some format specifications are not implemented. See `RoiDecoder.java` for details.
- Most of "normal" ROI files should work.
- Feel free to hack it and send me modifications.

## Requirements

- Python 3.5 and above.

## Install

`pip install read-roi`

Or you can use Anaconda and `conda-forge`:

```
conda config --add channels conda-forge
conda install read-roi
```

## License

Under BSD license. See [LICENSE](LICENSE).

## Authors

- Hadrien Mary <hadrien.mary@gmail.com>

## Release a new version

- Run tests: `pytest -v read_roi/`.
- Install [rever](https://regro.github.io/rever-docs): `conda install -y rever`.
- Run check: `rever check`.
- Bump and release new version: `rever VERSION_NUMBER`.
