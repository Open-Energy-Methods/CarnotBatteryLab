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
from scipy.optimize import brentq
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


def blower_flow(suction,bed,g,dx,c,*,valve_loss_K=0.):
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
    B+=valve_loss_K/(2*rho*c.return_area_m2**2)
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


def gas_route(nb,nh,reverse):
    """Physical indices in flow order; HX and return never reverse."""
    bed=list(range(nb))
    if reverse:bed.reverse()
    return np.array(bed+list(range(nb,nb+nh+1)),dtype=int)


def qualified_water_heat(t,solution,outlet_index,ledger_index,threshold_h):
    """Integrate the existing signed boundary ledger only above grade.

    Root detection is bracketed by accepted solver nodes; an excursion
    entirely between nodes is not certified. Step refinement is required.
    """
    t=np.asarray(t)
    if len(t)<2 or np.any(np.diff(t)<=0):
        raise ValueError("need increasing accepted times")
    def margin(z):return float(solution(z)[outlet_index]-threshold_h)
    def ledger(z):return float(solution(z)[ledger_index])
    margins=[margin(z) for z in t]
    seconds=heat=0.
    # Work per accepted step so an unresolved local excursion cannot
    # incorrectly classify a much larger region spanning many steps.
    for left,right,fl,fr in zip(t[:-1],t[1:],margins[:-1],margins[1:]):
        cuts=[left,right]
        if fl*fr<0:cuts.insert(1,brentq(margin,left,right))
        for l,r in zip(cuts[:-1],cuts[1:]):
            if margin((l+r)/2)>=0:
                seconds+=r-l
                heat+=ledger(r)-ledger(l)
    return float(seconds),float(heat)


def process_water_split(h_out,h_in,h_target,demand_W,*,bypass=True):
    """Ideal adiabatic mixing at fixed process mass flow and inlet state.

    Returns HX flow, bypass flow, delivery enthalpy and signed duty.
    When HX outlet is too cold, all flow passes the HX; unmet demand
    remains visible. No auxiliary heat or cold-water mass is created.
    """
    if not all(math.isfinite(x) for x in (h_out,h_in,h_target,demand_W)) or h_target<=h_in or demand_W<=0:
        raise ValueError("invalid process water demand")
    m=demand_W/(h_target-h_in)
    if bypass and h_out>h_target:
        through=demand_W/(h_out-h_in)
        return through,m-through,h_target,demand_W
    return m,0.,h_out,m*(h_out-h_in)


