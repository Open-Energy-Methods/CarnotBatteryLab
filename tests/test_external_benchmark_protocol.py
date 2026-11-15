"""Synthetic tests verify validation machinery, NEVER physical accuracy."""
from pathlib import Path
import pytest
from carnot_battery_lab.validation.experimental import (
    TimeSeries, ExperimentalMapping, PressureDatum, BenchmarkBlocked,
    compare_timeseries,compare_ergun_to_experiment,read_measured_csv)


def test_explicit_csv_schema_units_and_provenance(tmp_path):
    raw="hours,position_C\n"+"\n".join(f"{i/2},{20+2*i}" for i in range(11))+"\n"
    file=tmp_path/"test.csv"
    file.write_text(raw,encoding="utf8")
    ts=read_measured_csv(file,header_row=0,time_column="hours",
             sensor_column="position_C",time_unit="hours",
             run_id="SYNTHETIC-TEST-ONLY",sensor_id="NOT-MEASURED")
    assert ts.elapsed_s[2]==3600
    assert ts.measured_C[-1]==40
    assert len(ts.source_sha256)==64


def test_matching_numbers_cannot_create_validation_without_metadata():
    measured=TimeSeries(tuple(range(12)),tuple(20+i for i in range(12)),
                        "synthetic_hash","synthetic","synthetic")
    mapping=ExperimentalMapping(
        dataset_doi="10.17632/fgn79fzg7x.1",run_id="synthetic",sensor_id="synthetic",
        sensor_axial_position_m=None,bed_geometry_source_ref=None,
        mass_flow_source_ref=None,measured_inlet_temperature_source_ref=None,
        sensor_uncertainty_C=None,held_out_from_calibration=False,
        is_same_flow_topology=True)
    result=compare_timeseries(measured,tuple(range(12)),
                              tuple(20+i for i in range(12)),mapping)
    assert result.rmse_C==0.0
    assert result.status=="BLOCKED_METADATA"
    assert "bed_geometry_source_ref" in result.blocked_reasons
    assert "whole_run_not_used_in_calibration" in result.blocked_reasons


def test_complete_metadata_still_not_assigned_validation_pass():
    measured=TimeSeries(tuple(range(11)),tuple(25+i for i in range(11)),
                        "synthetic_hash","runA","TC1")
    mapping=ExperimentalMapping(
        dataset_doi="10.17632/fgn79fzg7x.1",run_id="runA",sensor_id="TC1",
        sensor_axial_position_m=0.25,bed_geometry_source_ref="source:p2",
        mass_flow_source_ref="source:p3",measured_inlet_temperature_source_ref="source:table1",
        sensor_uncertainty_C=1.0,held_out_from_calibration=True,
        is_same_flow_topology=True)
    result=compare_timeseries(measured,tuple(range(11)),
                              tuple(25+i+0.5 for i in range(11)),mapping)
    assert result.status=="COMPARED_NOT_VALIDATED"
    assert result.rmse_C==pytest.approx(0.5)
    assert result.blocked_reasons==()


def test_rejected_time_leakage_or_sensor_mismatch():
    with pytest.raises(BenchmarkBlocked):
        TimeSeries((0,1,1),(20,21,22),"hash","a","TC1")
    measured=TimeSeries((0,1,2),(20,21,22),"hash","a","TC1")
    mapping=ExperimentalMapping("doi","b","TC1",None,None,None,None,None,False,True)
    with pytest.raises(BenchmarkBlocked,match="different run"):
        compare_timeseries(measured,(0,1,2),(20,21,22),mapping,minimum_points=3)


def test_pressure_comparison_rejects_radial_and_unqualified_taps():
    datum=(PressureDatum(.04,120,10,150,"synthetic-control"),)
    params=dict(diameter_m=.3,length_m=.7,particle_diameter_m=.015,
                porosity=.4,gas_density_kg_m3=.9,gas_viscosity_Pa_s=2e-5)
    with pytest.raises(BenchmarkBlocked,match="radial"):
        compare_ergun_to_experiment(datum,pressure_taps_match_bed_only=True,
                                    axial_flow=False,**params)
    with pytest.raises(BenchmarkBlocked,match="pressure trace"):
        compare_ergun_to_experiment(datum,pressure_taps_match_bed_only=False,
                                    axial_flow=True,**params)
    result=compare_ergun_to_experiment(datum,pressure_taps_match_bed_only=True,
                                       axial_flow=True,**params)
    assert result["status"]=="COMPARED_NOT_VALIDATED"
    assert result["points"]==1


def test_pressure_source_missing_blocks():
    datum=(PressureDatum(.04,120,10,150,"synthetic"),)
    with pytest.raises(BenchmarkBlocked,match="geometry"):
        compare_ergun_to_experiment(datum,diameter_m=None,length_m=None,
          particle_diameter_m=None,porosity=None,gas_density_kg_m3=None,
          gas_viscosity_Pa_s=None,pressure_taps_match_bed_only=True,
          axial_flow=True)
