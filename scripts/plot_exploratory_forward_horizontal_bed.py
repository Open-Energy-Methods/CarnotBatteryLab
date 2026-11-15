"""Render UNCALIBRATED bed-forward errors against measured held-out source cases.

Observed inputs / outputs from original CC BY 4.0 DOI 10.17632/j37x6ptpk2.1;
source-backed geometry from Wolde et al. 2022, but pipe bore, cp and heat
loss remain assumed. Measured Tout feeds the experimental flow estimate.
These are NOT independent experimental predictive validation graphics.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot(input_file:Path,output_dir:Path)->tuple[Path,...]:
    data=json.loads(input_file.read_text())
    if data["status"]!="EXPLORATORY_NOT_PREDICTIVE_VALIDATION":
        raise ValueError("refuse to plot unqualified or mislabelled evidence class")
    output_dir.mkdir(parents=True,exist_ok=True)
    outputs=[]
    for case_id,run in data["cases"].items():
        time=[v/60 for v in run["time_s"]]
        fig,ax=plt.subplots(figsize=(8.2,4.5))
        ax.plot(time,run["measured_Tout_C"],label="Experiment: measured exhaust temperature",
                linewidth=2.0)
        ax.plot(time,run["model_Tout_C"],label="Uncalibrated 1D model; assumptions unverified",
                linewidth=1.8,linestyle="--")
        ax.axhline(80.0,linewidth=1,linestyle=":",color="grey",
                   label="80°C crossing diagnostic")
        ax.set(xlabel="Experiment time (minutes)",ylabel="Outlet temperature (°C)",
               title=(f"Case {case_id}: observed vs preliminary forward replay\n"
                      f"RMSE {run['rmse_C']:.1f}°C — NOT a validated model"))
        ax.legend(fontsize=8)
        ax.grid(alpha=.2)
        fig.text(.5,.007,
                 "Measured Tout also enters flow estimate; pipe bore assumed. "
                 "Original data DOI 10.17632/j37x6ptpk2.1 (CC BY 4.0)",
                 ha="center",fontsize=7)
        fig.tight_layout(rect=(0,.05,1,1))
        target=output_dir/f"UNVALIDATED_model_vs_measured_case_{case_id}.png"
        fig.savefig(target,dpi=165)
        plt.close(fig)
        outputs.append(target)
    return tuple(outputs)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("results/external_horizontal_bed/preliminary_forward_check.json"))
    p.add_argument("--output-dir",type=Path,default=Path("results/external_horizontal_bed/figures"))
    args=p.parse_args()
    outputs=plot(args.input,args.output_dir)
    print("UNVALIDATED_FORWARD_PLOTS",len(outputs))
    print("VALIDATION_STATUS=NOT_RUN")
    for f in outputs:
        print("UNVALIDATED_FORWARD_PLOT",f)


if __name__=="__main__":
    main()
