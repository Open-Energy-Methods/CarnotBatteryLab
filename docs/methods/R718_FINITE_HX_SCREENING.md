# M1: R718 finite-source/finite-sink feasibility screen

**Status:** first screening vertical slice, NOT completed M1, manufacturer-qualified or experiment-validated.

## Independent published context

Zühlsdorf, Schlemminger, Bantle, Evenmo & Elmegaard (2018), *Design recommendations for R-718 heat pumps in high temperature applications*, DOI 10.18462/iir.gl.2018.1367. Table 1 gives two distinct impellers: inlet 110 °C / 1 bar and 145 °C / 3.2 bar; nominal ratios 3.2 and 2; expected isentropic efficiency 0.74. **These are not the compressor operating points of the 80 °C waste-source / 150 °C process reference case.** The chosen screening ratio limit of 5:1/stage is NOT a manufacturer-proven map; the literature source supports the research motivation and illustrative efficiency, not complete-cycle external validation.

CoolProp documentation https://coolprop.org/fluid_properties/IF97.html explicitly gives water cp at 500 K and 101325 Pa = 1981.5422965970472 J/kg/K and saturation pressure at 500 K = 2638897.7562732203 Pa. These are asserted in the physics tests. HEOS::Water (IAPWS-95 family) versus IF97::Water (industrial formulation) offers a cross-formulation consistency check, but it is not an independent experimental validation.

## Correct source and process thermal boundaries

The H-REF contract specifies an 80 °C *source inlet* only, insufficient for a finite source-side heat exchanger. In this **supplementary research screening**, the source outlet is assumed 70 °C and minimum approach 5 K, requiring evaporation at 65 °C, NOT 75 °C inferred from inlet alone. Suction superheat is assumed 10 K. At the process end, 150 °C supply and 110 °C return, 5 K pinch yields 155 °C saturated condenser temperature. These choices are illustrative rather than measured or industrially established.

## Cycle and balance equations

Water refrigerant state points: suction (superheated evaporator outlet); stage1_out; stage2_in (externally cooled at intermediate pressure to saturation + 10 K); discharge; saturated condenser_liquid; and after_throttle (isenthalpic expansion to evaporating pressure). Single-stage mode omits the two intermediate states.

Isentropic compression to p_out uses h_out = h_in + [h(p_out,s_in)-h_in]/eta_is. Two-stage uses geometric-mean intermediate pressure. Per refrigerant mass:
- w_shaft = sum compressor (h_out-h_in)
- q_process = h_discharge - h_condenser_liquid
- q_intercool = h_stage1_out - h_stage2_in
- q_source = h_suction - h_after_throttle
- exact refrigerant first-law identity q_source + w_shaft - q_process - q_intercool = 0.

Mass flow is sized to the useful process duty Q_process = 1 MW. Electric compressor work W_e = W_shaft / eta_motor. Motor electrical losses W_e-W_shaft are distinct from refrigerant shaft work. The interstage cooler is supplied by a **separate coolant loop 60 → 75 °C**, and its rejected heat is NOT credited to the process heat. Its circulation pump and source/process pumps are currently not modelled. COP_electric = Q_process/W_e is not plant/annual COP.

## Heat exchanger check

For a counterflow HX where x runs from 0 (hot inlet/cold outlet) to 1 (hot outlet/cold inlet), required UA is the integral of Q/[T_hot(x)-T_cold(x)] dx over x=0..1. Both terminal and **internal** minimum approaches must be >= specified pinch. The evaporator uses the 80→70 °C source decline against the real-fluid two-phase/superheating refrigerant path. The condenser uses the water P,H temperature profile through desuperheating/condensation against 110→150 °C process heat. The interstage HX uses compressed water vapor desuperheating against external 60→75 °C coolant. The computed required-UA is **not** a vendor-specified exchanger geometry or a pressure-loss verified design. Installed-UA insufficiency and temperature crossover cause explicit infeasibility errors.

## Accepted evidence now versus required later

Implemented: real-water CoolProp state calls; two-stage/single-stage model; pressure-ratio/discharge-temperature guards; 3 finite counterflow HX checks; refrigerant shaft-energy closure; explicit rejected heat, motor electricity and coolant/source/process flow bookkeeping; independent analytic constant-hot LMTD HX test and internal-pinch negative control; external documented IF97 point check and HEOS/IF97 numerical consistency tests in CI.

**Still missing:** independently reproduced complete heat-pump/impeller benchmark; manufacturer compressor performance curves and valid operating envelope; pressure losses and flow/pumping electrical energy; physical installed-UA correlations/geometry; process source variability and real site mass flow limits; exergy destruction by all components; part-load/start-up and hot/cold-side transient states; TES coupling; cost and uncertainty. The illustrative engineering bounds max pressure ratio 5 and discharge 350 °C are not claimed as universal. R718 has not yet reached M1/H0 validated gate.

## Reproduction

Install: python -m pip install -e ".[physics,test]"

Tests: python -m pytest tests/test_finite_hx.py tests/test_r718_realfluid.py -v

Screen JSON: python scripts/run_r718_reference.py --output results/r718_h0_reference_screen.json

Without CoolProp, analytic HX tests still run but physical R718 tests must be reported **skipped**, never passed. Separate GitHub Actions real-fluid job installs the dependency and executes all R718 tests explicitly.
