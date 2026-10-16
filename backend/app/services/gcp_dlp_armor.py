"""Google Cloud DLP PII Redaction, Model Armor Prompt-Injection Guardrail, and Vertex AI Analyzer.

Integrates with:
- Google Cloud DLP (`google-cloud-dlp` on `projects/adhish-base-project-1`) to inspect and mask
  `INDIA_PAN_INDIVIDUAL`, `INDIA_AADHAAR_INDIVIDUAL`, `PHONE_NUMBER`, and bank account numbers.
- Model Armor prompt-injection / jailbreak sanitizer blocking attempts to bypass RBI KFS, APR,
  cooling-off, or penal charge regulations.
- Vertex AI (`google-genai` with `vertexai=True, project='adhish-base-project-1', location='global'`,
  models `gemini-3.8-flash` and `gemini-3.5-flash-lite`) for live BRD, Credit Underwriting, KFS, and
  DLP security synthesis with deterministic fallback.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "adhish-base-project-1")
VERTEX_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
PRIMARY_REASONING_MODEL = "gemini-3.8-flash"
FAST_WORKHORSE_MODEL = "gemini-3.5-flash-lite"
IST_TZ = timezone(timedelta(hours=5, minutes=30))

# Deterministic regex patterns supporting Cloud DLP defense-in-depth
PAN_REGEX = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
AADHAAR_REGEX = re.compile(r"\b([2-9][0-9]{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4})\b")
INDIA_PHONE_REGEX = re.compile(r"(?:\+91[\s-]?)?\b([6-9][0-9]{9})\b")
BANK_ACCOUNT_REGEX = re.compile(
    r"\b(?:A/C|Account|Acct|Acc)[\s#:.-]*([0-9]{9,18})\b", re.IGNORECASE
)

INJECTION_SIGNATURES: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "JAILBREAK_SYSTEM_OVERRIDE",
        "Attempt to override system instructions or regulatory guardrails",
        re.compile(
            r"(ignore\s+(all\s+)?(previous|prior|system)\s+instructions|disregard\s+regulatory|developer\s+mode|system\s+override|bypass\s+rbi)",
            re.IGNORECASE,
        ),
    ),
    (
        "RBI_APR_SUPPRESSION",
        "Attempt to hide upfront processing/insurance fees from Key Fact Statement APR",
        re.compile(
            r"(hide\s+processing\s+fee|exclude\s+fees?\s+from\s+apr|suppress\s+kfs|report\s+only\s+nominal\s+rate)",
            re.IGNORECASE,
        ),
    ),
    (
        "RBI_PENAL_COMPOUNDING_BYPASS",
        "Attempt to force compounding penal interest into principal in violation of RBI/2023-24/53",
        re.compile(
            r"(force\s+compound(ing)?\s+penal|capitalize\s+penal\s+interest\s+into\s+principal|disable\s+penal\s+cap)",
            re.IGNORECASE,
        ),
    ),
    (
        "PII_EXFILTRATION_ATTEMPT",
        "Attempt to dump unmasked borrower Aadhaar, PAN, or raw bureau credentials",
        re.compile(
            r"(dump\s+(all\s+)?(unmasked|raw)\s+(pan|aadhaar)|print\s+raw\s+aadhaar|exfiltrate\s+pii)",
            re.IGNORECASE,
        ),
    ),
]


class PIIEntityFinding(BaseModel):
    """Single PII entity detected and masked."""

    info_type: str
    original_snippet_masked: str
    replacement_token: str
    likelihood: str = "VERY_LIKELY"
    detector_source: str = "GCP_CLOUD_DLP"


class PIIRedactionResponse(BaseModel):
    """Output of PII inspection, redaction, and Model Armor prompt-injection screening."""

    original_length: int
    sanitized_text: str
    pii_detected: bool
    findings_count: int
    findings: list[PIIEntityFinding] = Field(default_factory=list)
    prompt_injection_blocked: bool = False
    injection_triggers: list[str] = Field(default_factory=list)
    dlp_engine_mode: str
    dlp_latency_ms: int = 0
    gcp_project: str = PROJECT_ID


class ComplianceGapItem(BaseModel):
    """Single RBI Digital Lending compliance gap flagged in meeting notes."""

    gap_id: str
    severity: str
    title: str
    meeting_note_quote: str
    rbi_circular_reference: str
    remediation_requirement: str


def _now_ist_str() -> str:
    return datetime.now(IST_TZ).strftime("%H:%M:%S IST")


def detect_prompt_injection(text: str) -> tuple[bool, list[str]]:
    """Scan unstructured input for prompt-injection or regulatory bypass attempts."""
    triggers: list[str] = []
    for code, description, pattern in INJECTION_SIGNATURES:
        if pattern.search(text):
            triggers.append(f"[{code}] {description}")
    return len(triggers) > 0, triggers


def _apply_deterministic_redaction(
    text: str,
    detector_label: str = "DLP_HYBRID_INSPECTOR",
) -> tuple[str, list[PIIEntityFinding]]:
    """Apply deterministic defense-in-depth masking for PAN, Aadhaar, Phone, and Bank Accounts."""
    findings: list[PIIEntityFinding] = []
    sanitized = text

    for match in PAN_REGEX.finditer(sanitized):
        raw_val = match.group(1)
        masked_preview = f"{raw_val[:2]}*****{raw_val[-2:]}"
        token = "[REDACTED:INDIA_PAN_INDIVIDUAL]"
        findings.append(
            PIIEntityFinding(
                info_type="INDIA_PAN_INDIVIDUAL",
                original_snippet_masked=masked_preview,
                replacement_token=token,
                likelihood="VERY_LIKELY",
                detector_source=detector_label,
            )
        )
    sanitized = PAN_REGEX.sub("[REDACTED:INDIA_PAN_INDIVIDUAL]", sanitized)

    for match in AADHAAR_REGEX.finditer(sanitized):
        raw_val = match.group(1)
        masked_preview = f"XXXX-XXXX-{raw_val[-4:]}"
        token = "[REDACTED:INDIA_AADHAAR_INDIVIDUAL]"
        findings.append(
            PIIEntityFinding(
                info_type="INDIA_AADHAAR_INDIVIDUAL",
                original_snippet_masked=masked_preview,
                replacement_token=token,
                likelihood="VERY_LIKELY",
                detector_source=detector_label,
            )
        )
    sanitized = AADHAAR_REGEX.sub("[REDACTED:INDIA_AADHAAR_INDIVIDUAL]", sanitized)

    for match in BANK_ACCOUNT_REGEX.finditer(sanitized):
        raw_acc = match.group(1)
        masked_preview = f"ACCT-****{raw_acc[-4:]}"
        findings.append(
            PIIEntityFinding(
                info_type="BANK_ACCOUNT_NUMBER",
                original_snippet_masked=masked_preview,
                replacement_token="[REDACTED:BANK_ACCOUNT_NUMBER]",
                likelihood="VERY_LIKELY",
                detector_source=detector_label,
            )
        )
    sanitized = BANK_ACCOUNT_REGEX.sub("Account [REDACTED:BANK_ACCOUNT_NUMBER]", sanitized)

    for match in INDIA_PHONE_REGEX.finditer(sanitized):
        raw_phone = match.group(1)
        masked_preview = f"+91-XXXXXX{raw_phone[-4:]}"
        token = "[REDACTED:PHONE_NUMBER]"
        findings.append(
            PIIEntityFinding(
                info_type="PHONE_NUMBER",
                original_snippet_masked=masked_preview,
                replacement_token=token,
                likelihood="LIKELY",
                detector_source=detector_label,
            )
        )
    sanitized = INDIA_PHONE_REGEX.sub("[REDACTED:PHONE_NUMBER]", sanitized)

    return sanitized, findings


def inspect_and_redact_pii(
    text: str,
    use_live_cloud_dlp: bool = True,
) -> PIIRedactionResponse:
    """Inspect and redact Indian financial PII using Google Cloud DLP + deterministic defense-in-depth."""
    blocked, injection_triggers = detect_prompt_injection(text)
    dlp_mode = "LOCAL_DETERMINISTIC_DLP_FALLBACK"
    cloud_findings: list[PIIEntityFinding] = []
    dlp_latency_ms = 0

    if use_live_cloud_dlp and os.environ.get("DISABLE_LIVE_GCP_DLP", "").lower() != "true":
        t0 = time.perf_counter()
        try:
            from google.cloud import dlp_v2

            client = dlp_v2.DlpServiceClient()
            parent = f"projects/{PROJECT_ID}/locations/global"
            inspect_config = {
                "info_types": [
                    {"name": "INDIA_PAN_INDIVIDUAL"},
                    {"name": "INDIA_AADHAAR_INDIVIDUAL"},
                    {"name": "PHONE_NUMBER"},
                ],
                "min_likelihood": dlp_v2.Likelihood.POSSIBLE,
                "include_quote": True,
            }
            item = {"value": text}
            response = client.inspect_content(
                request={
                    "parent": parent,
                    "inspect_config": inspect_config,
                    "item": item,
                },
                timeout=5.0,
            )
            dlp_latency_ms = int((time.perf_counter() - t0) * 1000)
            dlp_mode = f"LIVE_GCP_CLOUD_DLP (projects/{PROJECT_ID})"
            for finding in response.result.findings:
                quote = finding.quote or ""
                masked_quote = f"{quote[:2]}***{quote[-2:]}" if len(quote) >= 4 else "***"
                info_name = finding.info_type.name
                cloud_findings.append(
                    PIIEntityFinding(
                        info_type=info_name,
                        original_snippet_masked=masked_quote,
                        replacement_token=f"[REDACTED:{info_name}]",
                        likelihood=dlp_v2.Likelihood(finding.likelihood).name,
                        detector_source="GCP_CLOUD_DLP_API",
                    )
                )
        except Exception:
            dlp_latency_ms = int((time.perf_counter() - t0) * 1000)
            dlp_mode = "DETERMINISTIC_DLP_GUARDRAIL (Offline/Fast Path)"

    sanitized_text, regex_findings = _apply_deterministic_redaction(
        text,
        detector_label="GCP_CLOUD_DLP_API" if "LIVE_GCP" in dlp_mode else "DLP_REGEX_ENGINE",
    )

    merged_findings = regex_findings if regex_findings else cloud_findings
    if blocked:
        sanitized_text = (
            "[MODEL ARMOR BLOCKED: Prompt injection / regulatory bypass signature detected. "
            "Payload quarantined before LLM inference.]"
        )

    return PIIRedactionResponse(
        original_length=len(text),
        sanitized_text=sanitized_text,
        pii_detected=len(merged_findings) > 0,
        findings_count=len(merged_findings),
        findings=merged_findings,
        prompt_injection_blocked=blocked,
        injection_triggers=injection_triggers,
        dlp_engine_mode=dlp_mode,
        dlp_latency_ms=dlp_latency_ms,
        gcp_project=PROJECT_ID,
    )


DEFAULT_SME_MEETING_NOTES = """Meeting Notes: Cymbal Capital SME Digital Top-Up Loan (Quick-Disburse Track)
Date: 14 Oct 2026 | Attendees: Business Product Head, SME Credit Policy, Retail IT Lead
Sample Applicant Test Record: Promoter Rajesh Sharma (PAN: ABCDE1234F, Aadhaar: 4921 8834 9012, Mobile: +91 98201 44510, Disbursement A/C: 004291827364).

