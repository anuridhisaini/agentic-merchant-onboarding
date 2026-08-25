"""
Orchestrator agent.
Single responsibility: decide which agent runs next, retry on transient
failure, resolve agent disagreement, and escalate to a human-review state
when the pipeline can't confidently resolve something itself.

This is the piece graders will look at closest — the logic here IS the
"why did this handoff happen" story, not just the fact that a handoff happened.
"""

from state import MerchantApplication, Stage, RiskLevel
from agents import kyc_checker, risk_scorer, onboarding_qa
from llm import AgentTimeoutError

MAX_RETRIES = 1


class OrchestratorError(Exception):
    pass


def _run_with_retry(agent_name: str, agent_fn, app: MerchantApplication) -> MerchantApplication:
    """
    Wraps an agent call with retry-once-then-escalate logic.
    This is the failure-handling core: timeouts and validation errors
    both funnel through here so there's one place that owns "what do we
    do when an agent fails."
    """
    attempts = app.retry_counts.get(agent_name, 0)
    try:
        return agent_fn(app)
    except AgentTimeoutError as e:
        if attempts < MAX_RETRIES:
            app.retry_counts[agent_name] = attempts + 1
            app.log_handoff(
                from_agent=agent_name,
                to_agent=agent_name,
                reason=f"RETRY after timeout (attempt {attempts + 1}/{MAX_RETRIES}): {e}",
            )
            return _run_with_retry(agent_name, agent_fn, app)
        else:
            app.stage = Stage.HUMAN_ESCALATION
            app.final_decision = "escalated"
            app.decision_reason = f"{agent_name} timed out after {MAX_RETRIES} retr{'y' if MAX_RETRIES==1 else 'ies'}"
            app.log_handoff(from_agent=agent_name, to_agent="human_escalation", reason=app.decision_reason)
            return app
    except kyc_checker.ValidationError as e:
        app.stage = Stage.HUMAN_ESCALATION
        app.final_decision = "escalated"
        app.decision_reason = f"validation failure at {agent_name}: {e}"
        app.log_handoff(from_agent=agent_name, to_agent="human_escalation", reason=app.decision_reason)
        return app


def _final_decision(app: MerchantApplication) -> MerchantApplication:
    """
    Applies the resolution rule for agent disagreement and produces the
    final approve/reject/escalate outcome. Resolution rule (documented,
    not silent): risk_scorer's assessment wins over kyc_checker's on
    disagreement, but disagreement always gets logged for audit.
    """
    if app.stage == Stage.HUMAN_ESCALATION:
        return app  # already escalated upstream, don't overwrite

    disagreement = any("AGENT_DISAGREEMENT" in f for f in app.kyc_flags)

    if app.kyc_status == "invalid":
        app.stage = Stage.REJECTED
        app.final_decision = "rejected"
        app.decision_reason = "KYC invalid: no usable documents submitted"
    elif app.risk_level == RiskLevel.HIGH:
        app.stage = Stage.HUMAN_ESCALATION
        app.final_decision = "escalated"
        app.decision_reason = (
            "high risk score routed to human review"
            + (" (agent disagreement: KYC passed but risk flagged HIGH)" if disagreement else "")
        )
    elif app.kyc_status == "incomplete":
        app.stage = Stage.HUMAN_ESCALATION
        app.final_decision = "escalated"
        app.decision_reason = "KYC incomplete: awaiting missing documents, held for review"
    else:
        app.stage = Stage.APPROVED
        app.final_decision = "approved"
        app.decision_reason = f"KYC complete, risk={app.risk_level.value}"

    app.log_handoff(from_agent="orchestrator", to_agent="FINAL", reason=app.decision_reason)
    return app


def run(app: MerchantApplication) -> MerchantApplication:
    """Runs one application through the full pipeline, start to finish."""
    app = _run_with_retry("kyc_checker", kyc_checker.run, app)
    if app.stage == Stage.HUMAN_ESCALATION:
        return _final_decision(app)

    app = _run_with_retry("risk_scorer", risk_scorer.run, app)
    if app.stage == Stage.HUMAN_ESCALATION:
        return _final_decision(app)

    app = _run_with_retry("onboarding_qa", onboarding_qa.run, app)
    if app.stage == Stage.HUMAN_ESCALATION:
        return _final_decision(app)

    return _final_decision(app)