def run_closed_cycle(c:ClosedCycle,*,reverse_discharge=False,valve_loss_K=0.,cycles=1,water_control_gain_kg_s_K=0.,process_duty_W=None,process_bypass=True):
    """Backward-compatible M3.10 baseline, with optional M3.11 routing.

    Valve K is an assumed loss per active bed port, identical in each
    direction. Instant switching is idealised; no valve motion/dead volume.
    Legacy top-level charge/discharge and balances refer to cycle one.
    """
    if not isinstance(reverse_discharge,bool):
        raise ValueError("reverse_discharge must be boolean")
    if isinstance(valve_loss_K,bool) or not math.isfinite(valve_loss_K) or valve_loss_K<0:
        raise ValueError("invalid valve loss")
    if isinstance(cycles,bool) or not isinstance(cycles,int) or not 1<=cycles<=10:
        raise ValueError("cycle count must be 1..10")
    if isinstance(water_control_gain_kg_s_K,bool) or not math.isfinite(water_control_gain_kg_s_K) or not 0<=water_control_gain_kg_s_K<=.02:
        raise ValueError('water feedback gain outside 0..0.02 kg/s/K')
    if not isinstance(process_bypass,bool):
        raise ValueError("process_bypass must be boolean")
    if process_duty_W is not None:
        if isinstance(process_duty_W,bool) or not math.isfinite(process_duty_W) or process_duty_W<=0 or water_control_gain_kg_s_K!=0:
            raise ValueError("invalid fixed process duty or conflicting controller")
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
    threshold_h=float(_interp_checked(423.15,grid,H))
    if hi>=threshold_h:raise ValueError('150 C qualification requires colder inlet')
    low_band_h=float(_interp_checked(422.65,grid,H))
    high_band_h=float(_interp_checked(423.65,grid,H))
    def water_flow(T_K,charge):
        if charge:return 0.
        return float(np.clip(a.water_flow_kg_s+water_control_gain_kg_s_K*(T_K-423.15),
                             .1*a.water_flow_kg_s,2*a.water_flow_kg_s))
    demand_flow=None if process_duty_W is None else process_duty_W/(threshold_h-hi)
    if demand_flow is not None and not .1*a.water_flow_kg_s<=demand_flow<=2*a.water_flow_kg_s:
        raise ValueError("process demand outside assumed total water-flow envelope")
    def delivery(h,charge):
        if charge:return 0.,0.,h,0.
        if process_duty_W is None:
            flow=water_flow(float(_interp_checked(h,H,grid)),False)
            return flow,0.,h,flow*(h-hi)
        return process_water_split(h,hi,threshold_h,process_duty_W,bypass=process_bypass)
    init=AirVolumeState.from_TP(1.,a.initial_gas_K,a.initial_gas_P_Pa)
    is_=2*n;iw=is_+nb;il=iw+nh;iz=il+nh
    # Cumulative ledgers: heater electricity, heat to gas, blower electric,
    # blower gas work, cooler heat, water boundary heat, interface mass,
    # and three separately integrated gas/solid/wall/water exchange terms.
    y0=np.r_[vol*init.mass_kg,vol*init.internal_energy_J,
        np.full(nb,a.initial_bed_solid_K),np.full(nh,a.initial_water_wall_K),
        np.full(nh,h0),np.zeros(14)]
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
        B=1.75*rho*(1-e)*(dx/2)/(e**3*d)/ra**2+.25*kh*rho/rb**2+valve_loss_K/(2*rho*c.return_area_m2**2)
        z=2*abs(dp)/(A+math.sqrt(A*A+4*B*abs(dp)))
        m=math.copysign(z,dp)
        return m,m*up["h"],max(z/(ra*e),z/rb)/up["a"]
    def flows(y,charge):
        st=[decode(i,y) for i in range(n)]
        order=gas_route(nb,nh,reverse_discharge and not charge)
        m,w,el,head=blower_flow(st[-1],st[order[0]],g,dx,c,valve_loss_K=valve_loss_K)
        # Faces indexed by receiving cell. Blower adds work only at
        # discharge, not to the suction enthalpy flux removed from return.
        f=[(m,m*st[-1]["h"],m/(st[-1]["rho"]*g.cross_section_m2*g.porosity*st[-1]["a"]))]
        for i in range(1,n):
            l,r=st[order[i-1]],st[order[i]]
            if i<nb:f.append(ergun_face(l,r,g,dx))
            elif i==nb:f.append(mixed_face(l,r))
            elif i<n-1:f.append(hx_darcy_face(l,r,area=a.hx_gas_flow_area_m2,loss_coefficient=kh))
            else:f.append(hx_darcy_face(l,r,area=c.return_area_m2,loss_coefficient=kh/2+c.return_loss_K))
        return st,np.asarray(f),w,el,head,order
    def rhs(charge):
        def fun(_,y):
            st,f,w,el,head,order=flows(y,charge)
            tg=np.array([x["T"] for x in st]);ts=y[is_:iw];tw=y[iw:il]
            hl=y[il:iz];tl=_interp_checked(hl,H,grid)
            qgs=Ua*(tg[:nb]-ts)
            qgw=Uh*(tg[nb:-1]-tw);qwl=Uh*(tw-tl)
            # Charge mode: no water export (stagnant liquid inventory);
            # discharge: same water inlet and fixed mass flow as M3.9.
            mw,mb,hd,qd=delivery(float(hl[0]),charge)
            eheat=min(c.heater_max_electric_W,max(0.,c.heater_feedback_W_K*(c.heater_target_K-tg[-1]))) if charge else 0.
            qheat=c.heater_efficiency*eheat
            qcool=0. if charge else c.cooler_UA_W_K*max(0.,tg[-1]-c.cooler_sink_K)
            d=np.zeros_like(y)
            d[order]=f[:,0]-np.roll(f[:,0],-1)
            d[n+order]=f[:,1]-np.roll(f[:,1],-1)
            d[n:2*n]-=np.r_[qgs,qgw,qcool-qheat]
            d[n+order[0]]+=w
            d[is_:iw]=qgs/Cs
            d[iw:il]=(qgw-qwl)/Cw
            d[il:iz]=(mw*(np.r_[hl[1:],hi]-hl)+qwl)/Mw
            d[iz:]=[eheat,qheat,el,w,qcool,mw*(hl[0]-hi),f[nb,0],
                    sum(qgs),sum(qgw),sum(qwl),mw,mb,
                    0. if charge or process_duty_W is None else max(0.,process_duty_W-qd),
                    0. if charge or process_duty_W is None else max(0.,qd-process_duty_W)]
            return d
        return fun
    def stage(y_start,seconds,charge):
        sol=solve_ivp(rhs(charge),(0,seconds),y_start,method="BDF",
            rtol=3e-7,atol=np.r_[np.full(n,1e-10),np.full(n,.001),
            np.full(nb+nh,1e-6),np.full(nh,.001),np.full(14,.001)],
            max_step=c.max_step_s,first_step=min(1e-6,seconds),dense_output=True)
        if not sol.success:raise RuntimeError(sol.message)
        y=sol.y[:,-1];ds=y-y_start
        st,f,w,el,head,order=flows(y,charge)
        maxMach=0.;maxHeadRatio=0.;peak_pressure=0.;min_pressure=float('inf')
        peak_cooler=0.;peak_blower_electric=0.;peak_heater_electric=0.;peak_blower_flow=0.
        for j in range(sol.t.size):
            states,faces,_,power,h,_=flows(sol.y[:,j],charge)
            ret=states[-1]['T']
            peak_cooler=max(peak_cooler,0. if charge else c.cooler_UA_W_K*max(0.,ret-c.cooler_sink_K))
            peak_heater_electric=max(peak_heater_electric,min(c.heater_max_electric_W,max(0.,c.heater_feedback_W_K*(c.heater_target_K-ret))) if charge else 0.)
            peak_blower_electric=max(peak_blower_electric,power)
            peak_blower_flow=max(peak_blower_flow,float(faces[0,0]))
            maxMach=max(maxMach,float(np.max(faces[:,2])))
            maxHeadRatio=max(maxHeadRatio,h/states[-1]["P"])
            peak_pressure=max(peak_pressure,max(x['P'] for x in states))
            min_pressure=min(min_pressure,min(x['P'] for x in states))
        if maxMach>.1 or maxHeadRatio>.02:
            raise ValueError("low-Mach or low-head scope exceeded")
        masses=float(sum(ds[:n]));Ug=float(sum(ds[n:2*n]))
        Us=Cs*float(sum(ds[is_:iw]));Uw=Cw*float(sum(ds[iw:il]));Hl=Mw*float(sum(ds[il:iz]))
        Eheat,Qheat,Ebl,Wbl,Qcool,Qwater,Minterface,Qgs,Qgw,Qwl,Mwater,Mbypass,deficit,excess=map(float,ds[iz:])
        residuals={'gas':Ug-Qheat-Wbl+Qcool+Qgs+Qgw,
                   'solid':Us-Qgs,'wall':Uw-Qgw+Qwl,'water':Hl-Qwl+Qwater}
        thermal_res=Ug+Us+Uw+Hl-Qheat-Wbl+Qcool+Qwater
        electrical_res=Ug+Us+Uw+Hl-Eheat-Ebl+Qcool+Qwater+(Eheat-Qheat)+(Ebl-Wbl)
        if abs(masses)>1e-8 or max(abs(thermal_res),abs(electrical_res),*(abs(v) for v in residuals.values()))>1e-6*max(1.,abs(Qheat),abs(Qcool),abs(Qwater),abs(Wbl)):
            raise RuntimeError("closed loop first law violated")
        hx_temps=_interp_checked(sol.y[il,:],H,grid)-273.15
        delivered=[delivery(float(h),charge) for h in sol.y[il,:]]
        temps=_interp_checked(np.asarray([x[2] for x in delivered]),H,grid)-273.15
        flows_water=[x[0] for x in delivered]
        def mixed_solution(t):
            z=sol.sol(t)
            return (delivery(float(z[il]),charge)[2],z[iz+5])
        def grade(h):
            return (0.,0.) if charge else qualified_water_heat(sol.t,mixed_solution,0,1,h)
        qualified_s,qualified_J=grade(threshold_h)
        lo_s,lo_J=grade(low_band_h)
        hi_s,hi_J=grade(high_band_h)
        matched_s=matched_J=None
        if not charge and process_duty_W is not None:
            lower=max(low_band_h,hi+.9985*process_duty_W/demand_flow)
            upper=min(high_band_h,hi+1.0015*process_duty_W/demand_flow)
            ls,lj=grade(lower);us,uj=grade(upper)
            matched_s=max(0.,ls-us);matched_J=lj-uj
            if abs(Mwater+Mbypass-demand_flow*seconds)>1e-6:
                raise RuntimeError("process water mass balance violated")
            if abs(Qwater-(process_duty_W*seconds-deficit+excess))>.2:
                raise RuntimeError("process duty ledger violated")
        return y,dict(duration_s=seconds,
            water_throughput_kg=Mwater+Mbypass,hx_water_throughput_kg=Mwater,bypass_water_throughput_kg=Mbypass,
            process_demand_W=process_duty_W,
            process_demand_flow_kg_s=None if charge else demand_flow,
            process_duty_deficit_J=deficit,process_duty_excess_J=excess,
            simultaneous_target_duration_s=matched_s,simultaneous_target_heat_J=matched_J,
            final_hx_water_outlet_C=float(hx_temps[-1]),
            min_hx_water_outlet_at_accepted_nodes_C=float(min(hx_temps)),
            peak_cooler_at_accepted_nodes_W=peak_cooler,
            peak_heater_electric_at_accepted_nodes_W=peak_heater_electric,
            peak_blower_electric_at_accepted_nodes_W=peak_blower_electric,
            peak_blower_flow_at_accepted_nodes_kg_s=peak_blower_flow,
            min_delivered_duty_W=min(x[3] for x in delivered),
            max_delivered_duty_W=max(x[3] for x in delivered),
            water_min_flow_at_nodes_kg_s=min(flows_water),
            water_max_flow_at_nodes_kg_s=max(flows_water),
            water_target_band_duration_s=max(0.,lo_s-hi_s),
            water_target_band_heat_J=lo_J-hi_J,
            bed_flow_order=order[:nb].tolist(),
            water_grade_threshold_C=150.,qualified_water_duration_s=qualified_s,
            qualified_water_heat_J=qualified_J,
            signed_water_heat_outside_grade_J=Qwater-qualified_J,gas_input_mass_kg=float(sum(y_start[:n])),
            gas_final_mass_kg=float(sum(y[:n])),mass_residual_kg=masses,
            gas_internal_energy_change_J=Ug,solid_energy_change_J=Us,
            wall_energy_change_J=Uw,liquid_enthalpy_inventory_change_J=Hl,
            heater_electric_J=Eheat,heater_thermal_to_gas_J=Qheat,
            blower_electric_J=Ebl,blower_work_to_gas_J=Wbl,
            heater_loss_to_environment_J=Eheat-Qheat,motor_loss_to_environment_J=Ebl-Wbl,
            cooler_heat_to_assumed_sink_J=Qcool,water_boundary_heat_J=Qwater,
            thermal_first_law_residual_J=thermal_res,electrical_boundary_residual_J=electrical_res,
            final_water_outlet_C=float(temps[-1]),max_water_outlet_C=float(max(temps)),
            min_water_outlet_C=float(min(temps)),
            peak_gas_pressure_at_accepted_nodes_Pa=peak_pressure,
            min_gas_pressure_at_accepted_nodes_Pa=min_pressure,
            integrated_gas_to_solid_J=Qgs,integrated_gas_to_wall_J=Qgw,
            integrated_wall_to_water_J=Qwl,component_thermal_residuals_J=residuals,
            final_solid_C=(y[is_:iw]-273.15).tolist(),
            final_gas_pressure_Pa=[q["P"] for q in st],
            final_gas_temperature_C=[q["T"]-273.15 for q in st],
            final_blower_mass_flow_kg_s=float(f[0,0]),final_blower_head_Pa=head,
            cumulative_bed_HX_interface_mass_kg=Minterface,
            max_accepted_node_Mach=maxMach,max_blower_head_over_suction_pressure=maxHeadRatio)
    records=[]
    current=y0
    for k in range(cycles):
        start=current
        y1,ch_i=stage(start,c.charge_s,True)
        current,di_i=stage(y1,c.discharge_s,False)
        states0=[decode(i,start) for i in range(n)]
        states1=[decode(i,current) for i in range(n)]
        records.append(dict(cycle=k+1,charge=ch_i,discharge=di_i,
            max_gas_temperature_cycle_end_change_K=max(abs(x['T']-y['T']) for x,y in zip(states0,states1)),
            max_gas_pressure_cycle_end_change_Pa=max(abs(x['P']-y['P']) for x,y in zip(states0,states1)),
            max_gas_relative_cell_mass_cycle_end_change=float(np.max(np.abs(current[:n]-start[:n])/start[:n])),
            max_water_temperature_cycle_end_change_K=float(np.max(np.abs(_interp_checked(current[il:iz],H,grid)-_interp_checked(start[il:iz],H,grid)))),
            max_rock_cycle_end_change_K=float(np.max(np.abs(current[is_:iw]-start[is_:iw]))),
            max_wall_cycle_end_change_K=float(np.max(np.abs(current[iw:il]-start[iw:il]))),
            max_gas_cell_mass_cycle_end_change_kg=float(np.max(np.abs(current[:n]-start[:n]))),
            max_gas_cell_internal_energy_cycle_end_change_J=float(np.max(np.abs(current[n:2*n]-start[n:2*n]))),
            max_water_cell_enthalpy_cycle_end_change_J_kg=float(np.max(np.abs(current[il:iz]-start[il:iz])))))
        if k==0:y2=current;ch=ch_i;dis=di_i
    return {"research_stage":"M3_10_CLOSED_REAL_AIR_THERMAL_SEQUENCE",
        "assumptions":asdict(c),"charge":ch,"discharge":dis,
        "charge_end_is_discharge_start":True,
        "whole_cycle_gas_mass_residual_kg":float(sum(y2[:n]-y0[:n])),
        "whole_sequence_electrical_boundary_residual_J":ch["electrical_boundary_residual_J"]+dis["electrical_boundary_residual_J"],
        "total_heater_and_blower_electric_J":ch["heater_electric_J"]+ch["blower_electric_J"]+dis["blower_electric_J"],
        "water_heat_not_qualified_process_service_J":dis["water_boundary_heat_J"],
        "remaining_total_thermal_inventory_above_initial_J":sum(
            ch[k]+dis[k] for k in ('gas_internal_energy_change_J','solid_energy_change_J',
            'wall_energy_change_J','liquid_enthalpy_inventory_change_J')),
        "remaining_solid_inventory_above_initial_J":ch['solid_energy_change_J']+dis['solid_energy_change_J'],
        "all_discharge_accepted_water_nodes_ge_150C":dis['min_water_outlet_C']>=150.,
        "water_temperature_150C_not_a_continuous_guarantee":True,
        "return_cooler_has_assumed_infinite_sink":True,
        "gas_flow_direction_same_during_charge_and_discharge":not reverse_discharge,
        "valve_loss_K_per_active_bed_port":valve_loss_K,
        "water_control_gain_kg_s_K":water_control_gain_kg_s_K,
        "process_duty_W":process_duty_W,"process_bypass":process_bypass,
        "ideal_instantaneous_water_mixer":process_duty_W is not None and process_bypass,
        "water_flow_control_assumed_instantaneous":True,
        "instantaneous_ideal_valve_switch":True,
        "cycle_records":records,"cycle_count":cycles,
        "repeated_sequence_mass_residual_kg":float(sum(current[:n]-y0[:n])),
        "repeated_sequence_electrical_residual_J":sum(p[phase]["electrical_boundary_residual_J"] for p in records for phase in ("charge","discharge")),
        "grade_metric_is_not_matched_service":True,
        "water_flow_off_during_charge":True,
        "external_cooling_and_water_pump_electricity_excluded":True,
        "no_external_gas_mass_source_or_sink":True,
        "closed_gas_circulation_modeled":True,
        "verified_periodic_cycle":False,"hardware_qualified":False,
        "experimental_validation":False,"industrial_1MW_service_qualified":False,
        "Carnot_battery_RTE":None}
