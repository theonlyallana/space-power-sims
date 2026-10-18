"""Published LG M50 numbers, turned into the few functions our model calls.

Why this file exists separately from the time integrator: the integrator is
the physics we wrote, and this file is the measured (or fitted) behaviour of
one commercial cell. Mixing them makes it look as if a particle radius were
something we derived. It is not. The derivation is in EXPLAINED.md; the digits
are in params.yaml.

The open-circuit potentials are Chen et al.'s fits to half-cell data. The
ideal Nernst equation is where that idea starts, but intercalation materials
are not ideal solutions, so we do not pretend U(stoichiometry) falls out of
Nernst with unit activities.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from common.constants import FARADAY, GAS
from common.params import Entry, require


@dataclass(frozen=True)
class Cell:
    """Geometry and kinetics for one LG M50-shaped cell."""

    area_m2: float
    negative_thickness_m: float
    separator_thickness_m: float
    positive_thickness_m: float
    negative_radius_m: float
    positive_radius_m: float
    negative_porosity: float
    separator_porosity: float
    positive_porosity: float
    negative_active_fraction: float
    positive_active_fraction: float
    bruggeman: float
    cmax_negative: float
    cmax_positive: float
    electrolyte_concentration: float
    initial_negative: float
    initial_positive: float
    nominal_capacity_Ah: float
    voltage_min_V: float
    voltage_max_V: float
    alpha: float
    reference_temperature_K: float
    diffusivity_reference_negative: float
    activation_diffusion_negative: float
    diffusivity_reference_positive: float
    activation_diffusion_positive: float
    exchange_reference_negative: float
    activation_kinetics_negative: float
    exchange_reference_positive: float
    activation_kinetics_positive: float
    conductivity_cubic: float
    conductivity_three_halves: float
    conductivity_linear: float
    activation_conductivity: float
    ocp_negative: dict
    ocp_positive: dict
    shell_count: int
    shell_grading: float
    relative_tolerance: float
    absolute_tolerance: float

    @property
    def negative_surface_area_m2(self) -> float:
        """Active area of every graphite particle in the electrode.

        For spheres, area/volume is 3/R. Multiply by the active-material
        volume (fraction times electrode volume) and you have the surface the
        reaction current is spread over. That is why a small particle radius
        makes the same cell current a smaller interfacial current, and plating
        less likely.
        """
        return (
            3.0
            * self.negative_active_fraction
            / self.negative_radius_m
            * self.negative_thickness_m
            * self.area_m2
        )

    @property
    def positive_surface_area_m2(self) -> float:
        return (
            3.0
            * self.positive_active_fraction
            / self.positive_radius_m
            * self.positive_thickness_m
            * self.area_m2
        )

    def arrhenius(self, activation_energy_J_mol: float, temperature_K: float) -> float:
        """k(T) / k(T_ref) = exp[ (Ea/R) * (1/T_ref - 1/T) ].

        A lower temperature makes the exponent negative, so diffusion and
        charge transfer slow down. That is the whole of the cold-performance
        story before any particular cell is introduced.
        """
        return float(
            np.exp(
                activation_energy_J_mol
                / GAS
                * (1.0 / self.reference_temperature_K - 1.0 / temperature_K)
            )
        )

    def diffusivity_negative(self, temperature_K: float) -> float:
        return self.diffusivity_reference_negative * self.arrhenius(
            self.activation_diffusion_negative, temperature_K
        )

    def diffusivity_positive(self, temperature_K: float) -> float:
        return self.diffusivity_reference_positive * self.arrhenius(
            self.activation_diffusion_positive, temperature_K
        )

    def open_circuit_negative(self, stoichiometry: float) -> float:
        """Graphite potential vs Li/Li+, volts, from Chen's fit."""
        sto = float(np.clip(stoichiometry, 1e-6, 1.0 - 1e-6))
        c = self.ocp_negative
        return (
            c["exp_prefactor"] * np.exp(c["exp_slope"] * sto)
            + c["constant"]
            + c["tanh1_prefactor"] * np.tanh(c["tanh1_slope"] * (sto - c["tanh1_centre"]))
            + c["tanh2_prefactor"] * np.tanh(c["tanh2_slope"] * (sto - c["tanh2_centre"]))
            + c["tanh3_prefactor"] * np.tanh(c["tanh3_slope"] * (sto - c["tanh3_centre"]))
        )

    def open_circuit_positive(self, stoichiometry: float) -> float:
        """NMC potential vs Li/Li+, volts, from Chen's fit."""
        sto = float(np.clip(stoichiometry, 1e-6, 1.0 - 1e-6))
        c = self.ocp_positive
        return (
            c["linear_slope"] * sto
            + c["linear_intercept"]
            + c["tanh1_prefactor"] * np.tanh(c["tanh1_slope"] * (sto - c["tanh1_centre"]))
            + c["tanh2_prefactor"] * np.tanh(c["tanh2_slope"] * (sto - c["tanh2_centre"]))
            + c["tanh3_prefactor"] * np.tanh(c["tanh3_slope"] * (sto - c["tanh3_centre"]))
        )

    def exchange_current_negative(self, surface_concentration: float, temperature_K: float) -> float:
        """Butler-Volmer exchange current, A/m^2.

        The square-root form is the standard concentration dependence for a
        one-electron intercalation reaction. It goes to zero when the surface
        is empty or full, which is why the overpotential has to grow at the
        end of a charge: there is nowhere left to put the ion.
        """
        c_s = _surface_for_exchange(surface_concentration, self.cmax_negative)
        return (
            self.exchange_reference_negative
            * self.arrhenius(self.activation_kinetics_negative, temperature_K)
            * np.sqrt(self.electrolyte_concentration * c_s * (self.cmax_negative - c_s))
        )

    def exchange_current_positive(self, surface_concentration: float, temperature_K: float) -> float:
        c_s = _surface_for_exchange(surface_concentration, self.cmax_positive)
        return (
            self.exchange_reference_positive
            * self.arrhenius(self.activation_kinetics_positive, temperature_K)
            * np.sqrt(self.electrolyte_concentration * c_s * (self.cmax_positive - c_s))
        )

    def electrolyte_conductivity(self, temperature_K: float) -> float:
        """Nyman's fit at our fixed salt concentration, times an Arrhenius factor."""
        c = self.electrolyte_concentration / 1000.0
        sigma = (
            self.conductivity_cubic * c**3
            + self.conductivity_three_halves * c**1.5
            + self.conductivity_linear * c
        )
        return float(sigma * self.arrhenius(self.activation_conductivity, temperature_K))

    def ohmic_resistance(self, temperature_K: float) -> float:
        """Series resistance from Ohm's law through the three porous layers.

        kappa_eff = kappa * porosity^Bruggeman, then R = sum(thickness /
        kappa_eff) / electrode area. We leave out the solid-phase resistance.
        The positive electrode's electronic conductivity in this parameter set
        is poor (0.18 S/m), so that omission is one reason a full
        Doyle-Fuller-Newman model is the cross-check rather than a duplicate
        of this file.
        """
        kappa = self.electrolyte_conductivity(temperature_K)
        terms = (
            self.negative_thickness_m / (kappa * self.negative_porosity**self.bruggeman),
            self.separator_thickness_m / (kappa * self.separator_porosity**self.bruggeman),
            self.positive_thickness_m / (kappa * self.positive_porosity**self.bruggeman),
        )
        return float(sum(terms) / self.area_m2)

    def electrode_moles(self, concentration: float, active_fraction: float, thickness_m: float) -> float:
        """Lithium inventory in one electrode, moles, at a uniform concentration."""
        return float(concentration * active_fraction * thickness_m * self.area_m2)


