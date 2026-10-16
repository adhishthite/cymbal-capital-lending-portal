"""Deterministic RBI Key Fact Statement (KFS), APR, Cooling-Off, Penal Charge, and Credit Policy Engine.

Implements GitHub Issue #12:
- Reducing-balance monthly EMI calculation.
- Exact Newton-Raphson + binary-search Annual Percentage Rate (APR) solver incorporating
  upfront processing fees, documentation charges, and insurance per RBI KFS mandate
  (RBI/2024-25/18 DOR.STR.REC.13/13.03.00/2024-25).
- Mandatory 3-day cooling-off period calculator (loans >= 7 days get >= 3 calendar days
  cooling-off where borrower exits paying only proportionate APR with zero prepayment penalty).
- Penal Charge validator blocking compounding penal interest and enforcing simple,
  non-capitalized penal charges capped at <= 24% p.a. equivalent on overdue installment only
  (RBI/2023-24/53 DOR.MCS.REC.28/01.01.001/2023-24).
- SME Credit Policy DSCR & LTV boundary validator.
"""

from __future__ import annotations

import calendar
from typing import Literal

from pydantic import BaseModel, Field


class KFSRequest(BaseModel):
    """Input parameters for RBI Key Fact Statement (KFS) calculation."""

    borrower_name: str = Field(default="Apex Precision Engineering Pvt Ltd")
    loan_product: str = Field(default="SME Working Capital Top-Up Loan")
    principal_inr: float = Field(
        default=1_000_000.0, description="Sanctioned loan principal in INR"
    )
    nominal_annual_rate_pct: float = Field(
        default=14.50, description="Nominal annual ROI percentage"
    )
    tenure_months: int = Field(default=24, description="Loan repayment tenure in months")
    tenure_days: int | None = Field(
        default=None, description="Explicit tenure in days; defaults to tenure_months * 30"
    )
    processing_fee_inr: float = Field(default=10_000.0, description="Upfront processing fee in INR")
    documentation_fee_inr: float = Field(
        default=2_400.0, description="Upfront documentation charges in INR"
    )
    insurance_fee_inr: float = Field(
        default=1_500.0, description="Bundled credit insurance premium in INR"
    )
    requested_cooling_off_days: int = Field(
        default=3, description="Proposed cooling-off look-up period in calendar days"
    )
    exit_day_in_cooling_off: int = Field(
        default=2, description="Day on which borrower exercises cooling-off exit"
    )
    disbursement_year: int = Field(
        default=2026, description="Calendar year for day-count convention (365 vs 366)"
    )
    overdue_installment_inr: float = Field(
        default=48_249.43, description="Overdue installment amount for penal check"
    )
    overdue_days: int = Field(default=15, description="Days past due for penal charge calculation")
    annualized_penal_rate_pct: float = Field(
        default=18.0, description="Annualized simple penal charge rate (%)"
    )
    is_penal_compounded: bool = Field(
        default=False, description="Whether penal charge compounds into principal"
    )
    penal_charge_basis: Literal["OVERDUE_INSTALLMENT", "FULL_PRINCIPAL"] = Field(
        default="OVERDUE_INSTALLMENT",
        description="Basis on which late payment penal charge is levied",
    )
    include_ai_verdict: bool = Field(
        default=False,
        description="When True, invoke live Vertex AI gemini-3.5-flash-lite for statutory KFS audit verdict",
    )


class CoolingOffResult(BaseModel):
    """Result of RBI cooling-off / look-up period validation and payoff calculation."""

    tenure_days: int
    min_required_cooling_off_days: int
    configured_cooling_off_days: int
    effective_cooling_off_days: int
    is_compliant: bool
    exit_day: int
    can_exit_under_cooling_off: bool
    days_in_year: int
    is_leap_year: bool
    proportionate_apr_interest_inr: float
    prepayment_penalty_inr: float
    upfront_fees_refundable_inr: float
    total_cooling_off_exit_payoff_inr: float
    rbi_rule_citation: str
    violation_reason: str | None = None


class PenalChargeResult(BaseModel):
    """Result of RBI Fair Lending Practice penal charge validation."""

    is_compliant: bool
    annualized_penal_rate_pct: float
    max_allowed_penal_rate_pct: float = 24.0
    is_compounded: bool
    charge_basis: str
    overdue_installment_inr: float
    overdue_days: int
    days_in_year: int
    computed_penal_charge_inr: float
    rbi_circular_citation: str
    violation_reasons: list[str] = Field(default_factory=list)


