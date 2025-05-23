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
Run tests for energy contribution from on-site third-order
electrostatic energy (ES3).
"""

from __future__ import annotations

import pytest
import torch
from tad_mctc.autograd import dgradcheck
from tad_mctc.batch import pack

from dxtb import GFN2_XTB, IndexHelper
from dxtb._src.components.interactions.coulomb import thirdorder as es3
from dxtb._src.typing import DD, Tensor

from ..conftest import DEVICE, NONDET_TOL
from ..utils import get_elem_param
from .samples import samples

qat_samples = ["MB16_43_01", "MB16_43_02"]
qsh_samples = ["MB16_43_07"]


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", qsh_samples)
def test_qsh_single(dtype: torch.dtype, name: str) -> None:
    """Test ES3 for some samples from MB16_43."""
    dd: DD = {"dtype": dtype, "device": DEVICE}

    sample = samples[name]
    numbers = sample["numbers"].to(DEVICE)
    qsh = sample["q_gfn2"].to(**dd)
    ref = sample["es3_shell"].to(**dd)

    ihelp = IndexHelper.from_numbers(numbers, GFN2_XTB)
    es = es3.new_es3(torch.unique(numbers), GFN2_XTB, **dd)
    assert es is not None

    cache = es.get_cache(numbers=numbers, ihelp=ihelp)
    e = es.get_monopole_shell_energy(cache, qsh)
    assert pytest.approx(ref.cpu()) == e.sum(-1).cpu()


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name1", qsh_samples)
@pytest.mark.parametrize("name2", qsh_samples)
def test_qsh_batch(dtype: torch.dtype, name1: str, name2: str) -> None:
    """Test batched calculation of ES3."""
    dd: DD = {"dtype": dtype, "device": DEVICE}

    sample1, sample2 = samples[name1], samples[name2]
    numbers = pack(
        (
            sample1["numbers"].to(DEVICE),
            sample2["numbers"].to(DEVICE),
        )
    )
    qsh = pack(
        (
            sample1["q_gfn2"].to(**dd),
            sample2["q_gfn2"].to(**dd),
        )
    )
    ref = torch.stack(
        [
            sample1["es3_shell"].to(**dd),
            sample2["es3_shell"].to(**dd),
        ],
    )

    ihelp = IndexHelper.from_numbers(numbers, GFN2_XTB)
    es = es3.new_es3(torch.unique(numbers), GFN2_XTB, **dd)
    assert es is not None

    cache = es.get_cache(numbers=numbers, ihelp=ihelp)
    e = es.get_monopole_shell_energy(cache, qsh)
    assert pytest.approx(ref.cpu()) == e.sum(-1).cpu()


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", qat_samples)
def test_qat_single(dtype: torch.dtype, name: str) -> None:
    """Test ES3 for some samples from MB16_43."""
    dd: DD = {"dtype": dtype, "device": DEVICE}

    sample = samples[name]
    numbers = sample["numbers"].to(DEVICE)
    qat = sample["q"].to(**dd)
    ref = sample["es3_shell"].to(**dd)

    ihelp = IndexHelper.from_numbers(numbers, GFN2_XTB)
    es = es3.new_es3(torch.unique(numbers), GFN2_XTB, **dd)
    assert es is not None

    # atom-resolved charge test
    es.shell_scale = None

    cache = es.get_cache(numbers=numbers, ihelp=ihelp)
    e = es.get_monopole_atom_energy(cache, qat)
    assert pytest.approx(ref.cpu()) == e.sum(-1).cpu()


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name1", qat_samples)
@pytest.mark.parametrize("name2", qat_samples)
def test_qat_batch(dtype: torch.dtype, name1: str, name2: str) -> None:
    """Test batched calculation of ES3."""
    dd: DD = {"dtype": dtype, "device": DEVICE}

    sample1, sample2 = samples[name1], samples[name2]
    numbers = pack(
        (
            sample1["numbers"].to(DEVICE),
            sample2["numbers"].to(DEVICE),
        )
    )
    qat = pack(
        (
            sample1["q"].to(**dd),
            sample2["q"].to(**dd),
        )
    )
    ref = torch.stack(
        [
            sample1["es3_shell"].to(**dd),
            sample2["es3_shell"].to(**dd),
        ],
    )

    ihelp = IndexHelper.from_numbers(numbers, GFN2_XTB)
    es = es3.new_es3(torch.unique(numbers), GFN2_XTB, **dd)
    assert es is not None

    # atom-resolved charge test
    es.shell_scale = None

    cache = es.get_cache(numbers=numbers, ihelp=ihelp)
    e = es.get_monopole_atom_energy(cache, qat)
    assert pytest.approx(ref.cpu()) == e.sum(-1).cpu()


@pytest.mark.grad
@pytest.mark.parametrize("name", qat_samples)
def test_grad_param_atom(name: str) -> None:
    """Test autograd for ES3 parameters."""
    dd: DD = {"dtype": torch.double, "device": DEVICE}

    sample = samples[name]
    numbers = sample["numbers"].to(DEVICE)
    qat = sample["q"].to(**dd)

    ihelp = IndexHelper.from_numbers(numbers, GFN2_XTB)

    hd = get_elem_param(
        torch.unique(numbers),
        GFN2_XTB.element,
        "gam3",
        **dd,
    )

    # variable to be differentiated
    hd.requires_grad_(True)

    def func(hubbard_derivs: Tensor):
        es = es3.ES3(hubbard_derivs, **dd)
        cache = es.get_cache(numbers=numbers, ihelp=ihelp)
        return es.get_monopole_atom_energy(cache, qat)

    assert dgradcheck(func, hd, nondet_tol=NONDET_TOL)


@pytest.mark.grad
@pytest.mark.parametrize("name", qsh_samples)
def test_grad_param_shell(name: str) -> None:
    """Test autograd for ES3 parameters."""
    dd: DD = {"dtype": torch.double, "device": DEVICE}

    sample = samples[name]
    numbers = sample["numbers"].to(DEVICE)
    qsh = sample["q_gfn2"].to(**dd)

    ihelp = IndexHelper.from_numbers(numbers, GFN2_XTB)

    hd = get_elem_param(
        torch.unique(numbers),
        GFN2_XTB.element,
        "gam3",
        **dd,
    )

    assert GFN2_XTB.thirdorder is not None
    assert GFN2_XTB.thirdorder.shell is not False

    shell_scale = torch.tensor(
        [
            GFN2_XTB.thirdorder.shell.s,
            GFN2_XTB.thirdorder.shell.p,
            GFN2_XTB.thirdorder.shell.d,
        ],
        **dd,
    )

    # variable to be differentiated
    hd.requires_grad_(True)

    def func(hubbard_derivs: Tensor):
        es = es3.ES3(hubbard_derivs, shell_scale=shell_scale, **dd)
        cache = es.get_cache(numbers=numbers, ihelp=ihelp)
        return es.get_monopole_shell_energy(cache, qsh)

    assert dgradcheck(func, hd, nondet_tol=NONDET_TOL)
