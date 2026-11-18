"""Pressure-driven real-air/solid finite-volume bed prototype.

Each gas cell has rigid void volume, conserved mass and extensive internal
energy; pressure follows HEOS::Air, NOT prescribed inside the bed. Face mass
flux solves the quasi-steady Ergun pressure-gradient relation using upstream
density and viscosity. Face energy is upwind enthalpy flow. Acoustic and gas
kinetic energy are neglected; a low-Mach validity limit is checked.
Solid exchange conductance is an explicitly assumed volumetric coefficient,
not a calibrated Wakao correlation. This is a *standalone* bed prototype,
not connected to the M3.8 water HX, blower or gas conditioner.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from scipy.integrate import solve_ivp

from .packed_bed import PackedBedGeometry
from .real_air_control_volume import AirVolumeState


@dataclass(frozen=True)
class RealAirBedAssumptions:
    geometry:PackedBedGeometry
    cells:int=4
    solid_density_kg_m3:float=2600.
    solid_cp_J_kgK:float=850.
    assumed_volumetric_gas_solid_UA_W_m3K:float=5000.
    assumed_wall_UA_W_K:float=0.
    ambient_K:float=293.15
    max_superficial_Mach:float=.1
    # Bound actual interstitial velocity below sonic regime by using u/epsilon
    # in the guard, not just superficial velocity.
    def __post_init__(self):
        if not isinstance(self.cells,int) or not 2<=self.cells<=32:
            raise ValueError("prototype requires 2..32 cells")
        for v in (self.solid_density_kg_m3,self.solid_cp_J_kgK,
                  self.assumed_volumetric_gas_solid_UA_W_m3K,
                  self.ambient_K,self.max_superficial_Mach):
            if not math.isfinite(v) or v<=0:
                raise ValueError("invalid prototype coefficients")
        if not math.isfinite(self.assumed_wall_UA_W_K) or self.assumed_wall_UA_W_K<0:
            raise ValueError("invalid wall loss")
        if self.max_superficial_Mach>.2:
            raise ValueError("quasi-steady Ergun prototype restricted to low Mach")


def _tp_properties(T,P):
    from CoolProp import AbstractState
    from CoolProp.CoolProp import PT_INPUTS
    a=AbstractState("HEOS","Air")
    a.update(PT_INPUTS,P,T)
    return {"T":a.T(),"P":a.p(),"rho":a.rhomass(),"h":a.hmass(),
            "mu":a.viscosity(),"a":a.speed_sound(),"k":a.conductivity(),
            "cp":a.cpmass()}


def ergun_face(left:dict,right:dict,g:PackedBedGeometry,length_m:float):
    """Signed mass and energy flow from left to right; pressure is a state.

    Low-Mach, upstream-state face approximation, not an integrated
    compressible pressure-drop law at arbitrary pressure ratio.
    """
    if not math.isfinite(length_m) or length_m<=0:
        raise ValueError("invalid face length")
    dp=left["P"]-right["P"]
    if dp==0:return 0.,0.,0.
    up=left if dp>0 else right
    e=g.porosity;d=g.particle_diameter_m
    A=150*up["mu"]*(1-e)**2*length_m/(e**3*d*d)
    B=1.75*up["rho"]*(1-e)*length_m/(e**3*d)
    u=2*abs(dp)/(A+math.sqrt(A*A+4*B*abs(dp)))
    mdot=math.copysign(u*up["rho"]*g.cross_section_m2,dp)
    return mdot,mdot*up["h"],u/(e*up["a"])


def run_real_air_bed(a:RealAirBedAssumptions,*,duration_s:float,
    initial_T_K:float=383.15,initial_P_Pa:float=250000.,
    left_T_K:float=493.15,left_P_Pa:float=250100.,
    right_T_K:float=383.15,right_P_Pa:float=249900.)->dict:
    """Open left/right pressure reservoir boundaries; mass flows are solved.

    Both boundary reservoir temperatures and pressures are ASSUMED, not
    manufacturer blower behavior. Rigid bed pore volume excludes solid.
    Internal faces use dx, boundary faces dx/2; ignores entry/exit losses.
    """
    from CoolProp import AbstractState
    from CoolProp.CoolProp import DmassUmass_INPUTS
    if not math.isfinite(duration_s) or not 0<duration_s<=300:
        raise ValueError("prototype duration must be in (0,300] seconds")
    for T,P in ((initial_T_K,initial_P_Pa),(left_T_K,left_P_Pa),(right_T_K,right_P_Pa)):
        if not (280<T<800 and 50000<P<2000000):
            raise ValueError("initial/boundary state outside tested dry-air domain")
    N=a.cells;g=a.geometry;dx=g.length_m/N
    bulk=g.bed_volume_m3/N
    void=bulk*g.porosity
    Csolid=bulk*(1-g.porosity)*a.solid_density_kg_m3*a.solid_cp_J_kgK
    ua=bulk*a.assumed_volumetric_gas_solid_UA_W_m3K
    wall=a.assumed_wall_UA_W_K/N
    init=AirVolumeState.from_TP(void,initial_T_K,initial_P_Pa)
    # EOS evaluated on conservative m and U. One mutable state's properties
    # are immediately copied; no state aliasing between gas cells.
    air=AbstractState("HEOS","Air")
    def decode(m,U):
        if not (math.isfinite(m) and m>0 and math.isfinite(U)):
            raise ValueError("invalid gas inventory")
        air.update(DmassUmass_INPUTS,m/void,U/m)
        p=air.p();t=air.T()
        if not (280<t<800 and 50000<p<2000000):
            raise ValueError("gas EOS outside declared prototype domain")
        return {"T":t,"P":p,"rho":air.rhomass(),"h":air.hmass(),
                "mu":air.viscosity(),"a":air.speed_sound(),
                "k":air.conductivity(),"cp":air.cpmass()}
    left=_tp_properties(left_T_K,left_P_Pa)
    right=_tp_properties(right_T_K,right_P_Pa)
    def evaluate(y):
        cells=[decode(float(y[i]),float(y[N+i])) for i in range(N)]
        states=[left,*cells,right]
        faces=[ergun_face(states[i],states[i+1],g,
                         dx/2 if i in (0,N) else dx) for i in range(N+1)]
        return cells,np.array(faces,dtype=float)
    y0=np.array([init.mass_kg]*N+[init.internal_energy_J]*N+
                [initial_T_K]*N+[0.]*5)
    def rhs(_,y):
        cells,faces=evaluate(y)
        qgs=ua*(np.array([c["T"] for c in cells])-y[2*N:3*N])
        qwall=wall*(y[2*N:3*N]-a.ambient_K)
        dy=np.zeros_like(y)
        dy[:N]=faces[:-1,0]-faces[1:,0]
        dy[N:2*N]=faces[:-1,1]-faces[1:,1]-qgs
        dy[2*N:3*N]=(qgs-qwall)/Csolid
        # Signed flux integrals at *both* boundaries and ambient wall
        dy[3*N:]=[faces[0,0],faces[-1,0],faces[0,1],faces[-1,1],sum(qwall)]
        return dy
    sol=solve_ivp(rhs,(0.,duration_s),y0,method="BDF",rtol=2e-7,
           atol=np.array([1e-9]*N+[.01]*N+[1e-6]*N+[1e-7,1e-7,.01,.01,.01]))
    if not sol.success:raise RuntimeError(sol.message)
    y=sol.y[:,-1]
    # Use every accepted node, not just terminal speed. This is not a
    # continuous sonic bound, and no actual plant hydraulic rating is known.
    max_mach=max(float(np.max(evaluate(sol.y[:,i])[1][:,2]))
                 for i in range(sol.y.shape[1]))
    if max_mach>a.max_superficial_Mach:
        raise ValueError("interstitial Mach outside low-Mach model domain")
    cells,faces=evaluate(y)
    ml,mr,hl,hr,qwall=map(float,y[3*N:])
    mass_change=float(sum(y[:N]-y0[:N]))
    gas_change=float(sum(y[N:2*N]-y0[N:2*N]))
    solid_change=float(Csolid*sum(y[2*N:3*N]-y0[2*N:3*N]))
    rm=mass_change-ml+mr
    re=gas_change+solid_change-hl+hr+qwall
    if abs(rm)>1e-6*max(1.,abs(ml),abs(mr)) or abs(re)>1e-6*max(1.,abs(hl),abs(hr),abs(solid_change)):
        raise RuntimeError("real-air bed conservation defect")
    return {
      "cells":N,"final_gas_states":cells,
      "final_solid_temperature_K":list(y[2*N:3*N]),
      "final_signed_face_mass_flow_kg_s":list(faces[:,0]),
      "initial_total_gas_mass_kg":float(sum(y0[:N])),
      "final_total_gas_mass_kg":float(sum(y[:N])),
      "gas_internal_energy_change_J":gas_change,
      "solid_sensible_energy_change_J":solid_change,
      "left_signed_mass_in_kg":ml,"right_signed_mass_out_kg":mr,
      "left_signed_enthalpy_in_J":hl,"right_signed_enthalpy_out_J":hr,
      "wall_heat_loss_J":qwall,"mass_first_law_residual_kg":rm,
      "energy_first_law_residual_J":re,
      "maximum_accepted_node_interstitial_Mach":max_mach,
      "pressure_boundary_Pa_ASSUMED":[left_P_Pa,right_P_Pa],
      "pressure_at_gas_cells_calculated_from_mass_and_internal_energy":True,
      "variable_air_enthalpy_density_and_viscosity_used":True,
      "gas_solid_transfer_coefficient_is_uncalibrated":True,
      "bed_hydraulic_inertial_and_acoustic_dynamics_included":False,
      "coupled_HX_and_closed_loop_qualified":False,
      "experimentally_validated":False,
      "real_plant_qualified":False,
    }
