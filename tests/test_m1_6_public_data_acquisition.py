"""No-network controls for M1.6 source classification and target audit."""
from hashlib import md5
import pytest

from scripts.audit_public_r600_compressor_measurements import (
    parse_and_audit_bytes,fetch_source,REQUIRED_COLUMNS,
)


def record(origin,fluid,ps,pd,ts,eff=.60,vol=.75):
    return [
        origin,"OST Bock rig",fluid,"50","40","2","48.33",
        "40","","%.2f"%ts,"15","%.4f"%ps,"%.4f"%pd,
        "%.4f"%eff,"%.4f"%vol,
    ]


def fixture():
    import csv,io
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow([
        "source","compressor","refrigerant","bore_mm","stroke_mm",
        "n_cyl","f_elec_Hz","T_ev_C","T_co_C","T_suc_C",
        "DeltaT_sh_K","p_suc_bar","p_dis_bar","eta_is","eta_vol",
    ])
    writer.writerow(record("Experimental OST (Purdue 2024 Natural)",
                           "butane",3.5,10.,85.))
    writer.writerow(record("Experimental OST (Purdue 2024 Natural)",
                           "butane",5.0,50.,83.))
    writer.writerow(record("Experimental OST (Purdue 2024 Natural)",
                           "Butane/propane (x1=0.752)",5.,50.,83.))
    writer.writerow(record("Bitzer EN12900","Propane",5.,50.,85.))
    writer.writerow(record("Experimental Milano (D'Ignazi & Molinaroli 2026)",
                           "CO2",15.,90.,30.))
    return output.getvalue().encode()


def requirements():
    d=lambda ps,pd,t: {
        "compressor_stage_demands":[dict(
            suction_pressure_Pa=ps,discharge_pressure_Pa=pd,
            suction_temperature_C=t,stage_pressure_ratio=pd/ps,
            suction_volumetric_flow_m3_s=.2,
        )]}
    return {"r600_80C_source_110_150C_transcritical_screen":{
        "map_requirements_for_numerically_feasible_points":{
            "5000000":d(500000.,5e6,83.),"6000000":d(700000.,6e6,75.),
        }}}


def test_source_provenance_counts_and_r600_nonmatch():
    raw=fixture()
    result=parse_and_audit_bytes(raw,requirements(),
                                 expected_md5=md5(raw).hexdigest())
    assert result["source_csv_rows"]==5
    assert result["real_measured_nbutane_points"]==2
    assert result["real_nbutane_machine_ids"]==["OST Bock rig"]
    assert result["raw_origin_counts"]["SYNTHETIC_MANUFACTURER_POLYNOMIAL"]==1
    assert result["raw_origin_counts"]["MEASURED_EXPERIMENTAL_OST"]==3
    assert result["real_nbutane_range"]["suction_pressure_bar"]=={
        "min":3.5,"max":5.0}
    assert result["strict_nominal_point_comparison"][0][
        "raw_experimental_points_meeting_5pct_both_pressures_and_5K_suction"]==1
    assert result["strict_nominal_point_comparison"][1][
        "raw_experimental_points_meeting_5pct_both_pressures_and_5K_suction"]==0
    assert result["manufacturer_map_at_H_REF_available"] is False
    assert result["no_raw_data_copied_into_report"] is True
    assert "measured_compressor_shaft_W" in result["unreported_m15_fields"]


def test_checksum_mismatch_fails_closed():
    raw=fixture()
    with pytest.raises(ValueError,match="MD5 mismatch"):
        parse_and_audit_bytes(raw,requirements(),
                              expected_md5="0"*32)


def test_unsupported_external_url_rejected():
    with pytest.raises(ValueError,match="pinned"):
        fetch_source(url="https://not-zenodo.invalid/private")


def test_unknown_source_class_rejected_even_if_other_rows_valid():
    raw=fixture().replace(b"Bitzer EN12900",b"Internet Model")
    with pytest.raises(ValueError,match="unrecognized source"):
        parse_and_audit_bytes(raw,requirements(),
                              expected_md5=md5(raw).hexdigest())


def test_malformed_real_measurements_cannot_become_evidence():
    raw=fixture().replace(b"3.5000,10.0000",
                          b"3.5000,-1.0000")
    result=parse_and_audit_bytes(raw,requirements(),
                                 expected_md5=md5(raw).hexdigest())
    assert result["real_measured_nbutane_points"]==1
    assert result["malformed_real_nbutane_points"]==1
    assert result["manufacturer_map_at_H_REF_available"] is False
