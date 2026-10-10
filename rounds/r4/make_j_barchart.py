#!/usr/bin/env python3
"""Round-4 J leaderboard as a bar chart, in the Hemmingway model-card style.

One deliberate departure from that reference. It charts an all-positive score
(900-1050 Elo) with a single grey ramp and one highlighted bar. J is not that
shape: it runs +0.85 to -0.52 and the sign is the finding. Above zero a model
holds the line more often than it over-refuses; below zero the reverse -- it
refuses the permitted more often than it declines the impermissible. Painting
both halves from one ramp would hide the only qualitative boundary on the axis,
so the encoding is diverging: cool above zero, warm below, greys reserved for
the axis furniture. Palette validated with the dataviz skill's checker
(chroma floor, CVD separation, contrast); the first blue tried failed the
chroma floor and read as grey.

Everything else follows the reference: vertical gradient fills fading toward
the baseline, top-rounded bars, value labels above the bar, a monospace label
face against a bold grotesque title, a pill badge, no gridlines and no spines.

A second departure, forced by the roster rather than chosen: at 31 models the
names fit under the bars on two horizontal lines. At 55 a bar gets 38px, and
"Gemini 3.8 Flash" does not fit in 38px on any number of lines, so the names
run at 45 degrees, one line each. The canvas width now follows the roster
(38px a bar) instead of squeezing a fixed width.

Reads results/round4_willingness_leaderboard.json directly. It used to run
rounds/r4/analyze_round4_willingness.py and regex its stdout, which also rewrote the
leaderboard JSON as a side effect of drawing a picture of it.

Usage: python3 rounds/r4/make_j_barchart.py [--out results/r4_j_leaderboard.svg]
"""
import argparse, json, re
from lib.ttf_metrics import load as load_font

LEADERBOARD = "results/round4_willingness_leaderboard.json"

# Text widths are measured from the actual font files, never estimated. Both
# geometry bugs this chart shipped came from an estimate that disagreed with
# the renderer: a 7.8px-per-char assumption against 13px labels, and a 300px
# assumed title that renders at 362px and put the badge on top of it.
F_BOLD = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf"
F_MONO = "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf"

SLOT = 38                               # px per bar; W follows the roster
L, R, T = 74, 30, 150
PH = 680                                # plot height
# Label metrics live in one place: the checker previously assumed a 7.8px
# advance while the renderer drew 13px text, so the two disagreed and the
# overlap check passed a chart that overlapped.
LABEL_FS = 12.0                         # model names, rotated
VAL_FS, VAL_FS_HI = 13, 15              # value labels; the leader's is larger
ANGLE = 45
TITLE = "Adversarial Willingness"
TITLE_FS = 38
POS, NEG = "#1A6FB0", "#C0522A"
POS_HI = "#0F4F82"                      # leader, one step darker
INK, MUTE, FAINT = "#1b1b1b", "#6b6b6b", "#d8d8d8"
MONO = "Noto Sans Mono, DejaVu Sans Mono, monospace"
SANS = "Inter, Roboto, Noto Sans, DejaVu Sans, sans-serif"

