"""
The GFN1-xTB Hamiltonian.
"""

import torch

from ..basis import IndexHelper
from ..constants import EV2AU
from ..data import atomic_rad
from ..param import Param, get_elem_param, get_elem_valence, get_pair_param
from ..typing import Tensor, TensorLike
from ..utils import symmetrize

PAD = -1
"""Value used for padding of tensors."""


class Hamiltonian(TensorLike):
    """Hamiltonian from parametrization."""

    numbers: Tensor
    """Atomic numbers of the atoms in the system."""
    unique: Tensor
    """Unique species of the system."""

    par: Param
    """Representation of parametrization of xtb model."""

    ihelp: IndexHelper
    """Helper class for indexing."""

    hscale: Tensor
    """Off-site scaling factor for the Hamiltonian."""
    kcn: Tensor
    """Coordination number dependent shift of the self energy."""
    kpair: Tensor
    """Element-pair-specific parameters for scaling the Hamiltonian."""
    refocc: Tensor
    """Reference occupation numbers."""
    selfenergy: Tensor
    """Self-energy of each species."""
    shpoly: Tensor
    """Polynomial parameters for the distant dependent scaling."""
    valence: Tensor
    """Whether the shell belongs to the valence shell."""

    en: Tensor
    """Pauling electronegativity of each species."""
    rad: Tensor
    """Van-der-Waals radius of each species."""

    def __init__(
        self,
        numbers: Tensor,
        par: Param,
        ihelp: IndexHelper,
        device: torch.device | None = None,
        dtype: torch.dtype | None = None,
    ) -> None:
        super().__init__(device, dtype)
        self.numbers = numbers
        self.unique = torch.unique(numbers)
        self.par = par
        self.ihelp = ihelp

        # atom-resolved parameters
        self.rad = atomic_rad[self.unique].type(self.dtype).to(device=self.device)
        self.en = self._get_elem_param("en")

        # shell-resolved element parameters
        self.kcn = self._get_elem_param("kcn")
        self.selfenergy = self._get_elem_param("levels")
        self.shpoly = self._get_elem_param("shpoly")
        self.refocc = self._get_elem_param("refocc")
        self.valence = self._get_elem_valence()

        # shell-pair-resolved pair parameters
        self.hscale = self._get_hscale()
        self.kpair = self._get_pair_param(self.par.hamiltonian.xtb.kpair)

        # unit conversion
        self.selfenergy = self.selfenergy * EV2AU
        self.kcn = self.kcn * EV2AU

        if any(
            tensor.dtype != self.dtype
            for tensor in (
                self.hscale,
                self.kcn,
                self.kpair,
                self.refocc,
                self.selfenergy,
                self.shpoly,
                self.en,
                self.rad,
            )
        ):
            raise ValueError("All tensors must have same dtype")

        if any(
            tensor.device != self.device
            for tensor in (
                self.numbers,
                self.unique,
                self.ihelp,
                self.hscale,
                self.kcn,
                self.kpair,
                self.refocc,
                self.selfenergy,
                self.shpoly,
                self.valence,
                self.en,
                self.rad,
            )
        ):
            raise ValueError("All tensors must be on the same device")

    def get_occupation(self):
        """
        Obtain the reference occupation numbers for each orbital.
        """

        refocc = self.ihelp.spread_ushell_to_orbital(self.refocc)
        orb_per_shell = self.ihelp.spread_shell_to_orbital(
            self.ihelp.orbitals_per_shell
        )

        return torch.where(
            orb_per_shell != 0, refocc / orb_per_shell, refocc.new_tensor(0)
        )

    def _get_elem_param(self, key: str) -> Tensor:
        """Obtain element parameters for species.

        Parameters
        ----------
        key : str
            Name of the parameter to be retrieved.

        Returns
        -------
        Tensor
            Parameters for each species.
        """

        return get_elem_param(
            self.unique,
            self.par.element,
            key,
            pad_val=PAD,
            device=self.device,
            dtype=self.dtype,
        )

    def _get_elem_valence(self):
        """Obtain "valence" parameters for shells of species.

        Returns
        -------
        Tensor
            Valence parameters for each species.
        """

        return get_elem_valence(
            self.unique,
            self.par.element,
            pad_val=PAD,
            device=self.device,
            dtype=torch.bool,
        )

    def _get_pair_param(self, pair: dict[str, float]) -> Tensor:
        """Obtain element-pair-specific parameters for all species.

        Parameters
        ----------
        pair : dict[str, float]
            Pair parametrization.

        Returns
        -------
        Tensor
            Pair parameters for each species.
        """

        return get_pair_param(
            self.unique.tolist(), pair, device=self.device, dtype=self.dtype
        )

    def _get_hscale(self) -> Tensor:
        """Obtain the off-site scaling factor for the Hamiltonian.

        Returns
        -------
        Tensor
            Off-site scaling factor for the Hamiltonian.
        """

        angular2label = {
            0: "s",
            1: "p",
            2: "d",
            3: "f",
            4: "g",
        }

        def get_ksh(ushells: Tensor) -> Tensor:
            ksh = torch.ones(
                (len(ushells), len(ushells)), dtype=self.dtype, device=self.device
            )
            shell = self.par.hamiltonian.xtb.shell
            kpol = self.par.hamiltonian.xtb.kpol

            for i, ang_i in enumerate(ushells):
                ang_i = angular2label.get(int(ang_i.item()), PAD)

                if self.valence[i] == 0:
                    kii = kpol
                else:
                    kii = shell.get(f"{ang_i}{ang_i}", 1.0)

                for j, ang_j in enumerate(ushells):
                    ang_j = angular2label.get(int(ang_j.item()), PAD)

                    if self.valence[j] == 0:
                        kjj = kpol
                    else:
                        kjj = shell.get(f"{ang_j}{ang_j}", 1.0)

                    # only if both belong to the valence shell,
                    # we will read from the parametrization
                    if self.valence[i] == 1 and self.valence[j] == 1:
                        # check both "sp" and "ps"
                        ksh[i, j] = shell.get(
                            f"{ang_i}{ang_j}",
                            shell.get(
                                f"{ang_j}{ang_i}",
                                (kii + kjj) / 2.0,
                            ),
                        )
                    else:
                        ksh[i, j] = (kii + kjj) / 2.0

            return ksh

        ushells = self.ihelp.unique_angular
        if ushells.ndim > 1:
            ksh = torch.ones(
                (ushells.shape[0], ushells.shape[1], ushells.shape[1]),
                dtype=self.dtype,
                device=self.device,
            )
            for _batch in range(ushells.shape[0]):
                ksh[_batch] = get_ksh(ushells[_batch])

            return ksh

        return get_ksh(ushells)

    def build(
        self, positions: Tensor, overlap: Tensor, cn: Tensor | None = None
    ) -> Tensor:
        """Build the xTB Hamiltonian

        Parameters
        ----------
        overlap : Tensor
            Overlap matrix.
        cn : Tensor | None, optional
            Coordination number, by default None

        Returns
        -------
        Tensor
            Hamiltonian
        """

        real = self.numbers != 0
        mask = real.unsqueeze(-1) * real.unsqueeze(-2)
        real_shell = self.ihelp.spread_atom_to_shell(self.numbers) != 0
        mask_shell = real_shell.unsqueeze(-2) * real_shell.unsqueeze(-1)

        zero = torch.tensor(0.0, device=self.device, dtype=self.dtype)

        # ----------------
        # Eq.29: H_(mu,mu)
        # ----------------
        if cn is None:
            cn = torch.zeros_like(self.numbers).type(self.dtype)

        kcn = self.ihelp.spread_ushell_to_shell(self.kcn)

        # formula differs from paper to be consistent with GFN2 -> "kcn" adapted
        selfenergy = self.ihelp.spread_ushell_to_shell(
            self.selfenergy
        ) - kcn * self.ihelp.spread_atom_to_shell(cn)

        # ----------------------
        # Eq.24: PI(R_AB, l, l')
        # ----------------------
        distances = torch.cdist(
            positions, positions, p=2, compute_mode="use_mm_for_euclid_dist"
        )
        rad = self.ihelp.spread_uspecies_to_atom(self.rad)
        rr = torch.where(
            mask * ~torch.diag_embed(torch.ones_like(real)),
            distances / (rad.unsqueeze(-1) + rad.unsqueeze(-2)),
            distances.new_tensor(torch.finfo(distances.dtype).eps),
        )
        rr_sh = self.ihelp.spread_atom_to_shell(
            torch.sqrt(rr),
            (-2, -1),
        )

        shpoly = self.ihelp.spread_ushell_to_shell(self.shpoly)

        var_pi = (1.0 + shpoly.unsqueeze(-1) * rr_sh) * (
            1.0 + shpoly.unsqueeze(-2) * rr_sh
        )

        # --------------------
        # Eq.28: X(EN_A, EN_B)
        # --------------------
        en = self.ihelp.spread_uspecies_to_shell(self.en)
        var_x = torch.where(
            mask_shell,
            1.0
            + self.par.hamiltonian.xtb.enscale
            * torch.pow(en.unsqueeze(-1) - en.unsqueeze(-2), 2.0),
            zero,
        )

        # --------------------
        # Eq.23: K_{AB}^{l,l'}
        # --------------------
        kpair = self.ihelp.spread_uspecies_to_shell(self.kpair, dim=(-2, -1))
        hscale = self.ihelp.spread_ushell_to_shell(self.hscale, dim=(-2, -1))
        valence = self.ihelp.spread_ushell_to_shell(self.valence)

        var_k = torch.where(
            valence.unsqueeze(-1) * valence.unsqueeze(-2),
            hscale * kpair * var_x,
            hscale,
        )

        # ------------
        # Eq.23: H_EHT
        # ------------
        var_h = torch.where(
            mask_shell,
            0.5 * (selfenergy.unsqueeze(-1) + selfenergy.unsqueeze(-2)),
            zero,
        )

        # scale only off-diagonals
        mask_shell = mask_shell * ~torch.diag_embed(torch.ones_like(real_shell))
        h0 = torch.where(mask_shell, var_pi * var_k * var_h, var_h)

        h = self.ihelp.spread_shell_to_orbital(h0, dim=(-2, -1))
        hcore = h * overlap

        # force symmetry to avoid problems through numerical errors
        return symmetrize(hcore)

    def to(self, device: torch.device) -> "Hamiltonian":
        """
        Returns a copy of the `Hamiltonian` instance on the specified device.

        This method creates and returns a new copy of the `Hamiltonian` instance
        on the specified device "``device``".

        Parameters
        ----------
        device : torch.device
            Device to which all associated tensors should be moved.

        Returns
        -------
        Hamiltonian
            A copy of the `Hamiltonian` instance placed on the specified device.

        Notes
        -----
        If the `Hamiltonian` instance is already on the desired device `self`
        will be returned.
        """
        if self.__device == device:
            return self

        return self.__class__(
            self.numbers.to(device=device),
            self.par,
            self.ihelp.to(device=device),
            device=device,
        )

    def type(self, dtype: torch.dtype) -> "Hamiltonian":
        """
        Returns a copy of the `Hamiltonian` instance with specified floating point type.
        This method creates and returns a new copy of the `Hamiltonian` instance
        with the specified dtype.

        Parameters
        ----------
        dtype : torch.dtype
            Type of the floating point numbers used by the `Hamiltonian` instance.

        Returns
        -------
        Hamiltonian
            A copy of the `Hamiltonian` instance with the specified dtype.

        Notes
        -----
        If the `Hamiltonian` instance has already the desired dtype `self` will
        be returned.
        """
        if self.__dtype == dtype:
            return self

        return self.__class__(
            self.numbers.type(dtype=torch.long),
            self.par,
            self.ihelp.type(dtype=dtype),
            dtype=dtype,
        )