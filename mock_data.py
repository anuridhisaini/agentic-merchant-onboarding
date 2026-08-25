"""
Mock merchant onboarding applications.
Tagged by scenario so the same file can be reused for:
  - Day 4-5 agent dev/testing
  - Day 6 failure-handling tests
  - Day 8 throughput/accuracy reporting

Scenario tags: clean, missing_docs, high_risk, conflicting_signals, malformed
"""

from state import MerchantApplication

MOCK_APPLICATIONS: list[dict] = [
    # --- clean: should sail through approved ---
    dict(application_id="APP-001", business_name="Riverside Cafe", industry="food_service",
         country="US", monthly_volume_usd=15000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=["How long does approval usually take?"],
         scenario_tag="clean"),

    dict(application_id="APP-002", business_name="Northline Bookstore", industry="retail",
         country="US", monthly_volume_usd=8000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=[],
         scenario_tag="clean"),

    dict(application_id="APP-003", business_name="Sunset Yoga Studio", industry="fitness",
         country="CA", monthly_volume_usd=6000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=["What fees apply to international cards?"],
         scenario_tag="clean"),

    # --- missing_docs: KYC should flag incomplete ---
    dict(application_id="APP-004", business_name="Quickfix Auto Repair", industry="automotive",
         country="US", monthly_volume_usd=12000,
         documents={"id_document": "present", "business_license": "missing", "bank_statement": "present"},
         questions=[],
         scenario_tag="missing_docs"),

    dict(application_id="APP-005", business_name="GreenLeaf Landscaping", industry="services",
         country="US", monthly_volume_usd=5000,
         documents={"id_document": "missing", "business_license": "missing", "bank_statement": "present"},
         questions=["Can I submit documents later?"],
         scenario_tag="missing_docs"),

    # --- high_risk: industry/volume should push risk-scorer to HIGH ---
    dict(application_id="APP-006", business_name="Apex Crypto Exchange", industry="crypto",
         country="US", monthly_volume_usd=500000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=["What's the settlement time for high-volume accounts?"],
         scenario_tag="high_risk"),

    dict(application_id="APP-007", business_name="Global Cash Remit", industry="money_services",
         country="NG", monthly_volume_usd=250000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=[],
         scenario_tag="high_risk"),

    # --- conflicting_signals: KYC clean but risk-scorer flags high (agents disagree) ---
    dict(application_id="APP-008", business_name="Offshore Consulting Ltd", industry="crypto",
         country="KY", monthly_volume_usd=300000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=[],
         scenario_tag="conflicting_signals"),

    dict(application_id="APP-009", business_name="FastForex Traders", industry="money_services",
         country="US", monthly_volume_usd=180000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=["Why is my volume limit lower than expected?"],
         scenario_tag="conflicting_signals"),

    # --- malformed: bad/missing input types, should be caught by validation ---
    dict(application_id="APP-010", business_name="", industry="retail",
         country="US", monthly_volume_usd=-500,
         documents={},
         questions=[],
         scenario_tag="malformed"),

    dict(application_id="APP-011", business_name="Ambiguous Ventures", industry="unknown",
         country="", monthly_volume_usd=0,
         documents={"id_document": "present"},
         questions=[],
         scenario_tag="malformed"),

    # --- more clean / mixed for volume in throughput testing ---
    dict(application_id="APP-012", business_name="Harbor Hardware", industry="retail",
         country="US", monthly_volume_usd=9000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=[],
         scenario_tag="clean"),

    dict(application_id="APP-013", business_name="Nomad Coffee Roasters", industry="food_service",
         country="US", monthly_volume_usd=11000,
         documents={"id_document": "present", "business_license": "missing", "bank_statement": "missing"},
         questions=["What happens if I'm missing a document?"],
         scenario_tag="missing_docs"),

    dict(application_id="APP-014", business_name="Titan Bullion Trading", industry="crypto",
         country="RU", monthly_volume_usd=750000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=[],
         scenario_tag="high_risk"),

    dict(application_id="APP-015", business_name="Blue Ridge Pharmacy", industry="pharmacy",
         country="US", monthly_volume_usd=40000,
         documents={"id_document": "present", "business_license": "present", "bank_statement": "present"},
         questions=["Is my industry restricted?"],
         scenario_tag="conflicting_signals"),
]


def load_mock_applications() -> list[MerchantApplication]:
    return [MerchantApplication(**app) for app in MOCK_APPLICATIONS]
