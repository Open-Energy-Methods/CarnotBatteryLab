"""Alternative conservative variable-enthalpy gas/rock/wall packed-bed kernel.

This RESEARCH OPTION is intentionally separate from the validated baseline
GasRockBed/advance_bed; it does not retroactively alter the source-locked
experimental 512-cell results.

Fluid internal energy and advected sensible enthalpy use the SAME
NIST N2/O2 ideal-gas h(T)/cp(T) functions:
  Mg cp_f(T) dTf/dt = mdot*(h(Tup)-h(Tf)) - q_gs.
Solid internal energy similarly integrates a declared assumed cp_s(T).
Rock ↔ shell transfer is equal-and-opposite; shell → ambient is external.

The model has constant gas MASS inventory/density (low-Mach reduction),
while properties depend on temperature. It is NOT a compressible,
pressure-resolved or 2-D buoyant-flow simulation.

Copper-slag cp(T) slope, voidage, shell heat transfer, wall/pipe inertia
and mass flow are assumed scenarios, not fitted from 2024 Case B. The
2022 rig 7-mm steel shell motivates a cylindrical mass/capacity estimate,
not a verified complete 2024 geometry or loss coefficient.

No compressor maps, hydro/pressure validation or experimental-prediction
claim is made by satisfying first-law conservation tests.
"""
from __future__ import annotations
from dataclasses import dataclass,field
import math
from typing import Sequence
import numpy as np
from scipy.integrate import solve_ivp

from .packed_bed import PackedBedGeometry
from .ideal_dry_air import (
    air_cp_J_kgK,air_sensible_enthalpy_J_kg,
    air_mu_sutherland_Pa_s,air_k_powerlaw_W_mK,T_REF_K,
)


@dataclass(frozen=True)
class HypotheticalSlag:
    cp_reference_J_kgK:float=1100.
    cp_linear_slope_J_kgK2:float=.20
    density_kg_m3:float=3700.
    reference_K:float=T_REF_K

    def __post_init__(self):
        vals=(self.cp_reference_J_kgK,self.cp_linear_slope_J_kgK2,
              self.density_kg_m3,self.reference_K)
        if not all(math.isfinite(v) for v in vals) or (
            self.cp_reference_J_kgK<=0 or self.density_kg_m3<=0):
            raise ValueError("hypothetical slag input invalid")
        if not 298.15<=self.reference_K<=1500:
            raise ValueError("reference outside model domain")
        if min(self.cp(298.15),self.cp(1500.))<=0:
            raise ValueError("slag cp must remain positive throughout domain")

    def cp(self,T_K:float)->float:
        if not math.isfinite(T_K) or not 298.15<=T_K<=1500:
            raise ValueError("slag temperature outside research domain")
        return self.cp_reference_J_kgK+self.cp_linear_slope_J_kgK2*(T_K-self.reference_K)

    def h(self,T_K:float)->float:
        """Specific sensible energy relative to reference, consistent with cp."""
        self.cp(T_K)
        d=T_K-self.reference_K
        return self.cp_reference_J_kgK*d+.5*self.cp_linear_slope_J_kgK2*d*d


@dataclass(frozen=True)
class CylindricalSteelShell:
    inner_diameter_m:float=.158
    length_m:float=.400
    wall_thickness_m:float=.007
    steel_density_kg_m3:float=7850.
    steel_cp_J_kgK:float=500.

    def __post_init__(self):
        vals=vars(self).values()
        if not all(math.isfinite(x) and x>0 for x in vals):
            raise ValueError("steel shell geometry/material must be positive")

    @property
    def mass_kg(self)->float:
        r=self.inner_diameter_m/2
        return math.pi*((r+self.wall_thickness_m)**2-r*r)*self.length_m*self.steel_density_kg_m3

    @property
    def thermal_capacity_J_K(self)->float:
        return self.mass_kg*self.steel_cp_J_kgK


