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


def run_closed_cycle(c:ClosedCycle,*,reverse_discharge=False,valve_loss_K=0.,cycles=1,water_control_gain_kg_s_K=0.,process_duty_W=None,process_bypass=True,cooler_cap_W=None,trace_interval_s=None,cooler_control_K=None,recuperator=None,main_heat_loss=None,exergy_audit=False,exergy_environment_K=298.15):
    """Backward-compatible M3.10 baseline, with optional M3.11 routing.

    Valve K is an assumed loss per active bed port, identical in each
    direction. Instant switching is idealised; no valve motion/dead volume.
    Legacy top-level charge/discharge and balances refer to cycle one.
    """
    if not isinstance(exergy_audit,bool) or (not math.isfinite(exergy_environment_K)) or not 280.<exergy_environment_K<350.:
        raise ValueError("invalid exergy measurement configuration")
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
    for key,val in (("cooler_cap_W",cooler_cap_W),("trace_interval_s",trace_interval_s)):
        if val is not None and (isinstance(val,bool) or not math.isfinite(val) or val<0 or (key=="trace_interval_s" and val==0)):
            raise ValueError("invalid "+key)
    if cooler_control_K is not None and (isinstance(cooler_control_K,bool) or not math.isfinite(cooler_control_K) or not c.cooler_sink_K<=cooler_control_K<c.heater_target_K):
        raise ValueError("invalid cooler feedback setpoint")
    if recuperator is not None:
        from .thermal_retention import ThermalBuffer
        if not isinstance(recuperator,ThermalBuffer):raise ValueError("invalid thermal buffer")
    if trace_interval_s is not None and trace_interval_s<1.:
        raise ValueError("trace interval must be at least one second")
    if main_heat_loss is not None:
        from .thermal_retention import MainHeatLoss
        if not isinstance(main_heat_loss,MainHeatLoss):raise ValueError("invalid main heat loss")
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
    # Optional buffer state appended AFTER the unchanged legacy ledger.
    # Tbuf, captured J, returned J, loss J; never reset between phases.
    ir=iz+14
    if recuperator is not None:
        y0=np.r_[y0,a.initial_gas_K,0.,0.,0.]
    iq=ir+(4 if recuperator is not None else 0)
    if main_heat_loss is not None:y0=np.r_[y0,0.,0.,0.]
    # M3.17 diagnostic ledgers appended after ALL legacy / optional states.
    # Temperature and entropy are determined from the same properties as
    # the energy model; no external compressor efficiency is inserted.
    iex=iq+(3 if main_heat_loss is not None else 0)
    if exergy_audit:
        from CoolProp.CoolProp import PropsSI
        from .exergy_audit import LEDGER_KEYS,close_exergy_ledger,finite_nonnegative_transport
        Swater=np.array([PropsSI("Smass","T",float(t),"P",
                        a.water_pressure_assumed_Pa,"HEOS::Water") for t in grid])
        si=float(_interp_checked(hi,H,Swater))
        def S_liquid(h):return _interp_checked(h,H,Swater)
        y0=np.r_[y0,np.zeros(len(LEDGER_KEYS))]
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
        d=dict(T=T,P=P,rho=air.rhomass(),h=air.hmass(),
                    mu=air.viscosity(),a=air.speed_sound())
        if exergy_audit:d["s"]=air.smass()
        return d
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
    def cooler_rate(T,charge):
        q=0. if charge else c.cooler_UA_W_K*max(0.,T-(c.cooler_sink_K if cooler_control_K is None else cooler_control_K))
        return q if cooler_cap_W is None else min(q,cooler_cap_W)
    def heater_rate(T,charge):
        return min(c.heater_max_electric_W,max(0.,c.heater_feedback_W_K*(c.heater_target_K-T))) if charge else 0.
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
            eheat=heater_rate(tg[-1],charge)
            qheat=c.heater_efficiency*eheat
            qcool=cooler_rate(tg[-1],charge)
            d=np.zeros_like(y)
            d[order]=f[:,0]-np.roll(f[:,0],-1)
            d[n+order]=f[:,1]-np.roll(f[:,1],-1)
            d[n:2*n]-=np.r_[qgs,qgw,qcool-qheat]
            d[n+order[0]]+=w
            d[is_:iw]=qgs/Cs
            d[iw:il]=(qgw-qwl)/Cw
            d[il:iz]=(mw*(np.r_[hl[1:],hi]-hl)+qwl)/Mw
            d[iz:ir]=[eheat,qheat,el,w,qcool,mw*(hl[0]-hi),f[nb,0],
                    sum(qgs),sum(qgw),sum(qwl),mw,mb,
                    0. if charge or process_duty_W is None else max(0.,process_duty_W-qd),
                    0. if charge or process_duty_W is None else max(0.,qd-process_duty_W)]
            if recuperator is not None:
                capture,release,loss=recuperator.rates(tg[-1],y[ir],charge)
                d[2*n-1]+=release-capture
                d[ir:ir+4]=[(capture-release-loss)/recuperator.capacity_J_K,capture,release,loss]
            if main_heat_loss is not None:
                amb=main_heat_loss.ambient_K
                qr=main_heat_loss.rock_UA_W_K/nb*(ts-amb)
                qw=main_heat_loss.wall_UA_W_K/nh*(tw-amb)
                qg=main_heat_loss.return_UA_W_K*(tg[-1]-amb)
                d[is_:iw]-=qr/Cs
                d[iw:il]-=qw/Cw
                d[2*n-1]-=qg
                d[iq:iq+3]=[sum(qr),sum(qw),qg]
            if exergy_audit:
                sg=finite_nonnegative_transport
                smix=float(S_liquid(hd))
                shx=float(S_liquid(float(hl[0])))
                entropy_product=(mw+mb)*(smix-si)
                entropy_hx=mw*(shx-si)
                inter_r=float(np.sum(qgs*(1/ts-1/tg[:nb])))
                inter_w=float(np.sum(qgw*(1/tw-1/tg[nb:-1])))
                inter_l=float(np.sum(qwl*(1/tl-1/tw)))
                cooler_ent=sg(qcool,tg[-1],c.cooler_sink_K)
                heater_d=eheat-qheat*(1-exergy_environment_K/tg[-1])
                mixing=entropy_product-entropy_hx
                leak_ent=0.
                if main_heat_loss is not None:
                    leak_ent=(float(np.sum(qr*(1/amb-1/ts)))+
                        float(np.sum(qw*(1/amb-1/tw)))+
                        qg*(1/amb-1/tg[-1]))
                buffer_ent=0.
                if recuperator is not None:
                    Tbuf=float(y[ir])
                    buffer_ent=(sg(capture,tg[-1],Tbuf)+
                        sg(release,Tbuf,tg[-1])+
                        sg(loss,Tbuf,recuperator.ambient_K))
                d[iex:iex+len(LEDGER_KEYS)]=[entropy_product,entropy_hx,inter_r,
                    inter_w,inter_l,cooler_ent,heater_d,mixing,leak_ent,buffer_ent]
            return d
        return fun
    def stage(y_start,seconds,charge):
        atol=np.r_[np.full(n,1e-10),np.full(n,.001),
            np.full(nb+nh,1e-6),np.full(nh,.001),np.full(14,.001)]
        if recuperator is not None:atol=np.r_[atol,1e-6,.001,.001,.001]
        if main_heat_loss is not None:atol=np.r_[atol,.001,.001,.001]
        if exergy_audit:atol=np.r_[atol,np.full(len(LEDGER_KEYS),1e-4)]
        sol=solve_ivp(rhs(charge),(0,seconds),y_start,method="BDF",
            rtol=3e-7,atol=atol,
            max_step=c.max_step_s,first_step=min(1e-6,seconds),dense_output=True)
        if not sol.success:raise RuntimeError(sol.message)
        y=sol.y[:,-1];ds=y-y_start
        st,f,w,el,head,order=flows(y,charge)
        maxMach=0.;maxHeadRatio=0.;peak_pressure=0.;min_pressure=float('inf')
        peak_cooler=0.;peak_blower_electric=0.;peak_heater_electric=0.;peak_blower_flow=0.
        peak_gas_K=0.
        for j in range(sol.t.size):
            states,faces,_,power,h,_=flows(sol.y[:,j],charge)
            ret=states[-1]['T']
            peak_gas_K=max(peak_gas_K,max(x['T'] for x in states))
            peak_cooler=max(peak_cooler,cooler_rate(ret,charge))
            peak_heater_electric=max(peak_heater_electric,heater_rate(ret,charge))
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
        Eheat,Qheat,Ebl,Wbl,Qcool,Qwater,Minterface,Qgs,Qgw,Qwl,Mwater,Mbypass,deficit,excess=map(float,ds[iz:ir])
        capture=release=loss=buffer_change=0.
        if recuperator is not None:
            capture,release,loss=map(float,ds[ir+1:ir+4])
            buffer_change=recuperator.capacity_J_K*float(ds[ir])
        rock_loss=wall_loss=return_loss=0.
        if main_heat_loss is not None:rock_loss,wall_loss,return_loss=map(float,ds[iq:iq+3])
        main_loss=rock_loss+wall_loss+return_loss
        residuals={'gas':Ug-Qheat-Wbl+Qcool+Qgs+Qgw+capture-release+return_loss,
                   'solid':Us-Qgs+rock_loss,'wall':Uw-Qgw+Qwl+wall_loss,'water':Hl-Qwl+Qwater}
        if recuperator is not None:residuals['buffer']=buffer_change-capture+release+loss
        thermal_res=Ug+Us+Uw+Hl+buffer_change-Qheat-Wbl+Qcool+Qwater+loss+main_loss
        electrical_res=Ug+Us+Uw+Hl+buffer_change-Eheat-Ebl+Qcool+Qwater+loss+main_loss+(Eheat-Qheat)+(Ebl-Wbl)
        if abs(masses)>1e-8 or max(abs(thermal_res),abs(electrical_res),*(abs(v) for v in residuals.values()))>1e-6*max(1.,abs(Qheat),abs(Qcool),abs(Qwater),abs(Wbl),abs(capture),abs(release),abs(loss),abs(main_loss)):
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
        stage_exergy=None
        if exergy_audit:
            def system_entropy(q):
                st=[decode(i,q) for i in range(n)]
                gasS=sum(float(q[i])*st[i]["s"] for i in range(n))
                rockS=Cs*float(np.sum(np.log(q[is_:iw]/exergy_environment_K)))
                wallS=Cw*float(np.sum(np.log(q[iw:il]/exergy_environment_K)))
                liquidS=Mw*float(np.sum(S_liquid(q[il:iz])))
                bufferS=0. if recuperator is None else recuperator.capacity_J_K*math.log(float(q[ir])/exergy_environment_K)
                return gasS+rockS+wallS+liquidS+bufferS
            deltaS=system_entropy(y)-system_entropy(y_start)
            entropy_ledgers=dict(zip(LEDGER_KEYS,map(float,ds[iex:iex+len(LEDGER_KEYS)])))
            ent_sum=lambda key:entropy_ledgers[key]*exergy_environment_K
            components={
                "electric_heater_conversion":entropy_ledgers["heater_exergy_destroyed_J"],
                "gas_to_rock":ent_sum("rock_gas_entropy_generated_J_K"),
                "gas_to_HX_wall":ent_sum("wall_gas_entropy_generated_J_K"),
                "wall_to_liquid":ent_sum("water_wall_entropy_generated_J_K"),
                "gas_to_sink_cooler":ent_sum("cooler_entropy_generated_J_K"),
                "process_bypass_mixing":ent_sum("bypass_mixing_entropy_generated_J_K"),
                "main_ambient_heat_transfer":ent_sum("main_heat_leak_entropy_generated_J_K"),
                "regenerator_internal_and_ambient_transfer":ent_sum("buffer_entropy_generated_J_K"),
                "blower_motor_ambient_loss":Ebl-Wbl,
            }
            ambient=[]
            if main_heat_loss is not None:ambient.append((main_loss,main_heat_loss.ambient_K))
            if recuperator is not None:ambient.append((loss,recuperator.ambient_K))
            stage_exergy=close_exergy_ledger(
                T0_K=exergy_environment_K,
                inventory_energy_change_J=Ug+Us+Uw+Hl+buffer_change,
                inventory_entropy_change_J_K=deltaS,
                heater_electric_J=Eheat,heater_to_gas_J=Qheat,
                blower_electric_J=Ebl,blower_to_gas_J=Wbl,
                process_heat_J=Qwater,
                product_entropy_change_J_K=entropy_ledgers["product_entropy_out_J_K"],
                cooler_heat_J=Qcool,cooler_sink_K=c.cooler_sink_K,
                ambient_energy_by_temperature=ambient,
                identified_components_J=components)
            stage_exergy["integrated_diagnostic_entropy_ledgers"]=entropy_ledgers
            stage_exergy["water_HX_branch_entropy_export_J_K"]=entropy_ledgers["hx_branch_entropy_out_J_K"]
            stage_exergy["entropy_generation_nonnegative"]=stage_exergy["total_entropy_generation_J_K"]>=-1e-4
            stage_exergy["unallocated_exergy_negative"]=stage_exergy["unresolved_gas_hydraulics_and_numerical_exergy_J"]<-max(10.,1e-5*stage_exergy["electric_input_exergy_J"])
        trace=None
        if trace_interval_s is not None:
            times=np.r_[np.arange(0.,seconds,trace_interval_s),seconds]
            trace=[]
            for t in times:
                z=sol.sol(t)
                states,faces,_,power,_,_=flows(z,charge)
                _,_,hdel,qdel=delivery(float(z[il]),charge)
                trace.append(dict(time_s=float(t),heater_W=heater_rate(states[-1]["T"],charge),
                    heater_to_gas_W=c.heater_efficiency*heater_rate(states[-1]["T"],charge),
                    return_gas_K=float(states[-1]["T"]),
                    cooler_W=cooler_rate(states[-1]["T"],charge),blower_W=power,
                    gas_flow_kg_s=float(faces[0,0]),delivered_W=qdel,
                    delivered_C=float(_interp_checked(hdel,H,grid))-273.15))
        return y,dict(duration_s=seconds,phase_trace=trace,exergy_audit=stage_exergy,
            main_rock_ambient_heat_J=rock_loss,main_wall_ambient_heat_J=wall_loss,
            main_return_ambient_heat_J=return_loss,main_ambient_heat_J=main_loss,
            recuperator_captured_J=capture,recuperator_returned_J=release,recuperator_ambient_loss_J=loss,
            recuperator_inventory_change_J=buffer_change,
            recuperator_end_K=None if recuperator is None else float(y[ir]),
            peak_gas_temperature_at_accepted_nodes_K=peak_gas_K,
            peak_rock_temperature_at_accepted_nodes_K=float(np.max(sol.y[is_:iw,:])),
            peak_wall_temperature_at_accepted_nodes_K=float(np.max(sol.y[iw:il,:])),
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
            recuperator_cycle_end_change_K=0. if recuperator is None else abs(float(current[ir]-start[ir])),
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
            'wall_energy_change_J','liquid_enthalpy_inventory_change_J','recuperator_inventory_change_J')),
        "remaining_solid_inventory_above_initial_J":ch['solid_energy_change_J']+dis['solid_energy_change_J'],
        "all_discharge_accepted_water_nodes_ge_150C":dis['min_water_outlet_C']>=150.,
        "water_temperature_150C_not_a_continuous_guarantee":True,
        "return_cooler_has_assumed_infinite_sink":True,
        "gas_flow_direction_same_during_charge_and_discharge":not reverse_discharge,
        "valve_loss_K_per_active_bed_port":valve_loss_K,
        "water_control_gain_kg_s_K":water_control_gain_kg_s_K,
        "process_duty_W":process_duty_W,"process_bypass":process_bypass,
        "cooler_cap_W":cooler_cap_W,"trace_interval_s":trace_interval_s,
        "cooler_control_K":cooler_control_K,"recuperator_assumptions":None if recuperator is None else asdict(recuperator),
        "main_heat_loss_assumptions":None if main_heat_loss is None else asdict(main_heat_loss),
        "exergy_probe_enabled":exergy_audit,"exergy_environment_K":exergy_environment_K,
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
