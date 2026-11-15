"""Pressurised-liquid auxiliary circuits for an illustrative R718 heat-pump screen.

Darcy-Weisbach + laminar/Haaland turbulent friction, with explicit fluid
properties and line dimensions. NOT a detailed vendor hydraulic design.
No refrigerant-side pressure loss is hidden in these results.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from .r718 import R718Result, _prop


@dataclass(frozen=True)
class PipeCircuit:
    name: str
    pressure_Pa: float
    bulk_temperature_C: float
    length_m: float
    diameter_m: float
    roughness_m: float
    minor_loss_coefficient: float
    pump_efficiency: float

    def __post_init__(self) -> None:
        entries=(self.pressure_Pa,self.bulk_temperature_C,self.length_m,self.diameter_m,
                 self.roughness_m,self.minor_loss_coefficient,self.pump_efficiency)
        if not all(math.isfinite(x) for x in entries):
            raise ValueError("all pipe parameters must be finite")
        if (self.pressure_Pa<=0 or self.bulk_temperature_C<=-273.15
                or self.length_m<=0 or self.diameter_m<=0 or
                self.roughness_m<0 or self.minor_loss_coefficient<0
                or self.roughness_m >= self.diameter_m
                or not 0<self.pump_efficiency<=1):
            raise ValueError("invalid circuit geometry/efficiency")


@dataclass(frozen=True)
class PipeResult:
    name: str
    mass_flow_kg_s: float
    density_kg_m3: float
    viscosity_Pa_s: float
    reynolds: float
    friction_factor: float
    velocity_m_s: float
    pressure_drop_Pa: float
    pump_electric_W: float


def solve_pipe(circuit: PipeCircuit, mass_flow_kg_s: float,
               *, backend: str="HEOS::Water") -> PipeResult:
    if not math.isfinite(mass_flow_kg_s) or mass_flow_kg_s<0:
        raise ValueError("mass flow must be finite nonnegative")
    rho = _prop("D","P",circuit.pressure_Pa,"T",
                circuit.bulk_temperature_C+273.15,backend)
    mu = _prop("V","P",circuit.pressure_Pa,"T",
               circuit.bulk_temperature_C+273.15,backend)
    # Water liquid should be below saturation at stated pressure.
    tsat = _prop("T","P",circuit.pressure_Pa,"Q",0,backend)
    if circuit.bulk_temperature_C+273.15>=tsat:
        raise ValueError(f"{circuit.name}: not safely subcooled liquid")
    area=math.pi*circuit.diameter_m**2/4
    velocity=mass_flow_kg_s/(rho*area)
    re=rho*velocity*circuit.diameter_m/mu
    if re==0:
        f=0.0
    elif re<2300:
        f=64/re
    elif re>=4000:
        f=(-1.8*math.log10((circuit.roughness_m/circuit.diameter_m/3.7)**1.11
                           +6.9/re))**-2
    else:
        f_l=64/2300
        f_t=(-1.8*math.log10((circuit.roughness_m/circuit.diameter_m/3.7)**1.11
                           +6.9/4000))**-2
        f=f_l+(f_t-f_l)*(re-2300)/1700
    delta_p=(f*circuit.length_m/circuit.diameter_m
              +circuit.minor_loss_coefficient)*0.5*rho*velocity**2
    pump=delta_p*(mass_flow_kg_s/rho)/circuit.pump_efficiency
    return PipeResult(circuit.name,mass_flow_kg_s,rho,mu,re,f,velocity,delta_p,pump)


# All geometries are *hypothetical transparent screening inputs*. Process
# water at 130 C is carried at 1 MPa, not incorrectly treated as atmospheric.
ILLUSTRATIVE_CIRCUITS = (
    PipeCircuit("source_water",300_000.0,75.0,60.0,0.10,5e-5,12.0,0.72),
    PipeCircuit("process_pressurised_water",1_000_000.0,130.0,
                70.0,0.065,5e-5,14.0,0.72),
    PipeCircuit("intercooler_water",300_000.0,67.5,35.0,0.045,5e-5,9.0,0.72),
)


def add_liquid_auxiliaries(result: R718Result,
                           circuits: tuple[PipeCircuit,...]=ILLUSTRATIVE_CIRCUITS
                           ) -> dict[str, object]:
    if len(circuits)!=3:
        raise ValueError("source, process, interstage circuits required")
    flow=(result.source_mass_flow_kg_s,result.process_mass_flow_kg_s,
          result.intercooler_sink_flow_kg_s)
    pipes=[solve_pipe(c,m,backend=result.inputs.backend) for c,m in zip(circuits,flow)]
    extra=sum(p.pump_electric_W for p in pipes)
    # Refrigerant compressor electric includes motor, NOT inverter/gear.
    # Additional inverter and gear are explicitly assumed for comparison.
    eta_inverter=0.98
    eta_gear=0.95
    shaft=result.W_compressor_shaft_W
    compressor_grid=shaft/(result.inputs.motor_efficiency*eta_inverter*eta_gear)
    grid=compressor_grid+extra
    return {
        "circuits": pipes,
        "liquid_pump_electric_W": extra,
        "compressor_grid_electric_W": compressor_grid,
        "total_grid_electric_W": grid,
        "COP_grid_with_liquid_auxiliaries": result.Q_process_W/grid,
        "inverter_efficiency_assumed": eta_inverter,
        "gear_efficiency_assumed": eta_gear,
        "excluded": (
            "refrigerant line/HX pressure drop, condenser wall geometry, fan for TES, "
            "intercooler chiller if cooling fluid inlet cannot be supplied, controls/startup"
        ),
        "boundary": (
            "three pumps are separate external losses; their electrical work "
            "is assumed dissipated outside the refrigerant energy balance"
        ),
    }
