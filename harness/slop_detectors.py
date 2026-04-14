"""Rule-based slop pattern detectors.

Each detector returns a list of hits with line number, matched text, and weight.
All detections are objective — no LLM judge required.

Based on community 'Gods' Prose' / slop-detection preset.
"""
import re


# ============================================================
# 1. THROAT-CLEARING OPENERS
# ============================================================
# Responses that open with narration of reception: "the words landed",
# "silence fell", "question hung in the air"
THROAT_CLEARING_PATTERNS = [
    r"^[^.!?]{0,60}?(the\s+)?words?\s+(landed|fell|hit|struck|washed|hung|settled)",
    r"^[^.!?]{0,60}?(the\s+)?(question|statement|accusation|answer|reply)\s+(hung|landed|fell|hit|struck)",
    r"^[^.!?]{0,60}?silence\s+(fell|settled|hung|stretched|deepened|returned)",
    r"^[^.!?]{0,60}?(a\s+)?(moment|beat|pause)\s+(hung|passed|stretched)",
    r"^[^.!?]{0,60}?(the\s+)?air\s+(grew|became|turned|thickened)",
]


def detect_throat_clearing(text: str) -> list[dict]:
    """Detect responses that open with reception narration."""
    hits = []
    # Check first sentence / first paragraph
    first_block = text.split("\n\n")[0][:200]

    for pattern in THROAT_CLEARING_PATTERNS:
        m = re.search(pattern, first_block, re.IGNORECASE)
        if m:
            hits.append({
                "detector": "throat_clearing",
                "match": m.group(),
                "weight": 5,
                "severity": "major",
                "rule": "Banned: opening with narration of how input arrived. Begin with response, not registration.",
            })
            break  # one hit per response is enough
    return hits


# ============================================================
# 2. NEGATION-ASSERTION PATTERNS
# ============================================================
# "It wasn't X. It was Y." — explaining instead of rendering
NEGATION_PATTERNS = [
    r"(?:it|this|that|there)\s+(?:wasn'?t|was\s+not|isn'?t|is\s+not)\s+[^.!?]{5,60}[.!?]\s+(?:it|this|that|there)\s+(?:was|is)",
    r"not\s+(?:quite|exactly|just|merely)\s+[a-z]+[,.]?\s+(?:but|rather|more\s+like)",
    r"(?:not|no)\s+[a-z]+\s+but\s+[a-z]+",  # "not a whisper but a demand"
]


def detect_negation_assertion(text: str) -> list[dict]:
    """Detect negation-assertion patterns (explaining instead of rendering)."""
    hits = []
    for pattern in NEGATION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            hits.append({
                "detector": "negation_assertion",
                "match": m.group()[:80],
                "weight": 3,
                "severity": "minor",
                "rule": "Banned: 'wasn't X but Y'. Delete the negation, state the assertion.",
            })
    return hits


# ============================================================
# 3. FILTER WORDS (tell not show)
# ============================================================
FILTER_PHRASES = [
    "noticed that", "noticed how",
    "felt that", "felt how", "felt as if", "felt like",
    "realized that", "realized how",
    "observed that", "observed how",
    "saw that", "saw how",
    "could tell that", "could tell how",
    "knew that", "knew how",
    "watched as", "watched how",
    "sensed that", "sensed how",
    "understood that", "understood how",
]


def detect_filter_words(text: str) -> list[dict]:
    """Detect filter word density."""
    text_lower = text.lower()
    hits = []
    total = 0
    for phrase in FILTER_PHRASES:
        count = text_lower.count(phrase)
        if count > 0:
            total += count
            hits.append({"phrase": phrase, "count": count})

    if not hits:
        return []

    # Normalize by response length (per 1000 chars)
    density = total / (len(text) / 1000) if len(text) > 0 else 0

    severity = "minor"
    weight = 2
    if density > 3:
        severity = "major"
        weight = 5

    return [{
        "detector": "filter_words",
        "match": f"{total} filter words, density {density:.1f}/1000 chars",
        "hits": hits[:5],
        "weight": weight,
        "severity": severity,
        "rule": "Filter words ('noticed that', 'felt that') distance the reader. Show directly.",
    }]


