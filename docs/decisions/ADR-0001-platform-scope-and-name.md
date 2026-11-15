# ADR-0001: Adopt CarnotBatteryLab as research platform name

Date: 2026-11-15
Status: proposed initial repository decision

## Context

The previous CarnotBatteryArchBench project used one fixed synthetic-fluid
heat-pump point and nominal three-case TES comparison. The November 2026
scientific audit withdrew the ranking because several architectures and cost
bases were non-equivalent or infeasible. A full physical, economic and
uncertainty-aware framework exceeds a bench-screening scope.

## Decision

Use `CarnotBatteryLab` as the standalone new repository/package identity. Keep
historical code under `legacy_audited_screen/` and implement an independently
reviewable `src/carnot_battery_lab/` library with scientific contracts, cases,
physics modules, joint integration, optimisation, validation and reporting.

Separate industrial P2H+TES research and true P2H2P Carnot batteries into
independent service families. Do not promote a heat-only system as having
an electrical round-trip efficiency.

## Alternatives rejected

- `CarnotBatteryArchBench`: too focused on static architecture rankings.
- `HTHP-ControlBench`: already a distinct control project; risk of ambiguous
  history and work-product duplication.
- `CarnotFlex`: concise but less explicit scientific meaning and could imply
  electrical round-trip performance without a discharge engine.

## Consequences

More architecture and validation discipline; no shared unsupported legacy
performance claims; engineering cost cannot be compared until reference year,
scale and system boundary are reconciled. New code must not silently import
legacy calculations into the validated namespace.
