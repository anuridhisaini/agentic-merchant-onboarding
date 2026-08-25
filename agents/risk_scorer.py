"""
Risk-scorer agent.
Single responsibility: given the KYC output + merchant profile
(industry, volume, geography), produce a risk score (0-100) and level,
with human-readable reasons attached (graders/reviewers need to see WHY).

This is intentionally rule-based/transparent rather than a black-box LLM
score, because in a real onboarding flow you want an auditable reason for
every risk decision. This is also a natural place to show "agent disagreement"
in your demo: KYC can say "complete" while risk-scorer independently flags HIGH.
"""

from state import MerchantApplication, RiskLevel, Stage

HIGH_RISK_INDUSTRIES = {"crypto", "money_services", "gambling", "adult"}
WATCH_INDUSTRIES = {"pharmacy", "firearms", "cbd"}
HIGH_RISK_COUNTRIES = {"KY", "RU", "IR", "KP"}  # illustrative, not a real sanctions list

VOLUME_HIGH_THRESHOLD = 100_000
VOLUME_MED_THRESHOLD = 25_000


def run(app: MerchantApplication) -> MerchantApplication:
    score = 10.0  # baseline
    reasons = []

    if app.industry in HIGH_RISK_INDUSTRIES:
        score += 45
        reasons.append(f"industry '{app.industry}' is high-risk category")
    elif app.industry in WATCH_INDUSTRIES:
        score += 20
        reasons.append(f"industry '{app.industry}' is a watch-list category")

    if app.country in HIGH_RISK_COUNTRIES:
        score += 30
        reasons.append(f"country '{app.country}' flagged for elevated jurisdiction risk")

    if app.monthly_volume_usd >= VOLUME_HIGH_THRESHOLD:
        score += 25
        reasons.append(f"monthly volume ${app.monthly_volume_usd:,.0f} exceeds high-volume threshold")
    elif app.monthly_volume_usd >= VOLUME_MED_THRESHOLD:
        score += 10
        reasons.append(f"monthly volume ${app.monthly_volume_usd:,.0f} is above baseline")

    if app.kyc_status == "incomplete":
        score += 10
        reasons.append("KYC incomplete, raises uncertainty")
    elif app.kyc_status == "invalid":
        score += 20
        reasons.append("KYC invalid/no documents submitted")

    score = min(score, 100.0)

    if score >= 70:
        level = RiskLevel.HIGH
    elif score >= 35:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    app.risk_score = round(score, 1)
    app.risk_level = level
    app.risk_reasons = reasons or ["no risk factors identified"]

    # --- flag disagreement: KYC thought it was fine, risk model disagrees ---
    if app.kyc_status == "complete" and level == RiskLevel.HIGH:
        app.kyc_flags.append("AGENT_DISAGREEMENT: KYC complete but risk-scorer flags HIGH")

    app.stage = Stage.QA_REVIEW
    app.log_handoff(
        from_agent="risk_scorer",
        to_agent="onboarding_qa",
        reason=f"risk={level.value} (score={app.risk_score}): {'; '.join(reasons)}",
    )
    return app
