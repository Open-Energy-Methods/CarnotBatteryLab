"""M3.10 closed, pressure-connected small air/TES/HX charge-discharge prototype.

All hardware is hypothetical. Fixed gas volumes conserve total mass; EOS
recovers pressure. A check-valved, assumed low-head blower curve connects
the return/cooler volume to the bed. The same states persist through charge
and discharge, with NO preset hot solid or reset of inventory at switching.
Water is isobaric at an assumed pressure. Cooler uses a specified infinite
temperature sink; actual sink circulation and all external pumps are absent.
Not the original 1 MW service, 80 C waste-source HP or a cyclic steady state.
"""
from dataclasses import dataclass,asdict,field
import math
import numpy as np
from scipy.integrate import solve_ivp
from .open_real_air_water_train import OpenAirWaterTrain,hx_darcy_face
from .real_air_bed_prototype import ergun_face
from .real_air_control_volume import AirVolumeState
from .packed_bed import PackedBedGeometry
from .transient_liquid_hx import _water_table,_interp_checked


@dataclass(frozen=True)
class ClosedCycle:
    train:OpenAirWaterTrain=field(default_factory=lambda:OpenAirWaterTrain(
        bed_cells=3,hx_cells=3,initial_bed_solid_K=383.15))
    return_gas_volume_m3:float=.02
    return_area_m2:float=.012
    return_loss_K:float=3.
    blower_shutoff_head_Pa:float=500.
    blower_assumed_zero_head_flow_kg_s:float=.1
    blower_isentropic_efficiency:float=.65
    motor_efficiency:float=.85
    heater_max_electric_W:float=5000.
    heater_efficiency:float=.95
    heater_target_K:float=463.15
    heater_feedback_W_K:float=300.
    cooler_UA_W_K:float=100.
    cooler_sink_K:float=373.15
    charge_s:float=1200.
    discharge_s:float=180.
    max_step_s:float=5.

    def __post_init__(self):
        for k,v in asdict(self).items():
            if k=="train":continue
            if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v<=0:
                raise ValueError("invalid cycle input "+k)
        if max(self.blower_isentropic_efficiency,self.motor_efficiency,self.heater_efficiency)>1:
            raise ValueError("efficiencies cannot exceed unity")
        if not 300<self.cooler_sink_K<self.heater_target_K<473.15:
            raise ValueError("sink or heater target outside limited prototype range")
        if self.blower_shutoff_head_Pa/self.train.initial_gas_P_Pa>.015:
            raise ValueError("low-head blower approximation not applicable")
        t=self.train
        if max(abs(t.initial_bed_solid_K-t.initial_gas_K),
               abs(t.initial_water_wall_K-t.initial_gas_K))>1e-8:
            raise ValueError("start all inventories at same declared cold state")
        if self.charge_s>3600 or self.discharge_s>1800:
            raise ValueError("prototype duration outside supported study")


def blower_flow(suction,bed,g,dx,c):
    """Solve positive branch of assumed head curve minus bed half loss.

    Head = H0*(1-(m/m0)^2); discharge pressure = suction pressure + head.
    Check valve blocks reverse flow; no surge model or hardware curve.
    Low-head shaft enthalpy increase approximated by deltaP/(rho*eta).
    """
    e=g.porosity;d=g.particle_diameter_m;rho=suction["rho"]
    area=g.cross_section_m2
    A=150*suction["mu"]*(1-e)**2*(dx/2)/(e**3*d*d)/(rho*area)
    B=1.75*rho*(1-e)*(dx/2)/(e**3*d)/(rho*area)**2
    H0=c.blower_shutoff_head_Pa
    K=H0/c.blower_assumed_zero_head_flow_kg_s**2
    drive=suction["P"]+H0-bed["P"]
    if drive<=0:return 0.,0.,0.,0.
    m=2*drive/(A+math.sqrt(A*A+4*(B+K)*drive))
    # No extrapolation of blower curve into negative head / turbine mode.
    if m>c.blower_assumed_zero_head_flow_kg_s:
        m=c.blower_assumed_zero_head_flow_kg_s
        # With zero head at capped free delivery, excess pressure would
        # require an extra unknown restriction. Expose rather than hide it.
        raise ValueError("blower beyond declared positive-head characteristic")
    head=H0-K*m*m
    shaft=m*head/(rho*c.blower_isentropic_efficiency)
    electric=shaft/c.motor_efficiency
    return m,shaft,electric,head


