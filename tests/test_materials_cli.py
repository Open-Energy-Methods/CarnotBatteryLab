from pathlib import Path
import pytest
from carnot_battery_lab.physics.materials import SOLAR_SALT_SCREEN,check_bulk_temperature_window
from carnot_battery_lab.cli import main


def test_salt_cold_hot_nonfeasible_legacy():
    ok, reason=check_bulk_temperature_window(30,145,SOLAR_SALT_SCREEN)
    assert not ok and 'freeze' in reason


def test_salt_window_validity_not_full_plant_claim():
    ok, reason=check_bulk_temperature_window(290,500,SOLAR_SALT_SCREEN)
    assert ok and 'full' in reason
    assert not check_bulk_temperature_window(290,570,SOLAR_SALT_SCREEN)[0]


def test_cli_clean_and_missing(capsys):
    assert main(['validate-case',str(Path(__file__).parents[1]/'cases/reference_industrial_heat_150C.yaml')])==0
    assert 'input' in capsys.readouterr().out.lower()
    assert main(['validate-case','/does/not/exist.yaml'])==2
    assert 'INVALID' in capsys.readouterr().err
