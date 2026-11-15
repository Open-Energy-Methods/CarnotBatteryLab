import os
import sys
import numpy as np
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from audit_metrics import (
    flow_exergy_delta, audit_packed_bed, check_solar_salt_compatibility,
    T_REF_K,
)


def test_exact_stream_exergy_integral():
    # Integral of (1 - T0/T) dT between given states, cp constant.
    lo, hi = 30.0, 150.0
    integral = (hi-lo) - T_REF_K * np.log((hi+273.15)/(lo+273.15))
    assert flow_exergy_delta(hi, lo) == pytest.approx(integral, abs=1e-12)


def test_zero_change_produces_zero_flow_exergy():
    assert flow_exergy_delta(30,30) == pytest.approx(0)


def test_packed_bed_a_energy_exergy_bounds():
    a = audit_packed_bed('A',15)
    assert 0 < a.recovery_fraction < 1
    assert 0 < a.stream_exergy_ratio < 1
    assert a.recovered_exergy < a.charge_exergy
    assert a.electrical_input_per_delivered_exergy > 0


def test_corrected_metric_must_not_equal_legacy_formula():
    a = audit_packed_bed('A',15)
    old_ex_efficiency = 0.7707808736799348
    wrong_metric = (1/2.123)/old_ex_efficiency
    assert abs(a.electrical_input_per_delivered_exergy - wrong_metric) > 2.0


def test_solar_salt_guard_rejects_proposed_case():
    assert not check_solar_salt_compatibility(30,145)
    assert check_solar_salt_compatibility(290,565)
