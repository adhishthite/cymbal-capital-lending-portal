---
name: nbfc-uat-boundary-tester
description: Read a GitHub Issue or financial specification, extract lending parameters, and generate 100+ parameterized pytest UAT boundary test cases covering RBI APR math, zero/negative inputs, leap years, cooling-off cancellation, penal charge caps, DSCR/LTV thresholds, and PII masking. Use when generating or expanding UAT test suites for NBFC digital lending microservices.
---

# NBFC UAT boundary tester

Generate exhaustive, deterministic boundary test suites (`100+` parameterized cases) in `pytest` from a GitHub Issue or lending product specification.

## Workflow steps

Execute these steps in order to build and verify the boundary test suite:

1. **Fetch the GitHub Issue specification:** Read the target issue (for example, Issue #12: `Implement RBI Key Fact Statement (KFS) APR Calculator & Penal Charge Guardrail`) from `adhishthite/cymbal-capital-lending-portal` or inspect `0-spec/RBI_COMPLIANCE_CHECKLIST.md`.
2. **Extract financial boundaries and invariants:** Identify every numerical threshold, statutory formula, and rejection condition:
   - **Principal & Tenure validity:** Test `0`, `-1`, `-100000`, minimum micro-ticket (`₹10,000`), standard SME ticket (`₹10,00,000` and `₹75,00,000`), and high-value tickets (`₹5,00,00,000`).
   - **Nominal ROI vs. All-Inclusive APR spread:** Verify that a `₹10,00,000` loan at `14.50%` nominal ROI over `24` months with `₹14,500` total upfront deductions (`₹10,000` processing + `₹2,500` documentation + `₹2,000` insurance) yields an all-inclusive APR of `15.93%` (`±0.02%`).
   - **Cooling-off period boundary (`6` vs. `7` days):** Verify that loans with `tenure_days >= 7` enforce a minimum `3`-calendar-day cooling-off window with `₹0` prepayment penalty, and test cancellation payoffs across days `0`, `1`, `2`, `3`, and `4`.
   - **Leap-year day-count conventions (`365` vs. `366` days):** Test proportionate APR payoff math in leap years (`2024`, `2028`) versus standard years (`2025`, `2026`).
   - **Penal charge guardrails:** Verify that `is_compounded=True` is rejected regardless of rate, and test simple penal charge rates at `0.0%`, `12.0%`, `23.99%`, `24.00%` (compliant boundary), `24.01%` (violation boundary), and `36.00%`.
   - **SME Credit Policy DSCR & LTV boundaries:** Test DSCR at `1.14x` (reject), `1.15x` (escalate to Zonal Credit Head), `1.18x` (Apex Precision Engineering case — escalate to Zonal Credit Head), `1.24x` (escalate), and `1.25x` (auto-approve); test LTV at `74.99%`, `75.00%` (compliant cap), and `75.01%` (reject).
   - **PII redaction & prompt injection:** Verify masking of PAN (`ABCDE1234F`), Aadhaar (`4921 8834 9012`), Indian mobile numbers, and bank account numbers.
3. **Write parameterized `pytest` tests:** Author or update `backend/tests/test_uat_boundary_100.py` using `@pytest.mark.parametrize` with explicit case IDs so every boundary failure reports the exact financial rule and input vector.
4. **Execute and verify:** Run `uv run pytest` inside `backend/` and confirm all `105+` boundary cases and `15` unit tests pass with zero warnings or flakes.

## Completion criteria

The UAT boundary suite is complete only when:
- `backend/tests/test_uat_boundary_100.py` contains at least `100` distinct parameterized test cases (`105` cases standard) covering all seven boundary categories above.
- `uv run pytest` passes `100%` of cases deterministically in under 5 seconds.
