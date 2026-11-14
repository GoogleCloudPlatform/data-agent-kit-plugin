# Phase 4: Toxic Combination Analysis

This is the core of your assessment. Evaluate each bucket against the toxic
combination archetypes.

## Instructions

Evaluate each bucket against the toxic combination archetypes defined in
`references/toxic_combinations.md`.

For each bucket, you MUST:

1.  **Identify Archetypes**: Identify which toxic combination archetype(s) match
    the bucket's telemetry profile.
2.  **Explain Combination**: Explain the **toxic combination** — why these
    specific gaps together create a risk that is greater than the sum of its
    parts.
3.  **Assign Severity**: Assign a severity label modulated by the bucket's
    classification from Phase 2.
4.  **Provide Remediation**: Provide remediation scripts for every gap
    identified.

> [!IMPORTANT]
> Your reasoning MUST connect the dots between signals. Do not just
> list individual misconfigurations. Explain the attack path or failure mode
> that the combination enables. This is what makes you valuable — a config
> checker lists findings; you explain consequences.

## Severity Labels

Label    | Meaning
-------- | ---------------------------------------------------------------
Critical | Active exposure or full-chain attack path. Immediate action
High     | Significant gaps that enable serious attack scenarios. Urgent
Medium   | Notable gaps that weaken posture but require additional factors
Low      | Minor gaps, typically integrity/availability risks on

Severity is modulated by bucket classification. The same toxic combination on a
High-sensitivity bucket may be Critical, but Medium on a Low-sensitivity bucket.

## SAIF Risk Factors

See `references/saif_risk_factors.md` for the mapping of SAIF risks to telemetry
signals. Reference these risk names in your findings to maintain traceability to
the SAIF framework.
