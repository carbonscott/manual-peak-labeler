# X-ray diffraction peak labeler

A GUI for viewing/labeling X-ray diffraction peaks.


## Install with `pip`

```
pip install git+https://github.com/carbonscott/manual-peak-labeler --upgrade --user
```


## Dependency

```
pyqtgraph
numpy
```


## Usages/Keyboard shortcuts

- `L` Key: Enable labeling/unlabeling a peak pixel with a left mouse click.
- `M` Key: Enable adding/removing a image mask with two left mouse clicks
  (basically specify a range).
- `Space` Key: Disable special mouse click effects in `L` and `M` modes.
- `Z` Key: Show/Hide the overlay annotation (a label or a mask).
- `N` Key: Next image.
- `P` Key: Previous image.
- `G` Key: Go to a specific image by prompting users for an input.
