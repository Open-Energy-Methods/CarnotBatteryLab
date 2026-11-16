"""Plot 2024 source-measured TC and model's deliberately permissive extrema.

These are NOT calibrated uncertainty bands or experimentally validated
temperature predictions. Model bounds span both gas/rock phases and all
axial offsets still possible under 2022 instrument spacing. Incompatible
readings warrant investigation, but sensor lag/radial position are unknown.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate(input_path:Path,output_dir:Path)->list[Path]:
    data=json.loads(input_path.read_text())
    if data.get("status")!="CASE_B_UNQUALIFIED_MIXED_PHASE_TC_ENVELOPES_NO_VALIDATION":
        raise ValueError("cannot plot externally validated thermocouples from an unqualified source")
    if data.get("model_validation_pass") is not False:
        raise ValueError("physical validation gate must remain blocked")
    output_dir.mkdir(parents=True,exist_ok=True)
    paths=[]
    for name in ("T1","T4","T7"):
        samples=data["sensor_time_series"][name]
        t=[v["time_s"]/60 for v in samples]
        obs=[v["source_measured_TC_C"] for v in samples]
        low=[v["model_lower_extrema_C"] for v in samples]
        high=[v["model_upper_extrema_C"] for v in samples]
        fig,ax=plt.subplots(figsize=(8.6,4.8))
        ax.plot(t,obs,label=f"Measured {name}: mixed-contact Type-K probe",
                linewidth=1.9)
        ax.fill_between(t,low,high,alpha=.25,
            label="Model phase/possible-position EXTREMA (not measurement uncertainty)")
        ax.set(xlabel="Experiment elapsed time (minutes)",
               ylabel="Temperature (°C)",
               title=f"Case B {name}: observed probe vs unconstrained phase/position extrema\n"
                     "Unqualified observation operator; no sensor lag correction")
        ax.legend(fontsize=8)
        ax.grid(alpha=.25)
        fig.text(.5,.004,
                 "Source: 10.17632/j37x6ptpk2.1 (CC BY 4.0); "
                 "2022 TC sheath contacts rock + air; no sensor calibration/validation.",
                 ha="center",fontsize=7)
        fig.tight_layout(rect=(0,.04,1,1))
        path=output_dir/f"UNVALIDATED_case_B_{name}_mixed_phase_extrema.png"
        fig.savefig(path,dpi=160)
        plt.close(fig)
        paths.append(path)
    return paths


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_TC_phase_position_diagnostic.json"))
    p.add_argument("--output-dir",type=Path,default=Path(
        "results/external_horizontal_bed/tc_envelope_figures"))
    args=p.parse_args()
    paths=generate(args.input,args.output_dir)
    print(f"UNQUALIFIED_SENSOR_EXTREMA_FIGURES={len(paths)}")
    print("EXPERIMENTAL_PREDICTIVE_VALIDATION_PASS=False")


if __name__=="__main__":
    main()
