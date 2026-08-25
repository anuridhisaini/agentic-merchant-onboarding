"""
Single chokepoint for any LLM call in the system.

For the buildathon demo you can run everything rule-based (no API key needed,
100% reproducible for your metrics report). When you want an agent to actually
reason with an LLM (e.g. onboarding Q&A, or nuanced risk explanations),
flip USE_LLM = True and fill in call_llm() with a real Claude API call.

Keeping this in one place means:
  - swapping providers/models touches one function
  - you can inject failures here for Day 6 testing (see simulate_timeout)
"""

import random
import time

USE_LLM = False  # flip to True once you wire up a real API key


class AgentTimeoutError(Exception):
    pass


def call_llm(system_prompt: str, user_prompt: str, timeout_s: float = 5.0) -> str:
    """
    Real usage (uncomment and fill in when ready):

        import anthropic
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return resp.content[0].text

    For now this is a stub so the pipeline runs standalone.
    """
    if not USE_LLM:
        return "[LLM disabled - agent is using rule-based fallback logic]"
    raise NotImplementedError("Wire up your Claude API call here.")


def simulate_flaky_call(fail_rate: float = 0.15, min_latency=0.0, max_latency=0.05) -> None:
    """
    Used deliberately in Day 6 failure-handling tests to simulate an agent
    call that sometimes times out or is slow. Call this at the top of an
    agent function you want to stress-test.
    """
    time.sleep(random.uniform(min_latency, max_latency))
    if random.random() < fail_rate:
        raise AgentTimeoutError("Simulated agent timeout")