# ============================================================
# 4. FRAGMENTARY CHOPPINESS
# ============================================================
# Overusing short nominal strings: "Footsteps. Heavy. Familiar."
def detect_fragmentary_choppiness(text: str) -> list[dict]:
    """Detect excessive use of fragmentary sentences."""
    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) < 5:
        return []

    # Count very short sentences (< 4 words)
    short = [s for s in sentences if len(s.split()) <= 3]
    short_ratio = len(short) / len(sentences)

    # Look for consecutive short sentences (the real tell)
    max_consecutive = 0
    current = 0
    for s in sentences:
        if len(s.split()) <= 3:
            current += 1
            max_consecutive = max(max_consecutive, current)
        else:
            current = 0

    hits = []
    if max_consecutive >= 4:
        hits.append({
            "detector": "fragmentary_choppiness",
            "match": f"{max_consecutive} consecutive fragments",
            "weight": 5,
            "severity": "major",
            "rule": "Overusing fragments as technique. Merge: 'Footsteps. Heavy. Familiar.' → 'Heavy, familiar footsteps.'",
        })
    elif short_ratio > 0.35:
        hits.append({
            "detector": "fragmentary_choppiness",
            "match": f"{short_ratio:.0%} of sentences are fragments",
            "weight": 3,
            "severity": "minor",
            "rule": "Too many fragments. Fragments should be emphasis, not default.",
        })
    return hits


# ============================================================
# 5. ABSTRACT MICROCORRECTIONS
# ============================================================
# "almost", "not quite", "barely" — but only when modifying abstract claims
MICROCORRECTION_PATTERNS = [
    r"\bsounded\s+(?:almost|not\s+quite|barely)\b",
    r"\bseemed\s+(?:almost|not\s+quite|barely)\b",
    r"\bfelt\s+(?:almost|not\s+quite|barely)\b",
    r"\blooked\s+(?:almost|not\s+quite|barely)\b",
    r"(?:almost|not\s+quite|barely)\s+(?:steady|calm|cool|composed|confident|sure|certain)",
]


def detect_microcorrections(text: str) -> list[dict]:
    """Detect abstract microcorrections that don't affect behavior."""
    hits = []
    for pattern in MICROCORRECTION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            hits.append({
                "detector": "abstract_microcorrection",
                "match": m.group(),
                "weight": 2,
                "severity": "minor",
                "rule": "'Almost steady' without observable detail is weak hedging. Show it or drop it.",
            })
    return hits[:3]  # cap at 3


# ============================================================
# 6. VOICE-SOUND STATEMENTS
# ============================================================
# "the voice sounded steady/flat/muffled"
VOICE_STATEMENT_PATTERNS = [
    r"(?:her|his|their|the)\s+voice\s+(?:sounded|was)\s+(?:steady|flat|muffled|strained|shaky|quiet|soft|hard|cold|warm|higher|lower)",
    r"(?:her|his|their|the)\s+tone\s+(?:sounded|was)\s+(?:steady|flat|muffled|strained|shaky|quiet|soft|hard|cold|warm|higher|lower)",
]


def detect_voice_statements(text: str) -> list[dict]:
    """Detect lazy 'voice sounded X' statements."""
    hits = []
    for pattern in VOICE_STATEMENT_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            hits.append({
                "detector": "voice_statement",
                "match": m.group(),
                "weight": 2,
                "severity": "minor",
                "rule": "Show how the character achieves the tone, or how another character perceives it.",
            })
    return hits[:3]


# ============================================================
# 7. BLUSH ANIMATION
# ============================================================
# "paint spread from X to Y", "creeping blush", "spreading heat"
BLUSH_ANIMATION_PATTERNS = [
    r"(?:blush|flush|color|heat|red(?:ness)?|paint)\s+(?:spread|crept|crawled|climbed|traveled|rushed|flooded|rose)",
    r"(?:spreading|creeping|climbing|crawling)\s+(?:blush|flush|heat|red(?:ness)?|color)",
    r"(?:blush|flush)\s+(?:spread|rose|crept)\s+(?:from|across|up|over|along)",
    r"(?:color|red)\s+(?:climbed|crept|crawled)\s+(?:up|from|across|her|his)",
    r"(?:heat|warmth)\s+(?:climbed|crept|crawled|spread)\s+(?:up|from|across|her|his)",
]