@dataclass(frozen=True)
class EnthalpyWallBed:
    geometry:PackedBedGeometry=field(default_factory=lambda:
        PackedBedGeometry(.400,.158,.020,.39))
    cells:int=8
    assumed_gas_density_kg_m3:float=1.
    slag:HypotheticalSlag=field(default_factory=HypotheticalSlag)
    shell:CylindricalSteelShell=field(default_factory=CylindricalSteelShell)
    solid_to_wall_UA_W_K:float=5.
    wall_to_ambient_UA_W_K:float=.5
    ambient_K:float=300.

    def __post_init__(self):
        if isinstance(self.cells,bool) or not isinstance(self.cells,int) or self.cells<2:
            raise ValueError("at least two finite volumes needed")
        if abs(self.geometry.length_m-self.shell.length_m)>1e-10 or abs(
                self.geometry.diameter_m-self.shell.inner_diameter_m)>1e-10:
            raise ValueError("wall must match geometry of modeled bed")
        values=(self.assumed_gas_density_kg_m3,self.solid_to_wall_UA_W_K,
                self.wall_to_ambient_UA_W_K,self.ambient_K)
        if not all(math.isfinite(x) for x in values):
            raise ValueError("nonfinite bed inputs")
        if (self.assumed_gas_density_kg_m3<=0 or
            self.solid_to_wall_UA_W_K<0 or self.wall_to_ambient_UA_W_K<0 or
            not 298.15<=self.ambient_K<=1500):
            raise ValueError("invalid assumed gas/wall/ambient inputs")


@dataclass(frozen=True)
class EnthalpyWallState:
    gas_K:tuple[float,...]
    rock_K:tuple[float,...]
    wall_K:tuple[float,...]

    @classmethod
    def uniform(cls,bed:EnthalpyWallBed,temperature_K:float)->"EnthalpyWallState":
        if not math.isfinite(temperature_K) or not 298.15<=temperature_K<=1500:
            raise ValueError("initial temperature outside model")
        return cls((temperature_K,)*bed.cells,(temperature_K,)*bed.cells,
                   (temperature_K,)*bed.cells)


@dataclass(frozen=True)
class EnthalpyWallStep:
    final_state:EnthalpyWallState
    heat_from_inlet_gas_J:float
    heat_lost_to_ambient_J:float
    stored_energy_change_J:float
    first_law_residual_J:float
    final_outlet_gas_K:float
    solver_nfev:int
    status:str="CONSERVATIVE_IDEAL_DRY_AIR_AND_ASSUMED_SLAG_WALL_SCREEN_NOT_VALIDATED"


def _validate_state(bed:EnthalpyWallBed,state:EnthalpyWallState)->None:
    if any(len(arr)!=bed.cells for arr in (state.gas_K,state.rock_K,state.wall_K)):
        raise ValueError("state arrays must match grid")
    if not all(math.isfinite(t) and 298.15<=t<=1500. for arr in (
        state.gas_K,state.rock_K,state.wall_K) for t in arr):
        raise ValueError("state temperature outside NIST/model domain")


def energy_J(bed:EnthalpyWallBed,state:EnthalpyWallState)->float:
    _validate_state(bed,state)
    vol=bed.geometry.bed_volume_m3/bed.cells
    mg=bed.assumed_gas_density_kg_m3*bed.geometry.porosity*vol
    ms=bed.slag.density_kg_m3*(1-bed.geometry.porosity)*vol
    cw=bed.shell.thermal_capacity_J_K/bed.cells
    return (mg*sum(air_sensible_enthalpy_J_kg(t) for t in state.gas_K)
        + ms*sum(bed.slag.h(t) for t in state.rock_K)
        + cw*sum(t-T_REF_K for t in state.wall_K))