class AmortizationRow(BaseModel):
    """Single month row in the KFS repayment schedule."""

    month: int
    opening_balance_inr: float
    emi_inr: float
    interest_component_inr: float
    principal_component_inr: float
    closing_balance_inr: float


class KFSResponse(BaseModel):
    """Complete RBI Key Fact Statement (KFS) calculation output."""

    borrower_name: str
    loan_product: str
    principal_inr: float
    nominal_annual_rate_pct: float
    all_inclusive_apr_pct: float
    apr_spread_bps: int
    apr_spread_pct: float
    tenure_months: int
    monthly_emi_inr: float
    processing_fee_inr: float
    documentation_fee_inr: float
    insurance_fee_inr: float
    total_upfront_charges_inr: float
    net_disbursed_amount_inr: float
    total_interest_payable_inr: float
    total_cost_of_credit_inr: float
    total_amount_repayable_inr: float
    cooling_off: CoolingOffResult
    penal_charge_guardrail: PenalChargeResult
    is_rbi_kfs_compliant: bool
    compliance_violations: list[str]
    schedule_preview: list[AmortizationRow]


class CreditPolicyRequest(BaseModel):
    """SME Credit underwriting policy verification input."""

    applicant_name: str = Field(default="Apex Precision Engineering Pvt Ltd")
    loan_amount_inr: float = Field(default=7_500_000.0)
    dscr: float = Field(default=1.18, description="Debt Service Coverage Ratio")
    ltv_pct: float = Field(default=68.5, description="Loan-to-Value percentage")
    cibil_commercial_rank: int = Field(default=3, description="CIBIL MSME Rank (CMR-1 to CMR-10)")
    gstin_12m_turnover_inr: float = Field(default=42_000_000.0)
    requested_Nominal_roi_pct: float = Field(default=14.50)
    include_ai_memo: bool = Field(
        default=False,
        description="When True, invoke live Vertex AI gemini-3.8-flash for underwriting deviation memo",
    )


class CreditPolicyResult(BaseModel):
    """Deterministic SME credit policy decision."""

    applicant_name: str
    loan_amount_inr: float
    dscr: float
    ltv_pct: float
    cibil_commercial_rank: int
    decision: Literal["APPROVED_STANDARD", "ESCALATE_ZONAL_CREDIT_HEAD", "REJECTED"]
    approval_authority: str
    policy_triggers: list[str]
    is_compliant_with_policy_caps: bool


def is_calendar_leap_year(year: int) -> bool:
    """Return True if the given year is a leap year (366 days)."""
    return calendar.isleap(year)


def days_in_calendar_year(year: int) -> int:
    """Return 366 for leap years and 365 for standard years."""
    return 366 if is_calendar_leap_year(year) else 365


def calculate_monthly_emi(
    principal_inr: float,
    nominal_annual_rate_pct: float,
    tenure_months: int,
) -> float:
    """Compute reducing-balance monthly EMI in INR.

    Raises ValueError if principal <= 0, tenure_months <= 0, or nominal_annual_rate_pct < 0.
    """
    if principal_inr <= 0:
        raise ValueError("Loan principal must be strictly positive (principal_inr > 0).")
    if tenure_months <= 0:
        raise ValueError("Loan tenure must be at least 1 month (tenure_months >= 1).")
    if nominal_annual_rate_pct < 0:
        raise ValueError("Nominal annual interest rate cannot be negative.")
    if nominal_annual_rate_pct > 100.0:
        raise ValueError("Nominal annual interest rate exceeds 100% sanity threshold.")

    if nominal_annual_rate_pct == 0.0:
        return round(principal_inr / tenure_months, 2)

    monthly_rate = (nominal_annual_rate_pct / 100.0) / 12.0
    factor = (1.0 + monthly_rate) ** tenure_months
    emi = principal_inr * (monthly_rate * factor) / (factor - 1.0)
    return round(emi, 2)


