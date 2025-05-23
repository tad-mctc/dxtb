# This file is part of dxtb.
#
# SPDX-Identifier: Apache-2.0
# Copyright (C) 2024 Grimme Group
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Repulsion: Factory
==================

A factory function to create instances of the Repulsion class.
"""

from __future__ import annotations

import warnings

import torch
from tad_mctc.convert import any_to_tensor

from dxtb._src.constants import xtb
from dxtb._src.param import Param, ParamModule
from dxtb._src.typing import DD, Tensor, get_default_dtype
from dxtb._src.typing.exceptions import ParameterWarning

from .rep import Repulsion, RepulsionAnalytical

__all__ = ["new_repulsion"]


def new_repulsion(
    unique: Tensor,
    par: Param | ParamModule,
    cutoff: Tensor | float | int | None = None,
    with_analytical_gradient: bool = False,
    device: torch.device | None = None,
    dtype: torch.dtype | None = None,
) -> Repulsion | None:
    """
    Create new instance of Repulsion class.

    Parameters
    ----------
    unique : Tensor
        Unique elements in the system (shape: ``(nunique,)``).
    par : Param | ParamModule
        Representation of an extended tight-binding model.
    cutoff : float
        Real space cutoff for repulsion interactions (default: 25.0).
    with_analytical_gradient : bool, optional
        Whether to instantiate a repulsion class that implements a custom
        backward function with an analytical nuclear gradient, i.e., the first
        derivative w.r.t. positions is computed with an analytical formula
        instead of the AD engine. Defaults to ``False``.

    Returns
    -------
    Repulsion | None
        Instance of the Repulsion class or ``None`` if no repulsion is used.

    Raises
    ------
    ValueError
        If parametrization does not contain a halogen bond correction.
    """
    dd: DD = {
        "device": device,
        "dtype": dtype if dtype is not None else get_default_dtype(),
    }

    # compatibility with previous version based on `Param`
    if not isinstance(par, ParamModule):
        par = ParamModule(par, **dd)

    if "repulsion" not in par or par.is_none("repulsion"):
        # Although repulsion is used in all models, we do not want to exit
        # for custom models that are loaded from a parameter file. Hence, we
        # only issue a warning here, not an error.
        warnings.warn("No repulsion scheme found.", ParameterWarning)
        return None

    kexp = par.get("repulsion.effective.kexp")
    klight = (
        par.get("repulsion.effective.klight")
        if "klight" in par.get("repulsion.effective")
        else None
    )

    # get parameters for unique species
    arep = par.get_elem_param(unique, "arep", pad_val=0)
    zeff = par.get_elem_param(unique, "zeff", pad_val=0)

    if cutoff is None:
        cutoff = xtb.DEFAULT_REPULSION_CUTOFF
    cutoff = any_to_tensor(cutoff, **dd)

    if with_analytical_gradient is True:
        return RepulsionAnalytical(arep, zeff, kexp, klight, cutoff, **dd)
    return Repulsion(arep, zeff, kexp, klight, cutoff, **dd)
