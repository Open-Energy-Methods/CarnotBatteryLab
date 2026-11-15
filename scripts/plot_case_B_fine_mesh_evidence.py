"""Reproduce research figures from pinned numerical 512-grid JSON artifacts.

Observed Case B exhaust temperature (CC BY 4.0; DOI 10.17632/j37x6ptpk2.1)
is shown ONLY as the comparison target. The "historical" panel includes
the original measured-Tout-informed mass-flow forcing, explicitly flagged
as NON-BLIND. Independent forcing is shown separately.

No model figure is an experimentally validated pressure/drop or thermocline
result. All charts must label missing instrument bore and pressure data.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate(historical:Path,target_free:Path,outdir:Path)->tuple[Path,...]:
    a=json.loads(historical.read_text(encoding="utf-8"))
    b=json.loads(target_free.read_text(encoding="utf-8"))
    if a.get("source_sha256")!=b.get("source_sha256") or (
        a.get("status")!="SOURCE_LOCKED_NUMERICAL_REFINEMENT_ONLY_NOT_PHYSICAL_VALIDATION"
        or b.get("status")!="CASE_B_TARGET_INDEPENDENT_EXHAUST_FORCING_SPATIAL_SCREEN_UNVALIDATED"
        or b.get("measured_Tout_excluded_from_physics") is not True):
        raise ValueError("source or validation contract mismatch")
    outdir.mkdir(parents=True,exist_ok=True)
    products=[]
    fig,ax=plt.subplots(figsize=(8.6,5.0))
    measured=b["runs"]["512"]["measured_exhaust_C_for_evaluation_only"]
    t=b["runs"]["512"]["time_s"]
    ax.plot([v/60 for v in t],measured,linewidth=2.0,label="Measured Case B outlet (evaluation only)")
    for n in (32,128,512):
        x=b["runs"][str(n)]
        ax.plot([v/60 for v in x["time_s"]],x["model_exhaust_C"],
                label=f"Unfitted model, {n} cells",linestyle="--" if n!=512 else "-")
    ax.set(xlabel="Elapsed time (min)",ylabel="Outlet temperature (°C)",
           title="Source-locked Case B: predictive-boundary mesh comparison\n"
                 "Measured outlet excluded from gas-flow forcing; NOT physically validated")
    ax.axhline(80,color="grey",alpha=.7,linestyle=":",label="80°C breakthrough definition")
    ax.grid(alpha=.2)
    ax.legend(fontsize=8)
    fig.text(.5,.008,"Data: DOI 10.17632/j37x6ptpk2.1 (CC BY 4.0). "
             "Exhaust bore 52mm assumed; pressure calibration unresolved.",
             fontsize=7,ha="center")
    fig.tight_layout(rect=(0,.04,1,1))
    fname=outdir/"case_B_no_target_leak_mesh_vs_measured_UNVALIDATED.png"
    fig.savefig(fname,dpi=170)
    products.append(fname)
    plt.close(fig)

    fig,ax=plt.subplots(figsize=(8.4,4.9))
    ns=[64,128,256,512]
    for label,run,group in (
        ("Historical measured-Tout-informed flow",a,"refinement_evidence"),
        ("Target-independent implicit flow",b,"refinement"),
    ):
        info=run[group]
        pairs=info["pairs"] if group=="refinement_evidence" else info["pairwise"]
        if group=="refinement_evidence":
            xs=[128,256,512]
            ys=[pairs[f"{x//2}_to_{x}"]["outlet_temperature_RMS_K"] for x in xs]
        else:
            xs=[64,128,256,512]
            ys=[pairs[f"{x//2}_to_{x}"]["RMS_outlet_profile_difference_K"] for x in xs]
        ax.plot(xs,ys,"-o",label=label)
    ax.axhline(1.0,linestyle=":",color="grey",label="Provisional 1 K pairwise target")
    ax.set_xscale("log",base=2)
    ax.set_yscale("log")
    ax.set(xlabel="Fine-grid cell count N (coarse grid N/2)",
           ylabel="Pairwise whole-outlet-profile RMS change (K)",
           title="Spatial refinement on original Case B inputs (64–512 cells)")
    ax.grid(alpha=.2,which="both")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fname=outdir/"case_B_numerical_grid_refinement_comparison.png"
    fig.savefig(fname,dpi=170)
    products.append(fname)
    plt.close(fig)

    fig,ax=plt.subplots(figsize=(8.4,4.8))
    ns=[32,64,128,256,512]
    observed=b["runs"]["512"]["observed_first_80C_s"]
    ax.axhline(observed/60,color="black",linestyle=":",
               label="Measured Case B crossing (not a model fit)")
    ax.plot(ns,[b["runs"][str(n)]["model_first_80C_s"]/60 for n in ns],
            "-o",label="Target-independent model crossing")
    ax.plot([64,128,256,512],
            [a["runs"][str(n)]["first_model_80C_crossing_s"]/60
             for n in (64,128,256,512)],
            "-s",label="Historical target-informed-flow crossing")
    ax.set_xscale("log",base=2)
    ax.set(xlabel="Number of finite-volume cells",
           ylabel="First upward 80°C outlet crossing (min)",
           title="Grid-converged breakthrough remains physically inaccurate")
    ax.grid(alpha=.23)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fname=outdir/"case_B_breakthrough_convergence_vs_measured_UNVALIDATED.png"
    fig.savefig(fname,dpi=170)
    products.append(fname)
    plt.close(fig)
    return tuple(products)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--historic",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_fine_mesh_512.json"))
    p.add_argument("--target-independent",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_no_target_leak_512_mesh.json"))
    p.add_argument("--output-dir",type=Path,default=Path(
        "results/external_horizontal_bed/fine_mesh_figures"))
    args=p.parse_args()
    outputs=generate(args.historic,args.target_independent,args.output_dir)
    for o in outputs:
        print("SCIENCE_VERIFICATION_FIGURE",o)
    print("EXTERNAL_EXPERIMENTAL_VALIDATION_NOT_ESTABLISHED")


if __name__=="__main__":
    main()