def run_closed_cycle(c:ClosedCycle):
    from CoolProp import AbstractState
    from CoolProp.CoolProp import DmassUmass_INPUTS
    a=c.train;nb=a.bed_cells;nh=a.hx_cells;n=nb+nh+1
    g=PackedBedGeometry(length_m=a.bed_length_m,diameter_m=a.bed_diameter_m,
        particle_diameter_m=a.particle_diameter_m,porosity=a.porosity)
    dx=g.length_m/nb;bulk=g.bed_volume_m3/nb
    vol=np.array([bulk*g.porosity]*nb+[a.hx_gas_volume_m3/nh]*nh+
                 [c.return_gas_volume_m3])
    Cs=bulk*(1-g.porosity)*a.rock_rho*a.rock_cp
    Ua=bulk*a.bed_UA_per_m3
    Cw=a.hx_wall_C_J_K/nh
    Uh=2*a.hx_overall_UA_W_K/nh
    Mw=a.hx_water_mass_kg/nh
    grid,H,_,_,sat=_water_table(a.water_pressure_assumed_Pa)
    hi=float(_interp_checked(a.water_inlet_K,grid,H))
    h0=float(_interp_checked(a.initial_water_wall_K,grid,H))
    init=AirVolumeState.from_TP(1.,a.initial_gas_K,a.initial_gas_P_Pa)
    is_=2*n;iw=is_+nb;il=iw+nh;iz=il+nh
    # Cumulative ledgers: heater electricity, heat to gas, blower electric,
    # blower gas work, cooler heat, water boundary heat, interface mass.
    y0=np.r_[vol*init.mass_kg,vol*init.internal_energy_J,
        np.full(nb,a.initial_bed_solid_K),np.full(nh,a.initial_water_wall_K),
        np.full(nh,h0),np.zeros(7)]
    air=AbstractState("HEOS","Air")
    kh=(a.hx_assumed_friction*a.hx_length_m/a.hx_hydraulic_diameter_m+
        a.hx_total_minor_K)/nh
    def decode(i,y):
        m=y[i];U=y[n+i]
        if m<=0 or not math.isfinite(m) or not math.isfinite(U):
            raise ValueError("invalid closed gas inventory")
        air.update(DmassUmass_INPUTS,m/vol[i],U/m)
        T,P=air.T(),air.p()
        if not 280<T<800 or not 50_000<P<2e6:
            raise ValueError("closed loop EOS domain exceeded")
        return dict(T=T,P=P,rho=air.rhomass(),h=air.hmass(),
                    mu=air.viscosity(),a=air.speed_sound())
    def mixed_face(l,r):
        dp=l["P"]-r["P"]
        if abs(dp)<1e-7:return 0.,0.,0.
        up=l if dp>0 else r
        e=g.porosity;d=g.particle_diameter_m;rho=up["rho"]
        ra=g.cross_section_m2*rho;rb=a.hx_gas_flow_area_m2*rho
        A=150*up["mu"]*(1-e)**2*(dx/2)/(e**3*d*d)/ra
        B=1.75*rho*(1-e)*(dx/2)/(e**3*d)/ra**2+.25*kh*rho/rb**2
        z=2*abs(dp)/(A+math.sqrt(A*A+4*B*abs(dp)))
        m=math.copysign(z,dp)
        return m,m*up["h"],max(z/(ra*e),z/rb)/up["a"]
    def flows(y):
        st=[decode(i,y) for i in range(n)]
        m,w,el,head=blower_flow(st[-1],st[0],g,dx,c)
        # Faces indexed by receiving cell. Blower adds work only at
        # discharge, not to the suction enthalpy flux removed from return.
        f=[(m,m*st[-1]["h"],m/(st[-1]["rho"]*g.cross_section_m2*g.porosity*st[-1]["a"]))]
        for i in range(1,n):
            l,r=st[i-1:i+1]
            if i<nb:f.append(ergun_face(l,r,g,dx))
            elif i==nb:f.append(mixed_face(l,r))
            elif i<n-1:f.append(hx_darcy_face(l,r,area=a.hx_gas_flow_area_m2,loss_coefficient=kh))
            else:f.append(hx_darcy_face(l,r,area=c.return_area_m2,loss_coefficient=kh/2+c.return_loss_K))
        return st,np.asarray(f),w,el,head
    def rhs(charge):
        def fun(_,y):
            st,f,w,el,head=flows(y)
            tg=np.array([x["T"] for x in st]);ts=y[is_:iw];tw=y[iw:il]
            hl=y[il:iz];tl=_interp_checked(hl,H,grid)
            qgs=Ua*(tg[:nb]-ts)
            qgw=Uh*(tg[nb:-1]-tw);qwl=Uh*(tw-tl)
            # Charge mode: no water export (stagnant liquid inventory);
            # discharge: same water inlet and fixed mass flow as M3.9.
            mw=0. if charge else a.water_flow_kg_s
            eheat=min(c.heater_max_electric_W,max(0.,c.heater_feedback_W_K*(c.heater_target_K-tg[-1]))) if charge else 0.
            qheat=c.heater_efficiency*eheat
            qcool=0. if charge else c.cooler_UA_W_K*max(0.,tg[-1]-c.cooler_sink_K)
            d=np.zeros_like(y)
            d[:n]=f[:,0]-np.roll(f[:,0],-1)
            d[n:2*n]=f[:,1]-np.roll(f[:,1],-1)-np.r_[qgs,qgw,qcool-qheat]
            d[n]+=w
            d[is_:iw]=qgs/Cs
            d[iw:il]=(qgw-qwl)/Cw
            d[il:iz]=(mw*(np.r_[hl[1:],hi]-hl)+qwl)/Mw
            d[iz:]=[eheat,qheat,el,w,qcool,mw*(hl[0]-hi),f[nb,0]]
            return d
        return fun
    def stage(y_start,seconds,charge):
        sol=solve_ivp(rhs(charge),(0,seconds),y_start,method="BDF",
            rtol=3e-7,atol=np.r_[np.full(n,1e-10),np.full(n,.001),
            np.full(nb+nh,1e-6),np.full(nh,.001),np.full(7,.001)],
            max_step=c.max_step_s)
        if not sol.success:raise RuntimeError(sol.message)
        y=sol.y[:,-1];ds=y-y_start
        st,f,w,el,head=flows(y)
        maxMach=0.;maxHeadRatio=0.
        for j in range(sol.t.size):
            states,faces,_,_,h=flows(sol.y[:,j])
            maxMach=max(maxMach,float(np.max(faces[:,2])))
            maxHeadRatio=max(maxHeadRatio,h/states[-1]["P"])
        if maxMach>.1 or maxHeadRatio>.02:
            raise ValueError("low-Mach or low-head scope exceeded")
        masses=float(sum(ds[:n]));Ug=float(sum(ds[n:2*n]))
        Us=Cs*float(sum(ds[is_:iw]));Uw=Cw*float(sum(ds[iw:il]));Hl=Mw*float(sum(ds[il:iz]))
        Eheat,Qheat,Ebl,Wbl,Qcool,Qwater,Minterface=map(float,ds[iz:])
        thermal_res=Ug+Us+Uw+Hl-Qheat-Wbl+Qcool+Qwater
        electrical_res=Ug+Us+Uw+Hl-Eheat-Ebl+Qcool+Qwater+(Eheat-Qheat)+(Ebl-Wbl)
        if abs(masses)>1e-8 or max(abs(thermal_res),abs(electrical_res))>1e-6*max(1.,abs(Qheat),abs(Qcool),abs(Qwater),abs(Wbl)):
            raise RuntimeError("closed loop first law violated")
        temps=_interp_checked(sol.y[il,:],H,grid)-273.15
        return y,dict(duration_s=seconds,gas_input_mass_kg=float(sum(y_start[:n])),
            gas_final_mass_kg=float(sum(y[:n])),mass_residual_kg=masses,
            gas_internal_energy_change_J=Ug,solid_energy_change_J=Us,
            wall_energy_change_J=Uw,liquid_enthalpy_inventory_change_J=Hl,
            heater_electric_J=Eheat,heater_thermal_to_gas_J=Qheat,
            blower_electric_J=Ebl,blower_work_to_gas_J=Wbl,
            heater_loss_to_environment_J=Eheat-Qheat,motor_loss_to_environment_J=Ebl-Wbl,
            cooler_heat_to_assumed_sink_J=Qcool,water_boundary_heat_J=Qwater,
            thermal_first_law_residual_J=thermal_res,electrical_boundary_residual_J=electrical_res,
            final_water_outlet_C=float(temps[-1]),max_water_outlet_C=float(max(temps)),
            final_solid_C=(y[is_:iw]-273.15).tolist(),
            final_gas_pressure_Pa=[q["P"] for q in st],
            final_gas_temperature_C=[q["T"]-273.15 for q in st],
            final_blower_mass_flow_kg_s=float(f[0,0]),final_blower_head_Pa=head,
            cumulative_bed_HX_interface_mass_kg=Minterface,
            max_accepted_node_Mach=maxMach,max_blower_head_over_suction_pressure=maxHeadRatio)
    y1,ch=stage(y0,c.charge_s,True)
    y2,dis=stage(y1,c.discharge_s,False)
    return {"research_stage":"M3_10_CLOSED_REAL_AIR_THERMAL_SEQUENCE",
        "assumptions":asdict(c),"charge":ch,"discharge":dis,
        "charge_end_is_discharge_start":True,
        "whole_cycle_gas_mass_residual_kg":float(sum(y2[:n]-y0[:n])),
        "whole_sequence_electrical_boundary_residual_J":ch["electrical_boundary_residual_J"]+dis["electrical_boundary_residual_J"],
        "total_heater_and_blower_electric_J":ch["heater_electric_J"]+ch["blower_electric_J"]+dis["blower_electric_J"],
        "water_heat_not_qualified_process_service_J":dis["water_boundary_heat_J"],
        "return_cooler_has_assumed_infinite_sink":True,
        "gas_flow_direction_same_during_charge_and_discharge":True,
        "water_flow_off_during_charge":True,
        "external_cooling_and_water_pump_electricity_excluded":True,
        "no_external_gas_mass_source_or_sink":True,
        "closed_gas_circulation_modeled":True,
        "verified_periodic_cycle":False,"hardware_qualified":False,
        "experimental_validation":False,"industrial_1MW_service_qualified":False,
        "Carnot_battery_RTE":None}
