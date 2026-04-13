"""
Format benchmark scenarios into evaluation payloads for the judge prompts.
Takes scenarios from benchmark_v0.1.json and produces ready-to-send judge inputs.
"""
import json
import sys
from pathlib import Path


def format_context(messages: list[dict]) -> str:
    """Format a list of messages into readable conversation context."""
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        name = msg.get("name", role)
        content = msg.get("content", "").strip()
        if not content:
            continue
        # Truncate very long messages for context
        if len(content) > 2000:
            content = content[:2000] + "\n[... truncated ...]"
        lines.append(f"**{name}** ({role}):\n{content}\n")
    return "\n---\n".join(lines)


def format_single_eval(scenario: dict) -> dict:
    """Format a completion scenario into a judge payload."""
    context_text = format_context(scenario["context"])
    response_text = scenario["reference_response"]

    user_content = f"""<context>
{context_text}
</context>

<character_card>
Character: {scenario.get('character_name', 'Unknown')}
User character: {scenario.get('user_name', 'Unknown')}
</character_card>

<response_to_evaluate>
{response_text}
</response_to_evaluate>

<evaluation_mode>single</evaluation_mode>"""

    return {
        "scenario_id": scenario["id"],
        "type": "single",
        "user_content": user_content,
    }


def format_comparison_eval(scenario: dict) -> dict:
    """Format a swipe comparison scenario into a judge payload."""
    context_text = format_context(scenario["context"])

    variants_text = ""
    for variant in scenario["variants"]:
        letter = variant["id"]
        content = variant["content"].strip()
        if not content:
            continue
        if len(content) > 3000:
            content = content[:3000] + "\n[... truncated ...]"
        variants_text += f"\n### Response {letter}\n{content}\n"

    user_content = f"""<context>
{context_text}
</context>

<response_to_evaluate>
{variants_text}
</response_to_evaluate>

<evaluation_mode>comparison</evaluation_mode>"""

    return {
        "scenario_id": scenario["id"],
        "type": "comparison",
        "user_content": user_content,
        "ground_truth_winner": next(
            (v["id"] for v in scenario["variants"] if v["is_accepted"]), None
        ),
    }


def format_consistency_eval(scenario: dict) -> dict:
    """Format a consistency probe into a judge payload."""
    setup_text = format_context(scenario["setup_context"])
    test_text = format_context(scenario["test_context"])

    user_content = f"""<context>
## Setup Context (established facts and character traits)
{setup_text}

## [GAP: {scenario['gap_size']} messages not shown]

## Test Context (evaluate consistency with setup)
{test_text}
</context>

<evaluation_mode>consistency</evaluation_mode>

Probe question: {scenario['probe_question']}"""

    return {
        "scenario_id": scenario["id"],
        "type": "consistency",
        "user_content": user_content,
    }


def format_ooc_correction_eval(scenario: dict) -> dict:
    """Format an OOC correction scenario — a known failure to score."""
    context_text = format_context(scenario["context"])
    failed = scenario.get("failed_response", {})
    failed_text = failed.get("content", "").strip()

    correction_types = ", ".join(scenario.get("correction_types", []))
    correction_text = scenario.get("correction_text", "")[:300]

    user_content = f"""<context>
{context_text}
</context>

<response_to_evaluate>
{failed_text}
</response_to_evaluate>

<evaluation_mode>single</evaluation_mode>

NOTE: This response triggered a user OOC correction. The user said:
"{correction_text}"
Correction categories: {correction_types}

Score this response honestly — it is expected to have issues in the flagged areas."""

    return {
        "scenario_id": scenario["id"],
        "type": "ooc_correction",
        "user_content": user_content,
        "expected_low_dimensions": scenario.get("correction_types", []),
    }


def format_degradation_eval(scenario: dict) -> dict:
    """Format a degradation comparison — strong vs collapsed response."""
    strong = scenario["strong_phase"]
    collapse = scenario["collapse_phase"]

    strong_context = format_context(strong.get("context", []))
    collapse_context = format_context(collapse.get("context", []))

    user_content = f"""<context>
## Response A context (early in conversation)
{strong_context}
</context>

<response_to_evaluate>
### Response A (early conversation, message #{strong['message_index']})
{strong['response'][:3000]}

### Response B (late conversation, message #{collapse['message_index']})
{collapse['response'][:3000]}
</response_to_evaluate>

<evaluation_mode>comparison</evaluation_mode>

NOTE: These are from the SAME conversation at different points. Response A is from early when quality was reported as high. Response B is from late when the user reported quality degradation. Score each independently."""

    return {
        "scenario_id": scenario["id"],
        "type": "degradation_comparison",
        "user_content": user_content,
        "expected_winner": "A",
    }


def main():
    benchmark_path = Path(__file__).parent.parent / "benchmark_v0.2.json"
    output_path = Path(__file__).parent.parent / "eval_payloads_v2.json"

    with open(benchmark_path) as f:
        benchmark = json.load(f)

    payloads = []

    # Process each scenario type
    for scenario in benchmark["scenarios"].get("preference", []):
        payloads.append(format_comparison_eval(scenario))

    for scenario in benchmark["scenarios"].get("completion", []):
        payloads.append(format_single_eval(scenario))

    for scenario in benchmark["scenarios"].get("consistency", []):
        payloads.append(format_consistency_eval(scenario))

    for scenario in benchmark["scenarios"].get("ooc_correction", []):
        payloads.append(format_ooc_correction_eval(scenario))

    for scenario in benchmark["scenarios"].get("degradation", []):
        payloads.append(format_degradation_eval(scenario))

    with open(output_path, "w") as f:
        json.dump(payloads, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(payloads)} evaluation payloads:")
    by_type = {}
    for p in payloads:
        by_type.setdefault(p["type"], []).append(p)
    for t, items in by_type.items():
        print(f"  {t}: {len(items)}")

    # Also output a single example for testing
    example_path = Path(__file__).parent.parent / "eval_payload_example.json"
    with open(example_path, "w") as f:
        json.dump(payloads[0], f, indent=2, ensure_ascii=False)
    print(f"\nExample payload saved to {example_path}")


if __name__ == "__main__":
    main()
