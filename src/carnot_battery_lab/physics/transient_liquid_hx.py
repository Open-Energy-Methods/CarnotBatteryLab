"""M3.6 transient finite-volume counterflow gas-to-pressurised-water HX.

Fluid and wall hold-up are dynamic, axial advection is upwind, gas and water
flow in *opposite* directions. Water h(T,P), cp(T,P), density and saturation
limits originate from CoolProp; 1 K lookup interpolation is checked against
direct EOS calls. Gas remains the same constant-cp, constant-density air-like
surrogate as the original M3.5 packed-bed: no actual gas pressure or hardware
rating is asserted. Installed UA, surface split, hold-up, friction, water
pressure and circulating equipment are engineering ASSUMPTIONS, not measured.

A separate gas-conditioning cooler or heater is required to impose the
previous M3 bed return at 110 C after the process HX. The actual charge power
supply and initial gas, water and metal inventories remain explicitly modeled.

This is a numerical comparison with a candidate 1MW/110->150C process duty,
NOT an experimentally validated water loop or Carnot battery/RTE.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, pi, sqrt
from functools import lru_cache

import numpy as np
from scipy.integrate import solve_ivp

from .liquid_process_hx_gate import ProcessLiquidHXContract


def _pos(x):
    return isinstance(x,(float,int)) and not isinstance(x,bool) and isfinite(x) and x>0


@dataclass(frozen=True)
class TransientHXAssumptions:
    cells:int=8
    installed_overall_UA_W_K:float=40_000.
    wall_total_heat_capacity_J_K:float=1_000_000.
    water_total_holdup_kg:float=200.
    gas_total_holdup_kg:float=24.
    assumed_liquid_inlet_absolute_pressure_Pa:float=2_000_000.
    gas_equivalent_flow_area_m2:float=1.2
    liquid_equivalent_flow_area_m2:float=.025
    gas_hydraulic_diameter_m:float=.05
    liquid_hydraulic_diameter_m:float=.03
    gas_hydraulic_length_m:float=12.
    liquid_hydraulic_length_m:float=12.
    assumed_gas_darcy_friction:float=.03
    assumed_liquid_darcy_friction:float=.025
    assumed_gas_minor_loss_K:float=2.
    assumed_liquid_minor_loss_K:float=2.
    assumed_auxiliary_efficiency:float=.7
    # Measurement-free extrapolation guard; not a certified pipe pressure rating.
    water_saturation_approach_K:float=2.
    wall_initial_C:float=110.
    gas_initial_C:float=110.
    liquid_initial_C:float=110.

    def __post_init__(self):
        if isinstance(self.cells,bool) or not isinstance(self.cells,int) or not 2<=self.cells<=64:
            raise ValueError("HX cells must be integer 2..64")
        positive=("installed_overall_UA_W_K","wall_total_heat_capacity_J_K",
                  "water_total_holdup_kg","gas_total_holdup_kg",
                  "assumed_liquid_inlet_absolute_pressure_Pa",
                  "gas_equivalent_flow_area_m2","liquid_equivalent_flow_area_m2",
                  "gas_hydraulic_diameter_m","liquid_hydraulic_diameter_m",
                  "gas_hydraulic_length_m","liquid_hydraulic_length_m",
                  "assumed_gas_darcy_friction","assumed_liquid_darcy_friction",
                  "assumed_auxiliary_efficiency","water_saturation_approach_K")
        if any(not _pos(getattr(self,k)) for k in positive):
            raise ValueError("invalid HX equipment hypothesis")
        for k in ("assumed_gas_minor_loss_K","assumed_liquid_minor_loss_K"):
            v=getattr(self,k)
            if not isinstance(v,(int,float)) or not isfinite(v) or v<0:
                raise ValueError("invalid HX fitting loss coefficient")
        if self.assumed_auxiliary_efficiency>1:
            raise ValueError("HX hydraulic efficiency >1")
        for k in ("wall_initial_C","gas_initial_C","liquid_initial_C"):
            v=getattr(self,k)
            if not isinstance(v,(float,int)) or not isfinite(v) or v<=-273.15:
                raise ValueError("invalid HX initial temperature")


@dataclass(frozen=True)
class HXDynamicState:
    gas_cell_K:tuple[float,...]
    water_cell_K:tuple[float,...]
    wall_cell_K:tuple[float,...]

    @classmethod
    def initial(cls,a:TransientHXAssumptions):
        return cls((a.gas_initial_C+273.15,)*a.cells,
                   (a.liquid_initial_C+273.15,)*a.cells,
                   (a.wall_initial_C+273.15,)*a.cells)


@lru_cache(maxsize=12)
def _water_table(Pa:float,min_K:float=353.15):
    """Interpolated single-liquid CoolProp enthalpy/cp; no clamped extrapolation.

    0.5K table bounds are >=100C and (T_sat-2K). Error bounds are separately
    tested against original direct PropsSI and disclosed to user.
    """
    from CoolProp.CoolProp import PropsSI
    t_sat=float(PropsSI("T","P",Pa,"Q",0,"HEOS::Water"))
    t_low=min(min_K,363.15)-25.
    t_high=t_sat-2.
    if t_high<423.15:
        raise ValueError("assumed water pressure insufficient for 150C liquid with margin")
    n=max(2,int((t_high-t_low)/.5)+1)
    grid=np.linspace(t_low,t_high,n)
    H=np.array([PropsSI("H","T",float(t),"P",Pa,"HEOS::Water")
                for t in grid])
    CP=np.array([PropsSI("C","T",float(t),"P",Pa,"HEOS::Water")
                 for t in grid])
    rho_ref=float(PropsSI("D","T",383.15,"P",Pa,"HEOS::Water"))
    if not np.all(np.isfinite(H)) or not np.all(CP>0) or rho_ref<=0:
        raise ValueError("water CoolProp property table invalid")
    return grid,H,CP,rho_ref,t_sat


def _interp_checked(T,grid,values):
    t=np.asarray(T)
    if np.any(~np.isfinite(t)) or np.any(t<grid[0]-1e-6) or np.any(t>grid[-1]+1e-6):
        raise ValueError("water at omitted/multiphase/out-of-lookup EOS state")
    return np.interp(t,grid,values)


def required_process_water_flow_from_real_enthalpy(*,
    inlet_K:float=383.15,outlet_K:float=423.15,
    duty_W:float=1.e6,pressure_Pa:float=2.e6)->dict:
    """True nominal 1MW water mass flow at a *declared assumed* pressure.

    M3.4 previously used fixed 4180 J/kg/K (=5.9809 kg/s). For M3.6,
    that constant-cp simplification cannot simultaneously be imposed with
    real-water h(T,P): the real specific enthalpy difference defines the
    flow required for the exact original 1MW, 110->150C contract.
    """
    if any(not _pos(v) for v in (inlet_K,outlet_K,duty_W,pressure_Pa)
           ) or outlet_K<=inlet_K:
        raise ValueError("invalid exact liquid duty or process boundaries")
    grid,H,_,_,sat=_water_table(pressure_Pa)
    if outlet_K>=sat-2.:
        raise ValueError("assumed process pressure cannot keep 150C water liquid")
    hi=float(_interp_checked(inlet_K,grid,H))
    ho=float(_interp_checked(outlet_K,grid,H))
    flow=duty_W/(ho-hi)
    if not _pos(flow):
        raise ValueError("invalid real-water process flow")
    return {
        "target_heat_W":duty_W,
        "water_inlet_K":inlet_K,
        "water_outlet_K":outlet_K,
        "assumed_absolute_water_pressure_Pa":pressure_Pa,
        "CoolProp_water_inlet_h_J_kg":hi,
        "CoolProp_water_outlet_h_J_kg":ho,
        "original_1MW_real_water_required_flow_kg_s":flow,
        "water_flow_derived_from_real_enthalpy_not_constant_cp":True,
        "water_pressure_is_ASSUMED_not_measured":True,
    }


def _pressure_audit(
    a:TransientHXAssumptions,water_m_kg_s:float,gas_m_kg_s:float,
    gas_rho_kg_m3:float,water_rho_kg_m3:float,
    water_temp_max_K:float)->dict:
    from CoolProp.CoolProp import PropsSI
    vg=gas_m_kg_s/(gas_rho_kg_m3*a.gas_equivalent_flow_area_m2)
    vl=water_m_kg_s/(water_rho_kg_m3*a.liquid_equivalent_flow_area_m2)
    dg=(a.assumed_gas_darcy_friction*a.gas_hydraulic_length_m/
        a.gas_hydraulic_diameter_m+a.assumed_gas_minor_loss_K)*.5*gas_rho_kg_m3*vg*vg
    dl=(a.assumed_liquid_darcy_friction*a.liquid_hydraulic_length_m/
        a.liquid_hydraulic_diameter_m+a.assumed_liquid_minor_loss_K)*.5*water_rho_kg_m3*vl*vl
    min_P=a.assumed_liquid_inlet_absolute_pressure_Pa-dl
    maxsat=float(PropsSI("P","T",water_temp_max_K+
                        a.water_saturation_approach_K,"Q",0,"HEOS::Water"))
    return {
        "assumed_hx_gas_pressure_drop_Pa_uncalibrated":dg,
        "assumed_hx_water_pressure_drop_Pa_uncalibrated":dl,
        "assumed_min_liquid_pressure_Pa":min_P,
        "water_saturation_pressure_at_max_state_plus_margin_Pa":maxsat,
        "assumed_model_liquid_single_phase":bool(min_P>maxsat),
        "assumed_gas_hx_circulator_electric_W_uncalibrated":
            dg*(gas_m_kg_s/gas_rho_kg_m3)/a.assumed_auxiliary_efficiency,
        "assumed_liquid_hx_pump_electric_W_uncalibrated":
            dl*(water_m_kg_s/water_rho_kg_m3)/a.assumed_auxiliary_efficiency,
        "measured_installed_pressure_or_pump_curve_available":False,
    }


def advance_transient_hx(
    a:TransientHXAssumptions,state:HXDynamicState,*,
    gas_inlet_mean_K:float,gas_flow_kg_s:float,gas_cp_J_kgK:float,
    gas_density_kg_m3:float,water_flow_kg_s:float,
    water_inlet_K:float,dt_s:float,
    required_water_supply_K:float=423.15,
    minimum_local_gas_liquid_approach_K:float=5.,
)->dict:
    """Dynamic three-field FV with independent gas, water and metal storage.

    Gas i increases hot inlet->outlet, while the liquid flows N-1->0.
    Exact integrals: gas boundary flow, liquid enthalpy flow, gas->wall,
    wall->liquid. These independently close each of three phase balances.
    Gas inlet is the BED STEP MEAN from a prior conservative TES integration;
    neither true within-step interpolation nor plant gas pressure is known.
    """
    if any(not _pos(v) for v in (gas_inlet_mean_K,gas_flow_kg_s,
        gas_cp_J_kgK,gas_density_kg_m3,water_flow_kg_s,water_inlet_K,
        dt_s,required_water_supply_K,minimum_local_gas_liquid_approach_K)):
        raise ValueError("invalid transient HX inlet or duty contract")
    N=a.cells
    if any(len(v)!=N for v in (state.gas_cell_K,state.water_cell_K,state.wall_cell_K)):
        raise ValueError("HX state geometry mismatch")
    grid,H,CP,rho_l,t_sat=_water_table(
        a.assumed_liquid_inlet_absolute_pressure_Pa)
    if required_water_supply_K>=t_sat-a.water_saturation_approach_K:
        raise ValueError("150C process liquid not possible at assumed water pressure")
    h_in=float(_interp_checked(water_inlet_K,grid,H))
    y0=np.array((*state.gas_cell_K,*state.water_cell_K,
                 *state.wall_cell_K,0.,0.,0.,0.),dtype=float)
    if np.any(y0[:3*N]<=0) or np.any(~np.isfinite(y0)):
        raise ValueError("HX initial state nonphysical")
    _interp_checked(y0[N:2*N],grid,H)
    # Each interface has twice the *overall* UA: resistances in series.
    UA_hot_cell=2*a.installed_overall_UA_W_K/N
    UA_liquid_cell=2*a.installed_overall_UA_W_K/N
    m_g_cell=a.gas_total_holdup_kg/N
    m_l_cell=a.water_total_holdup_kg/N
    wall_cp_cell=a.wall_total_heat_capacity_J_K/N
    mcp_g=gas_flow_kg_s*gas_cp_J_kgK
    def rhs(_,y):
        tg=y[:N];tl=y[N:2*N];tw=y[2*N:3*N]
        h_l=_interp_checked(tl,grid,H)
        cp_l=_interp_checked(tl,grid,CP)
        hg_prev=np.r_[gas_inlet_mean_K,tg[:-1]]
        hl_prev=np.r_[h_l[1:],h_in]
        qgw=UA_hot_cell*(tg-tw)
        qwl=UA_liquid_cell*(tw-tl)
        dy=np.zeros_like(y)
        dy[:N]=(mcp_g*(hg_prev-tg)-qgw)/(m_g_cell*gas_cp_J_kgK)
        dy[N:2*N]=(water_flow_kg_s*(hl_prev-h_l)+qwl)/(m_l_cell*cp_l)
        dy[2*N:3*N]=(qgw-qwl)/wall_cp_cell
        dy[3*N]=mcp_g*(gas_inlet_mean_K-tg[-1])
        dy[3*N+1]=water_flow_kg_s*(h_l[0]-h_in)
        dy[3*N+2]=sum(qgw)
        dy[3*N+3]=sum(qwl)
        return dy
    sol=solve_ivp(rhs,(0.,dt_s),y0,method="BDF",
                  rtol=2e-7,atol=np.array([2e-6]*(3*N)+[1e-2]*4))
    if not sol.success or np.any(~np.isfinite(sol.y[:,-1])):
        raise RuntimeError("dynamic gas/liquid HX BDF failed: "+sol.message)
    y=sol.y[:,-1]
    final=HXDynamicState(tuple(y[:N]),tuple(y[N:2*N]),tuple(y[2*N:3*N]))
    old_g=np.asarray(state.gas_cell_K);old_l=np.asarray(state.water_cell_K)
    old_w=np.asarray(state.wall_cell_K)
    new_g=np.asarray(final.gas_cell_K);new_l=np.asarray(final.water_cell_K)
    new_w=np.asarray(final.wall_cell_K)
    _interp_checked(new_l,grid,H)
    water_max=max(float(max(sol.y[N:2*N,k])) for k in range(sol.y.shape[1]))
    pressure=_pressure_audit(a,water_flow_kg_s,gas_flow_kg_s,
                             gas_density_kg_m3,rho_l,water_max)
    ug=m_g_cell*gas_cp_J_kgK*sum(new_g-old_g)
    ul=m_l_cell*sum(_interp_checked(new_l,grid,H)-
                    _interp_checked(old_l,grid,H))
    uw=wall_cp_cell*sum(new_w-old_w)
    ib_g=float(y[3*N]);ib_l=float(y[3*N+1])
    q_gw=float(y[3*N+2]);q_wl=float(y[3*N+3])
    rg=ug-ib_g+q_gw
    rl=ul-q_wl+ib_l
    rw=uw-q_gw+q_wl
    total=ug+ul+uw-ib_g+ib_l
    scale=max(1.,abs(ib_g),abs(ib_l),abs(q_gw),abs(q_wl))
    if max(abs(rg),abs(rl),abs(rw),abs(total))>2e-5*scale:
        raise RuntimeError("independent transient HX gas/water/wall energy ledger failed")
    t_water_first=state.water_cell_K[0]
    t_water_last=final.water_cell_K[0]
    # The solver returns coarse accepted BDF sample states; their minimum is
    # NOT a continuous bound between numerical solver nodes.
    node_approach=min(float(np.min(
        sol.y[:N,k]-sol.y[N:2*N,k])) for k in range(sol.y.shape[1]))
    min_water_outlet_K_at_solver_nodes=float(np.min(sol.y[N,:]))
    max_water_outlet_K_at_solver_nodes=float(np.max(sol.y[N,:]))
    actual_mean_water_thermal_W=ib_l/dt_s
    qualifies=bool(
        pressure["assumed_model_liquid_single_phase"]
        and min_water_outlet_K_at_solver_nodes>=required_water_supply_K-1e-8
        and t_water_first>=required_water_supply_K-1e-8
        and t_water_last>=required_water_supply_K-1e-8
        and actual_mean_water_thermal_W>=1.e6*(1.-1e-7)
        and node_approach>=minimum_local_gas_liquid_approach_K-1e-8)
    return {
        "state":final,
        "gas_inlet_mean_K":gas_inlet_mean_K,
        "gas_outlet_start_K":state.gas_cell_K[-1],
        "gas_outlet_end_K":final.gas_cell_K[-1],
        "water_outlet_start_K":t_water_first,
        "water_outlet_end_K":t_water_last,
        "water_outlet_flow_average_heat_W":actual_mean_water_thermal_W,
        "model_nominal_water_supply_and_1MW_in_step":qualifies,
        "minimum_gas_minus_water_local_nodal_difference_K":node_approach,
        "minimum_water_outlet_temperature_K_at_numerical_solver_nodes":
            min_water_outlet_K_at_solver_nodes,
        "maximum_water_outlet_temperature_K_at_numerical_solver_nodes":
            max_water_outlet_K_at_solver_nodes,
        "minimum_is_discrete_solver_nodes_not_continuous_guarantee":True,
        "liquid_outlet_lower_than_required_at_start":bool(
            t_water_first<required_water_supply_K),
        "gas_holdup_change_J":ug,"water_enthalpy_holdup_change_J":ul,
        "wall_holdup_change_J":uw,
        "net_boundary_gas_heat_into_HX_J":ib_g,
        "net_boundary_liquid_heat_from_HX_J":ib_l,
        "integrated_gas_to_wall_J":q_gw,
        "integrated_wall_to_liquid_J":q_wl,
        "independent_gas_energy_residual_J":rg,
        "independent_water_energy_residual_J":rl,
        "independent_wall_energy_residual_J":rw,
        "overall_HX_energy_residual_J":total,
        "assumed_hx_pressure_pump_audit":pressure,
        "max_liquid_temperature_K_numerical_solver_nodes":water_max,
        "water_actual_pressure_measured":False,
        "installed_UA_measured":False,
        "gas_temperature_dependent_cp_validated":False,
        "liquid_EOS_interpolated_from_direct_CoolProp":True,
        "gas_water_pressure_drop_evidenced":False,
        "numerical_integrator_steps":sol.t.size,
        "physically_qualified_1MW_liquid_process":False,
    }


def eos_interpolation_check(*,pressure_Pa:float=2_000_000.)->dict:
    from CoolProp.CoolProp import PropsSI
    grid,H,CP,_,sat=_water_table(pressure_Pa)
    points=(383.4,403.7,423.3,448.1)
    checks=[]
    for t in points:
        h_direct=float(PropsSI("H","T",t,"P",pressure_Pa,"HEOS::Water"))
        h_interp=float(_interp_checked(t,grid,H))
        cp_direct=float(PropsSI("C","T",t,"P",pressure_Pa,"HEOS::Water"))
        cp_interp=float(_interp_checked(t,grid,CP))
        checks.append({"temperature_K":t,
                       "interpolated_enthalpy_minus_original_EOS_J_kg":
                            h_interp-h_direct,
                       "relative_cp_interpolation_error":(
                           cp_interp-cp_direct)/cp_direct})
    return {"water_pressure_Pa_ASSUMED":pressure_Pa,
            "water_saturation_K":sat,
            "property_lookup_does_not_extrapolate":True,
            "direct_EOS_comparison":checks,
            "source":"CoolProp HEOS::Water at fixed assumed pressure",
            "water_eos_calibrated_in_own_experiment":False}
