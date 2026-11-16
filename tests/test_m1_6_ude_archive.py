"""Offline UDE Carnot HP/TES archive provenance and unsafe ZIP controls."""
from hashlib import md5
from io import BytesIO
from zipfile import ZipFile
import pytest

from scripts.audit_ude_carnot_hp_tes_archive import inspect_archive


def package(*names):
    out=BytesIO()
    with ZipFile(out,"w") as z:
        for name in names:
            z.writestr(name,"TEST_ONLY\n")
    return out.getvalue()


def test_real_archive_inventory_contract_without_releasing_data():
    raw=package("README_overview.md",
                "data/Experiment_01/compressor_data.csv",
                "data/Experiment_01/pressures.csv",
                "models/compressor_model.py")
    report=inspect_archive(raw,expected_md5=md5(raw).hexdigest())
    assert report["zip_entries_total"]==4
    assert report["by_extension"][".csv"]==2
    assert report["by_extension"][".py"]==1
    assert "README_overview.md" in report[
        "relevant_metadata_or_model_file_paths"]
    assert report["complete_H_REF_80_70_110_150_map_qualified"] is False
    assert report["raw_archive_data_redistributed"] is False
    assert report["csv_column_headers_metadata_only"][
        "data/Experiment_01/compressor_data.csv"]["field_names"]==[
            "TEST_ONLY"]
    assert "data/README_overview.md" in report[
        "readme_section_headings_metadata_only"]


def test_archive_wrong_checksum_refused():
    with pytest.raises(ValueError,match="checksum"):
        inspect_archive(package("README_overview.md"),
                        expected_md5="0"*32)


@pytest.mark.parametrize("name",[
    "../secret.csv","data/../../secret.csv","/etc/passwd",
])
def test_malicious_archive_paths_rejected(name):
    raw=package(name)
    with pytest.raises(ValueError,match="unsafe"):
        inspect_archive(raw,expected_md5=md5(raw).hexdigest())