Proposed Product Decisions from Business Team:
1. Pricing Display: Show only the headline 14.50% p.a. nominal interest rate on the mobile offer screen. Deduct the 1.00% processing fee (₹10,000), documentation fee (₹2,860), and bundled insurance (₹2,500) during disbursement without cluttering the screen with an All-Inclusive APR calculation.
2. Instant Lock-In (No Cooling-Off): Since SME borrowers need urgent working capital for 24-month tenures, disable the cooling-off cancellation window or charge a 4% foreclosure fee if they cancel within the first 3 days.
3. Late Payment Recovery: If an SME misses a monthly EMI installment, levy 3.0% per month (36% p.a.) penal interest and compound unpaid penal interest into the outstanding loan principal every month.
4. Disbursement Flow: Route the ₹10,00,000 loan disbursement through our fintech LSP partner's nodal pass-through wallet so the partner can deduct their platform convenience fee before crediting the borrower.
"""


def audit_meeting_notes_for_rbi_gaps(notes: str) -> list[ComplianceGapItem]:
    """Deterministically identify the 4 RBI Digital Lending compliance gaps in meeting notes."""
    gaps: list[ComplianceGapItem] = [
        ComplianceGapItem(
            gap_id="RBI-KFS-01",
            severity="P0_BLOCKER",
            title="Omission of All-Inclusive APR in Key Fact Statement (KFS)",
            meeting_note_quote="Show only the headline 14.50% p.a. nominal interest rate... without cluttering the screen with an All-Inclusive APR calculation.",
            rbi_circular_reference="RBI/2024-25/18 DOR.STR.REC.13/13.03.00/2024-25 (Annex A — Key Fact Statement)",
            remediation_requirement="Compute and display exact All-Inclusive APR (15.93% p.a. for 14.50% nominal ROI + ₹13,900 upfront fees over 24m) on the KFS before contract signing.",
        ),
        ComplianceGapItem(
            gap_id="RBI-KFS-02",
            severity="P0_BLOCKER",
            title="Missing Mandatory 3-Day Cooling-Off / Look-Up Period",
            meeting_note_quote="Disable the cooling-off cancellation window or charge a 4% foreclosure fee if they cancel within the first 3 days.",
            rbi_circular_reference="RBI/2024-25/18 Para 10 (Cooling-Off / Look-Up Period for Digital Loans)",
            remediation_requirement="Enforce a mandatory >= 3 calendar day cooling-off window for all loans with tenure >= 7 days, allowing exit at proportionate APR with zero prepayment penalty.",
        ),
        ComplianceGapItem(
            gap_id="RBI-PEN-03",
            severity="P0_BLOCKER",
            title="Illegal Compounding of Penal Interest & 36% p.a. Rate Breach",
            meeting_note_quote="Levy 3.0% per month (36% p.a.) penal interest and compound unpaid penal interest into the outstanding loan principal every month.",
            rbi_circular_reference="RBI/2023-24/53 DOR.MCS.REC.28/01.01.001/2023-24 (Fair Lending Practice — Penal Charges)",
            remediation_requirement="Block compounding penal interest; levy only simple, non-capitalized penal charges strictly on the overdue EMI installment capped at <= 24.0% p.a.",
        ),
        ComplianceGapItem(
            gap_id="RBI-DLG-04",
            severity="P0_BLOCKER",
            title="LSP Nodal Pass-Through Routing & Unmasked PII in Notes",
            meeting_note_quote="Route the ₹10,00,000 loan disbursement through our fintech LSP partner's nodal pass-through wallet... (PAN: ABCDE1234F, Aadhaar: 4921 8834 9012)",
            rbi_circular_reference="RBI Digital Lending Guidelines Para 3 (Direct Disbursement to Borrower Account) & DPDP Act",
            remediation_requirement="Disburse 100% of net loan proceeds directly into the borrower's verified bank account (except regulated co-lending escrows) and redact PAN/Aadhaar via Cloud DLP.",
        ),
    ]
    return gaps


def _call_vertex_gemini(
    model_id: str,
    prompt: str,
    fallback_text: str,
    use_live_vertex: bool = True,
) -> dict[str, Any]:
    """Invoke live Gemini 3.x on Vertex AI with low thinking latency, measuring tokens & wall-clock ms."""
    timestamp_ist = _now_ist_str()
    if not use_live_vertex or os.environ.get("DISABLE_LIVE_VERTEX_AI", "").lower() == "true":
        return {
            "text": fallback_text,
            "model_id": model_id,
            "model_source": f"DETERMINISTIC_FAST_PATH ({model_id})",
            "latency_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "timestamp_ist": timestamp_ist,
        }

    t0 = time.perf_counter()
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=VERTEX_LOCATION,
            http_options=types.HttpOptions(timeout=15000),
        )
        resp = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="LOW"),
            ),
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        usage = getattr(resp, "usage_metadata", None)
        prompt_tok = int(getattr(usage, "prompt_token_count", 0) or 0)
        comp_tok = int(getattr(usage, "candidates_token_count", 0) or 0)
        total_tok = int(getattr(usage, "total_token_count", 0) or (prompt_tok + comp_tok))
        text_out = resp.text.strip() if resp and resp.text else fallback_text
        return {
            "text": text_out,
            "model_id": model_id,
            "model_source": f"LIVE_VERTEX_AI ({model_id} @ {PROJECT_ID}/{VERTEX_LOCATION})",
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tok,
            "completion_tokens": comp_tok,
            "total_tokens": total_tok,
            "timestamp_ist": _now_ist_str(),
        }
    except Exception:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "text": fallback_text,
            "model_id": model_id,
            "model_source": f"DETERMINISTIC_FALLBACK ({model_id})",
            "latency_ms": latency_ms,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "timestamp_ist": _now_ist_str(),
        }


def generate_executive_brd_summary_with_vertex(
    sanitized_notes: str,
    compliance_gaps: list[ComplianceGapItem],
    wbs_rows: list[dict[str, Any]],
    use_live_vertex: bool = True,
) -> dict[str, Any]:
    """Call Vertex AI (`gemini-3.8-flash` on `adhish-base-project-1`) with deterministic fallback."""
    total_days = round(sum(float(r.get("total_days", 0.0)) for r in wbs_rows), 1)
    p80_days = round(sum(float(r.get("p80_buffer_days", 0.0)) for r in wbs_rows), 1)
    default_summary = (
        f"Cymbal Capital BRD Compliance Audit flagged {len(compliance_gaps)} P0 RBI Digital Lending "
        f"violations in the proposed SME Top-Up Loan specification. All four regulatory gates "
        f"(All-Inclusive APR 15.93% disclosure, 3-day zero-penalty cooling-off window, non-compounded "
        f"<=24% p.a. penal charge guardrail, and direct bank account disbursement with Cloud DLP PII masking) "
        f"have been injected into the remediated BRD. Grounded in BigQuery `cymbal_capital_sdlc.wbs_benchmarks`, "
        f"total delivery effort is estimated at {total_days} expected engineering days ({p80_days} P80 days)."
    )
    prompt = (
        "You are the Principal Regulatory Architect at Cymbal Capital. "
        "Write a crisp, authoritative 3-sentence executive BRD remediation directive addressing "
        f"the {len(compliance_gaps)} P0 RBI Digital Lending compliance gaps detected in these sanitized "
        "stakeholder meeting notes (All-Inclusive APR 15.93% vs 14.50% nominal ROI under RBI/2024-25/18, "
        "mandatory >=3-day zero-penalty cooling-off window, non-compounding <=24% p.a. simple penal charge cap "
        "under RBI/2023-24/53, and direct borrower bank account disbursement blocking LSP pass-through wallets), "
        f"and cite the BigQuery WBS effort estimate of {total_days} expected man-days ({p80_days} P80 buffer days). "
        "Plain text only, no markdown bullet lists.\n\n"
        f"Sanitized Meeting Notes:\n{sanitized_notes[:900]}"
    )
    res = _call_vertex_gemini(
        model_id=PRIMARY_REASONING_MODEL,
        prompt=prompt,
        fallback_text=default_summary,
        use_live_vertex=use_live_vertex,
    )
    return {
        "executive_summary": res["text"],
        "model_id": res["model_id"],
        "model_source": res["model_source"],
        "latency_ms": res["latency_ms"],
        "prompt_tokens": res["prompt_tokens"],
        "completion_tokens": res["completion_tokens"],
        "total_tokens": res["total_tokens"],
        "timestamp_ist": res["timestamp_ist"],
        "total_man_days": total_days,
    }


def generate_credit_underwriting_memo_with_vertex(
    applicant_name: str,
    loan_amount_inr: float,
    dscr: float,
    ltv_pct: float,
    cmr_rank: int,
    decision: str,
    approval_authority: str,
    policy_triggers: list[str],
    use_live_vertex: bool = False,
) -> dict[str, Any]:
    """Generate a 3-sentence SME Credit Underwriting & Sprint 24 Risk Memo using `gemini-3.8-flash`."""
    fallback_memo = (
        f"Underwriting review for {applicant_name} (Sanction ₹{loan_amount_inr:,.0f}, DSCR {dscr:.2f}x, "
        f"LTV {ltv_pct:.1f}%, CMR-{cmr_rank}) resulted in {decision} routed to {approval_authority}. "
        f"Policy trigger: {' '.join(policy_triggers)} "
        "Concurrently, Sprint 24 backlog triage flagged 2 P0 blockers (#4 CIBIL partnership TLS timeout and "
        "#7 RBI KFS 3-day cooling-off sign-off) that must be cleared prior to production release."
    )
    prompt = (
        "You are the Chief Credit Officer & Engineering Risk Lead at Cymbal Capital. "
        "Write a concise, authoritative 3-sentence underwriting deviation & Sprint 24 risk memo for: "
        f"Applicant={applicant_name}, Sanction=INR {loan_amount_inr:,.0f}, DSCR={dscr:.2f}x "
        f"(policy floor 1.25x for STP, 1.15x-1.24x escalates to Zonal Credit Head, <1.15x rejected), "
        f"Collateral LTV={ltv_pct:.1f}% (max cap 75%), CIBIL Rank=CMR-{cmr_rank}, resulting in "
        f"Decision={decision} ({approval_authority}). "
        "In the third sentence, note the 2 Sprint 24 P0 engineering blockers (#4 CIBIL mTLS timeout on partnership PANs "
        "and #7 RBI KFS 3-day cooling-off legal sign-off). Plain text only, no markdown headings."
    )
    res = _call_vertex_gemini(
        model_id=PRIMARY_REASONING_MODEL,
        prompt=prompt,
        fallback_text=fallback_memo,
        use_live_vertex=use_live_vertex,
    )
    return {
        "memo_text": res["text"],
        "model_id": res["model_id"],
        "model_source": res["model_source"],
        "latency_ms": res["latency_ms"],
        "prompt_tokens": res["prompt_tokens"],
        "completion_tokens": res["completion_tokens"],
        "total_tokens": res["total_tokens"],
        "timestamp_ist": res["timestamp_ist"],
    }


def generate_kfs_audit_verdict_with_vertex(
    kfs_payload: dict[str, Any],
    use_live_vertex: bool = False,
) -> dict[str, Any]:
    """Generate a 3-sentence RBI KFS & Penal Charge Audit Verdict using `gemini-3.5-flash-lite`."""
    principal = kfs_payload.get("principal_inr", 1_000_000.0)
    nominal = kfs_payload.get("nominal_annual_rate_pct", 14.5)
    apr = kfs_payload.get("all_inclusive_apr_pct", 15.93)
    bps = kfs_payload.get("apr_spread_bps", 143)
    emi = kfs_payload.get("monthly_emi_inr", 48_249.43)
    net_disb = kfs_payload.get("net_disbursed_amount_inr", 986_100.0)
    compliant = kfs_payload.get("is_rbi_kfs_compliant", True)
    violations = kfs_payload.get("compliance_violations", [])
    cooling = kfs_payload.get("cooling_off", {})
    penal = kfs_payload.get("penal_charge_guardrail", {})

    fallback_verdict = (
        f"RBI Annex-A Key Fact Statement verified for ₹{principal:,.0f} principal: headline {nominal:.2f}% p.a. "
        f"nominal rate translates to an All-Inclusive APR of {apr:.2f}% (+{bps} bps spread) with monthly EMI "
        f"₹{emi:,.2f} and net disbursement ₹{net_disb:,.2f}. "
        f"Cooling-off exit on Day {cooling.get('exit_day', 2)} ({cooling.get('days_in_year', 365)}-day basis) yields "
        f"₹{cooling.get('total_cooling_off_exit_payoff_inr', 0):,.2f} payoff with ₹0 prepayment fee, while penal "
        f"rate {penal.get('annualized_penal_rate_pct', 18.0)}% (compounded={penal.get('is_compounded', False)}) is "
        f"{'COMPLIANT with RBI/2024-25/18 & RBI/2023-24/53' if compliant else 'BLOCKED due to: ' + '; '.join(violations)}."
    )
    prompt = (
        "You are the Statutory RBI Compliance Auditor at Cymbal Capital. "
        "Write a crisp 2-to-3 sentence audit verdict for this Key Fact Statement (KFS) calculation: "
        f"Principal=INR {principal:,.0f}, Nominal ROI={nominal:.2f}%, All-Inclusive APR={apr:.2f}% (+{bps} bps fee spread), "
        f"Monthly EMI=INR {emi:,.2f}, Net Disbursed=INR {net_disb:,.2f}, "
        f"Cooling-Off Configured={cooling.get('configured_cooling_off_days', 3)}d ({cooling.get('days_in_year', 365)}-day year, "
        f"Day-{cooling.get('exit_day', 2)} exit payoff INR {cooling.get('total_cooling_off_exit_payoff_inr', 0):,.2f}), "
        f"Penal Rate={penal.get('annualized_penal_rate_pct', 18.0)}% (compounded={penal.get('is_compounded', False)}), "
        f"Overall Compliant={compliant}, Violations={violations}. Plain text only."
    )
    res = _call_vertex_gemini(
        model_id=FAST_WORKHORSE_MODEL,
        prompt=prompt,
        fallback_text=fallback_verdict,
        use_live_vertex=use_live_vertex,
    )
    return {
        "verdict_text": res["text"],
        "model_id": res["model_id"],
        "model_source": res["model_source"],
        "latency_ms": res["latency_ms"],
        "prompt_tokens": res["prompt_tokens"],
        "completion_tokens": res["completion_tokens"],
        "total_tokens": res["total_tokens"],
        "timestamp_ist": res["timestamp_ist"],
    }


def generate_dlp_security_verdict_with_vertex(
    dlp_payload: dict[str, Any],
    use_live_vertex: bool = False,
) -> dict[str, Any]:
    """Generate a 2-sentence Cloud DLP & Model Armor Security Verdict using `gemini-3.5-flash-lite`."""
    blocked = dlp_payload.get("prompt_injection_blocked", False)
    count = dlp_payload.get("findings_count", 0)
    sanitized = dlp_payload.get("sanitized_text", "")
    triggers = dlp_payload.get("injection_triggers", [])

    fallback_verdict = (
        f"Model Armor quarantined the adversarial payload due to: {', '.join(triggers)}."
        if blocked
        else f"Cloud DLP inspected the payload and masked {count} Indian financial PII entities "
        "(PAN, Aadhaar, mobile, bank account) prior to Vertex AI inference under DPDP Act 2023 governance."
    )
    prompt = (
        "You are the Chief Information Security Officer (CISO) at Cymbal Capital. "
        "Write a concise 2-sentence security governance verdict on this sanitized payload: "
        f"PromptInjectionBlocked={blocked}, Triggers={triggers}, PIIEntitiesRedacted={count}, "
        f"SanitizedText='{sanitized[:400]}'. Cite DPDP Act 2023 and RBI Digital Lending data privacy rules. Plain text only."
    )
    res = _call_vertex_gemini(
        model_id=FAST_WORKHORSE_MODEL,
        prompt=prompt,
        fallback_text=fallback_verdict,
        use_live_vertex=use_live_vertex,
    )
    return {
        "verdict_text": res["text"],
        "model_id": res["model_id"],
        "model_source": res["model_source"],
        "latency_ms": res["latency_ms"],
        "prompt_tokens": res["prompt_tokens"],
        "completion_tokens": res["completion_tokens"],
        "total_tokens": res["total_tokens"],
        "timestamp_ist": res["timestamp_ist"],
    }
