"""Regenerate M2 screening figures from archived JSON, not hardcoded curves.

Requires pip install matplotlib (the research optional dependency). Figures
are explicitly labelled charge-only and hardware-unvalidated.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("results/m2_charge_only_screen.json"))
    p.add_argument("--output-dir",type=Path,default=Path("results/figures"))
    args=p.parse_args()
    payload=json.loads(args.input.read_text())
    if payload.get("scientific_status")!="coupled_charge_screen_unvalidated_compressor":
        raise ValueError("unsupported/unverified result class")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    cases=payload["cases"]
    bed=payload["bed"]
    n=bed["cells"]
    length=bed["geometry"]["length_m"]
    z=[(i+0.5)*length/n for i in range(n)]
    ref=cases["95.0"]["steps"]
    fig,ax=plt.subplots(figsize=(8,4.8))
    for idx in sorted({0,len(ref)//2,len(ref)-1}):
        s=ref[idx]
        ax.plot(z,[t-273.15 for t in s["bed_solid_axial_K"]],
                label=f"rock t={s['elapsed_s']/60:.0f} min")
        ax.plot(z,[t-273.15 for t in s["bed_fluid_axial_K"]],
                linestyle="--",label=f"gas t={s['elapsed_s']/60:.0f} min")
    ax.set(xlabel="Bed axial distance (m)",ylabel="Temperature (°C)",
           title="Gas/rock charging temperature evolution | model-based screening")
    ax.grid(alpha=.25)
    ax.legend(fontsize=8,ncol=2)
    fig.tight_layout()
    fig.savefig(args.output_dir/"gas_rock_axial_temperatures.png",dpi=160)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.6))
    for initial,run in sorted(cases.items(),key=lambda x:float(x[0])):
        steps=run["steps"]
        ax.plot([s["elapsed_s"]/60 for s in steps],
                [s["total_grid_electric_W"]/1000 for s in steps],
                marker="o",label=f"initial bed {initial} °C")
    ax.set(xlabel="Elapsed charging time (minutes)",
           ylabel="Partial-boundary grid demand (kW)",
           title="R718 charging electricity vs storage initial temperature | unvalidated")
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output_dir/"grid_electricity_temperature_feedback.png",dpi=160)
    plt.close(fig)
    stress=payload["compact_bed_breakthrough_stress"]
    if stress["steps"]:
        fig,ax=plt.subplots(figsize=(8,4.6))
        x=[s["elapsed_s"]/60 for s in stress["steps"]]
        y=[s["total_grid_electric_W"]/1000 for s in stress["steps"]]
        ax.plot(x,y,"-o",label="accepted charge states")
        if not stress["completed"]:
            ax.axvline(x[-1]+payload["control"]["dt_s"]/60,
                       linestyle=":",label="next step rejected")
        ax.set(xlabel="Elapsed time (minutes)",ylabel="Grid demand (kW)",
               title="Compact-bed breakthrough and operating-limit rejection | screen")
        ax.grid(alpha=.25)
        ax.legend()
        fig.tight_layout()
        fig.savefig(args.output_dir/"compact_bed_operating_envelope_stress.png",dpi=160)
        plt.close(fig)
    print(f"Created figures in {args.output_dir}; source={args.input}")


if __name__=="__main__":
    main()
