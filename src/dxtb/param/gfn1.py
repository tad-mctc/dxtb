"""
GFN1-xTB
========

This module loads the standard GFN1-xTB parametrization.
"""
from __future__ import annotations

import os.path as op

import tomli as toml

from .base import Param

with open(op.join(op.dirname(__file__), "gfn1-xtb.toml"), "rb") as fd:
    GFN1_XTB = Param(**toml.load(fd))