def solve_all_inclusive_apr(
    principal_inr: float,
    nominal_annual_rate_pct: float,
    tenure_months: int,
    processing_fee_inr: float = 0.0,
    documentation_fee_inr: float = 0.0,
    insurance_fee_inr: float = 0.0,
) -> float:
    """Solve exact All-Inclusive Annual Percentage Rate (APR) using Newton-Raphson with binary-search fallback.

    Per RBI KFS circular (RBI/2024-25/18), the APR is the annualized Internal Rate of Return (IRR)
    equating the net disbursed amount (Principal minus upfront processing, documentation, and insurance
    charges) to the present value of all monthly EMI installments.
    """
    if principal_inr <= 0:
        raise ValueError("Loan principal must be strictly positive (principal_inr > 0).")
    if tenure_months <= 0:
        raise ValueError("Loan tenure must be at least 1 month (tenure_months >= 1).")
    if nominal_annual_rate_pct < 0:
        raise ValueError("Nominal annual interest rate cannot be negative.")
    if processing_fee_inr < 0 or documentation_fee_inr < 0 or insurance_fee_inr < 0:
        raise ValueError("Upfront fee components cannot be negative.")

    total_upfront = processing_fee_inr + documentation_fee_inr + insurance_fee_inr
    if total_upfront >= principal_inr:
        raise ValueError("Total upfront charges cannot equal or exceed the loan principal.")

    if total_upfront == 0.0:
        return round(nominal_annual_rate_pct, 2)

    # Use unrounded high-precision EMI for IRR accuracy, matching standard financial calculators
    if nominal_annual_rate_pct == 0.0:
        emi = principal_inr / tenure_months
    else:
        m_rate = (nominal_annual_rate_pct / 100.0) / 12.0
        factor = (1.0 + m_rate) ** tenure_months
        emi = principal_inr * (m_rate * factor) / (factor - 1.0)

    net_disbursed = principal_inr - total_upfront

    def npv_and_derivative(monthly_irr: float) -> tuple[float, float]:
        if monthly_irr <= 1e-12:
            pv = emi * tenure_months
            dpv = -emi * tenure_months * (tenure_months + 1) / 2.0
            return pv - net_disbursed, dpv
        one_plus_r = 1.0 + monthly_irr
        pow_neg_n = one_plus_r ** (-tenure_months)
        pv = emi * (1.0 - pow_neg_n) / monthly_irr
        # Derivative d(PV)/d(monthly_irr)
        dpv = emi * (
            (
                tenure_months * (one_plus_r ** (-tenure_months - 1.0)) * monthly_irr
                - (1.0 - pow_neg_n)
            )
            / (monthly_irr * monthly_irr)
        )
        return pv - net_disbursed, dpv

    # Initial guess: start from nominal monthly rate + amortized upfront fee spread
    guess = (
        max((nominal_annual_rate_pct / 100.0) / 12.0, 1e-4)
        + (total_upfront / principal_inr) / tenure_months
    )

    converged = False
    for _ in range(100):
        f_val, f_prime = npv_and_derivative(guess)
        if abs(f_val) < 1e-9:
            converged = True
            break
        if abs(f_prime) < 1e-14:
            break
        next_guess = guess - (f_val / f_prime)
        if next_guess <= 0.0 or next_guess > 5.0:
            break
        if abs(next_guess - guess) < 1e-12:
            guess = next_guess
            converged = True
            break
        guess = next_guess

    if not converged:
        # Deterministic binary search fallback on [0.0, 5.0] monthly rate
        low, high = 0.0, 5.0
        for _ in range(120):
            mid = (low + high) / 2.0
            f_mid, _ = npv_and_derivative(mid)
            if abs(f_mid) < 1e-9:
                guess = mid
                break
            if f_mid > 0:
                low = mid
            else:
                high = mid
        guess = (low + high) / 2.0

    apr_pct = guess * 12.0 * 100.0
    return round(apr_pct, 2)


