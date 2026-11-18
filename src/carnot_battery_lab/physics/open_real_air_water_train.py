"""M3.9 small-scale pressure-connected real-air bed + counterflow water HX.

All geometry, reservoirs, conductances and inventories are numerical
hypotheses, not measured equipment. This open train is deliberately NOT
the industrial 1MW service and NOT a closed gas circulation loop.

Bed and HX gas cells share one conservative mass/internal-energy vector
and share the same pressure-driven face flux at their interface. No
intermediate prescribed gas flow, temperature, density or pressure.
Water is an independent constant-pressure enthalpy inventory with
prescribed mass flow, and the HX wall has its own thermal capacitance.
Pressure loss on the gas side uses Ergun in the bed and an explicitly
assumed Darcy + minor-loss characteristic in the HX. Neglects kinetic
energy, elevation, pressure waves, water-side pressure loss and axial
conduction. Assumed preheated bed is not a charged/cycled system.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
import math
import numpy as np
from scipy.integrate import solve_ivp
from .packed_bed import PackedBedGeometry
from .real_air_bed_prototype import ergun_face,_tp_properties
from .real_air_control_volume import AirVolumeState
from .transient_liquid_hx import _water_table,_interp_checked


@dataclass(frozen=True)
class OpenAirWaterTrain:
    bed_cells:int=4
    hx_cells:int=4
    bed_length_m:float=.5
    bed_diameter_m:float=.3
    particle_diameter_m:float=.01
    porosity:float=.4
    rock_rho:float=2600.
    rock_cp:float=850.
    bed_UA_per_m3:float=5000.
    hx_gas_volume_m3:float=.01
    hx_gas_flow_area_m2:float=.012
    hx_hydraulic_diameter_m:float=.03
    hx_length_m:float=1.
    hx_assumed_friction:float=.04
    hx_total_minor_K:float=2.
    hx_overall_UA_W_K:float=120.
    hx_water_mass_kg:float=1.
    hx_wall_C_J_K:float=1000.
    water_flow_kg_s:float=.02
    water_pressure_assumed_Pa:float=2e6
    water_inlet_K:float=383.15
    initial_bed_solid_K:float=493.15
    initial_gas_K:float=383.15
    initial_water_wall_K:float=383.15
    initial_gas_P_Pa:float=250000.
    inlet_gas_T_K:float=383.15
    inlet_gas_P_Pa:float=250100.
    outlet_reservoir_T_K:float=383.15
    outlet_reservoir_P_Pa:float=249900.

    def __post_init__(self):
        for key in ("bed_cells","hx_cells"):
            n=getattr(self,key)
            if isinstance(n,bool) or not isinstance(n,int) or not 2<=n<=16:
                raise ValueError("prototype grid must be 2..16 cells per component")
        for key,val in asdict(self).items():
            if not isinstance(val,(int,float)) or not math.isfinite(val) or val<=0:
                raise ValueError("invalid positive prototype input: "+key)
        if not 0<self.porosity<1:
            raise ValueError("invalid bed porosity")
        if not 50_000<self.outlet_reservoir_P_Pa<self.inlet_gas_P_Pa<2e6:
            raise ValueError("prototype requires positive forward reservoir pressure head")
        if not 50_000<self.initial_gas_P_Pa<2e6:
            raise ValueError("initial gas pressure outside domain")
        for t in (self.initial_bed_solid_K,self.initial_gas_K,
                  self.inlet_gas_T_K,self.outlet_reservoir_T_K,
                  self.initial_water_wall_K,self.water_inlet_K):
            if not 300<t<650:
                raise ValueError("initial/boundary temperature outside prototype domain")


def hx_darcy_face(left,right,*,area,loss_coefficient):
    """Signed low-Mach mass/enthalpy flux at one assumed gas resistance."""
    if not math.isfinite(area) or area<=0 or not math.isfinite(loss_coefficient) or loss_coefficient<=0:
        raise ValueError("invalid flow area or gas resistance")
    dp=left["P"]-right["P"]
    if abs(dp)<1e-7:return 0.,0.,0.
    up=left if dp>0 else right
    v=math.sqrt(2*abs(dp)/(up["rho"]*loss_coefficient))
    m=math.copysign(up["rho"]*area*v,dp)
    return m,m*up["h"],v/up["a"]


def run_open_air_water_train(a:OpenAirWaterTrain,*,duration_s:float=60.):
    """Coupled pressure-flow numerical prototype with independent ledgers."""
    from CoolProp import AbstractState
    from CoolProp.CoolProp import DmassUmass_INPUTS
    if not math.isfinite(duration_s) or not 0<duration_s<=300:
        raise ValueError("prototype duration outside (0,300]s")
    nb=a.bed_cells;nh=a.hx_cells;n=nb+nh
    g=PackedBedGeometry(length_m=a.bed_length_m,diameter_m=a.bed_diameter_m,
                        particle_diameter_m=a.particle_diameter_m,porosity=a.porosity)
    bulk=g.bed_volume_m3/nb
    volumes=np.array([bulk*g.porosity]*nb+[a.hx_gas_volume_m3/nh]*nh)
    rock_C=bulk*(1-g.porosity)*a.rock_rho*a.rock_cp
    bed_UA=bulk*a.bed_UA_per_m3
    wall_C=a.hx_wall_C_J_K/nh
    side_UA=2*a.hx_overall_UA_W_K/nh
    water_mass=a.hx_water_mass_kg/nh
    # Existing water EOS table at declared constant pressure, enthalpy
    # is the integration state; inversion avoids cp/interpolation mismatch.
    grid,H,CP,_,sat=_water_table(a.water_pressure_assumed_Pa)
    def water_T(h):
        return _interp_checked(h,H,grid)
    hi=float(_interp_checked(a.water_inlet_K,grid,H))
    h0=float(_interp_checked(a.initial_water_wall_K,grid,H))
    initial=AirVolumeState.from_TP(1.,a.initial_gas_K,a.initial_gas_P_Pa)
    left=_tp_properties(a.inlet_gas_T_K,a.inlet_gas_P_Pa)
    right=_tp_properties(a.outlet_reservoir_T_K,a.outlet_reservoir_P_Pa)
    air=AbstractState("HEOS","Air")
    def gas_decode(i,m,U):
        if not math.isfinite(m) or m<=0 or not math.isfinite(U):
            raise ValueError("gas inventory invalid")
        air.update(DmassUmass_INPUTS,m/volumes[i],U/m)
        T,P=air.T(),air.p()
        if not 280<T<800 or not 50_000<P<2e6:
            raise ValueError("gas EOS domain exceeded")
        return {"T":T,"P":P,"rho":air.rhomass(),"h":air.hmass(),
                "mu":air.viscosity(),"a":air.speed_sound(),"cp":air.cpmass(),
                "k":air.conductivity()}
    # State [gas m,gas U, bed Ts, HX wall T, HX liquid h, 7 integral terms]
    is_=2*n; iw=is_+nb; il=iw+nh; iz=il+nh
    y0=np.r_[volumes*initial.mass_kg,volumes*initial.internal_energy_J,
             np.full(nb,a.initial_bed_solid_K),
             np.full(nh,a.initial_water_wall_K),np.full(nh,h0),np.zeros(7)]
    dx=a.bed_length_m/nb
    # Half-cell resistances at component boundaries. At the bed/HX face,
    # solve one series resistance with the SAME mass flow through both.
    k_hx=(a.hx_assumed_friction*a.hx_length_m/a.hx_hydraulic_diameter_m+
           a.hx_total_minor_K)/nh
    def interface(l,r):
        dp=l["P"]-r["P"]
        if abs(dp)<1e-7:return 0.,0.,0.
        up=l if dp>0 else r
        e=g.porosity;d=g.particle_diameter_m
        A=150*up["mu"]*(1-e)**2*(dx/2)/(e**3*d*d)
        B=1.75*up["rho"]*(1-e)*(dx/2)/(e**3*d)
        # Convert bed superficial velocity and HX velocity to mass flux.
        ra=g.cross_section_m2*up["rho"]
        rb=a.hx_gas_flow_area_m2*up["rho"]
        c1=A/ra
        c2=B/(ra*ra)+(.25*k_hx*up["rho"])/(rb*rb)
        mag=2*abs(dp)/(c1+math.sqrt(c1*c1+4*c2*abs(dp)))
        m=math.copysign(mag,dp)
        return m,m*up["h"],max(mag/(ra*e),mag/rb)/up["a"]

    def evaluate(y):
        states=[gas_decode(i,y[i],y[n+i]) for i in range(n)]
        faces=[]
        extended=[left,*states,right]
        for f in range(n+1):
            l,r=extended[f:f+2]
            if f<nb:
                faces.append(ergun_face(l,r,g,dx/2 if f==0 else dx))
            elif f==nb:
                faces.append(interface(l,r))
            else:
                faces.append(hx_darcy_face(l,r,area=a.hx_gas_flow_area_m2,
                                   loss_coefficient=k_hx/2 if f==n else k_hx))
        return states,np.asarray(faces)
    def rhs(_,y):
        gas,f=evaluate(y)
        tg=np.array([x["T"] for x in gas])
        ts=y[is_:iw];tw=y[iw:il];hl=y[il:iz];tl=water_T(hl)
        qgs=bed_UA*(tg[:nb]-ts)
        qgw=side_UA*(tg[nb:]-tw)
        qwl=side_UA*(tw-tl)
        d=np.zeros_like(y)
        d[:n]=f[:-1,0]-f[1:,0]
        d[n:2*n]=f[:-1,1]-f[1:,1]-np.r_[qgs,qgw]
        d[is_:iw]=qgs/rock_C
        d[iw:il]=(qgw-qwl)/wall_C
        d[il:iz]=(a.water_flow_kg_s*(np.r_[hl[1:],hi]-hl)+qwl)/water_mass
        d[iz:]=[f[0,0],f[-1,0],f[0,1],f[-1,1],
                a.water_flow_kg_s*(hl[0]-hi),f[nb,0],f[nb,1]]
        return d
    sol=solve_ivp(rhs,(0,duration_s),y0,method="BDF",rtol=3e-7,
          atol=np.r_[np.full(n,1e-10),np.full(n,.001),
                    np.full(nb+nh,1e-6),np.full(nh,.001),
                    [1e-8,1e-8,.001,.001,.001,1e-8,.001]],
          max_step=min(2.,duration_s))
    if not sol.success:raise RuntimeError(sol.message)
    y=sol.y[:,-1];states,faces=evaluate(y)
    max_mach=max(float(np.max(evaluate(sol.y[:,i])[1][:,2]))
                 for i in range(sol.t.size))
    if max_mach>.1:raise ValueError("low-Mach assumption violated")
    ml,mr,el,er,ew,mi,ei=map(float,y[iz:])
    dm=y[:n]-y0[:n];du=y[n:2*n]-y0[n:2*n]
    dr=rock_C*float(sum(y[is_:iw]-y0[is_:iw]))
    dw=wall_C*float(sum(y[iw:il]-y0[iw:il]))
    dl=water_mass*float(sum(y[il:iz]-y0[il:iz]))
    # Separate component interface conservation, plus full train.
    mass_bed=float(sum(dm[:nb]))-ml+mi
    mass_hx=float(sum(dm[nb:]))-mi+mr
    energy_bed=float(sum(du[:nb]))+dr-el+ei
    energy_hx=float(sum(du[nb:]))+dw+dl-ei+er+ew
    if max(abs(mass_bed),abs(mass_hx))>1e-7*max(1.,abs(ml),abs(mr),abs(mi)):
        raise RuntimeError("component mass conservation defect")
    if max(abs(energy_bed),abs(energy_hx))>1e-6*max(1.,abs(el),abs(er),abs(ei),abs(ew)):
        raise RuntimeError("component energy conservation defect")
    tl=water_T(y[il:iz])
    return {
      "assumptions":asdict(a),"duration_s":duration_s,
      "gas_final_states":states,"gas_face_mass_flow_kg_s":faces[:,0].tolist(),
      "bed_solid_final_K":y[is_:iw].tolist(),
      "hx_wall_final_K":y[iw:il].tolist(),"water_final_K":tl.tolist(),
      "water_outlet_final_C":float(tl[0])-273.15,
      "water_outlet_max_accepted_node_C":float(max(water_T(sol.y[il,:])))-273.15,
      "water_net_boundary_heat_J":ew,
      "water_mean_thermal_duty_W":ew/duration_s,
      "bed_initial_solid_energy_source_ASSUMED":True,
      "bed_solid_inventory_change_J":dr,
      "hx_wall_inventory_change_J":dw,"water_inventory_change_J":dl,
      "gas_total_mass_change_kg":float(sum(dm)),
      "gas_total_internal_energy_change_J":float(sum(du)),
      "left_mass_in_kg":ml,"right_mass_out_kg":mr,
      "left_enthalpy_in_J":el,"right_enthalpy_out_J":er,
      "bed_HX_shared_interface_mass_kg":mi,
      "bed_HX_shared_interface_enthalpy_J":ei,
      "bed_mass_residual_kg":mass_bed,"HX_mass_residual_kg":mass_hx,
      "bed_energy_residual_J":energy_bed,"HX_energy_residual_J":energy_hx,
      "whole_train_mass_residual_kg":mass_bed+mass_hx,
      "whole_train_energy_residual_J":energy_bed+energy_hx,
      "maximum_interstitial_or_HX_Mach_at_accepted_nodes":max_mach,
      "water_property_model":"constant assumed pressure enthalpy inventory, interpolated CoolProp",
      "water_saturation_K_at_assumed_pressure":sat,
      "water_pressure_loss_and_pump_not_modeled":True,
      "gas_EOS_mass_and_energy_coupled_across_bed_HX":True,
      "gas_return_closed_loop_implemented":False,
      "gas_blower_and_cooler_equipment_qualified":False,
      "experimental_validation":False,"industrial_1MW_service_qualified":False,
      "Carnot_battery_RTE":None,
    }
