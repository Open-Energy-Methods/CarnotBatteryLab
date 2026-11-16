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
            z.writestr(name,"T_suction_C,p_suction_bar\n85,7\n" if name.endswith(".csv") else "# TEST_ONLY\n")
    return out.getvalue()


def test_real_archive_inventory_contract_without_releasing_data():
    raw=package("data/README_overview.md",
                "data/Experiment_01/compressor_data.csv",
                "data/Experiment_01/pressures.csv",
                "models/compressor_model.py")
    report=inspect_archive(raw,expected_md5=md5(raw).hexdigest())
    assert report["zip_entries_total"]==4
    assert report["by_extension"][".csv"]==2
    assert report["by_extension"][".py"]==1
    assert "data/README_overview.md" in report[
        "relevant_metadata_or_model_file_paths"]
    assert report["complete_H_REF_80_70_110_150_map_qualified"] is False
    assert report["raw_archive_data_redistributed"] is False
    assert report["csv_column_headers_metadata_only"][
        "data/Experiment_01/compressor_data.csv"]["field_names"]==[
            "T_suction_C","p_suction_bar"]
    assert "data/README_overview.md" in report[
        "readme_section_headings_metadata_only"]


def test_source_internal_nonpublic_model_warning_is_detected():
    out=BytesIO()
    with ZipFile(out,"w") as z:
        z.writestr("data/compressor-model (Welp)/README.txt",
                   "### This model may NOT be made public, proprietary origin ###\n")
        z.writestr("data/README_overview.md","# Datasets\n")
    raw=out.getvalue()
    report=inspect_archive(raw,expected_md5=md5(raw).hexdigest())
    assert report["underlying_experimental_model_code_cleared_for_redistribution"] is False
    assert len(report["source_file_reuse_warnings"])==1
    assert report["source_file_reuse_warnings"][0]["status"]==(
        "EXPLICIT_NONPUBLIC_OR_NONREDISTRIBUTION_LANGUAGE")
    assert report["raw_archive_data_redistributed"] is False


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
