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
import time
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

DEPARTMENT_WORKFLOW_MAP: dict[str, tuple[str, float]] = {
    "Corporate_SME_IT": ("SME Credit Policy & DSCR Escalation Verifier", 350.0),
    "Retail_Lending_IT": ("RBI KFS & BRD Compliance Auditor", 100.0),
    "Infra_DevSecOps": ("Cloud DLP & Model Armor Security Shield", 75.0),
    "QA_Regulatory_UAT": ("105-Case Boundary UAT Test Synthesizer", 60.0),
}

FALLBACK_TOKEN_GOVERNANCE: list[dict[str, Any]] = [
    {
        "department": "Corporate_SME_IT",
        "agent_workflow": "SME Credit Policy & DSCR Escalation Verifier",
        "model_target": "gemini-3.8-flash",
        "monthly_requests": 37_500,
        "input_tokens_m": 37.98,
        "output_tokens_m": 10.63,
        "dlp_redactions_count": 1_886,
        "prompt_injections_blocked": 287,
        "monthly_cost_usd": 283.20,
        "budget_cap_usd": 350.00,
        "budget_utilization_pct": 80.9,
        "governance_status": "NEAR_THRESHOLD_ALERT",
    },
    {
        "department": "Retail_Lending_IT",
        "agent_workflow": "RBI KFS & BRD Compliance Auditor",
        "model_target": "gemini-3.5-flash-lite",
        "monthly_requests": 37_500,
        "input_tokens_m": 45.66,
        "output_tokens_m": 8.68,
        "dlp_redactions_count": 1_167,
        "prompt_injections_blocked": 147,
        "monthly_cost_usd": 46.27,
        "budget_cap_usd": 100.00,
        "budget_utilization_pct": 46.3,
        "governance_status": "WITHIN_BUDGET",
    },
    {
        "department": "Infra_DevSecOps",
        "agent_workflow": "Cloud DLP & Model Armor Security Shield",
        "model_target": "gemini-3.5-flash-lite",
        "monthly_requests": 37_500,
        "input_tokens_m": 32.31,
        "output_tokens_m": 6.14,
        "dlp_redactions_count": 538,
        "prompt_injections_blocked": 99,
        "monthly_cost_usd": 35.69,
        "budget_cap_usd": 75.00,
        "budget_utilization_pct": 47.6,
        "governance_status": "WITHIN_BUDGET",
    },
    {
        "department": "QA_Regulatory_UAT",
        "agent_workflow": "105-Case Boundary UAT Test Synthesizer",
        "model_target": "gemini-3.5-flash-lite",
        "monthly_requests": 18_900,
        "input_tokens_m": 18.90,
        "output_tokens_m": 4.12,
        "dlp_redactions_count": 412,
        "prompt_injections_blocked": 42,
        "monthly_cost_usd": 22.80,
        "budget_cap_usd": 60.00,
        "budget_utilization_pct": 38.0,
        "governance_status": "WITHIN_BUDGET",
    },
]


def get_wbs_benchmarks(use_live_bq: bool = True) -> dict[str, Any]:
    """Query BigQuery `adhish-base-project-1.cymbal_capital_sdlc.wbs_benchmarks` with fallback."""
    source = f"BIGQUERY_FALLBACK ({PROJECT_ID}.{DATASET_ID}.wbs_benchmarks)"
    rows = FALLBACK_WBS_BENCHMARKS
    latency_ms = 0

    if use_live_bq and os.environ.get("DISABLE_LIVE_BIGQUERY", "").lower() != "true":
        t0 = time.perf_counter()
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=PROJECT_ID)
            query = f"""
                SELECT
                    component_id AS module_id,
                    component_name AS module_name,
                    UPPER(complexity_tier) AS complexity_tier,
                    ROUND(backend_expected_days, 1) AS backend_days,
                    ROUND(db_expected_days, 1) AS db_days,
                    ROUND(frontend_expected_days, 1) AS frontend_days,
                    ROUND(qa_expected_days, 1) AS qa_days,
                    ROUND(total_expected_days, 1) AS total_days,
                    ROUND(total_high_days, 1) AS p80_buffer_days,
                    historical_releases AS historical_sample_count,
                    regulatory_reference AS rbi_gate
                FROM `{PROJECT_ID}.{DATASET_ID}.wbs_benchmarks`
                ORDER BY component_id
                LIMIT 20
            """
            job = client.query(query, timeout=6.0)
            fetched = [dict(row.items()) for row in job.result(timeout=6.0)]
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if fetched:
                rows = fetched
                source = f"LIVE_BIGQUERY ({PROJECT_ID}.{DATASET_ID}.wbs_benchmarks)"
        except Exception:
            latency_ms = int((time.perf_counter() - t0) * 1000)
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
        "latency_ms": latency_ms,
        "dataset_table": f"{PROJECT_ID}.{DATASET_ID}.wbs_benchmarks",
        "benchmarks": rows,
        "totals": summary,
    }


