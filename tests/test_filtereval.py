import pytest
from camilladsp_plot import filters
import numpy as np


def test_conv():
    filt = filters.Conv(None, 44100)
    # TODO make proper tests
