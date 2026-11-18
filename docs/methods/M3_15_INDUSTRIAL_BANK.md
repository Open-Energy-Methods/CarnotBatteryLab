# M3.15 — area-equivalent industrial banks and heat-rejection constraints

## Verified input and hypothesis

M3.14b exact-head CI passed seven workflows. 1000 W passes the 12/16 joint grid and 12-cell half-step screens; 1250 W fails. Reference 16-cell cycle modeled electric 1884194.7835619815 J, cooler 1187228.3604017794 J, peak cooler 8760.079660933661 W, raw HX margin 3.011664491347915 K. These are hypothetical model quantities; no experimental or vendor validation.

Construct one nominal 1 MW bank using 1000 area-equivalents. Maintain 0.5 m radial-uniform axial bed depth, particle size, porosity, and local heat-transfer coefficients; increase cross-sectional area and extensive thermal/gas inventories, HX channel count (constant hydraulic diameter and assumed friction), return area, blower free flow, heater and cooler conductance proportionally. Twenty identical hypothetical vessels in parallel each have 2.1213 m diameter, each 50 equivalents. The numerical solver represents their exact equal-flow aggregate with a single effective axial diameter (9.4868 m); it does not resolve vessel-to-vessel maldistribution, radial gradients, wall heat loss, pressure shell, support loads, actual pipework or HX design. One equivalent HX per bank stands for many parallel channels, not a selected industrial exchanger.

Add a full-flow supply and return header of 10 m each, candidate diameter 3 or 4 m, assumed Darcy f=0.02 and combined minor K=4. Relative lumped resistance K_eq=(f*2L/D+K)*(A_return/A_header)^2 enters the existing return pressure-flow equation. Two-header geometric gas volume is added to the return lump; this models additional inventory but not separate header temperature or distributed pressure states. The full-flow length assumption is conservative relative to ideal evenly distributed flow but not an actual manifold bound. Branch losses/flow balance unknown. No auxiliary gas compression outside the modeled blower. Centralized water and coolant utilities assumed independent of gas circuits.

## Operating strategy

Three identical banks, offset by one 600 s slot, each charge 1200 s and discharge 600 s. Two charge while one discharges; three banks total 60 vessels, 15 MW installed heater nameplate. Ideal scheduled overlap is not a continuous-service qualification: no switching transients, outage margin, startup of plant banks, common-header interactions or storage between bank switches. Use final periodic bank traces sampled every 10 s, evaluate the two charge segments plus one discharge segment including one-sided endpoint loads, and integrate slot electricity from the bank stage ledgers, not sampled quadrature. Slot energy equals one bank cycle for this ideal staggered periodic schedule. One process-water pump at fixed service flow and a shared coolant pump at equivalent instantaneous rejection / (cp*10 K), each assumed 100 kPa differential and 65% efficiency, water/coolant densities 930/970 kg/m3. Cooler sink remains ideal 100 C, requires pressurized utility or alternative heat rejection; heat-rejection plant/fan/chiller electricity, valve actuation and distribution power excluded. Sampled maximum electrical loads are not continuous extrema. Cooler accepted-node peak reported separately.

Test ideal similarity (no additional headers), 3 m and 4 m headers, then 4 m header with assumed instantaneous cooler caps 3 MW and 1 MW; 12-cell repeat of 3 MW cap alongside 16-cell primary cases. All run ten no-reset cycles at fixed 1 MW and 150 C, 600 s service. Cooler cap modifies the thermal balance, not just postprocessing. Capacity limitations and any failed duty/periodicity are reported, never silently dropped. Similarity control verifies scaling against the prior module, not hardware. Conservative first-law and mass checks and explicit service deficit on every cycle. No claim of asymptotic convergence, industrial or continuous service qualification, Carnot RTE, waste-heat source suitability, or economic performance.

## Reproduce

pip install -e ".[physics,test]"
python -m pytest tests/test_m3_15_industrial_bank.py -q
python scripts/run_m3_15_industrial_bank.py --case header_4m_cap3MW --output results/case_header_4m_cap3MW.json

Run all six cases and aggregate with --aggregate results --output results/m3_15_summary.json.
