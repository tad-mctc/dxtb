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
Test Calculator setup.
"""

from __future__ import annotations

import pytest
import torch
from tad_mctc.exceptions import DtypeError

from dxtb import GFN1_XTB as par
from dxtb import Calculator, labels
from dxtb._src.timing import timer
from dxtb.typing import DD

from ..conftest import DEVICE


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
def test_fail(dtype: torch.dtype) -> None:
    dd: DD = {"dtype": dtype, "device": DEVICE}

    numbers = torch.tensor([6, 1, 1, 1, 1], **dd)

    with pytest.raises(DtypeError):
        Calculator(numbers, par, opts={"verbosity": 0})

    # because of the exception, the timer for the setup is never stopped
    timer.reset()


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
def test_fail_charge_single(dtype: torch.dtype) -> None:
    dd: DD = {"dtype": dtype, "device": DEVICE}

    numbers = torch.tensor([3, 1], device=DEVICE)
    positions = torch.zeros(2, 3, **dd)

    calc = Calculator(numbers, par, opts={"verbosity": 0})

    # charge must be a scalar for single structure
    with pytest.raises(ValueError) as excinfo:
        charge = torch.tensor([0.0], **dd)
        calc.singlepoint(positions, chrg=charge)

    assert "Charge tensor has only one element" in str(excinfo)


@pytest.mark.parametrize("dtype", [torch.float, torch.double])
def test_fail_charge_batch(dtype: torch.dtype) -> None:
    dd: DD = {"dtype": dtype, "device": DEVICE}

    numbers = torch.tensor([[3, 1], [3, 1]], device=DEVICE)
    positions = torch.zeros(2, 2, 3, **dd)

    calc = Calculator(numbers, par, opts={"verbosity": 0})
    with pytest.raises(ValueError) as excinfo:
        charge = torch.tensor([[0.0], [0.0]], **dd)
        calc.singlepoint(positions, chrg=charge)

    assert "Charge tensor has more than 1 dimension" in str(excinfo)

    with pytest.raises(ValueError) as excinfo:
        charge = torch.tensor(0.0, **dd)
        calc.singlepoint(positions, chrg=charge)

    assert "Charge tensor has invalid shape" in str(excinfo)


def run_asserts(c: Calculator, dtype: torch.dtype) -> None:
    assert c.dtype == dtype
    assert c.classicals.dtype == dtype
    assert c.interactions.dtype == dtype
    assert c.opts.dtype == dtype

    assert c.integrals.dtype == dtype
    assert c.integrals.hcore is not None
    assert c.integrals.hcore.dtype == dtype
    assert c.integrals.overlap is not None
    assert c.integrals.overlap.dtype == dtype

    assert c.integrals.dtype == dtype


@pytest.mark.parametrize(
    "int_driver", [labels.INTDRIVER_LIBCINT, labels.INTDRIVER_AUTOGRAD]
)
def test_change_type(int_driver: str) -> None:
    numbers = torch.tensor([6, 1, 1, 1, 1])
    calc = Calculator(
        numbers, par, opts={"int_driver": int_driver}, dtype=torch.double
    )

    calc = calc.type(torch.float32)
    run_asserts(calc, torch.float32)

    timer.reset()


@pytest.mark.parametrize(
    "int_driver", [labels.INTDRIVER_LIBCINT, labels.INTDRIVER_AUTOGRAD]
)
def test_change_type_after_energy(int_driver: str) -> None:
    dtype = torch.float64

    numbers = torch.tensor([1, 1])
    pos = torch.tensor([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=dtype)

    calc_64 = Calculator(
        numbers,
        par,
        dtype=dtype,
        opts={"int_driver": int_driver, "verbosity": 0},
    )
    calc_64.energy(pos)

    run_asserts(calc_64, dtype)

    # extra asserts on initialized
    bas = calc_64.integrals.mgr.driver.basis
    assert bas.dtype == dtype
    assert bas.ngauss.dtype == torch.uint8
    assert bas.pqn.dtype == torch.uint8
    assert bas.slater.dtype == dtype

    assert calc_64.integrals.hcore is not None
    assert calc_64.integrals.hcore.dtype == dtype
    assert calc_64.integrals.overlap is not None
    assert calc_64.integrals.overlap.dtype == dtype

    ############################################################################

    calc_32 = calc_64.type(torch.float32)
    run_asserts(calc_32, torch.float32)

    timer.reset()
