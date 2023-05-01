"""
Collection of utility functions for matrices/tensors.
"""
from __future__ import annotations

import torch

from .._types import Size, Tensor


@torch.jit.script
def real_atoms(numbers: Tensor) -> Tensor:
    return numbers != 0


@torch.jit.script
def real_pairs(numbers: Tensor, diagonal: bool = False) -> Tensor:
    """
    Generates mask that differentiates real atom pairs and padding.

    Parameters
    ----------
    numbers : Tensor
        Atomic numbers
    diagonal : bool, optional
        Whether the diagonal should be masked, i.e. filled with `False`.
        Defaults to `False`, i.e., `True` remains on the diagonal for real atoms.

    Returns
    -------
    Tensor
        Mask for real atom pairs.
    """
    real = real_atoms(numbers)
    mask = real.unsqueeze(-2) * real.unsqueeze(-1)

    if diagonal is True:
        mask *= ~torch.diag_embed(torch.ones_like(real))
    return mask


@torch.jit.script
def real_triples(numbers: Tensor, diagonal: bool = False) -> Tensor:
    """
    Generates mask that differentiates real atom triples and padding.
    Parameters
    ----------
    numbers : Tensor
        Atomic numbers of the atoms in the system.
    diagonal : bool, optional
        Whether the diagonal should be masked, i.e. filled with `False`.
        Defaults to `False`, i.e., `True` remains on the diagonal for real atoms.
    Returns
    -------
    Tensor
        Mask for real atom triples.
    """
    real = real_pairs(numbers, diagonal=False)
    mask = real.unsqueeze(-3) * real.unsqueeze(-2) * real.unsqueeze(-1)
    if diagonal is True:
        mask *= ~torch.diag_embed(torch.ones_like(real))
    return mask


def t2int(x: Tensor) -> int:
    """
    Convert tensor to int.

    Parameters
    ----------
    x : Tensor
        Tensor to convert.

    Returns
    -------
    int
        Integer value of the tensor.
    """
    return int(x.item())


def symmetrize(x: Tensor) -> Tensor:
    """
    Symmetrize a tensor after checking if it is symmetric within a threshold.

    Parameters
    ----------
    x : Tensor
        Tensor to check and symmetrize.

    Returns
    -------
    Tensor
        Symmetrized tensor.

    Raises
    ------
    RuntimeError
        If the tensor is not symmetric within the threshold.
    """
    try:
        atol = torch.finfo(x.dtype).eps * 10
    except TypeError:
        atol = 1e-5

    if x.ndim < 2:
        raise RuntimeError("Only matrices and batches thereof allowed.")

    if not torch.allclose(x, x.mT, atol=atol):
        raise RuntimeError(
            f"Matrix appears to be not symmetric (atol={atol:.3e}, "
            f"dtype={x.dtype})."
        )

    return (x + x.mT) / 2


def reshape_fortran(x: Tensor, shape: Size) -> Tensor:
    """
    Implements Fortran's `reshape` function (column-major).

    Parameters
    ----------
    x : Tensor
        Input tensor
    shape : Size
        Output size to which `x` is reshaped.

    Returns
    -------
    Tensor
        Reshaped tensor of size `shape`.
    """
    if len(x.shape) > 0:
        x = x.permute(*reversed(range(len(x.shape))))
    return x.reshape(*reversed(shape)).permute(*reversed(range(len(shape))))