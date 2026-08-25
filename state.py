"""
Shared state object passed between agents.
This is the single source of truth for a merchant application as it
moves through the pipeline. Every agent reads from it and writes back to it.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class Stage(str, Enum):
    """Where the application currently is in the pipeline."""
    INTAKE = "intake"
    KYC_CHECK = "kyc_check"
    RISK_SCORING = "risk_scoring"
    QA_REVIEW = "qa_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    HUMAN_ESCALATION = "human_escalation"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass
class HandoffLogEntry:
    """One record of an agent-to-agent (or agent-to-fallback) handoff."""
    timestamp: str
    from_agent: str
    to_agent: str
    reason: str
    state_snapshot: dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "from": self.from_agent,
            "to": self.to_agent,
            "reason": self.reason,
            "state_snapshot": self.state_snapshot,
        }


@dataclass
class MerchantApplication:
    """The full application record. This travels through the whole pipeline."""

    # --- input data (set at intake) ---
    application_id: str
    business_name: str
    industry: str
    country: str
    monthly_volume_usd: float
    documents: dict[str, Any] = field(default_factory=dict)  # e.g. {"id_document": "present", "business_license": "missing"}
    questions: list[str] = field(default_factory=list)  # merchant-submitted questions for the QA agent

    # --- scenario tag, only used for testing/mock data, not "real" input ---
    scenario_tag: str = "unspecified"

    # --- fields agents fill in as the pipeline progresses ---
    stage: Stage = Stage.INTAKE
    kyc_status: Optional[str] = None          # "complete" | "incomplete" | "invalid"
    kyc_flags: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    risk_score: Optional[float] = None        # 0-100
    risk_reasons: list[str] = field(default_factory=list)
    qa_answers: dict[str, str] = field(default_factory=dict)

    # --- pipeline bookkeeping ---
    handoff_log: list[HandoffLogEntry] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)
    final_decision: Optional[str] = None
    decision_reason: Optional[str] = None

    def log_handoff(self, from_agent: str, to_agent: str, reason: str):
        entry = HandoffLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
            state_snapshot={
                "stage": self.stage.value,
                "kyc_status": self.kyc_status,
                "risk_level": self.risk_level.value,
                "risk_score": self.risk_score,
            },
        )
        self.handoff_log.append(entry)

    def summary(self) -> dict:
        return {
            "application_id": self.application_id,
            "business_name": self.business_name,
            "scenario_tag": self.scenario_tag,
            "final_stage": self.stage.value,
            "final_decision": self.final_decision,
            "decision_reason": self.decision_reason,
            "kyc_status": self.kyc_status,
            "kyc_flags": self.kyc_flags,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "num_handoffs": len(self.handoff_log),
            "retries": self.retry_counts,
        }

    def full_dict(self) -> dict:
        """Complete serialization for the dashboard API - includes the full
        handoff log and Q&A answers, not just the summary."""
        return {
            "application_id": self.application_id,
            "business_name": self.business_name,
            "industry": self.industry,
            "country": self.country,
            "monthly_volume_usd": self.monthly_volume_usd,
            "scenario_tag": self.scenario_tag,
            "final_stage": self.stage.value,
            "final_decision": self.final_decision,
            "decision_reason": self.decision_reason,
            "kyc_status": self.kyc_status,
            "kyc_flags": self.kyc_flags,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "risk_reasons": self.risk_reasons,
            "qa_answers": self.qa_answers,
            "retries": self.retry_counts,
            "handoff_log": [entry.to_dict() for entry in self.handoff_log],
        }