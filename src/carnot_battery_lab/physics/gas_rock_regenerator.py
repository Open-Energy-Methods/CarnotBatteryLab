"""Conservative reduced-order two-temperature gas/rock TES for charge-only research.

Fluid/solid temperatures are separate 1-D finite-volume states. Upwind
advection in the gas and geometry-linked gas/rock heat transfer; one lumped
wall-loss term distributed across solid cells. Stiff time integration is
independent of spatial resolution. Constant nominal densities/cp: this is
NOT yet a temperature/pressure-resolved industrial bed design.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from .packed_bed import PackedBedGeometry, ergun_pressure_drop_Pa, hydraulic_power_W


@dataclass(frozen=True)
class GasRockBed:
    geometry: PackedBedGeometry = field(default_factory=lambda: PackedBedGeometry(
        length_m=4.0, diameter_m=5.0, particle_diameter_m=0.045, porosity=0.4))
    cells: int = 16
    gas_density_kg_m3: float = 2.5
    gas_cp_J_kgK: float = 1005.0
    gas_viscosity_Pa_s: float = 2.35e-5
    gas_conductivity_W_mK: float = 0.033
    rock_density_kg_m3: float = 2600.0
    rock_cp_J_kgK: float = 850.0
    ambient_K: float = 293.15
    wall_UA_W_K: float = 120.0
    blower_efficiency: float = 0.7

    def __post_init__(self) -> None:
        if isinstance(self.cells,bool) or not isinstance(self.cells,int) or self.cells<2:
            raise ValueError("bed requires at least 2 cells")
        values=(self.gas_density_kg_m3,self.gas_cp_J_kgK,self.gas_viscosity_Pa_s,
                self.gas_conductivity_W_mK,self.rock_density_kg_m3,
                self.rock_cp_J_kgK,self.ambient_K)
        if not all(math.isfinite(x) and x>0 for x in values):
            raise ValueError("bed properties and reference temperature must be positive")
        if not math.isfinite(self.wall_UA_W_K) or self.wall_UA_W_K<0:
            raise ValueError("bed wall UA must be nonnegative finite")
        if not 0<self.blower_efficiency<=1:
            raise ValueError("blower efficiency must lie in (0,1]")


@dataclass(frozen=True)
class BedState:
    fluid_temperature_K: tuple[float,...]
    solid_temperature_K: tuple[float,...]

    @classmethod
    def uniform(cls,bed:GasRockBed,temperature_C:float) -> "BedState":
        t=temperature_C+273.15
        if t<=0 or not math.isfinite(t):
            raise ValueError("initial temperature outside physical domain")
        return cls((t,)*bed.cells,(t,)*bed.cells)


@dataclass(frozen=True)
class BedStep:
    final_state: BedState
    inlet_temperature_K: float
    mean_outlet_temperature_K: float
    first_temperature_K: float
    final_outlet_temperature_K: float
    heat_from_hot_gas_J: float
    heat_loss_to_ambient_J: float
    stored_energy_change_J: float
    energy_residual_J: float
    pressure_drop_Pa: float
    blower_electric_W: float
    particle_reynolds: float
    nusselt: float
    h_fluid_solid_W_m2K: float
    solver_nfev: int


def bed_energy_J(bed:GasRockBed,state:BedState) -> float:
    if len(state.fluid_temperature_K)!=bed.cells or len(state.solid_temperature_K)!=bed.cells:
        raise ValueError("bed state length does not match cell count")
    v=bed.geometry.bed_volume_m3/bed.cells
    cf=v*bed.geometry.porosity*bed.gas_density_kg_m3*bed.gas_cp_J_kgK
    cs=v*(1-bed.geometry.porosity)*bed.rock_density_kg_m3*bed.rock_cp_J_kgK
    return cf*sum(state.fluid_temperature_K)+cs*sum(state.solid_temperature_K)


def advance_bed(
    bed:GasRockBed, state:BedState, *, inlet_K:float, mass_flow_kg_s:float,
    dt_s:float, relative_tolerance:float=1e-7
) -> BedStep:
    if (not math.isfinite(inlet_K) or inlet_K<=0 or
        not math.isfinite(mass_flow_kg_s) or mass_flow_kg_s<0 or
        not math.isfinite(dt_s) or dt_s<=0 or
        not (0<relative_tolerance<=1e-3)):
        raise ValueError("invalid bed step conditions")
    if len(state.fluid_temperature_K)!=bed.cells or len(state.solid_temperature_K)!=bed.cells:
        raise ValueError("invalid bed state")
    n=bed.cells
    v=bed.geometry.bed_volume_m3/n
    cf=v*bed.geometry.porosity*bed.gas_density_kg_m3*bed.gas_cp_J_kgK
    cs=v*(1-bed.geometry.porosity)*bed.rock_density_kg_m3*bed.rock_cp_J_kgK
    mcp=mass_flow_kg_s*bed.gas_cp_J_kgK
    area=bed.geometry.cross_section_m2
    u=mass_flow_kg_s/(bed.gas_density_kg_m3*area)
    re=mass_flow_kg_s*bed.geometry.particle_diameter_m/(area*bed.gas_viscosity_Pa_s)
    if mass_flow_kg_s>0 and not (15.0<=re<=8500.0):
        raise ValueError("Wakao heat-transfer correlation outside published Re=15..8500 domain")
    pr=bed.gas_cp_J_kgK*bed.gas_viscosity_Pa_s/bed.gas_conductivity_W_mK
    nu=2.0+1.1*(re**0.6)*(pr**(1.0/3.0))
    h=nu*bed.gas_conductivity_W_mK/bed.geometry.particle_diameter_m
    conductance_cell=h*bed.geometry.specific_interfacial_area_m2_per_m3*v
    wall_cell=bed.wall_UA_W_K/n
    pressure_drop=ergun_pressure_drop_Pa(bed.geometry,u,bed.gas_density_kg_m3,
                                           bed.gas_viscosity_Pa_s)
    blower=hydraulic_power_W(pressure_drop,mass_flow_kg_s/bed.gas_density_kg_m3,
                             bed.blower_efficiency)
    before=bed_energy_J(bed,state)
    y0=np.array([*state.fluid_temperature_K,*state.solid_temperature_K,0.0,0.0],
                dtype=float)
    if not np.all(np.isfinite(y0)) or np.min(y0[:2*n])<=0:
        raise ValueError("nonfinite or nonphysical initial bed state")

    def derivative(_time:float,y:np.ndarray) -> np.ndarray:
        tf=y[:n]
        ts=y[n:2*n]
        upstream=np.concatenate(([inlet_K],tf[:-1]))
        transfer=conductance_cell*(tf-ts)
        wall=wall_cell*(ts-bed.ambient_K)
        out=np.zeros_like(y)
        out[:n]=(mcp*(upstream-tf)-transfer)/cf
        out[n:2*n]=(transfer-wall)/cs
        out[2*n]=mcp*(inlet_K-tf[-1])
        out[2*n+1]=np.sum(wall)
        return out

    # BDF solves the heat-transfer stiffness without coupling dt to mesh cells.
    atol=np.array([1e-6]*(2*n)+[1e-3,1e-3],dtype=float)
    sol=solve_ivp(derivative,(0.0,dt_s),y0,method="BDF",rtol=relative_tolerance,
                  atol=atol)
    if not sol.success or not np.all(np.isfinite(sol.y[:,-1])):
        raise RuntimeError(f"bed integrator failure: {sol.message}")
    y=sol.y[:,-1]
    if np.min(y[:2*n])<=0:
        raise RuntimeError("nonphysical temperature after bed integration")
    final=BedState(tuple(y[:n]),tuple(y[n:2*n]))
    delta_u=bed_energy_J(bed,final)-before
    qgas=float(y[2*n])
    qwall=float(y[2*n+1])
    residual=delta_u-qgas+qwall
    mean_out=float(inlet_K-qgas/(mcp*dt_s)) if mcp>0 else float(y[n-1])
    return BedStep(final,float(inlet_K),mean_out,
                   state.fluid_temperature_K[0],float(y[n-1]),
                   qgas,qwall,delta_u,residual,pressure_drop,blower,
                   re,nu,h,int(sol.nfev))
