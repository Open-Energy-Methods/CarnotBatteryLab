# Contributing to CarnotBatteryLab

This research platform uses scientific pull-request review, not just software
linting. Before submitting a new model or an empirical constant:

1. State the physically defined system boundary, equations, units, correlation
   validity limits and all assumed parameter values.
2. Add a verified source ledger record for nontrivial empirical correlations
   and a separate independent check of the implemented equation.
3. Add small analytical tests, conservation tests, numerical convergence and
   an independent benchmark if the feature claims predictive capability.
4. Preserve raw data immutability, report all failed cases and specify
   accepted out-of-domain or infeasible states.
5. State model fidelity, costs, uncertainty and claimed performance limits.
6. Update the release matrix and figure provenance if a published conclusion
   changes. Never simply delete a failed historical result.

The repository owner has not selected a code/data distribution license yet.
No third-party dataset or model can be redistributed solely because it can be
read online. See `references/LITERATURE_EVIDENCE.md` for tracked origins.
