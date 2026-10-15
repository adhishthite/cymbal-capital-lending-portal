#!/usr/bin/env python3
"""Seed the Cymbal Capital Lending Portal GitHub backlog with 2 milestones, labels, and 12 issues."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

REPO = "adhishthite/cymbal-capital-lending-portal"
GH_WRAPPER = Path("/usr/local/google/home/adhishthite/.gemini/config/plugins/github/skills/github/scripts/gh")
GH_BIN = str(GH_WRAPPER) if GH_WRAPPER.exists() else "gh"

LABELS: list[tuple[str, str, str]] = [
    ("priority:P0", "B60205", "Critical regulatory or production blocker"),
    ("status:blocked", "D93F0B", "Blocked on external dependency or compliance sign-off"),
    ("status:unestimated", "FBCA04", "Missing BigQuery WBS man-day estimation"),
    ("status:ready-for-dev", "0E8A16", "BRD approved, RBI gates verified, and WBS sized"),
    ("compliance:rbi", "1D76DB", "RBI Digital Lending / KFS / Fair Lending mandate"),
    ("track:retail-it", "5319E7", "Retail Digital Lending engineering squad"),
    ("track:sme-it", "0052CC", "SME & Commercial Credit engineering squad"),
    ("track:infra", "006B75", "Cloud DLP, Model Armor, and BigQuery governance platform"),
]

MILESTONES: list[tuple[str, str]] = [
    (
        "Sprint 24 - SME Digital Lending Compliance",
        "Mandatory RBI Key Fact Statement (KFS), APR solver, cooling-off, and penal charge compliance sprint.",
    ),
    (
        "Sprint 25 - Monolith Extraction",
        "Decommission legacy Java/Oracle PL/SQL triggers and extract co-lending microservices.",
    ),
]

ISSUES: list[dict[str, Any]] = [
    {
        "number": 1,
        "title": "Extract SME Loan Origination state machine from legacy Java/Oracle monolith",
        "milestone": "Sprint 25 - Monolith Extraction",
        "labels": ["track:sme-it", "status:ready-for-dev"],
        "body": (
            "## Objective\n"
            "Decouple the SME Working Capital loan origination state machine from `LOS_CORE_PKG.pkb` "
            "into a stateless FastAPI service backed by Cloud Run (`min-instances=0`).\n\n"
            "## Acceptance Criteria\n"
            "- Preserve audit events in Firestore `cymbal_kfs_audits`.\n"
            "- Zero direct JDBC calls from the web tier."
        ),
    },
    {
        "number": 2,
        "title": "Implement RBI Account Aggregator (AA) FIP consent artifact signature verifier",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["compliance:rbi", "track:retail-it", "status:ready-for-dev"],
        "body": (
            "## Objective\n"
            "Validate ReBIT Account Aggregator JWS detached signatures on Financial Information Provider (FIP) "
            "bank statement pulls before running underwriting cash-flow rules.\n\n"
            "## Acceptance Criteria\n"
            "- Reject expired or tampered consent handles (`purpose.code != 103`)."
        ),
    },
    {
        "number": 3,
        "title": "Migrate Cloud DLP de-identification templates for Aadhaar vault tokenization",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["compliance:rbi", "track:infra", "status:ready-for-dev"],
        "body": (
            "## Objective\n"
            "Standardize `INDIA_PAN_INDIVIDUAL` and `INDIA_AADHAAR_INDIVIDUAL` redaction templates in "
            "`projects/adhish-base-project-1` prior to Vertex AI prompt dispatch.\n\n"
            "## Acceptance Criteria\n"
            "- Mask `ABCDE1234F` and `4921 8834 9012` in all application logs and LLM prompts."
        ),
    },
    {
        "number": 4,
        "title": "CIBIL Commercial Bureau API timeout on Partnership PANs",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["priority:P0", "status:blocked", "track:sme-it"],
        "body": (
            "## Blocker Summary (`status:blocked`, `priority:P0`)\n"
            "Commercial bureau pulls for SME Partnership Firms (where the 4th character of the entity PAN is `F`) "
            "are timing out after 30s on the CIBIL UAT gateway.\n\n"
            "## Impact\n"
            "- Blocks automated CMR-1 to CMR-10 rank retrieval for Partnership SME Top-Up applicants.\n"
            "- Waiting on TransUnion CIBIL network operations to whitelist Cloud NAT egress IP in `asia-south1`."
        ),
    },
    {
        "number": 5,
        "title": "Configure Model Armor prompt-injection guardrail for Underwriting Copilot",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["compliance:rbi", "track:infra", "status:ready-for-dev"],
        "body": (
            "## Objective\n"
            "Block adversarial instructions attempting to override RBI APR math, suppress processing fees, "
            "or force compounding penal interest before calling `gemini-2.5-flash`."
        ),
    },
    {
        "number": 6,
        "title": "Enforce direct bank account disbursement verification (block LSP nodal pass-through)",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["compliance:rbi", "priority:P0", "track:sme-it", "status:ready-for-dev"],
        "body": (
            "## Objective\n"
            "Enforce RBI Digital Lending Para 3 (`RBI-DLG-04`): 100% of sanctioned net loan proceeds must be "
            "credited directly to the verified borrower bank account without passing through any LSP nodal wallet."
        ),
    },
    {
        "number": 7,
        "title": "Missing RBI Key Fact Statement (KFS) cooling-off period sign-off",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["priority:P0", "status:blocked", "compliance:rbi", "track:retail-it"],
        "body": (
            "## Blocker Summary (`status:blocked`, `priority:P0`, `compliance:rbi`)\n"
            "Business Product proposed disabling the cooling-off window or charging a 4% foreclosure fee "
            "during the first 3 days on SME Top-Up loans.\n\n"
            "## Statutory Mandate (`RBI/2024-25/18`)\n"
            "- Loans with tenure >= 7 days MUST provide a minimum 3-calendar-day cooling-off look-up window.\n"
            "- Borrowers exiting during cooling-off pay ONLY proportionate APR with zero prepayment penalty."
        ),
    },
    {
        "number": 8,
        "title": "Build BigQuery SDLC token cost & WBS benchmark telemetry sink",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["track:infra", "status:ready-for-dev"],
        "body": (
            "## Objective\n"
            "Stream department-level Vertex AI token spend and WBS estimation accuracy into "
            "`adhish-base-project-1.cymbal_capital_sdlc.token_cost_governance` and `wbs_benchmarks`."
        ),
    },
    {
        "number": 9,
        "title": "Add GSTIN cash-flow velocity check for SME Top-Up loans",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["status:unestimated", "track:sme-it"],
        "body": (
            "## Unestimated Requirement (`status:unestimated`)\n"
            "Compare trailing 12-month GSTR-1 outward supplies against GSTR-3B tax paid to flag >10% variance "
            "on SME Top-Up loans above ₹50,00,000.\n\n"
            "## Next Step\n"
            "- Run `.agents/skills/brd-and-wbs-estimator/SKILL.md` against BigQuery `cymbal_capital_sdlc.wbs_benchmarks` "
            "to produce Backend/DB/Frontend/QA man-day estimates."
        ),
    },
    {
        "number": 10,
        "title": "Co-lending 80:20 escrow waterfall reconciliation",
        "milestone": "Sprint 25 - Monolith Extraction",
        "labels": ["status:unestimated", "compliance:rbi", "track:sme-it"],
        "body": (
            "## Unestimated Requirement (`status:unestimated`)\n"
            "Implement daily T+1 escrow settlement reconciliation splitting borrower EMI collections 80:20 "
            "between partner commercial bank and Cymbal Capital.\n\n"
            "## Next Step\n"
            "- Requires BigQuery WBS sizing before Sprint 25 capacity allocation."
        ),
    },
    {
        "number": 11,
        "title": "Decommission Oracle PL/SQL compounding penal interest trigger in LMS",
        "milestone": "Sprint 25 - Monolith Extraction",
        "labels": ["compliance:rbi", "track:retail-it", "status:ready-for-dev"],
        "body": (
            "## Objective\n"
            "Disable legacy `TRG_CALC_COMPOUND_PENAL_INT` trigger in Oracle LMS and route all late payment "
            "calculations through the RBI/2023-24/53 compliant simple penal charge microservice."
        ),
    },
    {
        "number": 12,
        "title": "Implement RBI Key Fact Statement (KFS) APR Calculator & Penal Charge Guardrail",
        "milestone": "Sprint 24 - SME Digital Lending Compliance",
        "labels": ["status:ready-for-dev", "compliance:rbi", "priority:P0", "track:sme-it"],
        "body": (
            "## Specification (`status:ready-for-dev`, `compliance:rbi`)\n"
            "Implement the deterministic RBI Key Fact Statement (KFS) and Fair Lending Penal Charge engine in "
            "`backend/app/services/kfs_calculator.py`.\n\n"
            "### Financial & Regulatory Parameters\n"
            "1. **Reducing-Balance Monthly EMI:** Standard actuarial formula over `tenure_months`.\n"
            "2. **Newton-Raphson All-Inclusive APR Solver (`RBI/2024-25/18`):**\n"
            "   - Must incorporate upfront `processing_fee_inr`, `documentation_fee_inr`, and `insurance_fee_inr`.\n"
            "   - Canonical benchmark: `₹10,00,000` principal at `14.50%` nominal ROI over `24` months with "
            "`₹13,900` total upfront fees (`₹10,000` processing + `₹2,400` doc + `₹1,500` insurance) yields "
            "an exact All-Inclusive APR of **`15.93%`** (`+143 bps` spread).\n"
            "3. **Mandatory 3-Day Cooling-Off Period (`RBI-KFS-02`):**\n"
            "   - Loans with `tenure_days >= 7` require `>= 3` calendar days cooling-off (1 day for `< 7` days).\n"
            "   - Zero prepayment penalty during cooling-off; borrower pays only proportionate APR (`365` vs `366` leap year).\n"
            "4. **Fair Lending Penal Charge Guardrail (`RBI/2023-24/53`):**\n"
            "   - Block compounding penal interest (`is_compounded == False`).\n"
            "   - Enforce simple penal charge strictly on `OVERDUE_INSTALLMENT` capped at `<= 24.00%` p.a.\n"
            "5. **Verification:**\n"
            "   - 15 unit tests (`tests/test_kfs_unit.py`) + 105 parameterized boundary UAT tests (`tests/test_uat_boundary_100.py`)."
        ),
    },
]


def run_gh(args: list[str]) -> str:
    """Execute gh CLI command and return stdout."""
    proc = subprocess.run(
        [GH_BIN, *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def ensure_labels() -> None:
    """Create or update all required repository labels."""
    print(f"Syncing {len(LABELS)} labels on {REPO}...")
    for name, color, description in LABELS:
        run_gh(
            [
                "label",
                "create",
                name,
                "--repo",
                REPO,
                "--color",
                color,
                "--description",
                description,
                "--force",
            ]
        )


def ensure_milestones() -> dict[str, int]:
    """Create or fetch the two required milestones and return title -> number mapping."""
    existing_raw = run_gh(["api", f"repos/{REPO}/milestones?state=all"])
    existing_list = json.loads(existing_raw) if existing_raw else []
    milestone_map: dict[str, int] = {m["title"]: int(m["number"]) for m in existing_list}

    for title, description in MILESTONES:
        if title not in milestone_map:
            print(f"Creating milestone: {title}")
            created_raw = run_gh(
                [
                    "api",
                    "--method",
                    "POST",
                    f"repos/{REPO}/milestones",
                    "-f",
                    f"title={title}",
                    "-f",
                    "state=open",
                    "-f",
                    f"description={description}",
                ]
            )
            created = json.loads(created_raw)
            milestone_map[title] = int(created["number"])
        else:
            print(f"Milestone already exists: {title} (#{milestone_map[title]})")

    return milestone_map


def ensure_issues(milestone_map: dict[str, int]) -> None:
    """Create or update Issues #1 through #12 in exact numerical order."""
    existing_raw = run_gh(
        [
            "issue",
            "list",
            "--repo",
            REPO,
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title",
        ]
    )
    existing_issues = json.loads(existing_raw) if existing_raw else []
    by_number: dict[int, dict[str, Any]] = {int(i["number"]): i for i in existing_issues}

    for spec in ISSUES:
        num = spec["number"]
        title = spec["title"]
        milestone_title = spec["milestone"]
        milestone_number = milestone_map[milestone_title]
        labels = spec["labels"]
        body = spec["body"]

        if num in by_number:
            print(f"Updating existing Issue #{num}: {title}")
            cmd = [
                "api",
                "--method",
                "PATCH",
                f"repos/{REPO}/issues/{num}",
                "-f",
                f"title={title}",
                "-f",
                f"body={body}",
                "-F",
                f"milestone={milestone_number}",
            ]
            for lbl in labels:
                cmd.extend(["-f", f"labels[]={lbl}"])
            run_gh(cmd)
        else:
            print(f"Creating Issue #{num}: {title}")
            cmd = [
                "api",
                "--method",
                "POST",
                f"repos/{REPO}/issues",
                "-f",
                f"title={title}",
                "-f",
                f"body={body}",
                "-F",
                f"milestone={milestone_number}",
            ]
            for lbl in labels:
                cmd.extend(["-f", f"labels[]={lbl}"])
            created_raw = run_gh(cmd)
            created = json.loads(created_raw)
            print(f"  -> Created #{created['number']}: {created['html_url']}")


def main() -> None:
    ensure_labels()
    milestone_map = ensure_milestones()
    ensure_issues(milestone_map)
    print("Successfully seeded all milestones, labels, and 12 issues!")


if __name__ == "__main__":
    main()