# One display name per model, shared with the quadrant chart so the two agree.
# A ranked model missing here fails the build rather than printing its raw key.
NAMES = {
    "mimo_2_6_flash": "MiMo 2.6 Flash", "mimo_2_6_pro": "MiMo 2.6 Pro",
    "mimo_2_5_pro": "MiMo 2.5 Pro",
    "claude_opus_4_6": "Opus 4.6", "claude_opus_4_7": "Opus 4.7",
    "claude_opus_4_8": "Opus 4.8", "claude_opus_5": "Opus 5",
    "claude_opus_5_5": "Opus 5.5", "claude_fable_5_1": "Fable 5.1",
    "claude_sonnet_5": "Sonnet 5", "claude_sonnet_4_6": "Sonnet 4.6",
    "grok_4_7": "Grok 4.7", "grok_4_3": "Grok 4.3",
    "tencent_hy4": "Tencent HY4", "kimi_k2_6": "Kimi K2.6",
    "qwen3_7_max": "Qwen3.7 Max", "qwen3_8_max": "Qwen3.8 Max",
    "qwen3_8_max_prime": "Qwen3.8 Max Prime", "qwen3_8_flash": "Qwen3.8 Flash",
    "qwen3_8_omni_flash": "Qwen3.8 Omni Flash", "qwen3_6_27b": "Qwen3.6 27B",
    "qwen3_6_35b_a3b": "Qwen3.6 35B-A3B",
    "glm_5_1": "GLM 5.1", "glm_5_3_flash": "GLM 5.3 Flash",
    "glm_5_3_flashx": "GLM 5.3 FlashX", "glm_5_3_prime": "GLM 5.3 Prime",
    "muse_spark_1_3": "Muse Spark 1.3",
    "gemini_3_5_flash": "Gemini 3.5 Flash", "gemini_3_7_flash": "Gemini 3.7 Flash",
    "gemini_3_8_flash": "Gemini 3.8 Flash", "gemma_4_31b": "Gemma 4 31B",
    "minimax_m3": "MiniMax M3", "minimax_m2_7": "MiniMax M2.7",
    "deepseek_v3_0324": "DeepSeek V3 0324", "deepseek_v4_flash": "DeepSeek V4 Flash",
    "deepseek_v4_1_flash": "DeepSeek V4.1 Flash", "deepseek_v4_pro": "DeepSeek V4 Pro",
    "ember_1": "Ember 1", "mistral_small_2603": "Mistral Small 2603",
    "mercury_2_5": "Mercury 2.5", "aion_3_5": "Aion 3.5",
    "command_a_plus": "Command A+",
    "gpt_4_1": "GPT-4.1", "gpt_5_5": "GPT-5.5", "gpt_6_astra": "GPT-6 Astra",
    "gpt_6_sol": "GPT-6 Sol", "gpt_6_sol_pro": "GPT-6 Sol Pro",
    "gpt_6_luna": "GPT-6 Luna", "gpt_6_luna_pro": "GPT-6 Luna Pro",
    "lunaris_8b": "Lunaris 8B", "cydonia_24b": "Cydonia 24B",
    "magnum_v4_72b": "Magnum v4 72B", "euryale_70b": "Euryale 70B",
    "skyfall_36b": "Skyfall 36B", "unslopnemo_12b": "UnslopNemo 12B",
    "rocinante_12b": "Rocinante 12B", "venice_dolphin_24b": "Dolphin 24B Venice",
    "hemmingway_1": "Hemmingway 1",
}
# The RP finetunes are a different kind of system and read differently on this
# axis: they sit low because they decline little, not because they over-refuse.
# venice_dolphin_24b is a community finetune too, but not an RP one, and it
# does over-refuse (0.77), so it is not greyed.
FINETUNES = {"lunaris_8b", "cydonia_24b", "magnum_v4_72b", "euryale_70b",
             "skyfall_36b", "unslopnemo_12b", "rocinante_12b"}