def calculate_cooling_off_period(
    principal_inr: float,
    all_inclusive_apr_pct: float,
    tenure_days: int,
    requested_cooling_off_days: int = 3,
    exit_day: int = 2,
    disbursement_year: int = 2026,
    upfront_charges_inr: float = 0.0,
) -> CoolingOffResult:
    """Validate RBI mandatory cooling-off period and compute proportionate APR exit payoff.

    RBI Digital Lending Rules mandate:
    - Loans with tenure >= 7 days MUST provide a minimum 3-calendar-day cooling-off period.
    - Loans with tenure < 7 days MUST provide a minimum 1-calendar-day cooling-off period.
    - Borrowers exiting during the cooling-off period pay zero prepayment penalty and only
      proportionate APR for the exact days the funds were held.
    """
    if tenure_days <= 0:
        raise ValueError("Tenure in days must be strictly positive (tenure_days >= 1).")
    if exit_day < 0:
        raise ValueError("Exit day cannot be negative.")
    if principal_inr <= 0:
        raise ValueError("Principal must be strictly positive.")

    min_required = 3 if tenure_days >= 7 else 1
    is_compliant = requested_cooling_off_days >= min_required
    effective_window = max(requested_cooling_off_days, min_required)
    can_exit = exit_day <= effective_window

    year_days = days_in_calendar_year(disbursement_year)
    leap = is_calendar_leap_year(disbursement_year)

    proportionate_interest = round(
        principal_inr * (all_inclusive_apr_pct / 100.0) * (exit_day / float(year_days)),
        2,
    )
    prepayment_penalty = 0.0
    total_payoff = round(principal_inr + proportionate_interest, 2)

    violation_reason = None
    if not is_compliant:
        violation_reason = (
            f"RBI KFS Violation (RBI-KFS-02): Loan tenure of {tenure_days} days requires at least "
            f"{min_required} calendar days cooling-off period, but only {requested_cooling_off_days} day(s) configured."
        )

    return CoolingOffResult(
        tenure_days=tenure_days,
        min_required_cooling_off_days=min_required,
        configured_cooling_off_days=requested_cooling_off_days,
        effective_cooling_off_days=effective_window,
        is_compliant=is_compliant,
        exit_day=exit_day,
        can_exit_under_cooling_off=can_exit,
        days_in_year=year_days,
        is_leap_year=leap,
        proportionate_apr_interest_inr=proportionate_interest,
        prepayment_penalty_inr=prepayment_penalty,
        upfront_fees_refundable_inr=round(upfront_charges_inr, 2),
        total_cooling_off_exit_payoff_inr=total_payoff,
        rbi_rule_citation="RBI/2024-25/18 DOR.STR.REC.13/13.03.00/2024-25 (Para 10 — Cooling-Off / Look-Up Period)",
        violation_reason=violation_reason,
    )


def validate_penal_charge(
    overdue_installment_inr: float,
    overdue_days: int,
    annualized_penal_rate_pct: float,
    is_compounded: bool = False,
    charge_basis: Literal["OVERDUE_INSTALLMENT", "FULL_PRINCIPAL"] = "OVERDUE_INSTALLMENT",
    disbursement_year: int = 2026,
) -> PenalChargeResult:
    """Validate penal charges against RBI Fair Lending Practice circular (RBI/2023-24/53).

    Enforces:
    1. No compounding / capitalization of penal interest into principal (is_compounded == False).
    2. Penal charges levied strictly on the overdue installment amount (never FULL_PRINCIPAL).
    3. Simple annualized penal charge rate capped at <= 24.0% p.a.
    """
    if overdue_installment_inr < 0:
        raise ValueError("Overdue installment amount cannot be negative.")
    if overdue_days < 0:
        raise ValueError("Overdue days cannot be negative.")
    if annualized_penal_rate_pct < 0:
        raise ValueError("Annualized penal charge rate cannot be negative.")

    violations: list[str] = []
    if is_compounded:
        violations.append(
            "RBI Penal Charge Violation (RBI-PEN-03): Penal charges cannot be compounded or capitalized into loan principal."
        )
    if charge_basis != "OVERDUE_INSTALLMENT":
        violations.append(
            "RBI Penal Charge Violation (RBI-PEN-03): Penal charges must be levied only on the defaulted EMI installment, never on full principal."
        )
    if annualized_penal_rate_pct > 24.0:
        violations.append(
            f"RBI Penal Charge Cap Violation (RBI-PEN-03): Annualized penal charge rate {annualized_penal_rate_pct:.2f}% exceeds the 24.00% p.a. statutory ceiling."
        )

    year_days = days_in_calendar_year(disbursement_year)
    simple_charge = round(
        overdue_installment_inr
        * (annualized_penal_rate_pct / 100.0)
        * (overdue_days / float(year_days)),
        2,
    )

    return PenalChargeResult(
        is_compliant=len(violations) == 0,
        annualized_penal_rate_pct=round(annualized_penal_rate_pct, 2),
        max_allowed_penal_rate_pct=24.0,
        is_compounded=is_compounded,
        charge_basis=charge_basis,
        overdue_installment_inr=round(overdue_installment_inr, 2),
        overdue_days=overdue_days,
        days_in_year=year_days,
        computed_penal_charge_inr=simple_charge,
        rbi_circular_citation="RBI/2023-24/53 DOR.MCS.REC.28/01.01.001/2023-24 (Fair Lending Practice — Penal Charges in Loan Accounts)",
        violation_reasons=violations,
    )


