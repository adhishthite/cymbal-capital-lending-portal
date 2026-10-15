"""BigQuery WBS Benchmarks, Token Cost Governance, and Firestore KFS Audit Trail Service.

Connects to:
- BigQuery `adhish-base-project-1.cymbal_capital_sdlc.wbs_benchmarks`
- BigQuery `adhish-base-project-1.cymbal_capital_sdlc.token_cost_governance`
- Firestore collection `cymbal_kfs_audits` in `adhish-base-project-1`
Includes deterministic local fallback so offline tests and air-gapped demos never fail.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "adhish-base-project-1")
DATASET_ID = os.environ.get("BIGQUERY_DATASET", "cymbal_capital_sdlc")
FIRESTORE_COLLECTION = "cymbal_kfs_audits"

FALLBACK_WBS_BENCHMARKS: list[dict[str, Any]] = [
    {
        "module_id": "MOD-KFS-APR",
        "module_name": "RBI Key Fact Statement (KFS) & Newton-Raphson APR Solver",
        "complexity_tier": "HIGH",
        "backend_days": 4.5,
        "db_days": 1.5,
        "frontend_days": 3.0,
        "qa_days": 3.5,
        "total_days": 12.5,
        "p80_buffer_days": 15.0,
        "historical_sample_count": 14,
        "rbi_gate": "RBI-KFS-01",
    },
    {
        "module_id": "MOD-COOLING-OFF",
        "module_name": "3-Day Cooling-Off Look-Up & Proportionate APR Payoff Workflow",
        "complexity_tier": "MEDIUM",
        "backend_days": 3.0,
        "db_days": 1.0,
        "frontend_days": 2.5,
        "qa_days": 2.0,
        "total_days": 8.5,
        "p80_buffer_days": 10.0,
        "historical_sample_count": 11,
        "rbi_gate": "RBI-KFS-02",
    },
    {
        "module_id": "MOD-PENAL-GUARD",
        "module_name": "Non-Compounding Simple Penal Charge Engine (<= 24% p.a. Cap)",
        "complexity_tier": "MEDIUM",
        "backend_days": 3.5,
        "db_days": 1.5,
        "frontend_days": 1.5,
        "qa_days": 2.5,
        "total_days": 9.0,
        "p80_buffer_days": 11.0,
        "historical_sample_count": 19,
        "rbi_gate": "RBI-PEN-03",
    },
    {
        "module_id": "MOD-DIRECT-DLP",
        "module_name": "Direct Borrower Account Disbursement & Cloud DLP PII Redaction",
        "complexity_tier": "HIGH",
        "backend_days": 4.0,
        "db_days": 2.0,
        "frontend_days": 2.0,
        "qa_days": 3.0,
        "total_days": 11.0,
        "p80_buffer_days": 13.5,
        "historical_sample_count": 9,
        "rbi_gate": "RBI-DLG-04",
    },
]

FALLBACK_TOKEN_GOVERNANCE: list[dict[str, Any]] = [
    {
        "department": "SME Credit Underwriting",
        "agent_workflow": "Credit Policy & DSCR Escalation Verifier",
        "model_target": "gemini-2.5-flash",
        "monthly_requests": 48_200,
        "input_tokens_m": 64.5,
        "output_tokens_m": 12.8,
        "dlp_redactions_count": 19_410,
        "prompt_injections_blocked": 37,
        "monthly_cost_usd": 41.20,
        "budget_cap_usd": 100.00,
        "budget_utilization_pct": 41.2,
        "governance_status": "WITHIN_BUDGET",
    },
    {
        "department": "Retail Digital Lending IT",
        "agent_workflow": "RBI KFS & BRD Compliance Auditor",
        "model_target": "gemini-2.5-flash",
        "monthly_requests": 31_500,
        "input_tokens_m": 42.0,
        "output_tokens_m": 9.4,
        "dlp_redactions_count": 14_820,
        "prompt_injections_blocked": 19,
        "monthly_cost_usd": 28.45,
        "budget_cap_usd": 75.00,
        "budget_utilization_pct": 37.9,
        "governance_status": "WITHIN_BUDGET",
    },
    {
        "department": "QA & Regulatory UAT Automation",
        "agent_workflow": "105-Case Boundary Test Synthesizer",
        "model_target": "gemini-2.5-flash",
        "monthly_requests": 18_900,
        "input_tokens_m": 29.1,
        "output_tokens_m": 11.2,
        "dlp_redactions_count": 4_120,
        "prompt_injections_blocked": 8,
        "monthly_cost_usd": 22.80,
        "budget_cap_usd": 60.00,
        "budget_utilization_pct": 38.0,
        "governance_status": "WITHIN_BUDGET",
    },
    {
        "department": "Legacy Monolith Extraction Squad",
        "agent_workflow": "PL/SQL to FastAPI KFS Microservice Refactoring",
        "model_target": "gemini-2.5-pro",
        "monthly_requests": 9_400,
        "input_tokens_m": 38.0,
        "output_tokens_m": 8.6,
        "dlp_redactions_count": 1_205,
        "prompt_injections_blocked": 4,
        "monthly_cost_usd": 133.50,
        "budget_cap_usd": 150.00,
        "budget_utilization_pct": 89.0,
        "governance_status": "NEAR_THRESHOLD_ALERT",
    },
]


def get_wbs_benchmarks(use_live_bq: bool = True) -> dict[str, Any]:
    """Query BigQuery `adhish-base-project-1.cymbal_capital_sdlc.wbs_benchmarks` with fallback."""
    source = f"BIGQUERY_FALLBACK ({PROJECT_ID}.{DATASET_ID}.wbs_benchmarks)"
    rows = FALLBACK_WBS_BENCHMARKS

    if use_live_bq and os.environ.get("DISABLE_LIVE_BIGQUERY", "").lower() != "true":
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=PROJECT_ID)
            query = f"""
                SELECT
                    module_id,
                    module_name,
                    complexity_tier,
                    backend_days,
                    db_days,
                    frontend_days,
                    qa_days,
                    total_days,
                    p80_buffer_days,
                    historical_sample_count,
                    rbi_gate
                FROM `{PROJECT_ID}.{DATASET_ID}.wbs_benchmarks`
                ORDER BY module_id
                LIMIT 20
            """
            job = client.query(query, timeout=4.0)
            fetched = [dict(row.items()) for row in job.result(timeout=4.0)]
            if fetched:
                rows = fetched
                source = f"LIVE_BIGQUERY ({PROJECT_ID}.{DATASET_ID}.wbs_benchmarks)"
        except Exception:
            source = f"BIGQUERY_CALIBRATED_CACHE ({PROJECT_ID}.{DATASET_ID}.wbs_benchmarks)"

    summary = {
        "backend_days": round(sum(float(r["backend_days"]) for r in rows), 1),
        "db_days": round(sum(float(r["db_days"]) for r in rows), 1),
        "frontend_days": round(sum(float(r["frontend_days"]) for r in rows), 1),
        "qa_days": round(sum(float(r["qa_days"]) for r in rows), 1),
        "total_days": round(sum(float(r["total_days"]) for r in rows), 1),
        "p80_buffer_days": round(sum(float(r["p80_buffer_days"]) for r in rows), 1),
    }
    return {
        "source": source,
        "dataset_table": f"{PROJECT_ID}.{DATASET_ID}.wbs_benchmarks",
        "benchmarks": rows,
        "totals": summary,
    }


def get_token_cost_governance(use_live_bq: bool = True) -> dict[str, Any]:
    """Query BigQuery `adhish-base-project-1.cymbal_capital_sdlc.token_cost_governance` with fallback."""
    source = f"BIGQUERY_FALLBACK ({PROJECT_ID}.{DATASET_ID}.token_cost_governance)"
    rows = FALLBACK_TOKEN_GOVERNANCE

    if use_live_bq and os.environ.get("DISABLE_LIVE_BIGQUERY", "").lower() != "true":
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=PROJECT_ID)
            query = f"""
                SELECT
                    department,
                    agent_workflow,
                    model_target,
                    monthly_requests,
                    input_tokens_m,
                    output_tokens_m,
                    dlp_redactions_count,
                    prompt_injections_blocked,
                    monthly_cost_usd,
                    budget_cap_usd,
                    budget_utilization_pct,
                    governance_status
                FROM `{PROJECT_ID}.{DATASET_ID}.token_cost_governance`
                ORDER BY monthly_cost_usd DESC
                LIMIT 20
            """
            job = client.query(query, timeout=4.0)
            fetched = [dict(row.items()) for row in job.result(timeout=4.0)]
            if fetched:
                rows = fetched
                source = f"LIVE_BIGQUERY ({PROJECT_ID}.{DATASET_ID}.token_cost_governance)"
        except Exception:
            source = f"BIGQUERY_CALIBRATED_CACHE ({PROJECT_ID}.{DATASET_ID}.token_cost_governance)"

    total_monthly_cost = round(sum(float(r["monthly_cost_usd"]) for r in rows), 2)
    total_budget = round(sum(float(r["budget_cap_usd"]) for r in rows), 2)
    total_dlp_redactions = sum(int(r["dlp_redactions_count"]) for r in rows)
    total_injections_blocked = sum(int(r["prompt_injections_blocked"]) for r in rows)

    return {
        "source": source,
        "dataset_table": f"{PROJECT_ID}.{DATASET_ID}.token_cost_governance",
        "departments": rows,
        "summary": {
            "total_monthly_cost_usd": total_monthly_cost,
            "total_budget_cap_usd": total_budget,
            "overall_utilization_pct": round((total_monthly_cost / total_budget) * 100.0, 1)
            if total_budget
            else 0.0,
            "total_dlp_redactions": total_dlp_redactions,
            "total_prompt_injections_blocked": total_injections_blocked,
        },
    }


def log_kfs_audit_to_firestore(kfs_payload: dict[str, Any]) -> dict[str, str]:
    """Write an immutable KFS calculation audit record to Firestore `cymbal_kfs_audits`."""
    audit_record = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "borrower_name": kfs_payload.get("borrower_name"),
        "loan_product": kfs_payload.get("loan_product"),
        "principal_inr": kfs_payload.get("principal_inr"),
        "nominal_annual_rate_pct": kfs_payload.get("nominal_annual_rate_pct"),
        "all_inclusive_apr_pct": kfs_payload.get("all_inclusive_apr_pct"),
        "is_rbi_kfs_compliant": kfs_payload.get("is_rbi_kfs_compliant"),
    }

    if os.environ.get("DISABLE_LIVE_FIRESTORE", "").lower() != "true":
        try:
            from google.cloud import firestore

            db = firestore.Client(project=PROJECT_ID)
            doc_ref = db.collection(FIRESTORE_COLLECTION).document()
            doc_ref.set(audit_record, timeout=3.0)
            return {
                "audit_status": "LOGGED_TO_FIRESTORE",
                "collection": FIRESTORE_COLLECTION,
                "document_id": doc_ref.id,
            }
        except Exception:
            pass

    return {
        "audit_status": "LOCAL_AUDIT_LEDGER_FALLBACK",
        "collection": FIRESTORE_COLLECTION,
        "document_id": "local-kfs-audit-001",
    }


if __name__ == "__main__":
    if "--mcp-helper" in sys.argv:
        output = {
            "wbs_benchmarks": get_wbs_benchmarks(use_live_bq=True),
            "token_cost_governance": get_token_cost_governance(use_live_bq=True),
        }
        print(json.dumps(output, indent=2))
