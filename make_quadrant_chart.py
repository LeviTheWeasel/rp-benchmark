#!/usr/bin/env python3
"""Round-4 quadrant chart: over-refusal vs held-line, with readable labels.

The label placement is the whole difficulty. Since 2026-09-25
`held_line_rate` is the first ask only: at most 4 exchanges (turn 2 of the 4
B-hard seeds), so models land on quarters, and 28 of the 55 ranked land on
exactly 0.50. Seven of those sit inside 0.036 of over-refusal, about 50px, and
two pairs are on the same pixel (Kimi K2.6 and Grok 4.7 at 0.073, DeepSeek V3
0324 and Qwen3.8 Max Prime at 0.225); three more pairs sit 1.3px apart.

The second push, held_under_pressure, is not drawn. It is a conditional rate
on another base (of the first asks a model held, the share still held at turn
4), 49 of the 55 sit at 1.00 on it (one held no first ask, so has none), and
the raters agree on it below the 0.6 bar. A second marker per model would put
a pile of hollow rings on the 1.00 and 0.50 rows for a signal the JSON itself
says to read as weak. The footnote states it and its kappa, read from the JSON.

The first version placed labels in lanes parallel to their row. That held at
31 models and fell apart at 57: its check reported 0 overlaps on a chart where
labels sat on top of other models' dots and leaders ran through labels,
because it only compared labels with labels.

So placement is now a search. Every point gets a set of candidate spots:
touching its dot (no leader), or further out along its row or above and below
it with a short leader. A spot is legal only if its label clears every other
label, every dot and every leader, and its leader clears every other label,
dot and leader. Hardest points (most neighbours) choose first, then a few
passes let each label move to a cheaper legal spot. A direct label that sits
near a second dot gets a leader instead, so no name is ambiguous about which
dot it belongs to.

check() measures the same things the search avoids -- the eye is not a test
suite, and an overlap-only check passed a chart the eye rejected twice.

Usage: python3 make_quadrant_chart.py [--out results/round4_quadrants.svg]
"""
import argparse, html, json, re
from math import hypot

from harness.config import RESULTS_DIR
from ttf_metrics import load as load_font
from make_j_barchart import (NAMES, VENDOR, F_MONO, F_BOLD, chip, load_icons,
                             load_rows, n_seeds, reduced, silent, unranked_note)

W = 1500
L, R, T = 86, 170, 132
PH = 850
PW = W - L - R
XMAX, YMAX = 0.95, 1.0
LFS = 12.0        # label size
ASC, DSC = 9.0, 3.0   # label box above / below the baseline at LFS
MR = 7.6          # drawn dot radius including its white ring
LONG = 70         # a leader longer than this is reported
MONO_F = load_font(F_MONO)
BOLD_F = load_font(F_BOLD)


# Label width comes from the font file. It used to be len(name) * 6.3, the same
# per-character guess that put the J chart's badge on top of its own title and
# let its overlap check pass a chart that overlapped.
def tw(txt):
    return MONO_F.width(txt, LFS)


def disp(r, ranked):
    """Display name shared with the bar chart, with the same * and dagger."""
    return (NAMES.get(r["model"], r["model"])
            + ("*" if reduced(r, ranked) else "") + ("†" if silent(r) else ""))


sx = lambda v: L + v / XMAX * PW
sy = lambda v: T + (1 - v / YMAX) * PH


# --- geometry primitives --------------------------------------------------------
def box_of(p, lx, ly):
    return (lx, ly - ASC, lx + p["w"], ly + DSC)


def boxes_hit(a, b, pad=2.0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0]
                or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def near_pt(box, x, y):
    return (min(max(x, box[0]), box[2]), min(max(y, box[1]), box[3]))


def box_circle(box, x, y):
    nx, ny = near_pt(box, x, y)
    return hypot(nx - x, ny - y)


def pt_seg(c, p, q):
    vx, vy = q[0] - p[0], q[1] - p[1]
    L2 = vx * vx + vy * vy
    t = 0 if L2 == 0 else max(0, min(1, ((c[0] - p[0]) * vx + (c[1] - p[1]) * vy) / L2))
    return hypot(c[0] - p[0] - t * vx, c[1] - p[1] - t * vy)


