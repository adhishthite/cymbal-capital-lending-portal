# Business requirements document template (RBI digital lending compliant)

This document defines the standard Business Requirements Document (BRD) template for Cymbal Capital digital lending products. Every new lending feature, top-up workflow, or credit underwriting rule must complete all sections below before entering sprint planning.

<!-- prettier-ignore -->
> [!IMPORTANT]
> All digital lending features at Cymbal Capital must comply with the RBI Digital Lending Guidelines (`RBI/2024-25/18 DOR.STR.REC.13/13.03.00/2024-25`) and the RBI Fair Lending Practice — Penal Charges in Loan Accounts circular (`RBI/2023-24/53 DOR.MCS.REC.28/01.01.001/2023-24`).

## 1. Executive summary and business objective

Provide a concise overview of the lending product or feature, target borrower segment (Retail, MSME, or Commercial), expected disbursement volume, and target sprint milestone.

| Metadata field | Value |
| :--- | :--- |
| **Feature title** | `<Insert Feature Title>` |
| **Business unit** | `Cymbal Capital — SME / Retail Digital Lending` |
| **Target milestone** | `Sprint 24 - SME Digital Lending Compliance` |
| **Product owner** | `<Insert Product Owner>` |
| **Regulatory classification** | `RBI Digital Lending / Key Fact Statement (KFS) Mandatory` |

## 2. Functional requirements

List deterministic functional requirements with testable acceptance criteria. Each requirement must link to a backend service, database table, or UI workflow.

1. **Loan origination and eligibility:** Define minimum Debt Service Coverage Ratio (DSCR), Loan-to-Value (LTV) ceiling, bureau score cutoffs, and GSTIN cash-flow velocity rules.
2. **Pricing and Key Fact Statement (KFS) generation:** Specify nominal interest rate, upfront processing fees, documentation charges, insurance costs, and the exact Newton-Raphson Annual Percentage Rate (APR) calculation.
3. **Disbursement and escrow routing:** Confirm direct credit to the borrower bank account or regulated co-lending escrow account without passing through Lending Service Provider (LSP) nodal or pass-through accounts.

## 3. Mandatory RBI regulatory compliance gates

Every BRD undergoes an automated audit against the four statutory RBI Digital Lending pillars. Mark each requirement with its verification status before requesting engineering estimation.

| Gate ID | Regulatory mandate | Statutory requirement | Verification rule |
| :--- | :--- | :--- | :--- |
| **RBI-KFS-01** | Key Fact Statement (KFS) & All-Inclusive APR | Disclose all-inclusive APR incorporating nominal ROI, processing fee, documentation charges, and insurance premium in the KFS before contract execution. | `all_inclusive_apr_pct > nominal_roi_pct` when upfront charges $> 0$. |
| **RBI-KFS-02** | Mandatory Cooling-Off / Look-Up Period | Provide a minimum 3-calendar-day cooling-off window for loans with tenure $\ge 7$ days. Allow borrower exit by paying only proportionate APR with zero prepayment penalty. | `cooling_off_days >= 3` for `tenure_days >= 7`; `prepayment_penalty_in_cooling_off == 0`. |
| **RBI-PEN-03** | Fair Lending — Penal Charges vs. Penal Interest | Levy late payment penalties strictly as simple, non-capitalized penal charges on the overdue installment amount only, capped at $\le 24\%$ p.a. equivalent. Never compound penal interest into principal. | `is_compounded == False` and `annualized_penal_charge_pct <= 24.0` on `overdue_installment_inr`. |
| **RBI-DLG-04** | Direct Disbursement & Data Privacy (Cloud DLP) | Disburse funds directly to the borrower bank account (no LSP pass-through) and redact PAN, Aadhaar, and account numbers in telemetry logs and AI prompts. | Mask `INDIA_PAN_INDIVIDUAL` and `INDIA_AADHAAR_INDIVIDUAL` prior to LLM inference or logging. |

## 4. Work breakdown structure (WBS) and BigQuery estimation

Ground all engineering effort estimates in historical delivery velocity from BigQuery (`adhish-base-project-1.cymbal_capital_sdlc.wbs_benchmarks`). Do not use ungrounded T-shirt sizing.

| Component module | Complexity tier | Backend man-days | DB / data man-days | Frontend man-days | QA / UAT man-days | Total man-days | Benchmark reference |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `<Module Name>` | `LOW / MEDIUM / HIGH` | `0.0` | `0.0` | `0.0` | `0.0` | `0.0` | `BQ: wbs_benchmarks` |

## 5. Boundary UAT verification matrix

Verify every financial calculation against at least 100 boundary test cases covering:

- Zero and negative loan principals or tenures.
- Exact spread between nominal ROI (`14.50%`) and all-inclusive APR (`15.93%`) under upfront fee deductions.
- Cooling-off period transitions at the 6-day vs. 7-day tenure boundary.
- Leap-year daily APR interest calculation (`366` days vs. `365` days).
- Compounding penal interest rejection and `24.00%` vs. `24.01%` penal charge cap boundaries.
- SME credit policy DSCR escalation boundaries (`1.14x` reject, `1.15x–1.24x` Zonal Credit Head escalation, `>= 1.25x` auto-approve) and LTV cap (`75.00%` vs. `75.01%`).
