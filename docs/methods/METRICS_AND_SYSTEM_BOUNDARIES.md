# Definitions, equations and system-boundary discipline

**Warning:** definitions below specify future evaluation; no combined system
outputs have been produced yet in the new platform.

## Control volumes and primary units

- Mass flow `kg/s`, temperature `K` for thermodynamic functions, pressure `Pa`,
  specific enthalpy `J/kg`, specific entropy `J/(kg K)`, heat/power `W`, stored
  energy `J`, time `s`.
- The electrical meter boundary includes compressor(s), pump(s), fan(s),
  circulating heaters, backup/booster and idle auxiliaries. Purchased grid
  energy and on-site generation must be recorded separately.
- Thermal-service boundary is the process HX. Only heat delivered at or above
  the prescribed supply-temperature/pressure and quality requirement counts as
  **qualified** useful heat. Warming a tank is not qualified useful output.
- Pressure losses and fluid mass balance are included in every closed loop.
  Electrical parasitics cannot be silently neglected after geometry changes.

## Equations and definitions

At a steady component, first-law residual:

`R_E = sum(m_dot*h_in) - sum(m_dot*h_out) + Q_dot_in + W_dot_in`.

For a transient component, compare with `dU/dt` and explicitly account for
work, exchange and boundary direction conventions. Adopt signs consistently
in the implementation and test sign reversals on simple components.

Flow exergy at constant composition (relative to dead-state) is
`b_ph = (h-h0) - T0(s-s0)`; changes along a stream are
`delta b_ph = delta h - T0 delta s`. For constant heat capacity at common
pressure, `delta b = cp [(T_hi-T_lo) - T0*ln(T_hi/T_lo)]`. These expressions
are **not** Carnot factors evaluated at a single outlet temperature for a
finite-temperature-drop stream. When pressure varies, include property-backed
entropy and enthalpy changes.

System heat COP (integrated over service horizon):

`COP_system = Q_qualified_process_heat / sum(W_electric_all)`.

*This is not the cycle-only compressor COP.* The energy of the waste-heat
source and transfer/exergy destruction still appear in the full balance.

Qualified TES heat-delivery fraction for periodic operation:

`eta_TES_energy = Q_TES_to_qualified_process / Q_charge_into_TES`, evaluated
on an equal initial/final storage state. Track any residual `U_final-U_initial`
explicitly. A one-charge/one-discharge start-from-cold transient **is not**
a conventional round-trip efficiency if the bed ends warmer.

TES flow exergy ratio:

`eta_TES_exergy = X_TES_out / X_TES_in`, integrated at physically consistent
charging and discharging interface boundaries under the same reference state,
with appropriate subtraction for ambient reference and any pressure effects.

Net electrical Carnot-battery round trip, **E-family only**:

`eta_electric_RTE = E_electric_exported_net / E_electric_charged_net`, with
meter conventions and external heat inputs explicitly disclosed. Thermal heat
export cannot replace electricity in the numerator.

Climate metrics: compute a time-resolved emissions ledger from consumption and
an appropriately defined grid-emissions signal; report whether average,
short-run marginal or lifecycle factors are used. Carbon savings depend on the
comparison baseline and are not intrinsic hardware properties.

## Economic study boundary

- Common currency and reference-year price basis; equipment scale and valid
  country/installation context; vendor quotation vs design estimate.
- CAPEX includes major equipment, TES media, tanks, insulation, HX, piping,
  valve systems, instrumentation, electrical equipment, controls, civil works,
  engineering, contingency and balance of plant under explicit boundaries.
- OPEX includes electricity (time matched), maintenance, replacement, cooling
  water/HTF losses and operator requirements as applicable.
- LCOH uses **only qualified useful heat** in its denominator with matched
  assumptions about annual output; constant annual model and time-discounted
  detailed model must reconcile in their common limit.
- Life, degradation, salvage, installation factor, interest/real vs nominal
  inflation, tax and carbon accounting need explicit definitions.

## Storage and temperature compatibility

Solar Salt (common 60/40 sodium/potassium nitrate) operates in systems with
cold/hot temperatures around 290/565 °C; its melt temperature is around
220 °C. A cold tank at 30 °C is physically impossible for that salt.
Treat design margins and heat tracing as necessary engineered requirements.
A low-melting alternative cannot inherit Solar Salt materials or cost inputs.

Dual-media thermocline = solid filler and liquid HTF; air/rock packed bed
should be called **solid-packed gas regenerator** unless a different
architecture-specific definition is provided and sourced.

## Research exclusion ledger

No defensible universal COP, storage-cost figure, exergy score or efficiency
ranking is embedded into the package. The former A/B/C output is quarantined
in `legacy_audited_screen/`. Such numbers must be regenerated only after
valid operating bounds, service parity and validation gates are met.
