"""Evidence gate and negative constraints must not depend on experimental access."""
import math
import pytest
from carnot_battery_lab.physics.transcritical_hp_screen import (
    thermal_interface_gate,ServiceEnvelope,PAPER_EVIDENCE)

def test_TES_charging_interface_is_not_150C_product_service():
    a=thermal_interface_gate(150.)
    assert a["TES_gas_charge_target_C"]==190.
    assert a["required_heat_pump_outlet_C"]==195.
    assert a["approach_margin_K"]==-45.
    assert not a["thermally_compatible_without_booster"]
    assert thermal_interface_gate(195.)["thermally_compatible_without_booster"]
    assert not thermal_interface_gate(194.99)["thermally_compatible_without_booster"]

def test_operating_points_and_uncertainty_not_invented():
    a=PAPER_EVIDENCE["PURDUE_2026"]
    assert a["steady_state_points_count"]==12
    assert a["source_in_C"]==100. and a["source_out_C"]==70.
    assert a["optimum_pure_R600a"]["COP"]==3.01
    assert a["optimum_mixture_R290_R601a_50_50"]["COP_unc"]==.28
    assert PAPER_EVIDENCE["IEA_2026"]["kind"]=="prediction_plus_equipment"

def test_reject_bad_envelopes():
    with pytest.raises(ValueError):ServiceEnvelope(80.,80.,110.,150.)
    with pytest.raises(ValueError):ServiceEnvelope(80.,60.,150.,110.)
    with pytest.raises(ValueError):ServiceEnvelope(80.,60.,110.,150.,motor_efficiency=1.2)
    with pytest.raises(ValueError):ServiceEnvelope(80.,60.,110.,215.)
    with pytest.raises(ValueError):thermal_interface_gate(float("nan"))

def test_R600_is_not_R600a():
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.transcritical_hp_screen import refrigerant_id
    a,_=refrigerant_id("R600")
    b,_=refrigerant_id("R600a")
    assert a!=b and "n-Butane" in a and "IsoButane" in b

def test_binary_mix_mass_to_molar_conversion():
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.transcritical_hp_screen import refrigerant_id
    a,meta=refrigerant_id("R290_R601a_60_40")
    assert meta["mass_fraction_propane"]==.6
    assert .6<meta["mole_fraction_propane"]<1.
    assert "IsoPentane" in a
    with pytest.raises(ValueError):refrigerant_id("R718")

@pytest.mark.parametrize("source,sink",[((100.,70.),(100.,150.)),((80.,60.),(110.,150.))])
def test_pure_butane_EOS_screen_no_false_calibration(source,sink):
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.transcritical_hp_screen import screen_envelope
    e=ServiceEnvelope(*source,*sink)
    x=screen_envelope(e,"R600a",low_dew_count=2,high_pressure_count=4)
    assert x["attempts"]==8
    assert x["status"] in ("SCREENED_EOS_FEASIBLE","NO_FEASIBLE_CANDIDATE_ON_GRID")
    assert x["experimental_validation"] is False
    if x["best"]:
        z=x["best"]
        assert z["energy_residual_W"]==pytest.approx(0.,abs=.1)
        assert z["COP_compressor_electric"]>1.
        assert z["discharge_temperature_C"]<=e.compressor_discharge_temperature_limit_C
        assert z["compressor_map_measured"] is False

def test_charge195_above_compressor160_rating():
    pytest.importorskip("CoolProp")
    from carnot_battery_lab.physics.transcritical_hp_screen import screen_envelope
    e=ServiceEnvelope(80.,60.,110.,195.)
    x=screen_envelope(e,"R600a",low_dew_count=2,high_pressure_count=4)
    assert x["best"] is None
    assert not thermal_interface_gate(150.)["thermally_compatible_without_booster"]
