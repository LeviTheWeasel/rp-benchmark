"""Main benchmark runner — generates RP responses and judges them."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .api import generate_rp_response, judge_response
from .config import (
    JUDGE_MODELS,
    TEST_MODELS,
    PROMPTS_DIR,
    RESULTS_DIR,
    BENCHMARK_FILE,
    PROJECT_ROOT,
)


def load_judge_prompt(judge_key: str, mode: str = "standard") -> str:
    """Load the appropriate judge system prompt.

    Modes: "standard" (1-5 scale), "flaw_hunter" (100-point deduction), "comparative" (A/B)
    """
    if mode == "flaw_hunter":
        return (PROMPTS_DIR / "judge_flaw_hunter.md").read_text()
    elif mode == "comparative":
        return (PROMPTS_DIR / "judge_comparative.md").read_text()
    else:
        if "claude" in judge_key:
            return (PROMPTS_DIR / "judge_claude.md").read_text()
        return (PROMPTS_DIR / "judge_gpt.md").read_text()


def load_benchmark() -> dict:
    with open(BENCHMARK_FILE) as f:
        return json.load(f)


# Lorebook source -> file mapping
LOREBOOK_MAP = {
    "ryujin_high": PROJECT_ROOT / "raw" / "lorebook_ryujin.json",
    "valen": PROJECT_ROOT / "raw" / "lorebook_esperia.json",
}

_lorebook_cache: dict = {}


def load_lorebook(source_chat: str) -> dict | None:
    """Load processed lorebook for a source chat if available."""
    if source_chat in _lorebook_cache:
        return _lorebook_cache[source_chat]

    path = LOREBOOK_MAP.get(source_chat)
    if path and path.exists():
        with open(path) as f:
            _lorebook_cache[source_chat] = json.load(f)
        return _lorebook_cache[source_chat]
    return None


def build_lorebook_context(lorebook: dict, conversation_text: str, max_entries: int = 15) -> str:
    """Simulate lorebook keyword matching and format entries for injection."""
    bundle = []

    # Always include constants
    for entry in lorebook.get("constant_entries", []):
        bundle.append(entry)

    # Match keyword entries
    text_lower = conversation_text.lower()
    scored = []
    for entry in lorebook.get("keyword_entries", []):
        hits = sum(1 for kw in entry.get("keywords", []) if kw.lower() in text_lower)
        if hits > 0:
            scored.append((hits, entry))

    scored.sort(key=lambda x: -x[0])
    bundle.extend(e for _, e in scored[: max_entries - len(bundle)])

    if not bundle:
        return ""

    lines = ["[World Info / Lorebook Entries]"]
    for entry in bundle:
        name = entry.get("name", "")
        content = entry.get("content", "")
        if name:
            lines.append(f"\n## {name}")
        lines.append(content)

    return "\n".join(lines)


def build_generation_prompt(scenario: dict) -> tuple[str, str]:
    """Build system + user prompts for RP generation from a scenario.

    Returns (system_prompt, user_message).
    """
    char_name = scenario.get("character_name", "Character")
    user_name = scenario.get("user_name", "User")

    system_prompt = (
        f"You are roleplaying as {char_name}. Write in third-person past tense. "
        f"Stay in character. Do not write actions or dialogue for {user_name} — "
        f"they are controlled by the user. Write a natural continuation of the "
        f"conversation that matches {char_name}'s established voice and personality."
    )

    # Inject lorebook if available
    source_chat = scenario.get("source_chat", "")
    lorebook = load_lorebook(source_chat)
    if lorebook:
        conversation_text = " ".join(
            msg.get("content", "") for msg in scenario.get("context", [])
        )
        lorebook_text = build_lorebook_context(lorebook, conversation_text)
        if lorebook_text:
            system_prompt += f"\n\n{lorebook_text}"

    # Format conversation history
    context_lines = []
    for msg in scenario.get("context", []):
        name = msg.get("name", msg.get("role", ""))
        content = msg.get("content", "").strip()
        if content:
            context_lines.append(f"{name}: {content}")

    user_message = "\n\n".join(context_lines)
    user_message += f"\n\n[Continue as {char_name}. Write your next response.]"

    return system_prompt, user_message


def build_judge_payload(
    scenario: dict,
    generated_response: str,
    mode: str = "single",
) -> str:
    """Build the evaluation payload for the judge."""
    # Format context
    context_lines = []
    for msg in scenario.get("context", []):
        name = msg.get("name", msg.get("role", ""))
        content = msg.get("content", "").strip()
        if content:
            context_lines.append(f"**{name}** ({msg.get('role', '')}):\n{content}")

    context_text = "\n\n---\n\n".join(context_lines)

    # Add lorebook context for judge if available
    lorebook_section = ""
    source_chat = scenario.get("source_chat", "")
    lorebook = load_lorebook(source_chat)
    if lorebook:
        conversation_text = " ".join(
            msg.get("content", "") for msg in scenario.get("context", [])
        )
        lorebook_text = build_lorebook_context(lorebook, conversation_text, max_entries=10)
        if lorebook_text:
            lorebook_section = f"\n\n<lorebook>\n{lorebook_text}\n</lorebook>\n\nNOTE: The lorebook above contains world info that was available to the AI during generation. Score dimension 3.12 (Context Integration) on how well the response uses this information — seamlessly woven vs exposition-dumped, factually accurate, and thematically integrated."

    char_name = scenario.get("character_name", "Unknown")
    user_name = scenario.get("user_name", "Unknown")

    return f"""<context>
{context_text}
</context>

