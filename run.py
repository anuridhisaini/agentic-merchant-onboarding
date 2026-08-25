"""
Entry point. Runs every mock application through the full agent pipeline,
prints per-application results, the handoff log for one example, and
aggregate metrics (the numbers you want for Day 8 of the buildathon plan).

Usage:
    python run.py            # run everything, print summary
    python run.py --verbose  # also print full handoff log per application
"""

import sys
import json
from collections import Counter

from mock_data import load_mock_applications
import orchestrator


def print_handoff_log(app):
    print(f"\n  Handoff log for {app.application_id} ({app.business_name}):")
    for entry in app.handoff_log:
        e = entry.to_dict()
        print(f"    [{e['timestamp']}] {e['from']:>15} -> {e['to']:<18} | {e['reason']}")


def main():
    verbose = "--verbose" in sys.argv
    applications = load_mock_applications()

    results = []
    decisions = Counter()
    scenario_outcomes = {}
    total_handoffs = 0
    total_retries = 0

    for app in applications:
        result = orchestrator.run(app)
        results.append(result)
        decisions[result.final_decision] += 1
        total_handoffs += len(result.handoff_log)
        total_retries += sum(result.retry_counts.values())
        scenario_outcomes.setdefault(result.scenario_tag, []).append(result.final_decision)

        status_line = (
            f"{result.application_id:<8} {result.business_name:<28} "
            f"[{result.scenario_tag:<20}] -> {result.final_decision:<10} "
            f"({result.decision_reason})"
        )
        print(status_line)
        if verbose:
            print_handoff_log(result)

    print("\n" + "=" * 90)
    print("AGGREGATE METRICS")
    print("=" * 90)
    n = len(applications)
    print(f"Total applications processed: {n}")
    print(f"Decisions breakdown:")
    for decision, count in decisions.items():
        print(f"  {decision:<12}: {count:>3} ({100*count/n:.1f}%)")
    print(f"Average handoffs per application: {total_handoffs/n:.2f}")
    print(f"Total retries triggered: {total_retries}")
    print(f"Applications that required escalation: {decisions.get('escalated', 0)} "
          f"({100*decisions.get('escalated', 0)/n:.1f}%)")

    print(f"\nOutcome by scenario tag:")
    for tag, outcomes in scenario_outcomes.items():
        c = Counter(outcomes)
        outcome_str = ", ".join(f"{k}={v}" for k, v in c.items())
        print(f"  {tag:<20}: {outcome_str}")

    # dump full structured results for your report / appendix
    with open("run_results.json", "w") as f:
        json.dump([r.summary() for r in results], f, indent=2)
    print(f"\nFull structured results written to run_results.json")


if __name__ == "__main__":
    main()