def _surface_for_exchange(surface_concentration: float, maximum: float) -> float:
    """Keep the exchange-current square root defined without freezing it.

    A floor one mol/m³ short of full holds the exchange current constant while
    the outer shell is still filling. On a cold discharge that draws a step
    down to that frozen overpotential, then a plateau, instead of letting the
    voltage fall through the cut-off as the surface fills. The floor here is
    a tiny fraction of the maximum, small enough that the cut-off arrives
    while the kinetics are still moving.
    """
    floor = 1e-10 * maximum
    return float(np.clip(surface_concentration, floor, maximum - floor))


def _float(book: dict[str, Entry], name: str) -> float:
    return float(require(book, name).value)


def cell_from_params(book: dict[str, Entry]) -> Cell:
    """Build the cell from the parameter book. No defaults hide in this function."""
    height = _float(book, "electrode_height_m")
    width = _float(book, "electrode_width_m")
    return Cell(
        area_m2=height * width,
        negative_thickness_m=_float(book, "negative_electrode_thickness_m"),
        separator_thickness_m=_float(book, "separator_thickness_m"),
        positive_thickness_m=_float(book, "positive_electrode_thickness_m"),
        negative_radius_m=_float(book, "negative_particle_radius_m"),
        positive_radius_m=_float(book, "positive_particle_radius_m"),
        negative_porosity=_float(book, "negative_electrolyte_porosity"),
        separator_porosity=_float(book, "separator_porosity"),
        positive_porosity=_float(book, "positive_electrolyte_porosity"),
        negative_active_fraction=_float(book, "negative_active_volume_fraction"),
        positive_active_fraction=_float(book, "positive_active_volume_fraction"),
        bruggeman=_float(book, "bruggeman_coefficient"),
        cmax_negative=_float(book, "maximum_concentration_negative_mol_m3"),
        cmax_positive=_float(book, "maximum_concentration_positive_mol_m3"),
        electrolyte_concentration=_float(book, "electrolyte_concentration_mol_m3"),
        initial_negative=_float(book, "initial_concentration_negative_mol_m3"),
        initial_positive=_float(book, "initial_concentration_positive_mol_m3"),
        nominal_capacity_Ah=_float(book, "nominal_capacity_Ah"),
        voltage_min_V=_float(book, "lower_voltage_cutoff_V"),
        voltage_max_V=_float(book, "upper_voltage_cutoff_V"),
        alpha=_float(book, "charge_transfer_coefficient"),
        reference_temperature_K=_float(book, "reference_temperature_K"),
        diffusivity_reference_negative=_float(book, "diffusivity_reference_negative_m2_s"),
        activation_diffusion_negative=_float(book, "activation_energy_diffusion_negative_J_mol"),
        diffusivity_reference_positive=_float(book, "diffusivity_reference_positive_m2_s"),
        activation_diffusion_positive=_float(book, "activation_energy_diffusion_positive_J_mol"),
        exchange_reference_negative=_float(book, "exchange_current_reference_negative"),
        activation_kinetics_negative=_float(book, "activation_energy_kinetics_negative_J_mol"),
        exchange_reference_positive=_float(book, "exchange_current_reference_positive"),
        activation_kinetics_positive=_float(book, "activation_energy_kinetics_positive_J_mol"),
        conductivity_cubic=_float(book, "electrolyte_conductivity_cubic_coeff"),
        conductivity_three_halves=_float(book, "electrolyte_conductivity_three_halves_coeff"),
        conductivity_linear=_float(book, "electrolyte_conductivity_linear_coeff"),
        activation_conductivity=_float(book, "activation_energy_conductivity_J_mol"),
        ocp_negative=dict(require(book, "ocp_negative_coefficients").value),
        ocp_positive=dict(require(book, "ocp_positive_coefficients").value),
        shell_count=int(require(book, "particle_shell_count").value),
        shell_grading=_float(book, "particle_shell_grading"),
        relative_tolerance=_float(book, "ode_relative_tolerance"),
        absolute_tolerance=_float(book, "ode_absolute_tolerance"),
    )