def _ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def segs_cross(p1, p2, p3, p4):
    d1, d2 = _ccw(p3, p4, p1), _ccw(p3, p4, p2)
    d3, d4 = _ccw(p1, p2, p3), _ccw(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def seg_box(p, q, box, pad=1.5):
    """Does segment p-q pass through box (Liang-Barsky clip)?"""
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def leader_of(p, box):
    """Leader from the dot's edge to the nearest point of its label box."""
    tx, ty = near_pt(box, p["x"], p["y"])
    d = hypot(tx - p["x"], ty - p["y"])
    if d < MR + 5:
        return None
    ux, uy = (tx - p["x"]) / d, (ty - p["y"]) / d
    return ((p["x"] + ux * (MR + 0.5), p["y"] + uy * (MR + 0.5)),
            (tx - ux * 2, ty - uy * 2))


# --- placement ------------------------------------------------------------------
def candidates(p):
    """(cost, lx, ly, direct) for every spot this label may take."""
    x, y, w = p["x"], p["y"], p["w"]
    mid = (ASC - DSC) / 2                      # baseline offset that centres text on y
    out = [(0, x + MR + 3, y + mid, True), (4, x - MR - 3 - w, y + mid, True),
           (2, x + 2, y - MR - 3 - DSC, True), (3, x + 2, y + MR + 3 + ASC, True),
           (5, x - 2 - w, y - MR - 3 - DSC, True), (6, x - 2 - w, y + MR + 3 + ASC, True)]
    for k in range(0, 14):                     # lanes above and below, and the row itself
        for s in ((1, -1) if k else (1,)):
            cy = y + s * (k * 13.0 + (MR + 9 if k else 0))
            ly = cy + mid
            for dx in range(-int(w) - 70, 90, 8):
                lx = x + dx
                box = box_of(p, lx, ly)
                d = box_circle(box, x, y)
                if d < MR + 5:
                    continue
                # cost: leader length, a nudge toward labels right of their dot
                out.append((8 + d + (3 if lx + w < x else 0), lx, ly, False))
    out.sort(key=lambda c: c[0])
    return out


def self_legal(p, lx, ly, direct, pts, static):
    """Spot legal on its own: on the canvas, off every dot and quadrant name.

    Returns (box, leader) or None. Conflicts with other LABELS depend on where
    those go, so they are scored by clash() during the search instead.
    """
    box = box_of(p, lx, ly)
    if box[0] < L + 2 or box[2] > W - 6 or box[1] < T - 14 or box[3] > T + PH + 4:
        return None
    for sb in static:
        if boxes_hit(box, sb, 3):
            return None
    own = box_circle(box, p["x"], p["y"])
    for q in pts:                              # no label on anyone's dot
        if q is p or hypot(q["x"] - p["x"], q["y"] - p["y"]) < 2.5:
            continue
        # A label close to a second dot reads as that dot's name, leader or
        # not ("Gemini 3.5 Flash" beside GLM 5.1's dot), so every label keeps
        # clear of every dot but its own. And where the leader is short
        # enough that the eye goes by distance instead, its own dot must be
        # clearly the nearest: a lane label spanning two dots of the row is
        # otherwise read as either one's.
        dq = box_circle(box, q["x"], q["y"])
        if dq < MR + 9 or (own < 45 and dq < own + 8):
            return None
    seg = None if direct else leader_of(p, box)
    if not direct and seg is None:
        return None
    if seg is not None:                        # the leader clears other dots
        far = clear_part(p, seg)
        for q in pts:
            if q is p or hypot(q["x"] - p["x"], q["y"] - p["y"]) < 2.5:
                continue
            if far and pt_seg((q["x"], q["y"]), far[0], far[1]) < MR + 3:
                return None
    return box, seg


def labels_hit(a, b):
    """Two label boxes too close. 8px sideways, or two names on one line read
    as one name ("Opus 4.7 Sonnet 5")."""
    return not (a[2] + 8 <= b[0] or b[2] + 8 <= a[0]
                or a[3] + 1.5 <= b[1] or b[3] + 1.5 <= a[1])


def clash(a, b):
    """Conflicts between two chosen spots, each (cost, lx, ly, box, seg, ext, ctr).

    Leaders are tested for crossing from their dot's CENTRE, not from the ring
    where they are drawn. In the 0.50 row neighbouring dots are closer than a
    dot is wide, so two leaders that swap sides (the left dot's label going
    right, the right dot's going left) start past each other, never touch as
    drawn, and still hand each label to the wrong dot. Extended to the centres
    they cross, which is what the eye sees.
    """
    ea, eb = a[5], b[5]
    if ea[2] + 8 < eb[0] or eb[2] + 8 < ea[0] or ea[3] + 2 < eb[1] or eb[3] + 2 < ea[1]:
        return 0
    n = labels_hit(a[3], b[3])
    if a[4] is not None:
        n += seg_box(a[4][0], a[4][1], b[3])
        if b[4] is not None:
            n += segs_cross(a[6], a[4][1], b[6], b[4][1])
    if b[4] is not None:
        n += seg_box(b[4][0], b[4][1], a[3])
    return n


def clear_part(p, seg):
    """The part of a leader that has to clear other dots.

    In the 0.50 row dots overlap (4-5px apart, 15px wide), so every leader
    leaving one of them starts inside a neighbour's ring. What matters is that
    it points away from its own dot and is clear of the others after that, so
    the first 14px from the dot's centre are exempt.
    """
    (x1, y1), (x2, y2) = seg
    d = hypot(x2 - p["x"], y2 - p["y"])
    if d <= 14:
        return None
    k = 14 / d
    return ((p["x"] + (x2 - p["x"]) * k, p["y"] + (y2 - p["y"]) * k), (x2, y2))


def place(points, static, iters=60000, seed=4):
    """Pick one spot per label, minimising leader length with zero conflicts.

    Greedy placement alone walls itself in: the first labels take the short
    spots on both sides of the 0.50 row, and every later leader has to cross
    them. So greedy is only the starting point; simulated annealing (seeded, so
    the chart is reproducible) then trades spots until no label, leader or dot
    conflicts, and a last pass moves each label to its cheapest spot that is
    still conflict-free.
    """
    import random
    from math import exp
    rng = random.Random(seed)
    n = len(points)
    for p in points:
        p["w"] = tw(p["m"])
        cl = []
        for cost, lx, ly, direct in candidates(p):
            ok = self_legal(p, lx, ly, direct, points, static)
            if ok:
                box, seg = ok
                ctr = (p["x"], p["y"])
                ext = box if seg is None else (
                    min(box[0], ctr[0]), min(box[1], ctr[1]),
                    max(box[2], ctr[0]), max(box[3], ctr[1]))
                cl.append((cost, lx, ly, box, seg, ext, ctr))
        p["cands"] = cl[:360]
    unplaceable = [p for p in points if not p["cands"]]
    if unplaceable:
        raise SystemExit("no legal spot at all for: %s"
                         % ", ".join(p["m"] for p in unplaceable))
    C = [p["cands"] for p in points]
    busy = [sum(max(0.0, 1 - hypot(q["x"] - p["x"], q["y"] - p["y"]) / 90)
                for q in points if q is not p) for p in points]
    order = sorted(range(n), key=lambda i: -busy[i])

    pick = [None] * n
    for i in order:                            # greedy start
        best = None
        for k, c in enumerate(C[i]):
            if all(pick[j] is None or not clash(c, C[j][pick[j]]) for j in range(n)):
                best = k
                break
        pick[i] = 0 if best is None else best

    def local(i, c):
        return sum(clash(c, C[j][pick[j]]) for j in range(n) if j != i)

    PEN = 400.0
    confl = [local(i, C[i][pick[i]]) for i in range(n)]
    t0, t1 = 60.0, 0.3
    for it in range(iters):
        if not any(confl) and it > iters // 2:
            break
        temp = t0 * (t1 / t0) ** (it / iters)
        hot = [i for i in range(n) if confl[i]]
        i = rng.choice(hot) if hot and rng.random() < 0.7 else rng.randrange(n)
        k = min(int(rng.expovariate(1 / 40.0)), len(C[i]) - 1)
        if k == pick[i]:
            continue
        new, old = C[i][k], C[i][pick[i]]
        ln = local(i, new)
        delta = (new[0] - old[0]) + PEN * (ln - confl[i])
        if delta <= 0 or rng.random() < exp(-delta / temp):
            for j in range(n):                 # conflicts are symmetric
                if j != i:
                    cj = C[j][pick[j]]
                    confl[j] += clash(new, cj) - clash(old, cj)
            pick[i] = k
            confl[i] = ln
    for _ in range(3):                         # polish: cheapest spot, no new conflict
        for i in order:
            cur = local(i, C[i][pick[i]])
            for k in range(pick[i]):
                if local(i, C[i][k]) <= cur:
                    pick[i] = k
                    break
    stuck = []
    for i, p in enumerate(points):
        c = C[i][pick[i]]
        p.update(cost=c[0], lx=c[1], ly=c[2], box=c[3], seg=c[4])
        if local(i, c):
            stuck.append(p)
    return points, stuck


def check(points, static):
    """The same rules the search enforces, counted independently of it."""
    bad = {"overlap": 0, "label_on_dot": 0, "ambiguous": 0, "leader_through_label": 0,
           "leader_through_dot": 0, "crossing": 0, "long_leader": 0, "offscreen": 0}
    for i, a in enumerate(points):
        ab = a["box"]
        if ab[0] < 0 or ab[2] > W - 4 or ab[1] < T - 16 or ab[3] > T + PH + 6:
            bad["offscreen"] += 1
        if any(boxes_hit(ab, sb, 1) for sb in static):
            bad["overlap"] += 1
        if a["seg"] and hypot(a["seg"][1][0] - a["x"], a["seg"][1][1] - a["y"]) > LONG:
            bad["long_leader"] += 1
        for b in points:
            if b is a:
                continue
            if hypot(b["x"] - a["x"], b["y"] - a["y"]) >= 2.5:
                db = box_circle(ab, b["x"], b["y"])
                if db < MR + 1:
                    bad["label_on_dot"] += 1
                # nearer to someone else's dot than to its own, by eye
                own = box_circle(ab, a["x"], a["y"])
                if own < 45 and db < own + 4:
                    bad["ambiguous"] += 1
                far = a["seg"] and clear_part(a, a["seg"])
                if far and pt_seg((b["x"], b["y"]), *far) < MR:
                    bad["leader_through_dot"] += 1
            if a["seg"] and seg_box(a["seg"][0], a["seg"][1], b["box"], pad=0):
                bad["leader_through_label"] += 1
        for b in points[i + 1:]:
            if boxes_hit(ab, b["box"], 0.5):
                bad["overlap"] += 1
            if a["seg"] and b["seg"] and segs_cross((a["x"], a["y"]), a["seg"][1],
                                                    (b["x"], b["y"]), b["seg"][1]):
                bad["crossing"] += 1
    return bad


def pressure_kappa(rows):
    """Turn-4 rater kappa, its n and the bar, as the leaderboard states them.

    Read from held_under_pressure_note rather than restated here, and every row
    must say the same thing: the footnote may not quote a number the JSON
    does not carry.
    """
    got = set()
    for r in rows:
        m = re.search(r"kappa at turn 4 is ([0-9.]+) \(n=(\d+).*?below the ([0-9.]+) bar",
                      r.get("held_under_pressure_note") or "")
        if m:
            got.add(m.groups())
    if len(got) != 1:
        raise SystemExit("held_under_pressure_note: expected one turn-4 kappa, got %s" % got)
    return got.pop()


def wrap(t, size, width):
    """Greedy word wrap on measured widths, for footnotes that outgrow a line."""
    lines, cur = [], ""
    for w in t.split(" "):
        nxt = (cur + " " + w) if cur else w
        if cur and MONO_F.width(nxt, size) > width:
            lines.append(cur)
            cur = w
        else:
            cur = nxt
    return lines + [cur]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RESULTS_DIR / "round4_quadrants.svg"))
    args = ap.parse_args()
    # Counts are read from the data, not written into the subtitle by hand:
    # models added after the main run change them, and a caption that silently
    # disagrees with the chart is worse than no caption.
    raw, d, unranked = load_rows(RESULTS_DIR / "round4_willingness_leaderboard.json")
    n_sess = sum(r["n_sessions_a"] + r["n_sessions_b"] for r in d)
    red = [r for r in d if reduced(r, d)]
    # The split is the analyzer's (quadrant_medians, and each row's quadrant),
    # so the chart draws it rather than recomputing its own. It still
    # recomputes both, and refuses to draw a line the rows disagree with.
    qm = raw["quadrant_medians"]
    med_o, med_h = qm["over_refusal_hard_rungs"], qm["held_line_rate"]
    mine = (sorted(r["over_refusal_hard_rungs"] for r in d)[len(d) // 2],
            sorted(r["held_line_rate"] for r in d)[len(d) // 2])
    if mine != (med_o, med_h) or qm["n_models"] != len(d):
        raise SystemExit("quadrant_medians %s disagree with the ranked rows %s"
                         % ((med_o, med_h, qm["n_models"]), mine + (len(d),)))
    side = {(True, True): "CALIBRATED", (False, True): "OVER-CAUTIOUS",
            (True, False): "PERMISSIVE", (False, False): "CONFUSED"}
    wrong = [r["model"] for r in d if r["quadrant"] != side[
        (r["over_refusal_hard_rungs"] <= med_o, r["held_line_rate"] >= med_h)]]
    if wrong:
        raise SystemExit("quadrant field disagrees with the medians for " + ", ".join(wrong))
    kap, kap_n, kap_bar = pressure_kappa(d)
    full_first = max(r["held_first_n"] for r in d)
    short_first = [r for r in d if r["held_first_n"] < full_first]

    # quadrant names are obstacles for the labels too
    corners = ((L + 14, T + 26, "start", "CALIBRATED"),
               (L + PW - 14, T + 26, "end", "OVER‑CAUTIOUS"),
               (L + 14, T + PH - 14, "start", "PERMISSIVE"),
               (L + PW - 14, T + PH - 14, "end", "CONFUSED"))
    static = []
    for x, y, anc, txt in corners:
        w = MONO_F.width(txt, 12.5) + 1.6 * len(txt)
        x0 = x if anc == "start" else x - w
        static.append((x0, y - 10, x0 + w, y + 3))

    # `m` is what gets drawn, `key` is what looks up the vendor colour. The
    # search is seeded, and a few seeds are tried and the best kept (fewest
    # conflicts, then fewest long leaders, then shortest total), so a rerun
    # draws the same chart and one unlucky seed does not ship a collision.
    best = None
    for seed in range(1, 7):
        pts, stuck = place([{"m": disp(r, d), "key": r["model"],
                             "x": sx(r["over_refusal_hard_rungs"]),
                             "y": sy(r["held_line_rate"])} for r in d], static, seed=seed)
        n_long = sum(1 for p in pts if p["seg"] and hypot(
            p["seg"][1][0] - p["x"], p["seg"][1][1] - p["y"]) > LONG)
        score = (len(stuck), n_long, sum(p["cost"] for p in pts))
        if best is None or score < best[0]:
            best = (score, seed, pts, stuck)
    _, seed, pts, stuck = best

    esc = html.escape
    icons = load_icons()
    vend_hex = {**icons["hex"], **{k: v[1] for k, v in icons["letters"].items()}}

    INK, MUTE, FAINT = "#1b1b1b", "#6b6b6b", "#ececea"
    MONO = "Noto Sans Mono, DejaVu Sans Mono, monospace"
    SANS = "Inter, Roboto, Noto Sans, DejaVu Sans, sans-serif"
    TITLE, TFS = "Adversarial Willingness", 34

    body = []
    # --- title block, same hierarchy as the bar chart ------------------------
    body.append(f'<text x="{L}" y="56" font-size="{TFS}" font-weight="700" '
                f'fill="{INK}">{TITLE}</text>')
    bx = L + BOLD_F.width(TITLE, TFS) + 18
    body.append(f'<rect x="{bx:.1f}" y="33" width="104" height="28" rx="14" '
                f'fill="#f0f0ee" stroke="#e0e0dd"/>')
    body.append(f'<text x="{bx + 16:.1f}" y="52" font-size="13" font-family="{MONO}" '
                f'fill="{MUTE}" letter-spacing="1.2">ROUND 4</text>')
    body.append(f'<text x="{L}" y="86" font-size="17" font-family="{MONO}" fill="{MUTE}">'
                f'{len(d)} ranked models &#183; {n_sess:,} sessions &#183; {n_seeds(d)} seeds each'
                f' (* {len(red)} with fewer sessions or first asks)</text>')
    body.append(f'<text x="{L}" y="108" font-size="14" font-family="{MONO}" fill="#9a9a9a">'
                f'target is the upper left: engages with what it should, holds what it must'
                f'</text>')

    # --- plot field ----------------------------------------------------------
    body.append(f'<rect x="{L}" y="{T}" width="{sx(med_o)-L:.1f}" '
                f'height="{sy(med_h)-T:.1f}" fill="url(#tgt)"/>')
    for v in (0, .2, .4, .6, .8):
        body += [f'<line x1="{sx(v):.1f}" y1="{T}" x2="{sx(v):.1f}" y2="{T+PH}" '
                 f'stroke="{FAINT}" stroke-width="1"/>',
                 f'<text x="{sx(v):.1f}" y="{T+PH+26}" font-size="13" font-family="{MONO}" '
                 f'fill="#9a9a9a" text-anchor="middle">{v:.1f}</text>']
    for v in (0, .25, .5, .75, 1.0):
        body += [f'<line x1="{L}" y1="{sy(v):.1f}" x2="{L+PW}" y2="{sy(v):.1f}" '
                 f'stroke="{FAINT}" stroke-width="1"/>',
                 f'<text x="{L-14}" y="{sy(v)+5:.1f}" font-size="13" font-family="{MONO}" '
                 f'fill="#9a9a9a" text-anchor="end">{v:.2f}</text>']
    # medians: the only rules that carry meaning, so the only ones drawn dark
    body += [f'<line x1="{sx(med_o):.1f}" y1="{T}" x2="{sx(med_o):.1f}" y2="{T+PH}" '
             f'stroke="#c9c8c2" stroke-width="1.5" stroke-dasharray="6 5"/>',
             f'<line x1="{L}" y1="{sy(med_h):.1f}" x2="{L+PW}" y2="{sy(med_h):.1f}" '
             f'stroke="#c9c8c2" stroke-width="1.5" stroke-dasharray="6 5"/>']
    for x, y, anc, txt in corners:
        body.append(f'<text x="{x:.0f}" y="{y:.0f}" font-size="12.5" font-family="{MONO}" '
                    f'font-weight="700" fill="#b4b3ad" letter-spacing="1.6" '
                    f'text-anchor="{anc}">{txt}</text>')

    # --- points: colour carries the vendor, the label stays ink --------------
    for p in pts:
        if p["seg"]:
            (x1, y1), (x2, y2) = p["seg"]
            body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                        f'stroke="#bdbcb5" stroke-width="1"/>')
    for p in pts:
        c = vend_hex.get(VENDOR.get(p["key"], ""), "#7A7A7A")
        # white ring so touching marks stay separable -- the 0.50 row has
        # neighbours 1-5px apart, closer than the marks are wide
        body.append(f'<circle cx="{p["x"]:.1f}" cy="{p["y"]:.1f}" r="6.5" '
                    f'fill="{c}" stroke="#ffffff" stroke-width="2.2"/>')
    for p in pts:
        # white halo: the median and grid rules run under some labels
        body.append(f'<text x="{p["lx"]:.1f}" y="{p["ly"]:.1f}" font-size="{LFS}" '
                    f'font-family="{MONO}" fill="#3a3a3a" stroke="#ffffff" '
                    f'stroke-width="3" stroke-linejoin="round" paint-order="stroke">'
                    f'{esc(p["m"])}</text>')

    # --- axis captions -------------------------------------------------------
    body += [f'<text x="{L+PW/2:.0f}" y="{T+PH+56}" font-size="14" font-family="{MONO}" '
             f'fill="{MUTE}" text-anchor="middle">over-refusal, rungs L3&#8211;L5 '
             f'&#8594; worse</text>',
             f'<text transform="translate(28,{T+PH/2:.0f}) rotate(-90)" font-size="14" '
             f'font-family="{MONO}" fill="{MUTE}" text-anchor="middle">held line at the '
             f'first ask, Track B-hard &#8594; better</text>']

    # --- vendor legend: the brand marks live here, not on the points ---------
    # At 1-5px between neighbours in the 0.50 row a 22px chip per point would
    # be a pile; in a legend the same marks read cleanly and cost no plot space.
    seen = []
    for p in pts:
        v = VENDOR.get(p["key"], "")
        if v and v not in seen:
            seen.append(v)
    LABEL = {"xai": "xAI", "openai": "OpenAI", "deepseek": "DeepSeek",
             "minimax": "MiniMax", "aionlabs": "Aion Labs",
             "cogcomp": "Cognitive Computations", "sao10k": "Sao10K",
             "thedrummer": "TheDrummer", "zhipu": "Zhipu"}
    lx, ly = L, T + PH + 92
    for v in seen:
        name = LABEL.get(v, v[:1].upper() + v[1:])
        step = 27 + MONO_F.width(name, 12) + 20
        if lx + step > W - 20:
            lx, ly = L, ly + 26
        body.append(chip(lx + 11, ly, v, icons, size=22, mark=13))
        body.append(f'<text x="{lx+27:.0f}" y="{ly+4:.0f}" font-size="12" '
                    f'font-family="{MONO}" fill="#8a8a8a">{esc(name)}</text>')
        lx += step
    on_line = sum(1 for r in d if r["held_line_rate"] == med_h)
    short = "; ".join(f'{NAMES.get(r["model"], r["model"])}* has {r["held_first_n"]} '
                      f'usable first asks ({r["held_line_rate"]:.2f})' for r in short_first)
    notes = [f'Split at the medians of the {len(d)} ranked models ({med_o:.2f} / '
             f'{med_h:.2f}). A model on a median line is counted on its upper-left side, '
             f'which is where the {on_line} at {med_h:.2f} go.',
             f'held line is the first ask only: {full_first} exchanges per model (turn 2 '
             f'of each B-hard seed), so models land on quarters and stack in rows'
             + (f'; {short}.' if short else '.'),
             f'The second push (held_under_pressure) is not plotted and not in J: the '
             f'two raters agree on it at kappa {kap} (n={kap_n}), under the {kap_bar} bar. '
             f'It is in the leaderboard JSON with its n.']
    for r in d:
        if silent(r):
            by = r.get("empty_rate_a_by_subtrack") or {}
            split = ", ".join("%s %.0f%%" % (k, 100 * by[k]) for k in sorted(by, reverse=True))
            notes.append(f'† {NAMES.get(r["model"], r["model"])}: '
                         f'{100 * r["empty_rate_a"]:.0f}% of Track A replies empty ({split}), '
                         f'treated as a provider content filter.')
    if unranked:
        un = unranked_note(unranked, raw)
        notes.append(un[:1].upper() + un[1:] + ".")
    fy = ly + 34
    for t in notes:
        for line in wrap(t, 11.5, W - L - 8):
            body.append(f'<text x="{L}" y="{fy}" font-size="11.5" font-family="{MONO}" '
                        f'fill="#a8a8a8">{esc(line)}</text>')
            if L + MONO_F.width(line, 11.5) > W - 8:
                stuck.append({"m": "footnote too wide"})
            fy += 18
    H = fy + 2

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{SANS}">',
         '<defs>'
         '<linearGradient id="tgt" x1="0" y1="0" x2="0.6" y2="1">'
         '<stop offset="0" stop-color="#1A6FB0" stop-opacity="0.13"/>'
         '<stop offset="1" stop-color="#1A6FB0" stop-opacity="0.015"/>'
         '</linearGradient></defs>',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>'] + body + ["</svg>"]
    out = args.out
    open(out, "w").write("\n".join(o))
    missing = [r["model"] for r in d if r["model"] not in NAMES]
    lead = [hypot(p["seg"][1][0] - p["x"], p["seg"][1][1] - p["y"]) for p in pts if p["seg"]]
    print("wrote %s  (%d models, %dx%d)" % (out, len(pts), W, H))
    print("  geometry:", check(pts, static))
    print("  direct labels %d, with leader %d, longest leader %.0fpx (seed %d)"
          % (len(pts) - len(lead), len(lead), max(lead, default=0), seed))
    if stuck or missing:
        print("  UNPLACED / PROBLEMS:", [p["m"] for p in stuck], "no name:", missing)
    return 1 if stuck or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
