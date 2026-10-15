# RBI digital lending and KFS compliance checklist

This checklist defines the mandatory verification rules enforced across Cymbal Capital digital lending services, requirement reviews, and automated UAT suites.

<!-- prettier-ignore -->
> [!WARNING]
> Any BRD, pull request, or release candidate that fails a P0 checklist item below is blocked from production deployment.

## 1. Key Fact Statement (KFS) and APR transparency

Verify that the loan origination and KFS microservice computes and discloses the exact all-inclusive cost of credit to the borrower.

- [x] **All-inclusive APR solver (`RBI-KFS-01`):** Compute APR using an iterative Newton-Raphson / binary-search Internal Rate of Return (IRR) solver on net disbursed cash flows (`Principal - Processing Fee - Documentation Charges - Insurance Premium`).
- [x] **Itemized fee disclosure:** Display nominal interest rate, upfront processing fee, documentation fee, and bundled insurance charges as separate line items on the KFS PDF and web screen.
- [x] **Zero hidden charges:** Prohibit charging any fee or recovery cost to the borrower that is not explicitly itemized in the signed KFS.

## 2. Cooling-off / look-up period governance

Ensure borrowers can exit digital loans within the statutory look-up window without penalty.

- [x] **Minimum 3-day window (`RBI-KFS-02`):** Enforce a cooling-off period of at least 3 calendar days for all digital loans with a tenure of 7 days or more (and at least 1 calendar day for tenures under 7 days).
- [x] **Zero foreclosure penalty during cooling-off:** Waive 100% of prepayment and foreclosure charges when a borrower cancels the loan within the active cooling-off window.
- [x] **Proportionate APR payoff math:** Calculate the exact exit payoff as `Principal + (Principal * All_Inclusive_APR * Days_Held / Days_In_Year) - Upfront_Fees_Refund_Adjustment`.

## 3. Fair lending practice — penal charges in loan accounts

Enforce the RBI prohibition on punitive, capitalized penal interest across all retail and SME loan products.

- [x] **No compounding of penalties (`RBI-PEN-03`):** Reject any loan product configuration where `is_compounded = true` or where unpaid late fees are capitalized into the interest-bearing principal balance.
- [x] **Overdue installment basis:** Calculate penal charges strictly on the overdue EMI installment amount, never on the total outstanding loan principal.
- [x] **Statutory ceiling (`<= 24.0%` p.a.):** Cap annualized penal charges at `24.0%` p.a. equivalent on the overdue installment amount.

## 4. SME underwriting, PII redaction, and AI governance

Protect borrower Personally Identifiable Information (PII) and enforce deterministic credit escalation thresholds.

- [x] **Cloud DLP PII masking (`RBI-DLG-04`):** Inspect and mask `INDIA_PAN_INDIVIDUAL`, `INDIA_AADHAAR_INDIVIDUAL`, `PHONE_NUMBER`, and bank account numbers using Google Cloud DLP (`projects/adhish-base-project-1`) before sending unstructured text to Vertex AI models or writing application logs.
- [x] **Prompt injection & jailbreak defense:** Block instructions attempting to override RBI APR math, waive cooling-off periods, or bypass credit policy limits.
- [x] **SME DSCR & LTV policy guardrails:**
  - Reject applications with `DSCR < 1.15x` or `LTV > 75.0%`.
  - Escalate applications with `1.15x <= DSCR < 1.25x` (such as `1.18x`) to the **Zonal Credit Head** with mandatory collateral and GSTIN velocity verification.
  - Approve standard applications with `DSCR >= 1.25x` and `LTV <= 75.0%`.
