"""
Run tests for Hessian of halogen bond correction.
"""
from __future__ import annotations

from math import sqrt

import pytest
import torch

from dxtb._types import DD
from dxtb.basis import IndexHelper
from dxtb.classical import new_halogen
from dxtb.param import GFN1_XTB as par
from dxtb.param import get_elem_angular
from dxtb.utils import batch, hessian

from ..utils import reshape_fortran
from .samples import samples

sample_list = ["br2nh3", "br2och2", "finch", "LiH", "SiH4", "MB16_43_01"]

device = None


@pytest.mark.parametrize("dtype", [torch.double])
@pytest.mark.parametrize("name", sample_list)
def test_single(dtype: torch.dtype, name: str) -> None:
    dd: DD = {"device": device, "dtype": dtype}
    tol = sqrt(torch.finfo(dtype).eps) * 100

    sample = samples[name]
    numbers = sample["numbers"].to(device)
    positions = sample["positions"].to(**dd)
    ref = reshape_fortran(
        sample["hessian"].to(**dd),
        torch.Size(2 * (numbers.shape[-1], 3)),
    )

    # variable to be differentiated
    positions.requires_grad_(True)

    xb = new_halogen(numbers, par, **dd)
    assert xb is not None

    ihelp = IndexHelper.from_numbers(numbers, get_elem_angular(par.element))
    cache = xb.get_cache(numbers, ihelp)

    # hessian
    hess = hessian(xb.get_energy, (positions, cache))
    assert pytest.approx(ref, abs=tol, rel=tol) == hess.detach()

    positions.detach_()


@pytest.mark.parametrize("dtype", [torch.double])
@pytest.mark.parametrize("name1", ["finch"])
@pytest.mark.parametrize("name2", sample_list)
def skip_test_batch(dtype: torch.dtype, name1: str, name2) -> None:
    dd: DD = {"device": device, "dtype": dtype}
    tol = sqrt(torch.finfo(dtype).eps) * 100

    sample1, sample2 = samples[name1], samples[name2]
    numbers = batch.pack(
        [
            sample1["numbers"].to(device),
            sample2["numbers"].to(device),
        ]
    )
    positions = batch.pack(
        [
            sample1["positions"].to(**dd),
            sample2["positions"].to(**dd),
        ]
    )

    ref = batch.pack(
        [
            reshape_fortran(
                sample1["hessian"].to(**dd),
                torch.Size(2 * (sample1["numbers"].to(device).shape[-1], 3)),
            ),
            reshape_fortran(
                sample2["hessian"].to(**dd),
                torch.Size(2 * (sample2["numbers"].shape[-1], 3)),
            ),
        ]
    )

    # variable to be differentiated
    positions.requires_grad_(True)

    xb = new_halogen(numbers, par, **dd)
    assert xb is not None

    ihelp = IndexHelper.from_numbers(numbers, get_elem_angular(par.element))
    cache = xb.get_cache(numbers, ihelp)

    hess = hessian(xb.get_energy, (positions, cache), is_batched=True)
    # print(hess)
    # print(ref_hess)
    # print(hess.shape)

    assert pytest.approx(ref, abs=tol, rel=tol) == hess.detach()

    positions.detach_()