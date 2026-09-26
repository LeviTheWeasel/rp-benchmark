#!/usr/bin/env python3
"""Cache the vendor marks the J chart draws, so the build does not need network.

Marks come from simple-icons (CC0). The marks themselves are trademarks of
their owners; using them to identify which vendor made which model in a
comparison chart is nominative use, not endorsement.

Two vendors have no simple-icons entry and get a lettered chip instead, which
is what the reference chart does for Zhipu. The six community finetunes have no
brand mark at all and get their author's initial, so the chart never implies a
corporate origin they do not have.
"""
import json, re, httpx
from pathlib import Path

OUT = Path("assets/brand_icons.json")
ICONS = {                      # vendor -> (simple-icons slug, brand hex)
    "anthropic": ("anthropic", "#D97757"),
    "openai": ("openai", "#412991"),
    "google": ("googlegemini", "#886FBF"),
    "qwen": ("qwen", "#615CED"),
    "deepseek": ("deepseek", "#4D6BFE"),
    "minimax": ("minimax", "#F23F5D"),
    "moonshot": ("moonshotai", "#16191E"),
    "meta": ("meta", "#0081FB"),
    "xiaomi": ("xiaomi", "#FF6900"),
}
LETTERS = {                    # vendor -> (letter, hex)
    "zhipu": ("Z", "#3859FF"),
    # Altworld is an organisation with no simple-icons entry, so it gets a
    # coloured chip like Zhipu. Two letters because "A" alone would collide
    # with Anthracite's grey chip, and colour is not enough to separate them
    # for a reader who cannot distinguish hues.
    "altworld": ("Al", "#C0522A"),
    "thedrummer": ("D", "#7A7A7A"),
    "sao10k": ("S", "#7A7A7A"),
    "anthracite": ("An", "#7A7A7A"),
}


def main():
    OUT.parent.mkdir(exist_ok=True)
    data = {"paths": {}, "hex": {}, "letters": LETTERS}
    with httpx.Client(timeout=30, follow_redirects=True) as c:
        for vendor, (slug, hexv) in ICONS.items():
            r = c.get("https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/%s.svg" % slug)
            r.raise_for_status()
            m = re.search(r'<path d="([^"]+)"', r.text)
            if not m:
                raise SystemExit("no path in %s" % slug)
            vb = re.search(r'viewBox="([^"]+)"', r.text)
            data["paths"][vendor] = m.group(1)
            data["hex"][vendor] = hexv
            data.setdefault("viewbox", {})[vendor] = vb.group(1) if vb else "0 0 24 24"
            print("  %-12s %-14s %5d chars  %s" % (vendor, slug, len(m.group(1)), hexv))
    OUT.write_text(json.dumps(data, indent=1))
    print("\nwrote %s (%d marks + %d lettered)" % (OUT, len(data["paths"]), len(LETTERS)))


if __name__ == "__main__":
    main()