# Which vendor made each model. Drives the chip; see rounds/r4/fetch_brand_icons.py for
# where the marks come from and why some of these are lettered rather than
# branded.
VENDOR = {
    "claude_opus_4_6": "anthropic", "claude_opus_4_7": "anthropic",
    "claude_opus_4_8": "anthropic", "claude_opus_5": "anthropic",
    "claude_opus_5_5": "anthropic", "claude_sonnet_5": "anthropic",
    "claude_sonnet_4_6": "anthropic", "claude_fable_5_1": "anthropic",
    "gpt_4_1": "openai", "gpt_5_5": "openai", "gpt_6_astra": "openai",
    "gpt_6_sol": "openai", "gpt_6_sol_pro": "openai",
    "gpt_6_luna": "openai", "gpt_6_luna_pro": "openai",
    "gemini_3_5_flash": "google", "gemini_3_7_flash": "google",
    "gemini_3_8_flash": "google", "gemma_4_31b": "google",
    "qwen3_7_max": "qwen", "qwen3_8_max": "qwen", "qwen3_8_flash": "qwen",
    "qwen3_8_max_prime": "qwen", "qwen3_8_omni_flash": "qwen",
    "qwen3_6_27b": "qwen", "qwen3_6_35b_a3b": "qwen",
    "deepseek_v4_pro": "deepseek", "deepseek_v4_1_flash": "deepseek",
    "deepseek_v4_flash": "deepseek", "deepseek_v3_0324": "deepseek",
    "glm_5_1": "zhipu", "glm_5_3_flash": "zhipu", "glm_5_3_flashx": "zhipu",
    "glm_5_3_prime": "zhipu",
    "minimax_m3": "minimax", "minimax_m2_7": "minimax",
    "kimi_k2_6": "moonshot", "muse_spark_1_3": "meta",
    "mimo_2_5_pro": "xiaomi", "mimo_2_6_pro": "xiaomi", "mimo_2_6_flash": "xiaomi",
    "grok_4_7": "xai", "grok_4_3": "xai", "tencent_hy4": "tencent",
    "ember_1": "fireworks", "mistral_small_2603": "mistral",
    "mercury_2_5": "inception", "aion_3_5": "aionlabs", "command_a_plus": "cohere",
    "venice_dolphin_24b": "cogcomp",
    "cydonia_24b": "thedrummer", "skyfall_36b": "thedrummer",
    "unslopnemo_12b": "thedrummer", "rocinante_12b": "thedrummer",
    "euryale_70b": "sao10k", "lunaris_8b": "sao10k",
    "magnum_v4_72b": "anthracite",
    "hemmingway_1": "altworld",
}
# Vendors added with the later waves, which assets/brand_icons.json has no mark
# for. Lettered like Zhipu until rounds/r4/fetch_brand_icons.py fetches real marks; the
# file's own entries win if it ever has them. Brand colour where the vendor has
# a well-known one, a neutral slate where it does not, and the finetune grey
# for the community author, as the other finetunes have.
EXTRA_LETTERS = {
    "xai": ("x", "#1b1b1b"), "tencent": ("T", "#0052D9"),
    "mistral": ("M", "#FA520F"), "cohere": ("Co", "#39594D"),
    "fireworks": ("F", "#4A5563"), "inception": ("I", "#4A5563"),
    "aionlabs": ("Ai", "#4A5563"), "cogcomp": ("C", "#7A7A7A"),
}
CHIP, MARK = 24, 14          # white plate, and the mark drawn inside it


def load_icons():
    icons = json.load(open("assets/brand_icons.json"))
    icons["letters"] = {**EXTRA_LETTERS, **icons["letters"]}
    return icons


def load_rows(path=LEADERBOARD):
    """Ranked rows in rank order, plus the unranked ones.

    Ranking is the analyzer's decision, not the chart's: a row is drawn only if
    it says ranked=true. The chart used to rank every row with a J, which put
    back two models the analyzer excludes for too little Track A data. Their J
    is still in the JSON; it just has no place in an order. The checks below
    make a JSON that contradicts itself fail the build instead of drawing it.
    """
    raw = json.load(open(path))
    lb = raw["leaderboard"]
    ranked = sorted((r for r in lb if r.get("ranked")), key=lambda r: r["rank"])
    unranked = [r for r in lb if not r.get("ranked")]
    bad = []
    if [r["rank"] for r in ranked] != list(range(1, len(ranked) + 1)):
        bad.append("ranks are not 1..%d" % len(ranked))
    if any(r["J"] is None for r in ranked):
        bad.append("a ranked row has no J")
    if any(a["J"] < b["J"] for a, b in zip(ranked, ranked[1:])):
        bad.append("rank order is not J order")
    if any(r.get("rank") is not None or not r.get("unranked_reason") for r in unranked):
        bad.append("an unranked row has a rank or no unranked_reason")
    if bad:
        raise SystemExit("%s: %s" % (path, "; ".join(bad)))
    return raw, ranked, unranked


def unranked_note(unranked, raw):
    """Why each unranked model is missing, in one sentence, from the JSON.

    Two reasons exist today: too few usable Track A exchanges (the minimum is
    read from ranking_rule, not restated here), or no Track B run at all.
    """
    m = re.search(r"at least (\d+) usable Track A", raw.get("ranking_rule", ""))
    thin = [r for r in unranked if r["J"] is not None]
    none = [r for r in unranked if r["J"] is None]
    if thin and not m:
        raise SystemExit("ranking_rule no longer states the Track A minimum")
    parts = []
    if thin:
        nm = [NAMES.get(r["model"], r["model"]) for r in thin]
        us = [str(r["usable_exchanges_a"]) for r in thin]
        parts.append("%s (%s usable Track A exchanges, under the minimum of %s)"
                     % (" and ".join(nm), " and ".join(us), m.group(1)))
    for r in none:
        why = "no Track B" if not r["n_sessions_b"] else "missing an axis"
        parts.append("%s (%s, so no J)" % (NAMES.get(r["model"], r["model"]), why))
    return "not ranked: " + "; ".join(parts) if parts else ""


