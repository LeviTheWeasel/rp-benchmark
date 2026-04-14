"""Objective text metrics for RP responses — no LLM judge required.

These catch what subjective judges miss and can't be gamed.
"""
import re
from collections import Counter

# Known AI-ese phrases that bleed through from training data
# Curated from RP community complaints and observation
AI_CLICHES = {
    # Sexual / intimate cliches
    "ministrations": 3,  # weight — how bad is this cliche
    "core of his being": 3,
    "core of her being": 3,
    "with renewed vigor": 3,
    "sent shivers down": 3,
    "shivers ran down": 3,
    "shivers coursed": 3,
    "breath hitched": 2,
    "breath caught": 2,
    "pupils dilated": 2,
    "ragged breath": 2,
    "a moan escaped": 2,
    "primal need": 3,
    "intoxicating scent": 3,
    "forbidden fruit": 3,
    "coiled serpent": 3,

    # Emotional cliches
    "a whirlwind of emotions": 3,
    "heart skipped a beat": 2,
    "heart hammered": 2,
    "mind racing": 2,
    "the weight of the world": 3,
    "storm of emotions": 3,
    "turmoil of emotions": 3,
    "a pit formed in": 2,

    # Descriptive cliches
    "dance of": 2,  # "dance of shadows", "dance of light and dark"
    "ballet of": 3,
    "symphony of": 3,
    "a mosaic of": 2,
    "tapestry of": 2,
    "kaleidoscope of": 3,
    "a stark contrast": 2,
    "echoing through": 2,
    "reverberating through": 2,
    "painted in hues of": 3,
    "bathed in golden light": 3,
    "dappled sunlight": 2,

    # Action/body cliches
    "eyes darkened": 2,
    "eyes flashed": 2,
    "jaw tightened": 2,
    "jaw clenched": 2,
    "lips curved into": 2,
    "a ghost of a smile": 2,
    "a smirk played": 2,
    "an eyebrow arched": 2,
    "a chuckle escaped": 2,
    "ran a hand through": 2,
    "pinched the bridge": 2,

    # Narrative cliches
    "little did they know": 3,
    "as if on cue": 3,
    "time seemed to stand still": 3,
    "the air grew thick": 2,
    "tension thickened": 2,
    "crackled with tension": 2,
    "electricity in the air": 3,
    "sent ripples through": 3,
    "a shudder ran": 2,
    "visceral reaction": 2,

    # Fantasy/Drama cliches
    "fate would have it": 3,
    "gods themselves": 3,
    "bond forged in": 3,
    "a dangerous dance": 3,
    "knew no bounds": 3,
    "hung in the balance": 3,

    # Overused openers
    "the air was thick with": 2,
    "silence stretched": 2,
    "the moment hung": 2,
}


def count_cliches(text: str) -> dict:
    """Count AI-ese cliches in text. Returns detection report."""
    text_lower = text.lower()
    hits = []
    total_weight = 0

    for phrase, weight in AI_CLICHES.items():
        count = text_lower.count(phrase)
        if count > 0:
            hits.append({"phrase": phrase, "count": count, "weight": weight})
            total_weight += count * weight

    return {
        "total_hits": sum(h["count"] for h in hits),
        "total_weight": total_weight,
        "unique_cliches": len(hits),
        "hits": sorted(hits, key=lambda x: -x["weight"] * x["count"]),
    }


def type_token_ratio(text: str) -> float:
    """Vocabulary diversity. Higher = more varied vocabulary. Range ~0.3-0.7."""
    words = re.findall(r"\b[a-zA-Zа-яА-Я]+\b", text.lower())
    if len(words) < 10:
        return 0.0
    return len(set(words)) / len(words)


