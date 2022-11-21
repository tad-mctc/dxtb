"""
Calculation of coordination number with various counting functions.
"""

import torch

from ..constants import xtb
from ..data import cov_rad_d3
from ..typing import CountingFunction, Tensor


def get_coordination_number(
    numbers: Tensor,
    positions: Tensor,
    counting_function: CountingFunction,
    rcov: Tensor | None = None,
    cutoff: Tensor | None = None,
    **kwargs,
) -> Tensor:
    """
    Compute fractional coordination number using an exponential counting function.

    Parameters
    ----------
    numbers : Tensor
        Atomic numbers of molecular structure.
    positions : Tensor
        Atomic positions of molecular structure.
    counting_function : CountingFunction
        Calculate weight for pairs.
    rcov : Tensor | None, optional
        Covalent radii for each species. Defaults to `None`.
    cutoff : Tensor | None, optional
        Real-space cutoff. Defaults to `None`.
    kwargs : dict[str, Any]
        Pass-through arguments for counting function.

    Returns
    -------
    Tensor
        Coordination numbers for all atoms.

    Raises
    ------
    ValueError
        If shape mismatch between `numbers`, `positions` and `rcov` is detected.
    """

    if cutoff is None:
        cutoff = positions.new_tensor(xtb.NCOORD_DEFAULT_CUTOFF)
    if rcov is None:
        rcov = cov_rad_d3[numbers].type(positions.dtype).to(positions.device)
    if numbers.shape != rcov.shape:
        raise ValueError(
            f"Shape of covalent radii {rcov.shape} is not consistent with "
            f"({numbers.shape})."
        )
    if numbers.shape != positions.shape[:-1]:
        raise ValueError(
            f"Shape of positions ({positions.shape[:-1]}) is not consistent "
            f"with atomic numbers ({numbers.shape})."
        )

    real = numbers != 0
    mask = (
        real.unsqueeze(-2)
        * real.unsqueeze(-1)
        * ~torch.diag_embed(torch.ones_like(real))
    )

    distances = torch.where(
        mask,
        torch.cdist(positions, positions, p=2, compute_mode="use_mm_for_euclid_dist"),
        positions.new_tensor(torch.finfo(positions.dtype).eps),
    )

    rc = rcov.unsqueeze(-2) + rcov.unsqueeze(-1)
    cf = torch.where(
        mask * (distances <= cutoff),
        counting_function(distances, rc.type(positions.dtype), **kwargs),
        positions.new_tensor(0.0),
    )
    return torch.sum(cf, dim=-1)