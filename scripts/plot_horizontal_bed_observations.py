"""Render SOURCE-MEASURED packed-bed curves without a forward-model overlay.

Measured inputs: original source-hashed public CSV runs A-D, DOI
10.17632/j37x6ptpk2.1 (CC BY 4.0). Axial sensor positions and pressure
units are NOT yet independently verified. Figure captions make that clear.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_horizontal_bed_observations import load_case, EXPECTED, DOI


def plot_source_measurements(input_dir:Path,outdir:Path) -> tuple[Path,...]:
    outdir.mkdir(parents=True,exist_ok=True)
    output=[]
    for case_id in EXPECTED:
        data=load_case(input_dir,case_id)
        rows=data["rows"]
        t=[r["Time exp."]/3600 for r in rows]
        fig,ax=plt.subplots(figsize=(8.4,4.8))
        signals=[
            (r"$T_{in}$","Heater/outlet inlet measurement","-"),
            (r"$T_{out}$","Exhaust outlet measurement","-"),
            (r"$T_1$","In-bed sensor T1 (position unverified)","--"),
            (r"$T_4$","In-bed sensor T4 (position unverified)","--"),
            (r"$T_7$","In-bed sensor T7 (position unverified)","--"),
        ]
        for field,label,linestyle in signals:
            ax.plot(t,[r[field] for r in rows],linestyle=linestyle,label=label,linewidth=1.5)
        ax.set_xlabel("Experiment elapsed time (hours)")
        ax.set_ylabel("Measured temperature (°C)")
        ax.set_title(f"Original horizontal packed-bed experiment — run {case_id}\n"
                     "Measurements only; no simulation or geometry fit")
        ax.grid(alpha=.22)
        ax.legend(fontsize=8)
        fig.text(.5,.005,f"Measured data: {DOI} (CC BY 4.0). "
                 "Exact sensor axial coordinates require source verification.",
                 ha="center",fontsize=7)
        fig.tight_layout(rect=(0,.04,1,1))
        target=outdir/f"measured_horizontal_bed_case_{case_id}_temperatures.png"
        fig.savefig(target,dpi=165)
        output.append(target)
        plt.close(fig)
        # Differential-pressure channel's physical units and tap location
        # are NOT stated in the source README. Use only native channels.
        fig,ax=plt.subplots(figsize=(7,4.4))
        ax.scatter([r["Velocity"] for r in rows],
                   [r[r"$\Delta P$"] for r in rows],s=9,alpha=.42)
        ax.set_xlabel("Measured exhaust-pipe velocity (m/s)")
        ax.set_ylabel("Recorded differential-pressure channel (native units unverified)")
        ax.set_title(f"Experimental run {case_id}: recorded hydraulic observations\n"
                     "Pressure units/taps unverified; NOT Ergun validation")
        ax.grid(alpha=.2)
        fig.text(.5,.005,f"Measured data: {DOI} (CC BY 4.0). "
                 "No Pa conversion or pressure-drop model overlay.",
                 ha="center",fontsize=7)
        fig.tight_layout(rect=(0,.04,1,1))
        target=outdir/f"measured_horizontal_bed_case_{case_id}_pressure_native.png"
        fig.savefig(target,dpi=165)
        output.append(target)
        plt.close(fig)
    return tuple(output)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input-dir",type=Path,default=Path("results/external_horizontal_bed"))
    parser.add_argument("--output-dir",type=Path,default=Path("results/external_horizontal_bed/figures"))
    args=parser.parse_args()
    outputs=plot_source_measurements(args.input_dir,args.output_dir)
    print(f"MEASURED_ONLY_PLOTS_CREATED={len(outputs)}")
    for path in outputs:
        print(f"MEASURED_PLOT={path}")
    print("MODEL_VALIDATION_STATUS=NOT_RUN")


if __name__=="__main__":
    main()
