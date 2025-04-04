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
Test for SCF.
Reference values obtained with tblite 0.2.1 disabling repulsion and dispersion.
"""

from __future__ import annotations

from math import sqrt

import pytest
import torch
from tad_mctc.batch import pack

from dxtb import GFN1_XTB, GFN2_XTB, Calculator
from dxtb._src.constants import labels
from dxtb._src.exlibs.available import has_libcint
from dxtb._src.typing import DD, Tensor

from ..conftest import DEVICE
from .samples import samples

slist = ["LiH", "SiH4"]
slist_more = ["H2", "H2O", "CH4"]
slist_large = ["PbH4-BiH3", "C6H5I-CH3SH", "MB16_43_01", "LYS_xao"]

opts = {
    "verbosity": 0,
    "maxiter": 300,
    "scf_mode": labels.SCF_MODE_FULL,
    "scp_mode": labels.SCP_MODE_POTENTIAL,
}

drivers = [
    labels.INTDRIVER_LIBCINT,
    labels.INTDRIVER_AUTOGRAD,
    labels.INTDRIVER_ANALYTICAL,
]


def single(
    dtype: torch.dtype,
    name: str,
    gfn: str,
    mixer: str,
    tol: float,
    scp_mode: str = "charge",
    intdriver: int = labels.INTDRIVER_LIBCINT,
) -> None:
    dd: DD = {"device": DEVICE, "dtype": dtype}

    sample = samples[name]
    numbers = sample["numbers"].to(DEVICE)
    positions = sample["positions"].to(**dd)
    ref = sample[f"e{gfn}"].to(**dd)
    charges = torch.tensor(0.0, **dd)

    if gfn == "gfn1":
        par = GFN1_XTB
    elif gfn == "gfn2":
        par = GFN2_XTB
    else:
        assert False

    options = dict(
        opts,
        **{
            "damp": 0.05 if mixer == "simple" else 0.4,
            "damp_dynamic": mixer != "simple",
            "int_driver": intdriver,
            "mixer": mixer,
            "scp_mode": scp_mode,
            "f_atol": tol,
            "x_atol": tol,
        },
    )
    calc = Calculator(numbers, par, opts=options, **dd)

    result = calc.singlepoint(positions, charges)
    res = result.scf.sum(-1)
    assert pytest.approx(ref.cpu(), abs=tol, rel=tol) == res.cpu()


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", slist)
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
@pytest.mark.parametrize("intdriver", drivers)
def test_single_gfn1(
    dtype: torch.dtype, name: str, mixer: str, intdriver: int
) -> None:
    tol = sqrt(torch.finfo(dtype).eps) * 10
    single(dtype, name, "gfn1", mixer, tol, intdriver=intdriver)


@pytest.mark.skipif(not has_libcint, reason="libcint not available")
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", slist)
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_single_gfn2(dtype: torch.dtype, name: str, mixer: str) -> None:
    tol = sqrt(torch.finfo(dtype).eps) * 10
    single(dtype, name, "gfn2", mixer, tol, intdriver=labels.INTDRIVER_LIBCINT)


@pytest.mark.large
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", slist_more)
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
@pytest.mark.parametrize("intdriver", drivers)
def test_single_gfn1_more(
    dtype: torch.dtype, name: str, mixer: str, intdriver: int
) -> None:
    tol = sqrt(torch.finfo(dtype).eps) * 10
    single(dtype, name, "gfn1", mixer, tol, intdriver=intdriver)


@pytest.mark.skipif(not has_libcint, reason="libcint not available")
@pytest.mark.large
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", slist_more)
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_single_gfn2_more(dtype: torch.dtype, name: str, mixer: str) -> None:
    tol = sqrt(torch.finfo(dtype).eps) * 10
    single(dtype, name, "gfn2", mixer, tol, intdriver=labels.INTDRIVER_LIBCINT)


@pytest.mark.large
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", slist_large)
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_single_medium_gfn1(dtype: torch.dtype, name: str, mixer: str) -> None:
    """Test a few larger system."""
    tol = sqrt(torch.finfo(dtype).eps) * 10
    single(dtype, name, "gfn1", mixer, tol)


@pytest.mark.skipif(not has_libcint, reason="libcint not available")
@pytest.mark.large
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", slist_large)
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_single_medium_gfn2(dtype: torch.dtype, name: str, mixer: str) -> None:
    """Test a few larger system."""
    tol = sqrt(torch.finfo(dtype).eps) * 10
    single(dtype, name, "gfn2", mixer, tol)


@pytest.mark.large
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", ["S2", "LYS_xao_dist"])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_single_difficult_gfn1(
    dtype: torch.dtype, name: str, mixer: str
) -> None:
    """These systems do not reproduce tblite energies to high accuracy."""
    tol = 5e-3
    single(dtype, name, "gfn1", mixer, tol, scp_mode="potential")


@pytest.mark.skipif(not has_libcint, reason="libcint not available")
@pytest.mark.large
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", ["S2", "LYS_xao_dist"])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_single_difficult_gfn2(
    dtype: torch.dtype, name: str, mixer: str
) -> None:
    """These systems do not reproduce tblite energies to high accuracy."""
    tol = 5e-3
    single(dtype, name, "gfn2", mixer, tol, scp_mode="potential")


@pytest.mark.large
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", ["C60", "vancoh2"])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_single_large_gfn1(dtype: torch.dtype, name: str, mixer: str) -> None:
    """Test a large systems (only float32 as they take some time)."""
    tol = sqrt(torch.finfo(dtype).eps) * 10
    single(dtype, name, "gfn1", mixer, tol)


@pytest.mark.skipif(not has_libcint, reason="libcint not available")
@pytest.mark.large
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name", ["C60", "vancoh2"])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_single_large_gfn2(dtype: torch.dtype, name: str, mixer: str) -> None:
    """Test a large systems (only float32 as they take some time)."""
    tol = sqrt(torch.finfo(dtype).eps) * 10
    single(dtype, name, "gfn2", mixer, tol)


def batched(
    dtype: torch.dtype,
    name1: str,
    name2: str,
    gfn: str,
    mixer: str,
    scp_mode: str,
    tol: float,
    intdriver: int = labels.INTDRIVER_LIBCINT,
) -> None:
    dd: DD = {"device": DEVICE, "dtype": dtype}

    sample = samples[name1], samples[name2]
    numbers = pack(
        (
            sample[0]["numbers"].to(DEVICE),
            sample[1]["numbers"].to(DEVICE),
        )
    )
    positions = pack(
        (
            sample[0]["positions"].to(**dd),
            sample[1]["positions"].to(**dd),
        )
    )
    ref = pack(
        (
            sample[0][f"e{gfn}"].to(**dd),
            sample[1][f"e{gfn}"].to(**dd),
        )
    )
    charges = torch.tensor([0.0, 0.0], **dd)

    if gfn == "gfn1":
        par = GFN1_XTB
    elif gfn == "gfn2":
        par = GFN2_XTB
    else:
        assert False

    options = dict(
        opts,
        **{
            "damp": 0.05 if mixer == "simple" else 0.4,
            "damp_dynamic": mixer != "simple",
            "mixer": mixer,
            "scp_mode": scp_mode,
            "int_driver": intdriver,
            "f_atol": 0.1 * tol,
            "x_atol": 0.1 * tol,
        },
    )
    calc = Calculator(numbers, par, opts=options, **dd)

    result = calc.singlepoint(positions, charges)
    res = result.scf.sum(-1)
    assert pytest.approx(ref.cpu(), abs=tol, rel=tol) == res.cpu()


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name1", ["LiH"])
@pytest.mark.parametrize("name2", ["LiH", "SiH4"])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
@pytest.mark.parametrize("intdriver", drivers)
def test_batch_gfn1(
    dtype: torch.dtype, name1: str, name2: str, mixer: str, intdriver: int
) -> None:
    batched(
        dtype,
        name1,
        name2,
        "gfn1",
        mixer,
        scp_mode="charge",
        tol=sqrt(torch.finfo(dtype).eps) * 10,
        intdriver=intdriver,
    )


@pytest.mark.skipif(not has_libcint, reason="libcint not available")
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name1", ["LiH"])
@pytest.mark.parametrize("name2", ["LiH", "SiH4"])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_batch_gfn2(
    dtype: torch.dtype, name1: str, name2: str, mixer: str
) -> None:
    batched(
        dtype,
        name1,
        name2,
        "gfn2",
        mixer,
        scp_mode="fock",
        tol=sqrt(torch.finfo(dtype).eps) * 10,
        intdriver=labels.INTDRIVER_LIBCINT,
    )


def batched_unconverged(
    ref: Tensor,
    dtype: torch.dtype,
    name1: str,
    name2: str,
    name3: str,
    gfn: str,
    mixer: str,
    maxiter: int,
) -> None:
    """
    Regression test for unconverged case. For double precision, the reference
    values are different. Hence, the test only includes single precision.
    """
    tol = sqrt(torch.finfo(dtype).eps) * 10
    dd: DD = {"device": DEVICE, "dtype": dtype}

    sample = samples[name1], samples[name2], samples[name3]
    numbers = pack(
        (
            sample[0]["numbers"].to(DEVICE),
            sample[1]["numbers"].to(DEVICE),
            sample[2]["numbers"].to(DEVICE),
        )
    )
    positions = pack(
        (
            sample[0]["positions"].to(**dd),
            sample[1]["positions"].to(**dd),
            sample[2]["positions"].to(**dd),
        )
    )

    charges = torch.tensor([0.0, 0.0, 0.0], **dd)

    if gfn == "gfn1":
        par = GFN1_XTB
        scp_mode = "potential"
    elif gfn == "gfn2":
        par = GFN2_XTB
        scp_mode = "fock"
    else:
        assert False

    options = dict(
        opts,
        **{
            "damp": 0.3,
            "maxiter": maxiter,
            "mixer": mixer,
            "mix_guess": False,
            "scf_mode": "full",
            "scp_mode": scp_mode,
            "f_atol": tol,
            "x_atol": tol,
        },
    )
    calc = Calculator(numbers, par, opts=options, **dd)

    result = calc.singlepoint(positions, charges)
    res = result.scf.sum(-1)
    assert pytest.approx(ref.cpu(), abs=tol, rel=tol) == res.cpu()


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
def test_batch_unconverged_partly_anderson(dtype: torch.dtype) -> None:
    dd: DD = {"device": DEVICE, "dtype": dtype}

    # only for regression testing (copied unconverged energies)
    ref = torch.tensor(
        [-1.058598357054240, -0.8818244757849318, -4.017705657967151], **dd
    )

    batched_unconverged(ref, dtype, "H2", "LiH", "SiH4", "gfn1", "anderson", 0)

    # only for regression testing (copied unconverged energies)
    ref = torch.tensor(
        [-1.058598357054240, -0.882224299270184, -4.026326793876873], **dd
    )

    batched_unconverged(ref, dtype, "H2", "LiH", "SiH4", "gfn1", "anderson", 1)


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
def test_batch_unconverged_partly_simple(dtype: torch.dtype) -> None:
    dd: DD = {"device": DEVICE, "dtype": dtype}

    # only for regression testing (copied unconverged energies)
    ref = torch.tensor(
        [-1.058598357054241, -0.8818244757849318, -4.017705657967151], **dd
    )

    batched_unconverged(ref, dtype, "H2", "LiH", "SiH4", "gfn1", "simple", 0)

    # only for regression testing (copied unconverged energies)
    ref = torch.tensor(
        [-1.058598357054240, -0.882224299270184, -4.026326793876873], **dd
    )

    batched_unconverged(ref, dtype, "H2", "LiH", "SiH4", "gfn1", "anderson", 1)


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
def test_batch_unconverged_fully_anderson(dtype: torch.dtype) -> None:
    dd: DD = {"device": DEVICE, "dtype": dtype}

    # only for regression testing (copied unconverged energies)
    ref = torch.tensor(
        [-0.8818244757849318, -0.8818244757849318, -4.017705657967151], **dd
    )

    batched_unconverged(ref, dtype, "LiH", "LiH", "SiH4", "gfn1", "anderson", 0)


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
def test_batch_unconverged_fully_simple(
    dtype: torch.dtype,
) -> None:
    dd: DD = {"device": DEVICE, "dtype": dtype}

    # only for regression testing (copied unconverged energies)
    ref = torch.tensor(
        [-0.8818244757849318, -0.8818244757849318, -4.017705657967151], **dd
    )

    batched_unconverged(ref, dtype, "LiH", "LiH", "SiH4", "gfn1", "simple", 0)


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name1", ["H2"])
@pytest.mark.parametrize("name2", ["LiH"])
@pytest.mark.parametrize("name3", ["SiH4"])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_batch_three_gfn1(
    dtype: torch.dtype, name1: str, name2: str, name3: str, mixer: str
) -> None:
    batch_three(dtype, name1, name2, name3, "gfn1", mixer)


@pytest.mark.skipif(not has_libcint, reason="libcint not available")
@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("name1", ["H2"])
@pytest.mark.parametrize("name2", ["LiH"])
@pytest.mark.parametrize("name3", ["SiH4"])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_batch_three_gfn2(
    dtype: torch.dtype, name1: str, name2: str, name3: str, mixer: str
) -> None:
    batch_three(dtype, name1, name2, name3, "gfn2", mixer)


def batch_three(
    dtype: torch.dtype, name1: str, name2: str, name3: str, gfn: str, mixer: str
) -> None:
    tol = sqrt(torch.finfo(dtype).eps) * 10
    dd: DD = {"device": DEVICE, "dtype": dtype}

    sample = samples[name1], samples[name2], samples[name3]
    numbers = pack(
        (
            sample[0]["numbers"].to(DEVICE),
            sample[1]["numbers"].to(DEVICE),
            sample[2]["numbers"].to(DEVICE),
        )
    )
    positions = pack(
        (
            sample[0]["positions"].to(**dd),
            sample[1]["positions"].to(**dd),
            sample[2]["positions"].to(**dd),
        )
    )
    ref = pack(
        (
            sample[0][f"e{gfn}"].to(**dd),
            sample[1][f"e{gfn}"].to(**dd),
            sample[2][f"e{gfn}"].to(**dd),
        )
    )
    charges = torch.tensor([0.0, 0.0, 0.0], **dd)

    if gfn == "gfn1":
        par = GFN1_XTB
    elif gfn == "gfn2":
        par = GFN2_XTB
    else:
        assert False

    options = dict(
        opts,
        **{
            "damp": 0.1 if mixer == "simple" else 0.4,
            "mixer": mixer,
            "scf_mode": "full",
            "scp_mode": "fock",
            "f_atol": tol,
            "x_atol": tol,
        },
    )
    calc = Calculator(numbers, par, opts=options, **dd)

    result = calc.singlepoint(positions, charges)
    res = result.scf.sum(-1)
    assert pytest.approx(ref.cpu(), rel=tol, abs=tol) == res.cpu()


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
@pytest.mark.parametrize("mixer", ["anderson", "simple"])
def test_batch_special(dtype: torch.dtype, mixer: str) -> None:
    """
    Test case for https://github.com/grimme-lab/dxtb/issues/67.

    Note that the tolerance for the energy is quite high because atoms always
    show larger deviations w.r.t. the tblite reference. Secondly, this test
    should check if the overcounting in the IndexHelper and the corresponing
    additional padding upon spreading is prevented.
    """
    tol = 1e-2  # atoms show larger deviations
    dd: DD = {"device": DEVICE, "dtype": dtype}

    numbers = torch.tensor([[2, 2], [17, 0]], device=DEVICE)
    positions = pack(
        [
            torch.tensor([[0.0, 0.0, 0.0], [0.0, 0.0, 1.5]], **dd),
            torch.tensor([[0.0, 0.0, 0.0]], **dd),
        ]
    )
    chrg = torch.tensor([0.0, 0.0], **dd)
    ref = torch.tensor([-2.8629311088577, -4.1663539440167], **dd)

    options = dict(
        opts,
        **{
            "damp": 0.05 if mixer == "simple" else 0.4,
            "mixer": mixer,
        },
    )
    calc = Calculator(numbers, GFN1_XTB, opts=options, **dd)

    result = calc.singlepoint(positions, chrg)
    res = result.scf.sum(-1)
    assert pytest.approx(ref.cpu(), abs=tol) == res.cpu()