<character_card>
Character: {char_name}
User character: {user_name}
</character_card>
{lorebook_section}

<response_to_evaluate>
{generated_response}
</response_to_evaluate>

<evaluation_mode>{mode}</evaluation_mode>"""


def _extract_source_label(scenario_id: str, scenario_type: str) -> str:
    """Extract a readable source label from a scenario ID.

    'ooc_sukuna_7' -> 'ref:sukuna'
    'degradation_sukuna_0' -> 'ref:sukuna'
    'swipe_valen_228' -> 'ref:valen'
    """
    # Try to find a known source name in the scenario ID
    sources = ["sukuna", "valen", "strovolos", "ryujin", "bell", "erp"]
    for source in sources:
        if source in scenario_id.lower():
            return "ref:%s" % source

    return "ref:%s" % scenario_type


def run_single_scenario(
    scenario: dict,
    test_model_key: str,
    test_model_id: str,
    judge_configs: dict[str, str],
    judge_mode: str = "standard",
) -> dict:
    """Run one scenario: generate response, then judge it with all judges.

    Returns a result dict with generation + all judge scores.
    """
    scenario_id = scenario.get("id", "unknown")
    print(f"  Generating with {test_model_key}...")

    # Step 1: Generate RP response
    system_prompt, user_message = build_generation_prompt(scenario)
    gen_result = generate_rp_response(test_model_id, system_prompt, user_message)
    generated_text = gen_result["content"]

    print(f"    Generated {len(generated_text)} chars")

    # Step 2: Judge with each judge model
    judge_payload = build_judge_payload(scenario, generated_text)
    judge_results = _run_judges(judge_payload, judge_configs, judge_mode=judge_mode)

    return {
        "scenario_id": scenario_id,
        "test_model": test_model_key,
        "test_model_id": test_model_id,
        "generation": {
            "content": generated_text,
            "usage": gen_result["usage"],
            "model": gen_result["model"],
        },
        "judges": judge_results,
    }


def run_prebuilt_scenario(
    payload: dict,
    judge_configs: dict[str, str],
) -> dict:
    """Judge a prebuilt payload (OOC corrections, degradation comparisons).

    No generation needed — the response to evaluate is already in the payload.
    """
    scenario_id = payload.get("scenario_id", "unknown")
    # Label by source: "ooc_sukuna_7" -> "ref:sukuna", "degradation_sukuna_0" -> "ref:sukuna"
    source_label = _extract_source_label(scenario_id, payload.get("type", ""))
    print("  Judging prebuilt: %s [%s]" % (scenario_id, source_label))

    judge_results = _run_judges(payload["user_content"], judge_configs)

    return {
        "scenario_id": scenario_id,
        "test_model": source_label,
        "test_model_id": None,
        "is_reference": True,
        "type": payload.get("type", "prebuilt"),
        "judges": judge_results,
        "expected_low_dimensions": payload.get("expected_low_dimensions"),
        "expected_winner": payload.get("expected_winner"),
        "ground_truth_winner": payload.get("ground_truth_winner"),
    }


def _run_judges(
    judge_payload: str,
    judge_configs: dict[str, str],
    judge_mode: str = "standard",
) -> dict:
    """Run all judges on a payload."""
    judge_results = {}

    for judge_key, judge_model_id in judge_configs.items():
        print(f"    Judging with {judge_key} ({judge_mode})...")
        judge_system = load_judge_prompt(judge_key, mode=judge_mode)

        result = judge_response(judge_model_id, judge_system, judge_payload)
        judge_results[judge_key] = {
            "scores": result["scores"],
            "usage": result["usage"],
            "model": result["model"],
            "judge_mode": judge_mode,
        }

        if result["scores"].get("parse_error"):
            print(f"      WARNING: Failed to parse judge JSON")

    return judge_results


def run_benchmark(
    test_models: dict[str, str] | None = None,
    judge_models: dict[str, str] | None = None,
    scenario_filter: list[str] | None = None,
    scenario_types: list[str] | None = None,
    max_scenarios: int | None = None,
    language: str | None = None,
    judge_mode: str = "standard",
) -> dict:
    """Run the full benchmark pipeline.

    Args:
        test_models: Dict of {name: model_id} for models to benchmark.
                     Defaults to all TEST_MODELS.
        judge_models: Dict of {name: model_id} for judge models.
                      Defaults to all JUDGE_MODELS.
        scenario_filter: List of scenario IDs to run. None = all.
        scenario_types: List of scenario types to include ("completion", "preference", "consistency").
                        None = completion only (for generation benchmarking).
        max_scenarios: Limit number of scenarios (for testing).
    """
    if test_models is None:
        test_models = TEST_MODELS
    if judge_models is None:
        judge_models = JUDGE_MODELS
    if scenario_types is None:
        scenario_types = ["completion"]

    benchmark = load_benchmark()

    # Types that need generation vs types that are prebuilt (judge-only)
    generation_types = {"completion"}
    prebuilt_types = {"ooc_correction", "degradation", "preference", "consistency"}

    # Collect scenarios by mode
    gen_scenarios = []
    prebuilt_payloads = []

    for stype in scenario_types:
        items = benchmark["scenarios"].get(stype, [])
        if stype in generation_types:
            gen_scenarios.extend(items)
        elif stype in prebuilt_types:
            # Load prebuilt payloads from the payloads file
            payloads_file = PROJECT_ROOT / "eval_payloads_v2.json"
            if payloads_file.exists():
                with open(payloads_file) as f:
                    all_payloads = json.load(f)
                # Match by scenario IDs
                scenario_ids = {s["id"] for s in items}
                for p in all_payloads:
                    if p.get("scenario_id") in scenario_ids:
                        prebuilt_payloads.append(p)

    # Language filter
    if language:
        gen_scenarios = [s for s in gen_scenarios if s.get("language", "en") == language]
        # For prebuilt, filter by scenario ID patterns (ru scenarios have russian source names)
        if language == "ru":
            ru_sources = {"lucian", "agora", "valdrian", "narlos", "rowena", "exiledking"}
            prebuilt_payloads = [p for p in prebuilt_payloads if any(src in p.get("scenario_id", "").lower() for src in ru_sources)]
        elif language == "en":
            ru_sources = {"lucian", "agora", "valdrian", "narlos", "rowena", "exiledking"}
            prebuilt_payloads = [p for p in prebuilt_payloads if not any(src in p.get("scenario_id", "").lower() for src in ru_sources)]

    if scenario_filter:
        gen_scenarios = [s for s in gen_scenarios if s["id"] in scenario_filter]
        prebuilt_payloads = [p for p in prebuilt_payloads if p["scenario_id"] in scenario_filter]

    if max_scenarios:
        total_available = len(gen_scenarios) + len(prebuilt_payloads)
        if total_available > max_scenarios:
            # Proportionally limit both
            ratio = max_scenarios / total_available
            gen_scenarios = gen_scenarios[:max(1, int(len(gen_scenarios) * ratio))]
            prebuilt_payloads = prebuilt_payloads[:max(1, int(len(prebuilt_payloads) * ratio))]

    total_scenarios = len(gen_scenarios) + len(prebuilt_payloads)
    gen_calls = len(gen_scenarios) * len(test_models) * (1 + len(judge_models))
    prebuilt_calls = len(prebuilt_payloads) * len(judge_models)

    print(f"RP-Bench Run")
    print(f"  Generation scenarios: {len(gen_scenarios)} (need model responses)")
    print(f"  Prebuilt scenarios: {len(prebuilt_payloads)} (judge-only)")
    print(f"  Test models: {list(test_models.keys())}")
    print(f"  Judge models: {list(judge_models.keys())}")
    print(f"  Total API calls: ~{gen_calls + prebuilt_calls}")
    print()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    results = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "test_models": test_models,
            "judge_models": judge_models,
            "scenario_count": total_scenarios,
            "scenario_types": scenario_types,
        },
        "results": [],
    }

    step = 0

    # Run generation scenarios (generate + judge)
    for i, scenario in enumerate(gen_scenarios):
        scenario_id = scenario.get("id", f"scenario_{i}")
        step += 1
        print(f"[{step}/{total_scenarios}] {scenario_id} (generate+judge)")

        for model_key, model_id in test_models.items():
            try:
                result = run_single_scenario(
                    scenario, model_key, model_id, judge_models,
                    judge_mode=judge_mode,
                )
                results["results"].append(result)
            except Exception as e:
                print(f"    ERROR: {e}")
                results["results"].append({
                    "scenario_id": scenario_id,
                    "test_model": model_key,
                    "error": str(e),
                })

    # Run prebuilt scenarios (judge-only)
    for i, payload in enumerate(prebuilt_payloads):
        scenario_id = payload.get("scenario_id", f"prebuilt_{i}")
        step += 1
        print(f"[{step}/{total_scenarios}] {scenario_id} (judge-only)")

        try:
            result = run_prebuilt_scenario(payload, judge_models)
            results["results"].append(result)
        except Exception as e:
            print(f"    ERROR: {e}")
            results["results"].append({
                "scenario_id": scenario_id,
                "test_model": "prebuilt",
                "error": str(e),
            })

    # Save results
    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = RESULTS_DIR / f"run_{run_id}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {output_path}")
    return results