def sentence_length_variance(text: str) -> dict:
    """Measures sentence rhythm. Low variance = monotonous."""
    # Split on sentence-ending punctuation
    sentences = re.split(r"[.!?]+\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    if len(sentences) < 3:
        return {"count": len(sentences), "avg": 0, "stdev": 0, "min": 0, "max": 0}

    lengths = [len(s.split()) for s in sentences]
    avg = sum(lengths) / len(lengths)
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    stdev = variance ** 0.5

    return {
        "count": len(sentences),
        "avg": round(avg, 1),
        "stdev": round(stdev, 1),
        "min": min(lengths),
        "max": max(lengths),
        "rhythm_score": round(stdev / avg if avg > 0 else 0, 2),  # 0.3+ is good, <0.2 is monotonous
    }


def repetition_score(text: str) -> dict:
    """Detect repeated phrases within the same response. High score = bad."""
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if len(words) < 20:
        return {"bigrams": 0, "trigrams": 0, "score": 0}

    # Bigrams and trigrams that appear 2+ times
    bigrams = Counter(" ".join(words[i:i+2]) for i in range(len(words) - 1))
    trigrams = Counter(" ".join(words[i:i+3]) for i in range(len(words) - 2))

    # Filter out common function-word bigrams
    skip = {"of the", "in the", "to the", "on the", "and the", "for the", "with the", "at the", "by the", "from the", "she was", "he was", "it was"}
    bigram_repeats = sum(c for bg, c in bigrams.items() if c >= 2 and bg not in skip) - sum(
        (c - 1) for bg, c in bigrams.items() if c >= 2 and bg not in skip
    )
    bigram_hits = [(bg, c) for bg, c in bigrams.items() if c >= 2 and bg not in skip]
    trigram_hits = [(tg, c) for tg, c in trigrams.items() if c >= 2]

    return {
        "repeated_bigrams": len(bigram_hits),
        "repeated_trigrams": len(trigram_hits),
        "worst_bigram": max(bigram_hits, key=lambda x: x[1]) if bigram_hits else None,
        "worst_trigram": max(trigram_hits, key=lambda x: x[1]) if trigram_hits else None,
        "score": len(bigram_hits) + 3 * len(trigram_hits),  # trigrams worse than bigrams
    }


def dialogue_ratio(text: str) -> float:
    """What fraction of the response is dialogue vs narration.
    Too low = all narration (might feel heavy). Too high = no setting/action."""
    lines = text.split("\n")
    dialogue_chars = 0
    total_chars = 0
    for line in lines:
        total_chars += len(line)
        # Count chars inside quotes
        in_quote = False
        for c in line:
            if c in '"«»':
                in_quote = not in_quote
            elif in_quote:
                dialogue_chars += 1

    return round(dialogue_chars / total_chars, 2) if total_chars > 0 else 0


def compute_all(text: str) -> dict:
    """Run all objective metrics on a response."""
    return {
        "length": len(text),
        "word_count": len(text.split()),
        "cliches": count_cliches(text),
        "vocabulary_diversity": round(type_token_ratio(text), 3),
        "sentence_rhythm": sentence_length_variance(text),
        "repetition": repetition_score(text),
        "dialogue_ratio": dialogue_ratio(text),
    }


def objective_score(metrics: dict) -> dict:
    """Convert metrics into a 0-100 objective score.

    Starts at 100, deducts for objective flaws. Complements the flaw hunter
    judge which handles subjective flaws.
    """
    score = 100
    deductions = []

    # Cliche weight (up to -30)
    cliche_deduction = min(30, metrics["cliches"]["total_weight"] * 2)
    if cliche_deduction > 0:
        deductions.append({
            "type": "cliches",
            "amount": -cliche_deduction,
            "detail": f"{metrics['cliches']['total_hits']} cliches ({metrics['cliches']['unique_cliches']} unique)",
        })
        score -= cliche_deduction

    # Low vocabulary diversity (-10 if < 0.4, -20 if < 0.3)
    vd = metrics["vocabulary_diversity"]
    if vd < 0.3:
        deductions.append({"type": "low_diversity", "amount": -20, "detail": f"TTR={vd}"})
        score -= 20
    elif vd < 0.4:
        deductions.append({"type": "low_diversity", "amount": -10, "detail": f"TTR={vd}"})
        score -= 10

    # Monotonous rhythm (-10 if rhythm_score < 0.2)
    rhythm = metrics["sentence_rhythm"].get("rhythm_score", 1)
    if rhythm > 0 and rhythm < 0.2:
        deductions.append({"type": "monotonous_rhythm", "amount": -10, "detail": f"sentence length stdev/avg = {rhythm}"})
        score -= 10

    # Within-response repetition (-2 per repeated bigram, -5 per trigram, max -20)
    rep = metrics["repetition"]
    rep_deduction = min(20, rep["repeated_bigrams"] * 2 + rep["repeated_trigrams"] * 5)
    if rep_deduction > 0:
        detail = f"{rep['repeated_bigrams']} bigrams, {rep['repeated_trigrams']} trigrams"
        if rep.get("worst_trigram"):
            detail += f" (worst: '{rep['worst_trigram'][0]}' x{rep['worst_trigram'][1]})"
        deductions.append({"type": "repetition", "amount": -rep_deduction, "detail": detail})
        score -= rep_deduction

    return {
        "objective_score": max(0, score),
        "deductions": deductions,
        "raw_metrics": metrics,
    }
