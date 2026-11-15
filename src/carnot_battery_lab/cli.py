"""Non-simulating CLI for contract validation and audit provenance."""
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import asdict
import yaml
from .cases import CaseValidationError, load_study_case


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CarnotBatteryLab (pre-alpha): validate research case contracts")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate-case", help="Validate illustrative case YAML; does not solve a plant")
    check.add_argument("file")
    args = parser.parse_args(argv)
    if args.command == "validate-case":
        try:
            case = load_study_case(args.file)
        except (OSError, CaseValidationError, ValueError, TypeError, yaml.YAMLError) as exc:
            print(f"INVALID: {exc}", file=sys.stderr)
            return 2
        output=asdict(case)
        output["nominal_useful_storage_MWh_th"]=case.nominal_useful_storage_MWh_th
        output["warning"]="Input contract only: no demonstrated fluid, equipment, storage or cycle feasibility."
        print(json.dumps(output, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