def evaluate_sme_credit_policy(request: CreditPolicyRequest) -> CreditPolicyResult:
    """Evaluate SME working capital / top-up credit policy boundaries (DSCR, LTV, CMR rank)."""
    if request.loan_amount_inr <= 0:
        raise ValueError("Loan amount must be positive.")
    if request.dscr <= 0:
        raise ValueError("DSCR must be positive.")
    if request.ltv_pct < 0 or request.ltv_pct > 100:
        raise ValueError("LTV percentage must be between 0 and 100.")

    triggers: list[str] = []
    rejected = False

    if request.dscr < 1.15:
        rejected = True
        triggers.append(f"DSCR {request.dscr:.2f}x is below the hard rejection floor of 1.15x.")
    if request.ltv_pct > 75.0:
        rejected = True
        triggers.append(
            f"Collateral LTV {request.ltv_pct:.2f}% exceeds the 75.00% maximum policy ceiling."
        )
    if request.cibil_commercial_rank > 6:
        rejected = True
        triggers.append(
            f"CIBIL Commercial Rank CMR-{request.cibil_commercial_rank} exceeds maximum acceptable risk rank CMR-6."
        )

    if rejected:
        return CreditPolicyResult(
            applicant_name=request.applicant_name,
            loan_amount_inr=request.loan_amount_inr,
            dscr=request.dscr,
            ltv_pct=request.ltv_pct,
            cibil_commercial_rank=request.cibil_commercial_rank,
            decision="REJECTED",
            approval_authority="Automated Credit Policy Gate (Hard Decline)",
            policy_triggers=triggers,
            is_compliant_with_policy_caps=False,
        )

    if 1.15 <= request.dscr < 1.25:
        triggers.append(
            f"DSCR {request.dscr:.2f}x falls in the 1.15x–1.24x exception band (Standard cutoff >= 1.25x). Mandatory escalation to Zonal Credit Head required."
        )
        return CreditPolicyResult(
            applicant_name=request.applicant_name,
            loan_amount_inr=request.loan_amount_inr,
            dscr=request.dscr,
            ltv_pct=request.ltv_pct,
            cibil_commercial_rank=request.cibil_commercial_rank,
            decision="ESCALATE_ZONAL_CREDIT_HEAD",
            approval_authority="Zonal Credit Head (SME Underwriting Deviation Matrix)",
            policy_triggers=triggers,
            is_compliant_with_policy_caps=True,
        )

    triggers.append(
        f"DSCR {request.dscr:.2f}x >= 1.25x and LTV {request.ltv_pct:.2f}% <= 75.00% meet standard STP underwriting norms."
    )
    return CreditPolicyResult(
        applicant_name=request.applicant_name,
        loan_amount_inr=request.loan_amount_inr,
        dscr=request.dscr,
        ltv_pct=request.ltv_pct,
        cibil_commercial_rank=request.cibil_commercial_rank,
        decision="APPROVED_STANDARD",
        approval_authority="Branch / Regional Credit Manager (Straight-Through Processing)",
        policy_triggers=triggers,
        is_compliant_with_policy_caps=True,
    )


