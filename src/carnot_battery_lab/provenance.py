"""Small, machine-readable source provenance record for study inputs.

Creates run manifests without asserting that an input case is a solved model.
The manifest is a record of input provenance and software environment only.
"""
from __future__ import annotations
import hashlib
import json
import platform
import subprocess
from pathlib import Path
from importlib import metadata
from . import __version__
from .cases import load_study_case


def _revision(repo_root: Path) -> str | None:
    result=subprocess.run(['git','-C',str(repo_root),'rev-parse','HEAD'],
                          capture_output=True,text=True,check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def build_input_manifest(case_file: str | Path, repo_root: str | Path) -> dict:
    """Case-validation evidence only; no simulated plant outputs."""
    case_path=Path(case_file)
    root=Path(repo_root)
    case=load_study_case(case_path)
    raw=case_path.read_bytes()
    return {
        'schema_version':'input-manifest-v1',
        'case_id':case.case_id,
        'case_sha256':hashlib.sha256(raw).hexdigest(),
        'case_contract_status':case.configuration_status,
        'scientific_result_status':'input_only_no_simulation',
        'package_version':__version__,
        'git_revision':_revision(root),
        'python_version':platform.python_version(),
        'dependencies':{
            dep:(metadata.version(dep) if _has_package(dep) else None)
            for dep in ('PyYAML','CoolProp','numpy','scipy')
        },
    }


def _has_package(distribution_name: str) -> bool:
    try:
        metadata.version(distribution_name)
        return True
    except metadata.PackageNotFoundError:
        return False


def write_manifest(manifest: dict, path: str | Path) -> None:
    output=Path(path)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
