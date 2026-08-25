"""
KYC-doc-checker agent.
Single responsibility: given the documents dict on the application,
decide whether KYC is complete, incomplete, or invalid, and record
which specific documents are missing/bad.

Rule-based by design — this is exactly the kind of deterministic check
that shouldn't cost you an LLM call in production. If you want to demo
LLM usage here instead (e.g. reading messy uploaded doc text), swap the
body for a call_llm() call and parse structured JSON back out.
"""

from state import MerchantApplication, Stage

REQUIRED_DOCS = ["id_document", "business_license", "bank_statement"]


class ValidationError(Exception):
    """Raised on malformed input the agent can't reasonably process."""
    pass


def run(app: MerchantApplication) -> MerchantApplication:
    # --- input validation guard (feeds Day 6 failure handling) ---
    if not app.business_name or not app.business_name.strip():
        raise ValidationError(f"{app.application_id}: missing business_name")
    if not isinstance(app.documents, dict):
        raise ValidationError(f"{app.application_id}: documents field is malformed")

    missing = [doc for doc in REQUIRED_DOCS if app.documents.get(doc) != "present"]

    if not missing:
        app.kyc_status = "complete"
        app.kyc_flags = []
        reason = "all required documents present"
    elif len(missing) == len(REQUIRED_DOCS):
        app.kyc_status = "invalid"
        app.kyc_flags = missing
        reason = f"no documents submitted ({', '.join(missing)} all missing)"
    else:
        app.kyc_status = "incomplete"
        app.kyc_flags = missing
        reason = f"missing documents: {', '.join(missing)}"

    app.stage = Stage.RISK_SCORING
    app.log_handoff(from_agent="kyc_checker", to_agent="risk_scorer", reason=reason)
    return app
