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
Data for SCF energies of charged samples.
"""

from __future__ import annotations

import torch
from tad_mctc.data.molecules import merge_nested_dicts, mols

from dxtb._src.typing import Molecule, Tensor, TypedDict


class Refs(TypedDict):
    """Format of reference records containing GFN1-xTB and GFN2-xTB reference values."""

    charge: Tensor
    """Total charge of the molecule"""

    egfn1: Tensor
    """SCF energy for GFN1-xTB"""

    egfn2: Tensor
    """SCF energy for GFN2-xTB"""


class Record(Molecule, Refs):
    """Store for molecular information and reference values"""


refs: dict[str, Refs] = {
    "Ag2Cl22-": {
        "charge": torch.tensor(-2.0),
        "egfn1": torch.tensor(-2.5297870091005e01, dtype=torch.float64),
        "egfn2": torch.tensor(-2.6630938354884e01, dtype=torch.float64),
    },
    "Al3+Ar6": {
        "charge": torch.tensor(3.0),
        "egfn1": torch.tensor(-3.6303223981129e01, dtype=torch.float64),
        "egfn2": torch.tensor(-2.5062823108448e01, dtype=torch.float64),
    },
    "AD7en+": {
        "charge": torch.tensor(1.0),
        "egfn1": torch.tensor(-4.3226840214360e01, dtype=torch.float64),
        "egfn2": torch.tensor(-4.2927443646640e01, dtype=torch.float64),
    },
    "C2H4F+": {
        "charge": torch.tensor(1.0),
        "egfn1": torch.tensor(-1.1004178291636e01, dtype=torch.float64),
        "egfn2": torch.tensor(-1.0549228548747e01, dtype=torch.float64),
    },
    "ZnOOH-": {
        "charge": torch.tensor(-1.0),
        "egfn1": torch.tensor(-1.0913986485487e01, dtype=torch.float64),
        "egfn2": torch.tensor(-9.3774182834381e00, dtype=torch.float64),
    },
}


samples: dict[str, Record] = merge_nested_dicts(mols, refs)
