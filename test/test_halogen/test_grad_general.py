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

from dxtb import GFN1_XTB as par
from dxtb import IndexHelper
from dxtb._src.components.classicals import new_halogen
from dxtb._src.typing import DD

from .samples import samples

device = None


@pytest.mark.grad
@pytest.mark.parametrize("name", ["br2nh3"])
def test_grad_fail(name: str) -> None:
    dtype = torch.double
    dd: DD = {"device": device, "dtype": dtype}

    sample = samples[name]
    numbers = sample["numbers"].to(device)
    positions = sample["positions"].to(**dd)

    xb = new_halogen(numbers, par, **dd)
    if xb is None:
        assert False

    ihelp = IndexHelper.from_numbers(numbers, par)
    cache = xb.get_cache(numbers, ihelp)
    energy = xb.get_energy(positions, cache)

    with pytest.raises(RuntimeError):
        xb.get_gradient(energy, positions)
