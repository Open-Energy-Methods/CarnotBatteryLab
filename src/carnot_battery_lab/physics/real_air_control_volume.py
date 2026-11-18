"""Conservative real-gas rigid control volume for future variable-density TES/HX.

This is an independently testable primitive, not yet a coupled packed-bed
or heat exchanger. Mass and extensive INTERNAL ENERGY are state variables.
The EOS returns T,P,h and transport properties from rho=m/V and u=U/m.
Inlet/outlet flow energy is enthalpy, not internal energy. No pressure is
imposed simultaneously with fixed volume/mass. Flow is prescribed; no
momentum equation or installed blower, valve or pressure rating is claimed.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
import numpy as np
from scipy.integrate import solve_ivp


def _positive(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and isfinite(x) and x>0


@dataclass(frozen=True)
class AirVolumeState:
    volume_m3:float
    mass_kg:float
    internal_energy_J:float

    def __post_init__(self):
        if not all(_positive(x) for x in (self.volume_m3,self.mass_kg)):
            raise ValueError("positive rigid volume and gas mass required")
        if not isfinite(self.internal_energy_J):
            raise ValueError("finite extensive internal energy required")

    @classmethod
    def from_TP(cls,volume_m3,T_K,P_Pa):
        if not all(_positive(x) for x in (volume_m3,T_K,P_Pa)):
            raise ValueError("invalid initial EOS state")
        from CoolProp.CoolProp import PropsSI
        rho=PropsSI("D","T",T_K,"P",P_Pa,"HEOS::Air")
        u=PropsSI("U","T",T_K,"P",P_Pa,"HEOS::Air")
        return cls(volume_m3,volume_m3*rho,volume_m3*rho*u)

    def properties(self):
        from CoolProp.CoolProp import PropsSI
        rho=self.mass_kg/self.volume_m3
        u=self.internal_energy_J/self.mass_kg
        T=PropsSI("T","D",rho,"U",u,"HEOS::Air")
        P=PropsSI("P","D",rho,"U",u,"HEOS::Air")
        if not (280<T<800 and 50_000<P<2_000_000):
            raise ValueError("gas state outside declared dry-air test domain")
        props={key:float(PropsSI(output,"T",T,"P",P,"HEOS::Air"))
               for key,output in (("h_J_kg","H"),("cp_J_kgK","C"),
                                  ("mu_Pa_s","V"),("k_W_mK","L"))}
        return {"T_K":float(T),"P_Pa":float(P),"rho_kg_m3":rho,
                "u_J_kg":u,**props}


def advance_air_volume(state:AirVolumeState,*,duration_s:float,
                       inlet_mass_flow_kg_s:float=0.,
                       outlet_mass_flow_kg_s:float=0.,
                       inlet_T_K:float=383.15,inlet_P_Pa:float=250000.,
                       heat_into_gas_W:float=0.) -> dict:
    """Prescribed flow, fixed-volume EOS primitive; no kinetic/work terms.

    External heat can be signed. Outlet is perfectly mixed. Integrated inlet,
    outlet and heat ledgers independently checked; no fictitious mass source.
    """
    if not _positive(duration_s) or any(not isinstance(x,(int,float))
      or not isfinite(x) or x<0 for x in (inlet_mass_flow_kg_s,outlet_mass_flow_kg_s)):
        raise ValueError("invalid flow or integration interval")
    if not isfinite(heat_into_gas_W):
        raise ValueError("invalid heat input")
    if state.mass_kg+(inlet_mass_flow_kg_s-outlet_mass_flow_kg_s)*duration_s<=0:
        raise ValueError("gas inventory exhausted under imposed flow")
    from CoolProp.CoolProp import PropsSI
    h_in=(float(PropsSI("H","T",inlet_T_K,"P",inlet_P_Pa,"HEOS::Air"))
          if inlet_mass_flow_kg_s else 0.)
    initial=state.properties()
    def rhs(_,y):
        v=AirVolumeState(state.volume_m3,float(y[0]),float(y[1]))
        props=v.properties()
        hin=inlet_mass_flow_kg_s*h_in
        hout=outlet_mass_flow_kg_s*props["h_J_kg"]
        return [inlet_mass_flow_kg_s-outlet_mass_flow_kg_s,
                hin-hout+heat_into_gas_W,hin,hout,heat_into_gas_W]
    sol=solve_ivp(rhs,(0,duration_s),
                  [state.mass_kg,state.internal_energy_J,0.,0.,0.],
                  method="RK45",rtol=1e-8,atol=[1e-10,1e-3,1e-3,1e-3,1e-3])
    if not sol.success:
        raise RuntimeError(sol.message)
    m,U,Hin,Hout,Q=map(float,sol.y[:,-1])
    final=AirVolumeState(state.volume_m3,m,U)
    props=final.properties()
    mres=m-state.mass_kg-(inlet_mass_flow_kg_s-outlet_mass_flow_kg_s)*duration_s
    eres=U-state.internal_energy_J-Hin+Hout-Q
    if abs(mres)>1e-8*max(1.,m) or abs(eres)>1e-7*max(1.,abs(Hin),abs(Hout),abs(Q),abs(U-state.internal_energy_J)):
        raise RuntimeError("rigid air control-volume conservation failed")
    return {"initial":initial,"final":props,"final_mass_kg":m,
            "final_internal_energy_J":U,"volume_m3":state.volume_m3,
            "mass_balance_residual_kg":mres,"energy_balance_residual_J":eres,
            "inlet_enthalpy_J":Hin,"outlet_enthalpy_J":Hout,"heat_J":Q,
            "gas_momentum_and_pressure_loss_model_included":False,
            "coupled_variable_density_packed_bed_HX_implemented":False,
            "physical_equipment_qualified":False}
