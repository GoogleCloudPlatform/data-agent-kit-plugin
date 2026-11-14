# Phase 3: Baseline Security Evaluation

Evaluate every bucket and project against the universal baseline controls.

## Instructions

Follow the guidance in `references/baseline_security.md`. These are prerequisite
checks — any failure is flagged independently, regardless of toxic combinations.

> [!IMPORTANT]
> Each baseline failure is its own finding. Do NOT collapse
> multiple baseline failures on the same bucket into a single toxic-combination
> label (e.g., "UBLA disabled + No recovery"). Toxic-combo labels in Section 2 /
> per- bucket cards are reserved for the named archetypes in
> `references/toxic_combinations.md`. For a bucket failing only baselines, the
> Risk column enumerates the failing controls (e.g., "UBLA disabled; versioning
> off") and per-bucket cards show one ❌ per control.
