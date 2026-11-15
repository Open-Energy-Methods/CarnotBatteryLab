# M2 first R718 / gas–rock packed-bed coupling: charge-only physics

**Scope:** an independently testable, conservative **screening** coupling of a high-temperature R718 condenser to a 1-D gas/rock regenerative TES. This is deliberately **not** a complete M2, M5, industrial design, process-heat service, or a verified P2H2P Carnot battery. M1 compressor hardware remains unsupported at the example operating point.

## Schematic and system boundary

Waste heat source (80→70°C, assumed), R718 2-stage evaporator/compressor, finite source/condenser/interstage HX → **hot circulating gas** → 1-D two-temperature packed bed → cooler circulating gas **feeds back to condenser-side inlet**. The same gas stream circulates at an explicitly commanded flow; the compressor working fluid is water vapor, NOT the bed gas. An illustrative cooled blower and 2 liquid auxiliary pumps are metered electrically. The bed only CHARGES during this experiment. Zero industrial process load is claimed delivered.

The code reuses the existing R718 quantity named \`useful_process_heat_W\` as **condenser heat transferred into the bed gas** while in charge-only mode. It is not qualified process heat and must never enter an industrial LCOH denominator in this experiment.

## 1. Transient governing equations

A 1-D conservative finite-volume gas–rock regenerator uses gas and solid temperatures \`Tf_i\` and \`Ts_i\`. For each cell volume \`V_i\`, porosity ε, constant nominal material properties:

- Gas cell stored capacity \`Cf_i = ε ρg cp_g V_i\`
- Solid cell stored capacity \`Cs_i = (1−ε) ρs cp_s V_i\`
- Interfacial conductance \`H_i = h A_i\`, with \`A_i = 6(1−ε)V_i / d_p\` for spheres
- Gas: \`Cf_i dTf_i/dt = m_dot cp_g (Tf_upstream−Tf_i) − H_i(Tf_i−Ts_i)\`
- Rock: \`Cs_i dTs_i/dt = H_i(Tf_i−Ts_i) − UA_wall_i(Ts_i−T_ambient)\`

The inlet cell uses commanded hot-gas inlet; other cells use upwind adjacent gas nodes, giving a defined first-order spatial model. No arbitrary NTU uplift or energy per step is imposed. The gas/solid coupling is stiff and solved with SciPy's BDF; time-step and grid count are independent.

Nusselt correlation from Wakao, Kaguei & Funazkri (1979): \`Nu = 2+1.1 Re_p^0.6 Pr^(1/3)\`, doi:10.1016/0009-2509(79)85064-2; nominal published range **15 ≤ Re_p ≤ 8500**, enforced for nonzero flows; stagnant limit Nu=2 is a deliberate conduction approximation. Particle Reynolds \`Re_p = m_dot d_p/(A_cross μ)\` and \`Pr = cp_g μ/k_g\`. Note particle morphology, channeling, and voidage dependence still require experimental validation.

Ergun (1952) determines pressure drop using bed geometry and nominal gas density; fan electrical work \`W_fan = ΔP * (m_dot/ρg)/η_fan\`. This stage assumes the blower's electrical/viscous work is cooled and rejected to the environment, **not invisibly credited as useful TES heat**; real gas thermodynamic pressure/temperature profiles must replace this simplification in a higher-fidelity version.

The bed integral includes two extra differential states, \`Q_hotgas = ∫m_dot cp_g(T_in−T_out) dt\` and \`Q_wall = ∫UA_wall(Ts−Ta)dt\`. Independently compute \`ΔU = U_final−U_initial\` from temperatures and physical inventory. Require \`ΔU+Q_wall−Q_hotgas≈0\` under numerical tolerance for every step and cumulatively.

## 2. Coupled condenser / return temperature calculation

With charge-controller duty \`Q_HP\` and gas flow \`m_dot\`, the condenser raises the gas by \`ΔT = Q_HP/(m_dot cp_g)\`. Unlike a pre-assumed fixed COP source, the gas return temperature is **computed** from the dynamically solved bed outlet, then used to set condenser inlet/outlet temperature, saturation pressure, required HX UA and compressor electricity.

For each macro-step, solve a fixed-point iteration on the **time-average** outlet temperature. Each trial integrates the entire bed with \`T_in = T_return_guess + ΔT\`, producing \`T_return_new = T_in − Q_hotgas/(m_dot cp_g Δt)\`. Once residual ≤0.003 K, solve the real-fluid R718 cycle at that gas inlet and outlet; reject HX pinch, compressor envelope or source flow infeasibility. Do not update bed state if the R718 solution is rejected. Report \`ΔU+Q_wall−Q_HP*Δt\` separately to expose any HP/bed splitting error.

At this stage the **commanded condenser duty is fixed**, and a compressor map does not dynamically reduce available capacity at higher bed temperatures. Infeasibility detection is credible; operating dynamics outside the assumed R718 ratio, and actual charge rate limits, remain future work. When storage warms, the condenser temperature and HP work rise at the same imposed duty, producing a **conditional physical feedback sensitivity**, not verified full-plant transient predictive behaviour.

## 3. Reference configuration and assumptions

- R718 source: the existing illustrative 80→70°C waste-heat, finite source HX, two-stage external intercooling, condensing approach 5 K, plus limitations in \`R718_FINITE_HX_SCREENING.md\`.
- Gas/rock: spherical equivalent particle diameter 45 mm, porosity 0.4, nominal bed 4 m long × 5 m diameter, 16 cells, 25 kg/s of pressurised gas.
- Constant nominal gas ρ=2.5 kg/m³, cp=1005 J/(kg K), μ=2.35e−5 Pa s, k=0.033 W/(m K), pressure independent. Rock ρ=2600 kg/m³, cp=850 J/(kg K).
- Nominal wall UA=120 W/K, blower efficiency 0.70; no real fan curve. The gas stream pressure/thermodynamic property evolution is NOT yet modeled.
- The high gas circulation demand is a necessary test of fan power versus charge ΔT. These numbers are initial methodological inputs, not a manufacturer’s geometry/design or validated site inventory.
- Fixed condenser 1 MW gross heat to gas; time-step 180 s, six steps (18-min demonstration), with sensitivity to initial temperature 90,95,105°C.
- Compressor grid energy includes inverter and gear efficiency assumptions and source/interstage liquid pumps, but gas-circuit **external piping** ΔP is omitted, as are refrigerant pressure loss and any cooling utility energy.
- All results are preliminary **charge-only**. No cyclic TES efficiency, delivered process heat, electricity return, system LCOH, manufacturer fit, or experimental validation can be claimed.

## 4. Verification and comparison

Tests cover stagnant equilibrium (no phantom heat/pumping), wall-loss standby, nonzero charging energy balance with integrated flux states, geometry-dependent fan power, 3 different spatial grids with separately checked conservation, invalid-domain detection, warmer initial-bed power penalty, and operation rejection if the required compressor/HX condition is infeasible.

These prove **internal conservation and causal bed/HP feedback**, not predictive accuracy: source datasets are needed for bed outlet shape and pressure-drop validation, cross-solver checks, off-design compressor matching and thermal breakthrough. A numerical grid retaining energy conservation does **not** establish spatial convergence of T_out(t). Explicit space/time/front-convergence and experimental validation are still hard requirements for M2/M5.

## 5. Reproduce

- Install \`python -m pip install -e ".[test,physics]"\`.
- Run \`python -m pytest tests/test_m2_gas_rock_coupling.py -v\`.
- Run \`python scripts/run_m2_coupled_charge.py --output results/m2_charge_only_screen.json\`.
- The JSON includes exact bed/control/HP parameters, recorded individual steps, aggregate energy/electricity ledgers, per-state temperatures and explicit limitations.
- The real-fluid CI job installs CoolProp and SciPy and archives the generated JSON.

## 6. Remaining scientific gates

1. **M1:** obtain and honour complete measured compressor map, provide alternative viable stage topology/cascade at requested lift; quantify all refrigerant-side and plant pressure losses.
2. **M2:** material- and T-dependent gas/solid cp and density; gas-momentum/pressure coupling, axial thermal dispersion and wall thermal inertia; flow reversal, storage discharge with process HX, cyclic steady operation, temperature-qualified usable heat.
3. **V1/V2/V3:** pre-register independent bed outlet/pressure benchmark and reproduce it with hold-out tests; genuine grid/time convergence and structural error budget.
4. **M5:** replace fixed-duty source with a capacity-constrained R718 control/envelope model, add process heat and multi-mode operation, and compare matched-service H0/H1; no false complete Carnot battery claims.

**This is the first integrated thermal physics result and a reproducible starting point, not an M2 completion or scientific v1.0 release.**
