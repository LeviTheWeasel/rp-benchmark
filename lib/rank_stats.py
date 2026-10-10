#!/usr/bin/env python3
"""One correct Spearman, because the repo had three wrong ones.

docs/METHODOLOGY.md sec 14.3 documents both forms and says which to use:

    no ties   rho = 1 - 6*sum(d^2) / (n*(n^2-1))
    with ties rho = cov(Rx, Ry) / (sd(Rx)*sd(Ry))   <- average-rank arrays

The d^2 form is an algebraic shortcut that is EXACT only when every rank is
distinct. Feed it average ranks and it is biased, and the bias grows with the
number of ties. Two call sites got this wrong in different ways:

  * analyze_r4_craft_proxy ranked over `sorted(set(values))`, so its ranks ran
    0..k-1 over the DISTINCT values while the formula divided by n. On 57
    models with 50 distinct craft scores that reported rho = +0.135 where the
    tie-corrected figure is -0.123 -- a published sign flip.
  * analyze_method_correlations built correct average ranks and then put them
    through the no-ties formula.

So: rank() for average ranks, spearman() for the tie-corrected coefficient,
and nothing here takes a shortcut that depends on there being no ties.
"""
from __future__ import annotations

import math


def rank(values):
    """Average ranks, 1-based. Ties share the mean of the ranks they span."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        mean = (i + j - 1) / 2.0 + 1.0
        for k in range(i, j):
            out[order[k]] = mean
        i = j
    return out


def spearman(xs, ys, min_n=3):
    """Tie-corrected Spearman rho, or None if there are too few usable pairs.

    Pearson on the average-rank arrays, which is the general form and reduces
    to the d^2 shortcut when no value repeats.
    """
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < min_n:
        return None
    a = rank([p[0] for p in pairs])
    b = rank([p[1] for p in pairs])
    n = len(pairs)
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a)
                    * sum((y - mb) ** 2 for y in b))
    if den == 0:          # one side is entirely tied; rho is undefined
        return None
    return num / den


def spearman_p(rho, n):
    """Two-sided p from the t-approximation of METHODOLOGY sec 14.3.

    Returns None where the approximation does not apply (n < 3, |rho| == 1).
    """
    if rho is None or n < 3 or abs(rho) >= 1.0:
        return None
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    df = n - 2
    # Student-t survival via the incomplete beta, two-sided.
    x = df / (df + t * t)
    return _betainc_half(df / 2.0, 0.5, x)


def _betainc_half(a, b, x):
    """Regularised incomplete beta I_x(a, b), continued-fraction form."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = (math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b))
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 200):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break
    return front * (f - 1.0)