def advance_enthalpy_wall(
    bed:EnthalpyWallBed,state:EnthalpyWallState,*,
    inlet_K:float,mass_flow_kg_s:float,dt_s:float,
    relative_tolerance:float=1e-7,
)->EnthalpyWallStep:
    _validate_state(bed,state)
    if (not all(math.isfinite(x) for x in (
            inlet_K,mass_flow_kg_s,dt_s,relative_tolerance))
        or not 298.15<=inlet_K<=1500 or mass_flow_kg_s<0 or dt_s<=0
        or not 0<relative_tolerance<=1e-3):
        raise ValueError("invalid physical step or integration settings")
    n=bed.cells
    vol=bed.geometry.bed_volume_m3/n
    mg=bed.assumed_gas_density_kg_m3*bed.geometry.porosity*vol
    ms=bed.slag.density_kg_m3*(1-bed.geometry.porosity)*vol
    cw=bed.shell.thermal_capacity_J_K/n
    gs_area=bed.geometry.specific_interfacial_area_m2_per_m3*vol
    gsw=bed.solid_to_wall_UA_W_K/n
    gwa=bed.wall_to_ambient_UA_W_K/n
    area=bed.geometry.cross_section_m2
    diameter=bed.geometry.particle_diameter_m
    hin=air_sensible_enthalpy_J_kg(inlet_K)
    initial=energy_J(bed,state)
    y0=np.asarray([*state.gas_K,*state.rock_K,*state.wall_K,0.,0.],dtype=float)

    def rhs(_t:float,y:np.ndarray)->np.ndarray:
        g=y[:n]
        s=y[n:2*n]
        w=y[2*n:3*n]
        if (np.min(g)<298.15 or np.min(s)<298.15 or np.min(w)<298.15
                or np.max(y[:3*n])>1500):
            # The validity guard is intentional, not silent extrapolation.
            raise ValueError("gas/solid/wall thermal state outside declared property range")
        hg=[air_sensible_enthalpy_J_kg(float(t)) for t in g]
        cg=[air_cp_J_kgK(float(t)) for t in g]
        cs=[bed.slag.cp(float(t)) for t in s]
        upstream=np.r_[hin,hg[:-1]]
        q_adv=mass_flow_kg_s*(upstream-np.asarray(hg))
        q_exchange=np.zeros(n,dtype=float)
        for i in range(n):
            mu=air_mu_sutherland_Pa_s(float(g[i]))
            k=air_k_powerlaw_W_mK(float(g[i]))
            re=mass_flow_kg_s*diameter/(area*mu)
            if mass_flow_kg_s>0 and not 15<=re<=8500:
                raise ValueError("variable-property Wakao Reynolds number outside 15..8500")
            pr=cg[i]*mu/k
            nu=2+1.1*re**.6*pr**(1/3)
            h=nu*k/diameter
            q_exchange[i]=h*gs_area*(g[i]-s[i])
        q_sw=gsw*(s-w)
        q_amb=gwa*(w-bed.ambient_K)
        dy=np.zeros_like(y)
        dy[:n]=(q_adv-q_exchange)/(mg*np.asarray(cg))
        dy[n:2*n]=(q_exchange-q_sw)/(ms*np.asarray(cs))
        dy[2*n:3*n]=(q_sw-q_amb)/cw
        dy[3*n]=mass_flow_kg_s*(hin-hg[-1])
        dy[3*n+1]=float(np.sum(q_amb))
        return dy

    atol=np.r_[[1e-6]*(3*n),[1e-3,1e-3]]
    sol=solve_ivp(rhs,(0,dt_s),y0,method="BDF",
                  rtol=relative_tolerance,atol=atol)
    if not sol.success or not all(math.isfinite(x) for x in sol.y[:,-1]):
        raise RuntimeError("enthalpy-wall ODE integration failed")
    y=sol.y[:,-1]
    final=EnthalpyWallState(tuple(float(x) for x in y[:n]),
                            tuple(float(x) for x in y[n:2*n]),
                            tuple(float(x) for x in y[2*n:3*n]))
    change=energy_J(bed,final)-initial
    qin=float(y[3*n])
    qamb=float(y[3*n+1])
    return EnthalpyWallStep(final,qin,qamb,change,change-qin+qamb,
                            final.gas_K[-1],int(sol.nfev))