def n_seeds(rows):
    """Seeds per model, from the data: the fullest Track A plus Track B run."""
    return (max(r["n_sessions_a"] for r in rows)
            + max(r["n_sessions_b"] for r in rows))


def reduced(r, rows):
    """A model scored on less than the full data, marked * on both charts.

    Fewer sessions than the full seed set, or fewer usable first asks than the
    full four. The second matters since held_line_rate became the first ask
    only: with 3 first asks each one is a third of the held rate, not a
    quarter (GLM 5.1, one empty first ask).
    """
    return (r["n_sessions_a"] < max(x["n_sessions_a"] for x in rows)
            or r["n_sessions_b"] < max(x["n_sessions_b"] for x in rows)
            or (r.get("held_first_n") or 0) < max(x.get("held_first_n") or 0 for x in rows))


def silent(r):
    """Empty replies that climb with the rung: the analyzer's own flag.

    Same thresholds as rounds/r4/analyze_round4_willingness.py. Its J is scored on the
    replies it chose to give, so it gets a dagger, not a different rank.
    """
    return (r["empty_rate_a"] or 0) >= 0.20 and (r["empty_rung_slope_a"] or 0) >= 0.25


def chip(cx, cy, vendor, icons, size=None, mark=None):
    """A white rounded plate with the vendor mark, as in the reference chart.

    Sized by argument so the quadrant chart's legend can reuse it smaller than
    the bars do, instead of a second near-identical copy drifting out of sync.
    """
    CHIP_, MARK_ = size or CHIP, mark or MARK
    g = ['<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="%d" fill="#ffffff" '
         'stroke="#e6e6e6" stroke-width="0.8"/>'
         % (cx - CHIP_ / 2, cy - CHIP_ / 2, CHIP_, CHIP_, max(4, CHIP_ // 4))]
    if vendor in icons["paths"]:
        vb = icons["viewbox"].get(vendor, "0 0 24 24").split()
        span = float(vb[2])
        k = MARK_ / span
        g.append('<g transform="translate(%.2f %.2f) scale(%.4f)">'
                 '<path d="%s" fill="%s"/></g>'
                 % (cx - MARK_ / 2, cy - MARK_ / 2, k,
                    icons["paths"][vendor], icons["hex"][vendor]))
    elif vendor in icons["letters"]:
        ch, hx = icons["letters"][vendor]
        g.append('<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="4" fill="%s"/>'
                 % (cx - MARK_ / 2, cy - MARK_ / 2, MARK_, MARK_, hx))
        g.append('<text x="%.1f" y="%.1f" font-size="%.1f" font-weight="700" '
                 'text-anchor="middle" fill="#ffffff">%s</text>'
                 % (cx, cy + MARK_ * 0.24, MARK_ * 0.62, ch))
    return "".join(g)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


def fmt_j(v):
    return ("%.2f" % v).replace("-", "−")


def boxes_overlap(a, b, pad=0.0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0]
                or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/r4_j_leaderboard.svg")
    args = ap.parse_args()

    icons = load_icons()
    raw, ranked, unranked = load_rows()
    rows = [(r["model"], r["J"]) for r in ranked]
    n = len(rows)
    bold, mono = load_font(F_BOLD), load_font(F_MONO)
    CAP, DESC = 0.72, 0.22          # Roboto cap height / descent, in em

    # Axis range follows the data, with room past each end for the value label
    # and, on the short bars, the chip beyond it.
    jmin = min(-0.1, min(v for _, v in rows)) - 0.10
    jmax = max(v for _, v in rows) + 0.08
    JMIN, JMAX = (int(jmin * 20) - 1) / 20.0, (int(jmax * 20) + 1) / 20.0

    def label_of(r):
        s = NAMES.get(r["model"], r["model"])
        return s + ("*" if reduced(r, ranked) else "") + ("†" if silent(r) else "")
    names = [label_of(r) for r in ranked]
    k45 = 0.7071
    name_drop = max(mono.width(s, LABEL_FS) for s in names) * k45 + LABEL_FS
    W = L + R + n * SLOT
    PW = W - L - R

    # Footnotes are known before the canvas is sized, so it grows a line per
    # footnote line instead of letting a long note run off the right edge.
    notes = []
    for r in ranked:
        if silent(r):
            by = r.get("empty_rate_a_by_subtrack") or {}
            split = ", ".join("%s %.0f%%" % (k, 100 * by[k]) for k in sorted(by, reverse=True))
            notes.append("† %s: %.0f%% of Track A replies empty (%s), treated as a "
                         "provider content filter; J is scored on the replies it gave"
                         % (NAMES.get(r["model"], r["model"]), 100 * r["empty_rate_a"], split))
    if unranked:
        notes.append(unranked_note(unranked, raw))
    note_lines = []
    for t in notes:                 # pack whole notes, never split one
        if note_lines and mono.width(note_lines[-1] + "  ·  " + t, 13) <= PW:
            note_lines[-1] += "  ·  " + t
        else:
            note_lines.append(t)
    ly = T + PH + int(22 + name_drop + 32)      # names, then the key line
    H = ly + 24 + 20 * max(0, len(note_lines) - 1) + 20
    slot = PW / n
    bw = slot * 0.72
    y = lambda v: T + PH * (JMAX - v) / (JMAX - JMIN)
    y0 = y(0.0)

    d = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
         'viewBox="0 0 %d %d" font-family="%s">' % (W, H, W, H, SANS),
         '<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H), "<defs>"]
    # Fade toward the baseline, as the reference does: the bar's weight sits
    # at the value end, where the eye reads it. For a negative bar the value
    # end is the bottom, so its gradient runs the other way. It used to share
    # the positive direction, which put the chip on the palest part of the bar
    # instead of "where the fill is darkest".
    for name, top, y1, y2 in (("gp", POS, 0, 1), ("gh", POS_HI, 0, 1), ("gn", NEG, 1, 0)):
        d.append('<linearGradient id="%s" x1="0" y1="%d" x2="0" y2="%d">'
                 '<stop offset="0" stop-color="%s" stop-opacity="1"/>'
                 '<stop offset="1" stop-color="%s" stop-opacity="0.13"/>'
                 '</linearGradient>' % (name, y1, y2, top, top))
    d.append("</defs>")

    boxes = []          # (x0, y0, x1, y1, what) for everything axis-aligned
    d.append('<text x="%d" y="62" font-size="%d" font-weight="700" fill="%s">%s</text>'
             % (L, TITLE_FS, INK, TITLE))
    boxes.append((L, 62 - CAP * TITLE_FS, L + bold.width(TITLE, TITLE_FS), 62, "title"))
    # The badge repeats nothing the title says, so the title no longer carries
    # "Round 4" -- the badge is what qualifies it, as in the reference.
    badge_txt, badge_fs = "ROUND 4", 14
    bw_txt = mono.width(badge_txt, badge_fs) + 1.2 * (len(badge_txt) - 1)  # letter-spacing
    badge_w = bw_txt + 34
    badge_x = L + bold.width(TITLE, TITLE_FS) + 20
    d.append('<rect x="%.1f" y="38" width="%.1f" height="30" rx="15" fill="#f0f0ee" '
             'stroke="#e0e0dd"/>' % (badge_x, badge_w))
    d.append('<text x="%.1f" y="58" font-size="%d" font-family="%s" fill="%s" '
             'letter-spacing="1.2">%s</text>'
             % (badge_x + 17, badge_fs, MONO, MUTE, badge_txt))
    boxes.append((badge_x, 38, badge_x + badge_w, 68, "badge"))
    sub = ("Youden’s J = held line at the first ask − over-refusal (L3–L5)")
    d.append('<text x="%d" y="97" font-size="19" font-family="%s" fill="%s">%s</text>'
             % (L, MONO, MUTE, esc(sub)))
    boxes.append((L, 97 - 14, L + mono.width(sub, 19), 97 + 4, "subtitle"))

    v = -0.8
    while v <= JMAX + 1e-9:
        if v >= JMIN - 1e-9:
            yy = y(v)
            d.append('<text x="%d" y="%.1f" font-size="15" font-family="%s" fill="%s" '
                     'text-anchor="end">%s</text>'
                     % (L - 14, yy + 5, MONO, MUTE if abs(v) > 1e-9 else INK,
                        ("%.1f" % (0.0 if abs(v) < 1e-9 else v)).replace("-", "−")))
        v = round(v + 0.2, 1)
    # Zero is the qualitative boundary, so it gets a real rule; nothing else does.
    d.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.5"/>'
             % (L - 6, y0, L + PW, y0, "#bdbdbd"))

    chips, vals, drawn = [], [], []
    for i, (key, v) in enumerate(rows):
        cx = L + slot * (i + 0.5)
        x = cx - bw / 2
        hi = (i == 0)
        fill = "url(#gh)" if hi else ("url(#gp)" if v >= 0 else "url(#gn)")
        h = abs(y(v) - y0)
        top = y(v) if v >= 0 else y0
        r = min(6.0, bw / 2, h)
        if h >= 0.5:   # a J of exactly 0 has no bar, only its label on the rule
            if v >= 0:   # round the value end only
                path = ("M%.1f %.1f v%.1f a%.1f %.1f 0 0 1 %.1f %.1f h%.1f "
                        "a%.1f %.1f 0 0 1 %.1f %.1f v%.1f z"
                        % (x, top + h, -(h - r), r, r, r, -r, bw - 2 * r, r, r, r, r, h - r))
            else:
                path = ("M%.1f %.1f v%.1f a%.1f %.1f 0 0 0 %.1f %.1f h%.1f "
                        "a%.1f %.1f 0 0 0 %.1f %.1f v%.1f z"
                        % (x, top, h - r, r, r, r, r, bw - 2 * r, r, r, r, -r, -(h - r)))
            d.append('<path d="%s" fill="%s"/>' % (path, fill))
        drawn.append((key, v, round(h, 1)))

        # Chip sits just inside the value end, where the fill is darkest and a
        # white plate reads cleanly. The models near zero have a bar shorter
        # than the chip (some have none), so theirs goes outside, past the
        # value label -- every model gets a mark, and an absent chip never has
        # to be read as missing data.
        fs = VAL_FS_HI if hi else VAL_FS
        cap = CAP * fs
        inside = h > CHIP + 12
        vy = (y(v) - 8) if v >= 0 else (y(v) + 8 + cap)
        if inside:
            cy = (y(v) + CHIP / 2 + 5) if v >= 0 else (y(v) - CHIP / 2 - 5)
        else:
            cy = (vy - cap - 5 - CHIP / 2) if v >= 0 else (vy + DESC * fs + 5 + CHIP / 2)
        d.append(chip(cx, cy, VENDOR.get(key, ""), icons))
        chips.append((cx, cy))
        boxes.append((cx - CHIP / 2, cy - CHIP / 2, cx + CHIP / 2, cy + CHIP / 2,
                      "chip " + key))
        txt = fmt_j(v)
        wv = bold.width(txt, fs)
        d.append('<text x="%.1f" y="%.1f" font-size="%d" font-weight="%d" '
                 'text-anchor="middle" fill="%s">%s</text>'
                 % (cx, vy, fs, 700 if hi else 600,
                    INK if hi else (POS if v >= 0 else NEG), txt))
        vals.append((key, txt))
        boxes.append((cx - wv / 2, vy - cap, cx + wv / 2, vy + DESC * fs, "value " + key))

    # Names hang down-left from the bar at 45 degrees, anchored at their end.
    ny = T + PH + 14
    rot = []
    for i, (r, s) in enumerate(zip(ranked, names)):
        cx = L + slot * (i + 0.5)
        key = r["model"]
        col = INK if i == 0 else (MUTE if key in FINETUNES else "#3a3a3a")
        wt = 700 if i == 0 else 400
        d.append('<text x="%.1f" y="%.1f" font-size="%.1f" font-family="%s" '
                 'font-weight="%d" text-anchor="end" fill="%s" '
                 'transform="rotate(-%d %.1f %.1f)">%s</text>'
                 % (cx + 4, ny, LABEL_FS, MONO, wt, col, ANGLE, cx + 4, ny, esc(s)))
        wn = mono.width(s, LABEL_FS)
        rot.append((cx + 4, ny, wn))

    # --- footer: key on the left, what the marks mean on the right ------------
    lx = L
    for c, t in ((POS, "holds the line more than it over-refuses"),
                 (NEG, "over-refuses more than it holds")):
        d.append('<rect x="%d" y="%d" width="13" height="13" rx="3" fill="%s"/>'
                 % (lx, ly - 11, c))
        d.append('<text x="%d" y="%d" font-size="14" font-family="%s" fill="%s">%s</text>'
                 % (lx + 20, ly, MONO, MUTE, t))
        boxes.append((lx, ly - 11, lx + 20 + mono.width(t, 14), ly + 3, "key " + t[:12]))
        lx += 20 + int(mono.width(t, 14)) + 36
    n_sess = sum(r["n_sessions_a"] + r["n_sessions_b"] for r in ranked)
    red = [r for r in ranked if reduced(r, ranked)]
    right = ("grey labels = RP finetunes · * fewer than %d sessions or %d first asks "
             "(%d models) · %d ranked models · %s sessions"
             % (n_seeds(ranked), max(r["held_first_n"] for r in ranked), len(red), n,
                format(n_sess, ",")))
    d.append('<text x="%d" y="%d" font-size="13" font-family="%s" fill="%s" '
             'text-anchor="end">%s</text>' % (L + PW, ly, MONO, "#8a8a8a", esc(right)))
    boxes.append((L + PW - mono.width(right, 13), ly - 10, L + PW, ly + 3, "footer right"))
    for j, note in enumerate(note_lines):
        fy = ly + 24 + 20 * j
        d.append('<text x="%d" y="%d" font-size="13" font-family="%s" fill="%s">%s</text>'
                 % (L, fy, MONO, "#8a8a8a", esc(note)))
        boxes.append((L, fy - 10, L + mono.width(note, 13), fy + 3, "footer note %d" % j))
    d.append("</svg>")

    open(args.out, "w").write("\n".join(d))

    # --- geometry checks: the eye is not a test suite -------------------------
    bad = []
    missing = [r["model"] for r in ranked if r["model"] not in NAMES]
    missing += ["vendor:" + r["model"] for r in ranked
                if VENDOR.get(r["model"]) not in icons["paths"]
                and VENDOR.get(r["model"]) not in icons["letters"]]
    if missing:
        bad.append("no display name / mark for " + ", ".join(missing))
    if CHIP > bw:
        bad.append("CHIP %dpx wider than the %.1fpx bar" % (CHIP, bw))
    if len(chips) != len(rows):
        bad.append("only %d chips for %d models" % (len(chips), len(rows)))
    for cx, cy in chips:
        if cy - CHIP / 2 < T - 20 or cy + CHIP / 2 > T + PH:
            bad.append("chip at y=%.0f escapes the plot" % cy)
    # every axis-aligned thing against every other: values, chips, title, footer
    for i, a in enumerate(boxes):
        if a[0] < 0 or a[2] > W or a[1] < 0 or a[3] > H:
            bad.append("%s off the canvas" % a[4])
        for b in boxes[i + 1:]:
            if boxes_overlap(a, b, pad=1.5):
                bad.append("%s | %s" % (a[4], b[4]))
    # rotated names: parallel, so neighbours clear each other if the
    # perpendicular gap beats the line height; then the extents
    gap = slot * k45
    if gap < LABEL_FS * 1.25:
        bad.append("rotated names %.1fpx apart, need %.1f" % (gap, LABEL_FS * 1.25))
    name_bottom = max(yy + wn * k45 for _, yy, wn in rot)
    name_left = min(xx - wn * k45 - LABEL_FS * k45 for xx, _, wn in rot)
    if name_left < 2:
        bad.append("a name runs off the left edge (x=%.0f)" % name_left)
    if name_bottom > ly - 16:
        bad.append("names reach y=%.0f, footer starts at %d" % (name_bottom, ly - 16))
    off = sum(1 for _, v in rows if not (JMIN < v < JMAX))
    print("wrote %s  (%dx%d, %d bars, axis %.2f..%.2f)" % (args.out, W, H, n, JMIN, JMAX))
    print("  collisions / problems: %d    bars outside axis range: %d" % (len(bad), off))
    for b in bad[:12]:
        print("    " + b)
    print("  slot %.1fpx, bar %.1fpx, chip %dpx; names bottom y=%.0f, left x=%.0f"
          % (slot, bw, CHIP, name_bottom, name_left))
    return 0 if not bad and off == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
