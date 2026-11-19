"""Hypothetical single-bank regenerative thermal buffer and service audit."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ThermalBuffer:
    capacity_J_K:float
    conductance_W_K:float
    ambient_loss_UA_W_K:float
    ambient_K:float=298.15
    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.capacity_J_K,self.conductance_W_K,self.ambient_loss_UA_W_K,self.ambient_K)) or self.capacity_J_K<=0 or self.conductance_W_K<=0 or self.ambient_loss_UA_W_K<0 or not 280<self.ambient_K<350:
            raise ValueError("invalid hypothetical buffer")
    def rates(self,gas_K,buffer_K,charge):
        if min(gas_K,buffer_K)<self.ambient_K or not all(math.isfinite(x) for x in (gas_K,buffer_K)):
            raise ValueError("buffer or return gas outside passive ambient scope")
        capture=0. if charge else self.conductance_W_K*max(0.,gas_K-buffer_K)
        release=self.conductance_W_K*max(0.,buffer_K-gas_K) if charge else 0.
        loss=self.ambient_loss_UA_W_K*(buffer_K-self.ambient_K)
        return capture,release,loss

def buffer_periodic_gate(records):
    """For two last cycle boundaries, also require buffer/output repeatability."""
    if len(records)<3:return False
    for prev,cur in zip(records[-3:-1],records[-2:]):
        if cur["recuperator_cycle_end_change_K"]>.05:return False
        for phase in ("charge","discharge"):
            for key in ("recuperator_captured_J","recuperator_returned_J","recuperator_ambient_loss_J"):
                a,b=prev[phase][key],cur[phase][key]
                if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>max(10.,.005*max(abs(a),abs(b))):return False
    return True

def water_service_exergy(mass_kg,hin,hout,sin,sout,T0=298.15):
    """Flow exergy rise at equal inlet/outlet pressure, no kinetic terms."""
    if not all(math.isfinite(x) for x in (mass_kg,hin,hout,sin,sout,T0)) or mass_kg<0 or T0<=0:
        raise ValueError("invalid exergy inputs")
    return mass_kg*((hout-hin)-T0*(sout-sin))


@dataclass(frozen=True)
class MainHeatLoss:
    """Independent assumed lumped insulation conductances, not vendor data."""
    rock_UA_W_K:float
    wall_UA_W_K:float
    return_UA_W_K:float
    ambient_K:float=298.15

    def __post_init__(self):
        vals=(self.rock_UA_W_K,self.wall_UA_W_K,self.return_UA_W_K,self.ambient_K)
        if not all(math.isfinite(x) for x in vals) or min(vals[:3])<0 or not 280<self.ambient_K<350:
            raise ValueError("invalid main insulation assumptions")
