from pathlib import Path
import pytest
from carnot_battery_lab.cases import CaseValidationError, load_study_case, parse_study_case

ROOT=Path(__file__).parents[1]


def test_reference_heat_case_requires_useful_service():
    case=load_study_case(ROOT/'cases/reference_industrial_heat_150C.yaml')
    assert case.service == 'process_heat'
    assert case.nominal_useful_storage_MWh_th == 6.0
    assert case.configuration_status == 'illustrative'


def test_high_temperature_case_not_advertised_validated():
    case=load_study_case(ROOT/'cases/high_temperature_challenge_250C.yaml')
    assert case.configuration_status == 'illustrative'
    assert case.process_supply_C == 250.0


def test_reject_unexpected_key_and_missing_load():
    data={
        'case_id':'x','service':'process_heat','source_inlet_C':80.,
        'ambient_C':20.,'useful_storage_duration_h':4.,
        'temporal_resolution_min':15,'configuration_status':'illustrative',
        'reference_only':True,'notes':'x',
        'process_supply_C':150.,'process_return_C':110.,
    }
    with pytest.raises(CaseValidationError):
        parse_study_case(data)
    data['load_MW_th']=1.
    data['untraceable_magic_NTU']=25
    with pytest.raises(CaseValidationError):
        parse_study_case(data)


def test_reject_nonfinite_and_temperature_inversion():
    case=load_study_case(ROOT/'cases/reference_industrial_heat_150C.yaml')
    from dataclasses import asdict
    d=asdict(case)
    d['ambient_C']=float('nan')
    with pytest.raises(CaseValidationError):parse_study_case(d)
    d['ambient_C']=20.0
    d['process_supply_C']=100.0
    with pytest.raises(CaseValidationError):parse_study_case(d)


def test_case_cannot_claim_nonillustrative_without_new_schema():
    from dataclasses import asdict
    d=asdict(load_study_case(ROOT/'cases/reference_industrial_heat_150C.yaml'))
    d['reference_only']=False
    with pytest.raises(CaseValidationError):parse_study_case(d)
