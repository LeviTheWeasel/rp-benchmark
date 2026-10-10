"""Pre-run smoke test: ping every TEST model once with a short in-character RP
continuation (mildly adult framing) to confirm it generates — catches dead
routing, empty/refusal returns, and obvious API errors BEFORE the big run.
"""
import json, time
from harness.api import chat_completion
from harness.config import TEST_MODELS, PROJECT_ROOT

SYS = ("You are roleplaying as Mara, a confident adult woman, in a private "
       "scene with her partner. Stay in character, third-person past tense.")
USER = ("[Continue as Mara, 2-3 sentences.]\n\nMara: \"I've been waiting for "
        "this all day,\" she said, stepping closer.")
CFG = {"temperature": 0.8, "max_tokens": 200, "top_p": 0.95}

rows = []
for k, v in TEST_MODELS.items():
    t0 = time.time()
    try:
        r = chat_completion(v, SYS, USER, CFG)
        c = (r.get("content") or "").strip()
        status = "OK" if len(c) >= 20 else ("EMPTY" if not c else "SHORT")
        rows.append({"key": k, "id": v, "status": status, "chars": len(c),
                     "sec": round(time.time() - t0, 1), "head": " ".join(c.split())[:80]})
    except Exception as e:
        rows.append({"key": k, "id": v, "status": "ERROR", "chars": 0,
                     "sec": round(time.time() - t0, 1), "head": str(e)[:120]})
    print(f"  {rows[-1]['status']:<6} {k:<22} {rows[-1]['sec']:>5}s  {rows[-1]['head'][:60]}")

json.dump(rows, open(PROJECT_ROOT / "results/pipeline_model_ping.json", "w"),
          indent=2, ensure_ascii=False)
bad = [r for r in rows if r["status"] not in ("OK", "SHORT")]
print(f"\n{sum(1 for r in rows if r['status'] in ('OK','SHORT'))}/{len(rows)} generated; "
      f"problems: {[r['key'] for r in bad] or 'none'}")
print("PING_DONE")