def detect_blush_animation(text: str) -> list[dict]:
    """Detect dramatic blush-tracking cliches."""
    hits = []
    for pattern in BLUSH_ANIMATION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            hits.append({
                "detector": "blush_animation",
                "match": m.group(),
                "weight": 3,
                "severity": "minor",
                "rule": "Don't track blush route. Use minimalist marker or body language.",
            })
    return hits[:2]


# ============================================================
# 8. SELF-NEGATION LOOPS
# ============================================================
# Character thinks "stop" / "don't" while continuing the action
SELF_NEGATION_PATTERNS = [
    r"`[^`]*(?:stop|don't|can't|shouldn't|no,?\s)[^`]*`[^`]{0,200}?(?:kept|continued|couldn't\s+stop|went\s+on)",
    r"\*[^*]*(?:stop|don't|can't|shouldn't)[^*]*\*[^*]{0,200}?(?:kept|continued)",
]


def detect_self_negation_loop(text: str) -> list[dict]:
    """Detect 'mental stop while action continues' loops."""
    hits = []
    for pattern in SELF_NEGATION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            hits.append({
                "detector": "self_negation_loop",
                "match": m.group()[:100],
                "weight": 3,
                "severity": "minor",
                "rule": "Mental 'stop' + actual 'no stop' = bad writing. Show loss of control, not denial.",
            })
    return hits


# ============================================================
# 9. RHETORICAL MID-SENTENCE QUESTIONS
# ============================================================
# "Was it fear? Or something else?" — AI fingerprint
def detect_rhetorical_questions(text: str) -> list[dict]:
    """Detect rhetorical questions within narration (not character thought)."""
    hits = []
    # Find narrative questions (not inside quotes or thought backticks)
    # Pattern: ? followed by another short question in narration
    pattern = r"\?\s+(?:Or|Perhaps|Maybe|But)\s+[^.!?]{3,40}\?"
    for m in re.finditer(pattern, text):
        # Skip if inside quotes
        before = text[:m.start()]
        if before.count('"') % 2 == 1:
            continue
        hits.append({
            "detector": "rhetorical_question",
            "match": m.group()[:80],
            "weight": 2,
            "severity": "minor",
            "rule": "AI fingerprint: rhetorical 'Or was it?' questions in narration.",
        })
    return hits[:3]


# ============================================================
# 10. SNAPPY TRIADS
# ============================================================
# "A X, a Y, a Z" — three-part listing as default rhythm
def detect_snappy_triads(text: str) -> list[dict]:
    """Detect overuse of three-part parallel lists."""
    # Pattern: "a/an X, a/an Y, a/an Z" or "X, Y, Z" as standalone sentence
    pattern = r"[.!?]\s+(?:A|An|The)\s+\w+[,.]\s+(?:a|an|the)\s+\w+[,.]\s+(?:a|an|the)\s+\w+[.!?]"
    hits = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        hits.append({
            "detector": "snappy_triad",
            "match": m.group()[:80],
            "weight": 2,
            "severity": "minor",
            "rule": "AI fingerprint: three-part parallel lists used as rhythm default.",
        })
    return hits[:3]


# ============================================================
# MASTER DETECTOR
# ============================================================
def detect_all_slop(text: str) -> dict:
    """Run all slop detectors and return aggregated results."""
    all_hits = []
    all_hits.extend(detect_throat_clearing(text))
    all_hits.extend(detect_negation_assertion(text))
    all_hits.extend(detect_filter_words(text))
    all_hits.extend(detect_fragmentary_choppiness(text))
    all_hits.extend(detect_microcorrections(text))
    all_hits.extend(detect_voice_statements(text))
    all_hits.extend(detect_blush_animation(text))
    all_hits.extend(detect_self_negation_loop(text))
    all_hits.extend(detect_rhetorical_questions(text))
    all_hits.extend(detect_snappy_triads(text))

    total_weight = sum(h["weight"] for h in all_hits)
    by_detector = {}
    for h in all_hits:
        d = h["detector"]
        by_detector.setdefault(d, []).append(h)

    # Length-normalized: slop density per 1000 chars
    text_len = max(100, len(text))
    weight_per_1k = total_weight * 1000 / text_len

    return {
        "total_hits": len(all_hits),
        "total_weight": total_weight,
        "weight_per_1k_chars": round(weight_per_1k, 2),
        "by_detector": by_detector,
        "hits": all_hits,
    }