def build_amortization_preview(
    principal_inr: float,
    nominal_annual_rate_pct: float,
    tenure_months: int,
    max_rows: int = 6,
) -> list[AmortizationRow]:
    """Generate the first N rows of the reducing-balance repayment schedule."""
    emi = calculate_monthly_emi(principal_inr, nominal_annual_rate_pct, tenure_months)
    monthly_rate = (nominal_annual_rate_pct / 100.0) / 12.0
    balance = principal_inr
    rows: list[AmortizationRow] = []

    for month in range(1, min(tenure_months, max_rows) + 1):
        interest_part = round(balance * monthly_rate, 2)
        principal_part = round(emi - interest_part, 2)
        if month == tenure_months or principal_part > balance:
            principal_part = round(balance, 2)
        closing = round(max(0.0, balance - principal_part), 2)
        rows.append(
            AmortizationRow(
                month=month,
                opening_balance_inr=round(balance, 2),
                emi_inr=emi,
                interest_component_inr=interest_part,
                principal_component_inr=principal_part,
                closing_balance_inr=closing,
            )
        )
        balance = closing
    return rows


def calculate_kfs(request: KFSRequest) -> KFSResponse:
    """Compute the full RBI Key Fact Statement (KFS) response and validate all regulatory guardrails."""
    emi = calculate_monthly_emi(
        request.principal_inr,
        request.nominal_annual_rate_pct,
        request.tenure_months,
    )
    apr = solve_all_inclusive_apr(
        principal_inr=request.principal_inr,
        nominal_annual_rate_pct=request.nominal_annual_rate_pct,
        tenure_months=request.tenure_months,
        processing_fee_inr=request.processing_fee_inr,
        documentation_fee_inr=request.documentation_fee_inr,
        insurance_fee_inr=request.insurance_fee_inr,
    )
    upfront_total = round(
        request.processing_fee_inr + request.documentation_fee_inr + request.insurance_fee_inr,
        2,
    )
    net_disbursed = round(request.principal_inr - upfront_total, 2)
    total_repayable_emi = round(emi * request.tenure_months, 2)
    total_interest = round(max(0.0, total_repayable_emi - request.principal_inr), 2)
    total_cost_of_credit = round(total_interest + upfront_total, 2)

    effective_tenure_days = (
        request.tenure_days if request.tenure_days is not None else request.tenure_months * 30
    )

    cooling_off = calculate_cooling_off_period(
        principal_inr=request.principal_inr,
        all_inclusive_apr_pct=apr,
        tenure_days=effective_tenure_days,
        requested_cooling_off_days=request.requested_cooling_off_days,
        exit_day=request.exit_day_in_cooling_off,
        disbursement_year=request.disbursement_year,
        upfront_charges_inr=upfront_total,
    )

    penal_guardrail = validate_penal_charge(
        overdue_installment_inr=request.overdue_installment_inr,
        overdue_days=request.overdue_days,
        annualized_penal_rate_pct=request.annualized_penal_rate_pct,
        is_compounded=request.is_penal_compounded,
        charge_basis=request.penal_charge_basis,
        disbursement_year=request.disbursement_year,
    )

    violations: list[str] = []
    if cooling_off.violation_reason:
        violations.append(cooling_off.violation_reason)
    violations.extend(penal_guardrail.violation_reasons)

    spread_pct = round(apr - request.nominal_annual_rate_pct, 2)
    spread_bps = round(spread_pct * 100)

    return KFSResponse(
        borrower_name=request.borrower_name,
        loan_product=request.loan_product,
        principal_inr=round(request.principal_inr, 2),
        nominal_annual_rate_pct=round(request.nominal_annual_rate_pct, 2),
        all_inclusive_apr_pct=apr,
        apr_spread_bps=spread_bps,
        apr_spread_pct=spread_pct,
        tenure_months=request.tenure_months,
        monthly_emi_inr=emi,
        processing_fee_inr=round(request.processing_fee_inr, 2),
        documentation_fee_inr=round(request.documentation_fee_inr, 2),
        insurance_fee_inr=round(request.insurance_fee_inr, 2),
        total_upfront_charges_inr=upfront_total,
        net_disbursed_amount_inr=net_disbursed,
        total_interest_payable_inr=total_interest,
        total_cost_of_credit_inr=total_cost_of_credit,
        total_amount_repayable_inr=round(request.principal_inr + total_cost_of_credit, 2),
        cooling_off=cooling_off,
        penal_charge_guardrail=penal_guardrail,
        is_rbi_kfs_compliant=len(violations) == 0,
        compliance_violations=violations,
        schedule_preview=build_amortization_preview(
            request.principal_inr,
            request.nominal_annual_rate_pct,
            request.tenure_months,
        ),
    )
