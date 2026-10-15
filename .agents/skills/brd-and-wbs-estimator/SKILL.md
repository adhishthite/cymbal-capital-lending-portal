---
name: brd-and-wbs-estimator
description: Audit unstructured lending meeting notes against RBI Digital Lending KFS, APR, cooling-off, and penal charge rules, flag compliance gaps, and produce a structured BRD and Backend/DB/Frontend/QA man-day WBS table grounded in BigQuery cymbal_capital_sdlc.wbs_benchmarks. Use when converting stakeholder notes, voice transcripts, or product proposals into an RBI-compliant BRD and engineering effort estimate.
---

# BRD and BigQuery WBS estimator

Convert raw stakeholder meeting notes into an RBI-compliant Business Requirements Document (BRD) and a deterministic Work Breakdown Structure (WBS) grounded in BigQuery historical benchmarks.

## Workflow steps

Follow these steps in order until every compliance gap is remediated and every module has a BigQuery-backed man-day estimate:

1. **Sanitize PII before analysis:** Inspect raw meeting notes with `app/services/gcp_dlp_armor.py` (`inspect_and_redact_pii`) so no unmasked PAN, Aadhaar, or bank account numbers enter logs or model prompts.
2. **Audit against RBI Digital Lending rules:** Cross-check the notes against [`0-spec/RBI_COMPLIANCE_CHECKLIST.md`](../../../0-spec/RBI_COMPLIANCE_CHECKLIST.md) and flag violations across the four mandatory gates:
   - **Gate `RBI-KFS-01` (All-Inclusive APR):** Flag any proposal that quotes only a nominal interest rate or hides processing, documentation, or insurance fees outside the APR calculation.
   - **Gate `RBI-KFS-02` (Cooling-Off Period):** Flag any proposal that omits the cooling-off period, sets a window under 3 calendar days for loans with tenure $\ge 7$ days, or charges a prepayment fee during the cooling-off window.
   - **Gate `RBI-PEN-03` (Penal Charges vs. Penal Interest):** Flag any proposal that compounds late payment interest into principal or applies penal rates above `24.0%` p.a. on the overdue installment.
   - **Gate `RBI-DLG-04` (Direct Disbursement & PII Protection):** Flag any proposal that routes loan proceeds through a third-party LSP nodal account or logs raw PAN/Aadhaar identifiers.
3. **Query BigQuery WBS benchmarks:** Query `adhish-base-project-1.cymbal_capital_sdlc.wbs_benchmarks` via `app/services/bq_telemetry.py` (`get_wbs_benchmarks`) to retrieve historical man-day effort across `backend_days`, `db_days`, `frontend_days`, and `qa_days`.
4. **Generate the structured BRD and WBS table:** Format the output using [`0-spec/BRD_TEMPLATE.md`](../../../0-spec/BRD_TEMPLATE.md), embedding:
   - A table of detected RBI compliance gaps with exact circular citations and mandatory remediations.
   - A component-by-component WBS table showing `Backend`, `DB`, `Frontend`, `QA`, and `Total Man-Days` alongside the `P80` risk buffer.
   - A ready-to-create GitHub Issue payload linked to milestone `Sprint 24 - SME Digital Lending Compliance`.

## Completion criteria

The output is complete only when:
- All four RBI compliance gates (`RBI-KFS-01` through `RBI-DLG-04`) are explicitly evaluated with pass/fail status and statutory citations.
- Every WBS line item maps to a benchmark row in `cymbal_capital_sdlc.wbs_benchmarks` with exact `Backend`, `DB`, `Frontend`, and `QA` man-days summed deterministically.
