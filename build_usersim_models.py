#!/usr/bin/env python3
"""Build clean `magmell-usersim-*` Ollama tags for the round-4 user simulator.

The installed `strovolos-magmell-*` tags carry a baked SYSTEM prompt (a
"flamboyant theatrical impresario and creative-writing consultant" persona).
The OpenAI-compatible endpoint's system message does replace it, but relying
on that is fragile, so we build purpose-made tags from the same base blobs
with no SYSTEM line at all.

Other deltas vs the source tags:
  - num_ctx 32768 -> 16384. Round-4 sessions top out near 10k tokens, and
    16k leaves headroom for OLLAMA_NUM_PARALLEL=2 inside 16 GB VRAM
    (8.7 GB weights + ~2.5 GB KV per slot).
  - temperature 0.8 -> 0.9. The sim should be a bit more surprising than a
    model under evaluation; round 3's sim prompt asks for users who
    "occasionally do unexpected things".

Usage:
  python3 build_usersim_models.py            # build all
  python3 build_usersim_models.py v12        # build one
  python3 build_usersim_models.py --dry-run  # print Modelfiles only

Blob digests are pinned here on purpose: they identify the exact weights a
round-4 run used. Re-derive with `ollama show --modelfile strovolos-magmell-vN`.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

BLOB_DIR = "/mnt/storage/ollama/blobs"

# Local blobs from the strovolos-magmell-* tags. These need the ChatML
# TEMPLATE spelled out because we build straight from the raw GGUF blob.
SOURCES = {
    "v9": "sha256-3611a40c45a6ddd9a708e705a71bf882724e6b125f1cc5d366b757b978a7d567",
    "v10": "sha256-7da0f65ea5e4c3311f196b1d63112598c01466b937c67a7f7623e71869ae48f7",
    "v11": "sha256-85d7f3b441638495a8995e2862383d992e82e781a76b1773253dcdab260e95c0",
    "v12": "sha256-c3e33d8ad63a52d5ff033af95401443487c0c145749679258a9f166195ab180e",
}

# Sources that are already Ollama tags. Building FROM a tag inherits its
# TEMPLATE and stop tokens, which is what we want for stock Mag-Mell -- its
# GGUF ships a chat template and guessing at one instead is a good way to get
# silently degraded output.
TAG_SOURCES = {
    "stock": "hf.co/bartowski/MN-12B-Mag-Mell-R1-GGUF:Q5_K_M",
}

PARAMS = """PARAMETER num_ctx 16384
PARAMETER temperature 0.9
PARAMETER top_p 0.9
PARAMETER min_p 0.05
"""

TEMPLATE = '''FROM {blob}
TEMPLATE """{{{{ if .System }}}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{{{ end }}}}<|im_start|>assistant
{{{{ .Response }}}}<|im_end|>
"""
''' + PARAMS + """PARAMETER stop <|im_start|>
PARAMETER stop <|im_end|>
PARAMETER stop </s>
"""

TAG_TEMPLATE = "FROM {tag}\n" + PARAMS


def build(version: str, dry_run: bool = False) -> bool:
    tag = f"magmell-usersim-{version}:latest"

    if version in TAG_SOURCES:
        src = TAG_SOURCES[version]
        modelfile = TAG_TEMPLATE.format(tag=src)
        blob = None
    else:
        blob = f"{BLOB_DIR}/{SOURCES[version]}"
        modelfile = TEMPLATE.format(blob=blob)

    if dry_run:
        print(f"=== {tag} ===\n{modelfile}")
        return True

    if blob and not Path(blob).exists():
        print(f"  SKIP {tag}: blob missing at {blob}")
        return False

    with tempfile.NamedTemporaryFile("w", suffix=".Modelfile",
                                     delete=False) as fh:
        fh.write(modelfile)
        path = fh.name

    print(f"  building {tag} ...")
    proc = subprocess.run(["ollama", "create", tag, "-f", path],
                          capture_output=True, text=True)
    Path(path).unlink(missing_ok=True)
    if proc.returncode != 0:
        print(f"  FAILED {tag}: {proc.stderr.strip()[:300]}")
        return False
    print(f"  ok {tag}")
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry_run = "--dry-run" in sys.argv
    known = list(SOURCES) + list(TAG_SOURCES)
    versions = args or known

    ok = 0
    for v in versions:
        if v not in known:
            print(f"  unknown version {v!r} (have: {', '.join(known)})")
            continue
        ok += build(v, dry_run)
    print(f"\n{ok}/{len(versions)} built")
    return 0 if ok == len(versions) else 1


if __name__ == "__main__":
    sys.exit(main())
