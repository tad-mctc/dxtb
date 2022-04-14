# This file is part of xtbml.

"""
Definition of energy terms as abstract base class for classical interactions.
"""

from typing import Optional, Tuple
from pydantic import BaseModel
from abc import ABC, abstractmethod
from torch import Tensor

from xtbml.exlibs.tbmalt import Geometry

# TODO: allow for usability with base Params object
class Energy_Contribution(BaseModel, ABC):
    """
    Abstract base class for calculation of classical contributions, like repulsion interactions.
    This class provides a method to retrieve the contributions to the energy, gradient and virial
    within a given cutoff.
    """  # TODOC

    geometry: Geometry
    """Molecular structure data"""

    trans: Optional[Tensor] = None
    """Lattice points"""

    cutoff: Optional[float] = None
    """Real space cutoff"""

    energy: Optional[Tensor] = None  # single value, needs gradient
    """Repulsion energy"""

    gradient: Optional[Tensor] = None
    """Molecular gradient of the repulsion energy"""

    sigma: Optional[Tensor] = None
    """Strain derivatives of the repulsion energy"""

    class Config:
        # allow for geometry and tensor fields
        arbitrary_types_allowed = True

    @abstractmethod
    def get_engrad(self) -> Tuple[Tensor, Tensor]:
        """
        Obtain energy and gradient for classical contribution
        (energy is calculated during this step).
        For periodic applications also calculate virial force.
        """
        return
