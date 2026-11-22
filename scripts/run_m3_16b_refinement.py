"""Independent zero-cooling mesh/time confirmation and assumed insulation sensitivity."""
import argparse,json
from pathlib import Path
from run_m3_16_thermal_retention import run
from carnot_battery_lab.physics.thermal_retention import MainHeatLoss
from carnot_battery_lab.physics.retention_refinement import compare,preferred_capacity

# Cooling is zero in every case; no buffer. Retain identical process service.
CASES={
    "h5_n16":(16,5.,0.,None,5.,False),
    "h5_n12":(12,5.,0.,None,5.,False),
    "h5_halfstep":(16,2.5,0.,None,5.,False),
    "h3_n16":(16,5.,0.,None,3.,False),
    "h3_n12":(12,5.,0.,None,3.,False),
    "h3_n8":(8,5.,0.,None,3.,False),
    "h3_halfstep":(16,2.5,0.,None,3.,False),
    "h3_quarterstep":(16,1.25,0.,None,3.,False),
    "h2_n16":(16,5.,0.,None,2.,False),
    "h3_loss100":(16,5.,0.,None,3.,False),
    "h3_loss500":(16,5.,0.,None,3.,False),
    "h3_loss1000":(16,5.,0.,None,3.,False),
}
LOSSES={f"h3_loss{u}":MainHeatLoss(.6*u,.2*u,.2*u) for u in (100,500,1000)}

def aggregate(root):
    from dataclasses import asdict
    cases={}
    for p in root.rglob("case_*.json"):
        v=json.loads(p.read_text());s=v["summary"];k=s["case"]
        if k in cases or k not in CASES:raise ValueError("duplicate or unknown case")
        if (s["cells"],s["max_step_s"],s["cooler_cap_W"],s["cooler_control_K"],s["heater_per_bank_MW"],s["buffer_enabled"])!=CASES[k]:raise ValueError("case mismatch")
        if s["main_heat_loss_assumptions"]!=(asdict(LOSSES[k]) if k in LOSSES else None):raise ValueError("loss mismatch")
        cases[k]=s
    if set(cases)!=set(CASES):raise ValueError("incomplete campaign")
    # Preserve exact prior reference evidence; avoid silently altering the model.
    for k,ref in (("h5_n16",1058467.0194850015),("h3_n16",1058471.6585475714)):
        assert cases[k]["full"] and abs(cases[k]["mean_electric_W"]-ref)/ref<.005
    groups={}
    for h,keys in ((5,("h5_n12","h5_halfstep")),(3,("h3_n12","h3_halfstep","h3_quarterstep"))):
        ref=cases[f"h{h}_n16"]
        comparisons={k:compare(cases[k],ref) for k in keys}
        groups[str(h)]=dict(comparisons=comparisons,confirmed=all(x["pass_screen"] for x in comparisons.values()))
    preferred=preferred_capacity(cases["h3_n16"],cases["h5_n16"],confirmed_low=groups["3"]["confirmed"],confirmed_high=groups["5"]["confirmed"])
    loss_study={}
    for k in LOSSES:
        a,b=cases[k],cases["h3_n16"]
        loss_study[k]=dict(both_eligible=a["eligible"] and b["eligible"],heat_leak_J=a["main_heat_loss_J"],
            electric_difference_W=a["mean_electric_W"]-b["mean_electric_W"],heat_per_electric=1e6/a["mean_electric_W"] if a["full"] else None)
    x=dict(cases=cases,refinement=groups,preferred_confirmed_adiabatic_case=preferred,
        coarse_n8_diagnostic_only=True,h2_exploratory_not_confirmed=True,loss_sensitivity=loss_study,
        loss_cases_independently_refined=False,insulation_measured=False,component_exergy_balance_complete=False,
        hardware_qualified=False,industrial_service_qualified=False,Carnot_battery_RTE=None)
    print(json.dumps(x),flush=True)
    return x

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--case",choices=CASES);p.add_argument("--aggregate",type=Path)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    if bool(a.case)==bool(a.aggregate):p.error("select exactly one mode")
    x=run(a.case,cases=CASES,main_heat_loss=LOSSES.get(a.case)) if a.case else aggregate(a.aggregate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
