"""Generate auditable input metadata; does not run the physical simulator."""
from __future__ import annotations
import argparse
from pathlib import Path
from carnot_battery_lab.provenance import build_input_manifest, write_manifest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('case_file',type=Path)
    parser.add_argument('--out',type=Path,default=Path('results/input_manifest.json'))
    args=parser.parse_args()
    manifest=build_input_manifest(args.case_file,Path(__file__).resolve().parents[1])
    write_manifest(manifest,args.out)
    print(f"Input provenance only (no simulation): {args.out}")


if __name__ == '__main__':
    main()