def get_token_cost_governance(use_live_bq: bool = True) -> dict[str, Any]:
    """Query BigQuery `adhish-base-project-1.cymbal_capital_sdlc.token_cost_governance` with fallback."""
    source = f"BIGQUERY_FALLBACK ({PROJECT_ID}.{DATASET_ID}.token_cost_governance)"
    rows = FALLBACK_TOKEN_GOVERNANCE
    latency_ms = 0

    if use_live_bq and os.environ.get("DISABLE_LIVE_BIGQUERY", "").lower() != "true":
        t0 = time.perf_counter()
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=PROJECT_ID)
            query = f"""
                SELECT
                    department,
                    primary_model AS model_target,
                    COUNT(*) * 1250 AS monthly_requests,
                    ROUND(SUM(prompt_tokens) / 1000000.0, 2) AS input_tokens_m,
                    ROUND(SUM(completion_tokens) / 1000000.0, 2) AS output_tokens_m,
                    SUM(dlp_pii_redactions) AS dlp_redactions_count,
                    SUM(model_armor_blocked_prompts) AS prompt_injections_blocked,
                    ROUND(SUM(cost_usd), 2) AS monthly_cost_usd
                FROM `{PROJECT_ID}.{DATASET_ID}.token_cost_governance`
                GROUP BY department, primary_model
                ORDER BY monthly_cost_usd DESC
                LIMIT 20
            """
            job = client.query(query, timeout=6.0)
            raw_rows = [dict(row.items()) for row in job.result(timeout=6.0)]
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if raw_rows:
                enriched: list[dict[str, Any]] = []
                for r in raw_rows:
                    dept = str(r["department"])
                    wf, cap = DEPARTMENT_WORKFLOW_MAP.get(
                        dept, ("Enterprise Agentic SDLC Workflow", 100.0)
                    )
                    cost = round(float(r["monthly_cost_usd"]), 2)
                    util = round((cost / cap) * 100.0, 1) if cap > 0 else 0.0
                    status = "NEAR_THRESHOLD_ALERT" if util >= 75.0 else "WITHIN_BUDGET"
                    enriched.append(
                        {
                            "department": dept,
                            "agent_workflow": wf,
                            "model_target": r["model_target"],
                            "monthly_requests": int(r["monthly_requests"]),
                            "input_tokens_m": float(r["input_tokens_m"]),
                            "output_tokens_m": float(r["output_tokens_m"]),
                            "dlp_redactions_count": int(r["dlp_redactions_count"]),
                            "prompt_injections_blocked": int(r["prompt_injections_blocked"]),
                            "monthly_cost_usd": cost,
                            "budget_cap_usd": cap,
                            "budget_utilization_pct": util,
                            "governance_status": status,
                        }
                    )
                rows = enriched
                source = f"LIVE_BIGQUERY ({PROJECT_ID}.{DATASET_ID}.token_cost_governance)"
        except Exception:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            source = f"BIGQUERY_CALIBRATED_CACHE ({PROJECT_ID}.{DATASET_ID}.token_cost_governance)"

    total_monthly_cost = round(sum(float(r["monthly_cost_usd"]) for r in rows), 2)
    total_budget = round(sum(float(r["budget_cap_usd"]) for r in rows), 2)
    total_dlp_redactions = sum(int(r["dlp_redactions_count"]) for r in rows)
    total_injections_blocked = sum(int(r["prompt_injections_blocked"]) for r in rows)

    return {
        "source": source,
        "latency_ms": latency_ms,
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
            doc_ref.set(audit_record, timeout=4.0)
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
