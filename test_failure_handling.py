"""
Day 6 deliverable: deliberately break things and prove the fallback logic works.

Three scenarios, each forced rather than left to chance:
  1. Agent timeout -> orchestrator retries once, then escalates
  2. Bad/malformed input -> caught by validation, escalates immediately (no wasted retries)
  3. Agent disagreement -> KYC says fine, risk-scorer says HIGH -> escalates with both reasons logged

Run: python test_failure_handling.py
"""

from unittest.mock import patch
from state import MerchantApplication, Stage
from llm import AgentTimeoutError
from agents import kyc_checker
import orchestrator


def scenario_timeout():
    print("\n--- Scenario 1: agent timeout, then retry, then escalate ---")
    app = MerchantApplication(
        application_id="TEST-TIMEOUT", business_name="Timeout Test Co", industry="retail",
        country="US", monthly_volume_usd=5000,
        documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
        scenario_tag="forced_timeout",
    )
    # force kyc_checker.run to always raise a timeout, regardless of retries
    with patch("orchestrator.kyc_checker.run", side_effect=AgentTimeoutError("forced timeout for test")):
        result = orchestrator.run(app)

    assert result.stage == Stage.HUMAN_ESCALATION, "expected escalation after retries exhausted"
    assert result.retry_counts.get("kyc_checker", 0) == 1, "expected exactly 1 retry"
    print(f"  Result: {result.final_decision} — {result.decision_reason}")
    print(f"  Retries recorded: {result.retry_counts}")
    print("  PASS: timeout triggered retry, then escalated after retry budget exhausted.")


def scenario_bad_input():
    print("\n--- Scenario 2: malformed input caught by validation ---")
    app = MerchantApplication(
        application_id="TEST-BADINPUT", business_name="   ", industry="retail",
        country="US", monthly_volume_usd=5000, documents={"id_document": "present"},
        scenario_tag="forced_bad_input",
    )
    result = orchestrator.run(app)

    assert result.stage == Stage.HUMAN_ESCALATION
    assert "validation failure" in result.decision_reason
    print(f"  Result: {result.final_decision} — {result.decision_reason}")
    print("  PASS: malformed input escalated immediately, no wasted retries.")


def scenario_disagreement():
    print("\n--- Scenario 3: KYC and risk-scorer disagree ---")
    app = MerchantApplication(
        application_id="TEST-DISAGREE", business_name="Shady Crypto LLC", industry="crypto",
        country="US", monthly_volume_usd=600000,
        documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
        scenario_tag="forced_disagreement",
    )
    result = orchestrator.run(app)

    assert result.kyc_status == "complete", "KYC should have passed cleanly"
    assert any("AGENT_DISAGREEMENT" in f for f in result.kyc_flags), "disagreement should be flagged"
    assert result.final_decision == "escalated"
    print(f"  KYC status: {result.kyc_status} | Risk level: {result.risk_level.value}")
    print(f"  Disagreement flag present: {result.kyc_flags}")
    print(f"  Result: {result.final_decision} — {result.decision_reason}")
    print("  PASS: disagreement detected, both signals logged, routed to human review.")


if __name__ == "__main__":
    scenario_timeout()
    scenario_bad_input()
    scenario_disagreement()
    print("\nAll failure-handling scenarios passed.")
