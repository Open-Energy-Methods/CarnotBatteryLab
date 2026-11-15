import hashlib
import json
from pathlib import Path
from carnot_battery_lab.provenance import build_input_manifest,write_manifest


def test_manifest_references_exact_input_bytes(tmp_path):
    root=Path(__file__).parents[1]
    path=root/'cases/reference_industrial_heat_150C.yaml'
    result=build_input_manifest(path,root)
    assert result['case_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert result['scientific_result_status']=='input_only_no_simulation'
    assert result['case_contract_status']=='illustrative'
    out=tmp_path/'m.json'
    write_manifest(result,out)
    assert json.loads(out.read_text())['case_sha256']==result['case_sha256']
