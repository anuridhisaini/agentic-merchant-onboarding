"""
Onboarding-Q&A agent.
Single responsibility: answer merchant-submitted questions during onboarding.

This is the one agent where an LLM naturally earns its place (open-ended
questions, needs to sound human). Ships with a small FAQ lookup as a
rule-based fallback so the pipeline still runs end-to-end without an API key;
swap in call_llm() with the FAQ text as context (a tiny RAG) for the real thing.
"""

from state import MerchantApplication, Stage
from llm import call_llm, USE_LLM, LLMCallError

FAQ = {
    "approval time": "Most applications are reviewed within 2-3 business days after all documents are submitted.",
    "international": "International card transactions carry an additional 1% cross-border fee.",
    "missing document": "You can submit missing documents any time before final review; incomplete applications are paused, not rejected.",
    "volume limit": "Volume limits are set based on your risk tier and can be increased after 90 days of clean transaction history.",
    "restricted": "Some industries require additional compliance review; this does not automatically mean rejection.",
    "settlement": "Settlement time is T+2 business days by default, T+1 available for accounts in good standing after 6 months.",
}


def _match_faq(question: str) -> str:
    q = question.lower()
    for key, answer in FAQ.items():
        if key in q:
            return answer
    return "This question needs a human reviewer — it doesn't match our standard onboarding FAQ."


def run(app: MerchantApplication) -> MerchantApplication:
    for question in app.questions:
        answer = None
        if USE_LLM:
            try:
                context = "\n".join(f"- {k}: {v}" for k, v in FAQ.items())
                answer = call_llm(
                    system_prompt=(
                        "You are a merchant onboarding assistant. Answer briefly and factually "
                        f"using only this FAQ context:\n{context}\n"
                        "If the question isn't covered, say it needs a human reviewer."
                    ),
                    user_prompt=question,
                )
            except LLMCallError as e:
                # real call failed (network, rate limit, bad key) - fall back rather than crash
                app.kyc_flags.append(f"QA_LLM_FALLBACK: {e}")
                answer = _match_faq(question)
        else:
            answer = _match_faq(question)
        app.qa_answers[question] = answer

    app.stage = Stage.APPROVED  # QA is the last stop before final decision routing
    app.log_handoff(
        from_agent="onboarding_qa",
        to_agent="orchestrator",
        reason=f"answered {len(app.questions)} question(s), routing to final decision",
    )
    return app