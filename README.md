# Cymbal Capital — Digital Lending & RBI KFS Compliance Portal

This repository contains the **Cymbal Capital Digital Lending & RBI Key Fact
Statement (KFS) Compliance Portal**, a reference full-stack application for the
AI-Native Software Development Lifecycle (SDLC) Workshop on Google Cloud.

## Architecture overview

The portal pairs a **Python 3.12 + FastAPI** backend (managed via `uv`) with a
**Vite + React 19 + TypeScript** frontend (managed via `bun` and `biome`) styled
in a low-glare **OKLCH** color system.

| Layer | Technology stack | Purpose |
| :--- | :--- | :--- |
| **Specifications (`0-spec/`)** | [`BRD_TEMPLATE.md`](0-spec/BRD_TEMPLATE.md), [`RBI_COMPLIANCE_CHECKLIST.md`](0-spec/RBI_COMPLIANCE_CHECKLIST.md) | Statutory RBI Digital Lending & KFS gates (`RBI-KFS-01` to `RBI-DLG-04`). |
| **Agent skills (`.agents/skills/`)** | `brd-and-wbs-estimator`, `nbfc-uat-boundary-tester` | Reusable skills for RBI BRD auditing, BigQuery WBS sizing, and 105-case UAT generation. |
| **Backend (`backend/`)** | Python 3.12, FastAPI, `uv`, `pytest`, `ruff` | Deterministic Newton-Raphson APR solver, cooling-off payoff calculator, penal charge validator, Cloud DLP redactor, and BigQuery telemetry. |
| **Frontend (`frontend/`)** | React 19, TypeScript, Vite, `bun`, `biome`, OKLCH | Interactive 4-module workshop console with light/dark theme toggle. |

## Workshop modules

1. **Module 2: BRD & BigQuery WBS Sizer** — Audits SME Top-Up meeting notes,
   redacts PAN/Aadhaar via Cloud DLP, flags 4 P0 RBI compliance gaps, and computes
   a BigQuery-backed engineering WBS estimate (`cymbal_capital_sdlc.wbs_benchmarks`).
2. **Module 3: SME Credit Policy & Sprint Risk Agent** — Evaluates the Apex
   Precision Engineering ₹75L loan application (`DSCR 1.18x` Zonal Credit Head
   escalation) and triages Sprint 24 GitHub Issue blockers (`#4`, `#7`) and
   unestimated items (`#9`, `#10`).
3. **Module 4: RBI KFS & APR Engine + 105 UAT Suite (Issue #12)** — Interactive
   calculator proving the spread between Nominal ROI (`14.50%`) and All-Inclusive
   APR (`15.93%`), 3-day cooling-off exit math, non-compounding `<= 24%` p.a.
   penal charge guardrails, and a 105-case boundary UAT suite.
4. **Module 6: Model Armor, Cloud DLP & Token Governance** — Live PII redaction
   for `INDIA_PAN_INDIVIDUAL` (`ABCDE1234F`) and `INDIA_AADHAAR_INDIVIDUAL`
   (`4921 8834 9012`), prompt-injection defense, and BigQuery department token
   cost governance (`cymbal_capital_sdlc.token_cost_governance`).

## Quick start

Run the full validation pipeline (`format` -> `lint` -> `test`) from the root
directory:

```bash
make check
```
