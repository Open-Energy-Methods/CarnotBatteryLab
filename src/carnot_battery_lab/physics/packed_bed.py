"""Geometry-resolved packed-bed hydraulic primitives.

These correlations do not establish a validated TES model alone. Applicability
requires review for particle shape, channeling, wall effects and gas heating.
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PackedBedGeometry:
    length_m: float
    diameter_m: float
    particle_diameter_m: float
    porosity: float

    def __post_init__(self) -> None:
        if min(self.length_m, self.diameter_m, self.particle_diameter_m) <= 0:
            raise ValueError("geometric lengths must be >0")
        if not all(math.isfinite(x) for x in (self.length_m, self.diameter_m, self.particle_diameter_m, self.porosity)):
            raise ValueError("geometry must be finite")
        if not (0 < self.porosity < 1):
            raise ValueError("porosity must lie strictly between zero and one")
        if self.particle_diameter_m > self.diameter_m/5:
            raise ValueError("particle-to-tank diameter ratio is too large for nominal bulk correlations")

    @property
    def cross_section_m2(self) -> float:
        return math.pi * self.diameter_m**2 / 4

    @property
    def bed_volume_m3(self) -> float:
        return self.cross_section_m2 * self.length_m

    @property
    def specific_interfacial_area_m2_per_m3(self) -> float:
        """Spherical particles only; irregular rock requires shape correction."""
        return 6*(1-self.porosity)/self.particle_diameter_m


def ergun_pressure_drop_Pa(
    bed: PackedBedGeometry, superficial_velocity_m_per_s: float,
    rho_kg_per_m3: float, dynamic_viscosity_Pa_s: float
) -> float:
    """Ergun (1952) for incompressible uniform properties, nonnegative flow.

    ΔP = L [150 μ (1-ε)^2 U /(ε^3 d_p^2) +
              1.75 ρ (1-ε) U²/(ε^3 d_p)].
    """
    args = (superficial_velocity_m_per_s,rho_kg_per_m3,dynamic_viscosity_Pa_s)
    if not all(math.isfinite(x) for x in args):
        raise ValueError("fluid inputs must be finite")
    if superficial_velocity_m_per_s < 0 or rho_kg_per_m3 <= 0 or dynamic_viscosity_Pa_s <= 0:
        raise ValueError("invalid fluid inputs")
    e, dp, U = bed.porosity, bed.particle_diameter_m, superficial_velocity_m_per_s
    return bed.length_m * (
        150*dynamic_viscosity_Pa_s*(1-e)**2*U/(e**3*dp**2)
        + 1.75*rho_kg_per_m3*(1-e)*U*U/(e**3*dp)
    )


def hydraulic_power_W(delta_p_Pa: float, volumetric_flow_m3_s: float, efficiency: float) -> float:
    """Incompressible fan/pump power approximation, not gas-compressor work."""
    if not all(math.isfinite(x) for x in (delta_p_Pa,volumetric_flow_m3_s,efficiency)):
        raise ValueError("invalid hydraulic inputs")
    if delta_p_Pa < 0 or volumetric_flow_m3_s < 0 or not (0 < efficiency <= 1):
        raise ValueError("invalid hydraulic inputs")
    return delta_p_Pa*volumetric_flow_m3_s/efficiency
