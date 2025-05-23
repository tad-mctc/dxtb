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
Testing halogen bond correction gradient (autodiff).
"""

from __future__ import annotations

import pytest
import torch
from tad_mctc.autograd import dgradcheck, dgradgradcheck
from tad_mctc.batch import pack

from dxtb import GFN1_XTB as par
from dxtb import IndexHelper
from dxtb._src.components.classicals import Halogen
from dxtb._src.typing import DD, Callable, Tensor

from ...conftest import DEVICE
from ...utils import get_elem_param
from .samples import samples

sample_list = ["br2nh3", "br2och2", "tmpda"]

tol = 1e-8


def gradchecker(dtype: torch.dtype, name: str) -> tuple[
    Callable[[Tensor, Tensor, Tensor], Tensor],  # autograd function
    tuple[Tensor, Tensor, Tensor],  # differentiable variables
]:
    """Prepare gradient check from `torch.autograd`."""
    assert par.halogen is not None

    dd: DD = {"dtype": dtype, "device": DEVICE}

    sample = samples[name]
    numbers = sample["numbers"].to(DEVICE)
    positions = sample["positions"].to(**dd)
    ihelp = IndexHelper.from_numbers(numbers, par)

    # variables to be differentiated
    _damp = torch.tensor(par.halogen.classical.damping, **dd)
    _damp.requires_grad_(True)

    _rscale = torch.tensor(par.halogen.classical.rscale, **dd)
    _rscale.requires_grad_(True)

    _xbond = get_elem_param(
        torch.unique(numbers), par.element, "xbond", pad_val=0, **dd
    )
    _xbond.requires_grad_(True)

    def func(damp: Tensor, rscale: Tensor, xbond: Tensor) -> Tensor:
        xb = Halogen(damp, rscale, xbond, **dd)
        cache = xb.get_cache(numbers, ihelp)
        return xb.get_energy(positions, cache)

    return func, (_damp, _rscale, _xbond)


@pytest.mark.grad
@pytest.mark.parametrize("dtype", [torch.double])
@pytest.mark.parametrize("name", sample_list)
def test_grad(dtype: torch.dtype, name: str) -> None:
    """
    Check a single analytical gradient of parameters against numerical
    gradient from `torch.autograd.gradcheck`.
    """
    func, diffvars = gradchecker(dtype, name)
    assert dgradcheck(func, diffvars, atol=tol)


@pytest.mark.grad
@pytest.mark.parametrize("dtype", [torch.double])
@pytest.mark.parametrize("name", sample_list)
def test_gradgrad(dtype: torch.dtype, name: str) -> None:
    """
    Check a single analytical gradient of parameters against numerical
    gradient from `torch.autograd.gradgradcheck`.
    """
    func, diffvars = gradchecker(dtype, name)
    assert dgradgradcheck(func, diffvars, atol=tol)


def gradchecker_batch(dtype: torch.dtype, name1: str, name2: str) -> tuple[
    Callable[[Tensor, Tensor, Tensor], Tensor],  # autograd function
    tuple[Tensor, Tensor, Tensor],  # differentiable variables
]:
    """Prepare gradient check from `torch.autograd`."""
    assert par.halogen is not None

    dd: DD = {"dtype": dtype, "device": DEVICE}

    sample1, sample2 = samples[name1], samples[name2]
    numbers = pack(
        [
            sample1["numbers"].to(DEVICE),
            sample2["numbers"].to(DEVICE),
        ]
    )
    positions = pack(
        [
            sample1["positions"].to(**dd),
            sample2["positions"].to(**dd),
        ]
    )
    ihelp = IndexHelper.from_numbers(numbers, par)

    # variables to be differentiated
    _damp = torch.tensor(par.halogen.classical.damping, **dd)
    _damp.requires_grad_(True)

    _rscale = torch.tensor(par.halogen.classical.rscale, **dd)
    _rscale.requires_grad_(True)

    _xbond = get_elem_param(
        torch.unique(numbers), par.element, "xbond", pad_val=0, **dd
    )
    _xbond.requires_grad_(True)

    def func(damp: Tensor, rscale: Tensor, xbond: Tensor) -> Tensor:
        xb = Halogen(damp, rscale, xbond, **dd)
        cache = xb.get_cache(numbers, ihelp)
        return xb.get_energy(positions, cache)

    return func, (_damp, _rscale, _xbond)


@pytest.mark.grad
@pytest.mark.parametrize("dtype", [torch.double])
@pytest.mark.parametrize("name1", ["br2nh3"])
@pytest.mark.parametrize("name2", sample_list)
def test_grad_batch(dtype: torch.dtype, name1: str, name2: str) -> None:
    """
    Check a single analytical gradient of parameters against numerical
    gradient from `torch.autograd.gradcheck`.
    """
    func, diffvars = gradchecker_batch(dtype, name1, name2)
    assert dgradcheck(func, diffvars, atol=tol)


@pytest.mark.grad
@pytest.mark.parametrize("dtype", [torch.double])
@pytest.mark.parametrize("name1", ["br2nh3"])
@pytest.mark.parametrize("name2", sample_list)
def test_gradgrad_batch(dtype: torch.dtype, name1: str, name2: str) -> None:
    """
    Check a single analytical gradient of parameters against numerical
    gradient from `torch.autograd.gradgradcheck`.
    """
    func, diffvars = gradchecker_batch(dtype, name1, name2)
    assert dgradgradcheck(func, diffvars, atol=tol)
