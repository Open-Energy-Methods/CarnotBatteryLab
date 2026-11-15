import pytest
from carnot_battery_lab.physics.economics import capital_recovery_factor,levelized_cost_of_heat_per_MWh
from carnot_battery_lab.optimization.pareto import EvaluatedDesign,non_dominated_designs


def test_crf_at_zero_discount_and_flat_annual_lcoh():
    assert capital_recovery_factor(0,10)==pytest.approx(.1)
    assert levelized_cost_of_heat_per_MWh(1e6,10000,20000,1000,0.,10)==pytest.approx(130)


def test_crf_positive_rate():
    assert capital_recovery_factor(.05,20)==pytest.approx(.080242587,rel=1e-6)


def test_pareto_only_feasible_and_nondominated():
    designs=[EvaluatedDesign('A',(1,3),True,'runA'),
             EvaluatedDesign('B',(2,2),True,'runB'),
             EvaluatedDesign('C',(3,4),True,'runC'),
             EvaluatedDesign('D',(.5,.5),False,'runD'),
             EvaluatedDesign('E',(1,3),True,'runE')]
    assert [d.identifier for d in non_dominated_designs(designs)]==['A','B','E']


def test_pareto_rejects_bad_evidence_or_objectives():
    with pytest.raises(ValueError):EvaluatedDesign('bad',(float('nan'),),True,'runA')
    with pytest.raises(ValueError):EvaluatedDesign('x',(1,),True,'')
    with pytest.raises(ValueError):non_dominated_designs([EvaluatedDesign('x',(1,),True,'x'),EvaluatedDesign('y',(1,2),True,'y')])
