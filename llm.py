"""
Single chokepoint for any LLM call in the system.

USE_LLM auto-detects: if ANTHROPIC_API_KEY is set in your environment, the
onboarding Q&A agent uses real Claude calls. If not, it falls back to the
rule-based FAQ lookup automatically — so the pipeline NEVER breaks just
because a key isn't set. This means the same code works for your local dev
(with a key) and a judge cloning the repo cold (without one).

Keeping this in one place means:
  - swapping providers/models touches one function
  - you can inject failures here for Day 6 testing (see simulate_flaky_call)
"""

import os
import random
import time

# Auto-detect: use real Claude calls only if a key is actually present.
USE_LLM = bool(os.environ.get("ANTHROPIC_API_KEY"))

_client = None  # lazy-initialized so importing this module never requires the package


class AgentTimeoutError(Exception):
    pass


class LLMCallError(Exception):
    """Raised when a real API call fails (network, auth, rate limit, etc.)."""
    pass


def _get_client():
    global _client
    if _client is None:
        import anthropic  # imported lazily so `pip install anthropic` is only needed when USE_LLM is True
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env automatically
    return _client


def call_llm(system_prompt: str, user_prompt: str, timeout_s: float = 5.0) -> str:
    """
    Makes a real Claude API call if ANTHROPIC_API_KEY is set, otherwise raises
    so the caller can fall back to rule-based logic. Callers (e.g. onboarding_qa.py)
    should wrap this in try/except and fall back gracefully — never let a flaky
    network call take down the whole pipeline.
    """
    if not USE_LLM:
        raise LLMCallError("No ANTHROPIC_API_KEY set in environment; falling back to rule-based logic.")

    try:
        client = _get_client()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=timeout_s,
        )
        return resp.content[0].text
    except Exception as e:
        raise LLMCallError(f"Claude API call failed: {e}") from e


def simulate_flaky_call(fail_rate: float = 0.15, min_latency=0.0, max_latency=0.05) -> None:
    """
    Used deliberately in Day 6 failure-handling tests to simulate an agent
    call that sometimes times out or is slow. Call this at the top of an
    agent function you want to stress-test.
    """
    time.sleep(random.uniform(min_latency, max_latency))
    if random.random() < fail_rate:
        raise AgentTimeoutError("Simulated agent timeout")