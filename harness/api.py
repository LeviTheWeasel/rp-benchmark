"""OpenRouter API client for RP-Bench."""
import json
import os
import random
import threading
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

from .config import (
    OPENROUTER_BASE_URL,
    OLLAMA_BASE_URL,
    LOCAL_PREFIX,
    REMOTE_PREFIX,
    REMOTE_BASE_URL,
    REMOTE_API_KEY,
    JUDGE_CONFIG,
    GENERATION_CONFIG,
    MODEL_CONFIG_OVERRIDES,
    REQUEST_DELAY_SECONDS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    MAX_TRANSIENT_RETRIES,
    TRANSIENT_MAX_WAIT_SECONDS,
    PROJECT_ROOT,
)

load_dotenv(PROJECT_ROOT / ".env")

_last_request_time = 0.0
# Thread-safe rate gate. Under concurrency the benchmark lowers _min_interval
# so aggregate request starts scale with worker count; 429s are still caught
# and retried below as the safety net.
_rate_lock = threading.Lock()
_min_interval = REQUEST_DELAY_SECONDS


def set_min_interval(seconds: float):
    """Set the minimum spacing between request starts (global, thread-safe).

    Typical use: set to REQUEST_DELAY_SECONDS / concurrency before a parallel
    run so N workers can keep ~N requests in flight.
    """
    global _min_interval
    _min_interval = max(0.0, seconds)


def _get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return key


class AccountError(RuntimeError):
    """Non-recoverable account-level failure: 401/402.

    Distinct from a transient failure because no amount of waiting fixes it —
    the key is out of credit, revoked, or unauthorised. Once one call sees this,
    every subsequent call in the run will fail identically, so it latches and
    fails the rest of the run instantly.

    Round 4's first P4 attempt ran out of credit at session 163 and then ground
    through 206 more sessions x ~26 calls x 3 retry attempts of guaranteed-fail
    requests before stopping. The failure was unavoidable; spending an hour
    discovering it 206 more times was not.
    """


class ModelBlocked(RuntimeError):
    """This key may not call THIS model; every other model is unaffected.

    403 used to be latched as an account failure alongside 401 and 402. It is
    not one: it means a gated release, a provider restriction, or a region
    block on one model id. Latching the run on it cost a full 16-model wave --
    sakana/fugu-max answered 403 on the first call and all 668 remaining
    sessions then failed carrying that model's error, while the same key
    served gemma-4-31b and mercury-2.5 seconds later.
    """


_blocked_models = set()


class TransientExhausted(RuntimeError):
    """The transient budget ran out: 429s or 5xx that never stopped.

    A distinct type because it must NOT fall into the hard-error handler.
    It briefly did: RuntimeError was added to that handler's except tuple to
    surface 4xx response bodies, which silently made every rate-limit
    exhaustion cost 3 hard attempts x 6 transient retries and their backoffs
    instead of failing once. Cydonia burned three times the necessary time on
    a provider that was never going to answer.
    """


_account_failed: AccountError | None = None


def reset_account_error():
    """Clear the latch (call after topping up credit)."""
    global _account_failed
    _account_failed = None


def is_local(model: str) -> bool:
    """True if this model id routes to the local Ollama server."""
    return model.startswith(LOCAL_PREFIX)


def is_remote(model: str) -> bool:
    """True if this model id routes to a rented inference endpoint."""
    return model.startswith(REMOTE_PREFIX)


def _endpoint(model: str) -> tuple[str, str, dict]:
    """Resolve (base_url, wire_model_id, headers) for a model id.

    Local ids carry a 'ollama/' prefix that is stripped before going on the
    wire; Ollama's OpenAI-compatible endpoint needs no auth.
    """
    if is_local(model):
        return OLLAMA_BASE_URL, model[len(LOCAL_PREFIX):], {
            "Content-Type": "application/json",
        }
    if is_remote(model):
        if not REMOTE_BASE_URL:
            raise RuntimeError(
                "REMOTE_BASE_URL not set but model %r asks for the remote "
                "route. Put the pod's https URL in .env." % model)
        h = {"Content-Type": "application/json"}
        if REMOTE_API_KEY:
            h["Authorization"] = "Bearer %s" % REMOTE_API_KEY
        return REMOTE_BASE_URL, model[len(REMOTE_PREFIX):], h
    return OPENROUTER_BASE_URL, model, {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/rp-bench",
        "X-Title": "RP-Bench",
    }


def _transient_backoff(n: int, retry_after: str | None) -> float:
    """Exponential backoff with jitter for a transient failure.

    Honours the provider's Retry-After header when it gives us one — guessing
    longer than the server asked wastes time, guessing shorter just earns
    another 429.

    Jitter matters under concurrency: without it, N workers that hit the same
    rate limit all sleep the same duration and retry in lockstep, reproducing
    the burst that caused the limit.
    """
    if retry_after:
        try:
            return min(float(retry_after), TRANSIENT_MAX_WAIT_SECONDS)
        except ValueError:
            pass  # HTTP-date form; fall through to exponential
    base = RETRY_DELAY_SECONDS * (2 ** (n - 1))
    # Cap AFTER jitter, or the 0.5-1.5x multiplier pushes the tail past the
    # documented maximum.
    return min(base * (0.5 + random.random()), TRANSIENT_MAX_WAIT_SECONDS)


def _rate_limit():
    # Hold the lock only to claim a start slot (spacing the bursts); the slow
    # HTTP call happens outside the lock so workers run concurrently.
    global _last_request_time
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _min_interval:
            time.sleep(_min_interval - elapsed)
        _last_request_time = time.time()


def chat_completion(
    model: str,
    system_prompt: str,
    user_content: str,
    config: dict | None = None,
) -> dict:
    """Send a chat completion request to OpenRouter.

    Returns the parsed response dict with keys: content, model, usage, raw.
    """
    # A 403 is a standing fact about this key and this model. Re-asking costs
    # a round trip per session to be told the same thing.
    if model in _blocked_models:
        raise ModelBlocked("%s: blocked for this key by an earlier 403" % model)
    if config is None:
        config = GENERATION_CONFIG
    # Merged HERE rather than in generate_rp_response: multiturn.run_session
    # calls chat_completion directly with GENERATION_CONFIG, so an override
    # applied only in the wrapper never reached the model actually under test.
    override = MODEL_CONFIG_OVERRIDES.get(model)
    if override:
        config = {**config, **override}

    base_url, wire_model, headers = _endpoint(model)
    local = is_local(model)
    # The rate gate exists to space OpenRouter requests; a dedicated pod has no
    # shared quota to protect, so it is exempt like the local route.
    ungated = local or is_remote(model)

    payload = {
        "model": wire_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        **config,
    }

    global _account_failed
    if _account_failed is not None:
        raise _account_failed

    attempt = 0            # hard errors
    transient = 0          # 429 / 5xx, separate budget (see config)
    while True:
        # The rate gate exists to space OpenRouter requests. Local generations
        # contend for the GPU, not for a shared API quota — running them
        # through the same global interval would serialize them behind cloud
        # spacing for no reason.
        if not ungated:
            _rate_limit()
        try:
            # A 12B on a local GPU is prefill-bound on long RP histories and
            # routinely outruns the cloud timeout. 600s rather than 300s: a 27B
            # at Q4_K_M does not fit a 16GB card (17.4GB of weights plus a
            # 4.3GB KV cache at 16k ctx), so a third of its layers run on the
            # CPU and both prefill and generation are several times slower.
            # Cloud gets 240s rather than 120s: several wave-2 providers
            # (tencent/hy4, qwen3.8-flash, glm-5.3-flash, deepseek-v4.1-flash)
            # exceed 120s on long RP contexts, so the call timed out, retried,
            # and hit the same wall -- spending the retry budget on a limit of
            # our own making rather than on a real provider fault.
            with httpx.Client(timeout=600.0 if (local or is_remote(model)) else 240.0) as client:
                resp = client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

            # 429 and 5xx are both "try again later" from the provider, not
            # defects in our request. Retry them on the transient budget with
            # exponential backoff.
            if resp.status_code == 429 or resp.status_code >= 500:
                transient += 1
                if transient > MAX_TRANSIENT_RETRIES:
                    raise TransientExhausted(
                        "%s after %d transient retries (HTTP %d) for model %s"
                        % ("Rate limited" if resp.status_code == 429
                           else "Upstream error", transient - 1,
                           resp.status_code, wire_model))
                wait = _transient_backoff(transient, resp.headers.get("Retry-After"))
                print("  HTTP %d on %s, retry %d/%d in %.1fs"
                      % (resp.status_code, wire_model, transient,
                         MAX_TRANSIENT_RETRIES, wait))
                time.sleep(wait)
                continue

            # 403 is per-MODEL, not per-account. It means this key may not
            # call this model -- a gated release, a provider restriction, a
            # region block. Latching the whole run on it once cost a full
            # 16-model wave: sakana/fugu-max returned 403 on the first call
            # and every one of the other 668 sessions then failed with that
            # model's error, while the same key served gemma-4-31b and
            # mercury-2.5 seconds later. Block the model, keep the run.
            if resp.status_code == 403:
                _blocked_models.add(wire_model)
                raise ModelBlocked(
                    "HTTP 403 from OpenRouter for %s -- this key may not call "
                    "that model. Skipping it; the run continues." % wire_model)

            # 401 and 402 genuinely are account-level and never recover by
            # retrying. Latch and abort rather than re-discovering it on every
            # remaining call.
            if resp.status_code in (401, 402):
                _account_failed = AccountError(
                    "HTTP %d from OpenRouter (%s). No further requests will be "
                    "attempted this run. %s"
                    % (resp.status_code, wire_model,
                       "Out of credit — top up at openrouter.ai/credits."
                       if resp.status_code == 402 else
                       "Check OPENROUTER_API_KEY."))
                print("\n!! %s\n" % _account_failed)
                raise _account_failed

            if resp.status_code >= 400:
                # raise_for_status() discards the body, which is where the
                # provider explains itself ("max_tokens too large for this
                # prompt", "unknown field", ...). Debugging a 400 without it
                # means guessing.
                raise RuntimeError("HTTP %d from %s: %s"
                                   % (resp.status_code, wire_model,
                                      resp.text[:400]))
            # Under load OpenRouter sometimes returns a non-JSON body (HTML
            # error page, truncated stream). resp.json() then raises
            # JSONDecodeError — treat it like a transient error and retry
            # rather than letting it bubble up and drop the whole session.
            data = resp.json()

            # Reasoning models can leave content=None when their internal
            # thinking exhausts max_tokens. Treat that as an empty response
            # so callers can decide what to do (skip / retry with higher
            # budget) instead of crashing on .strip() downstream.
            # A 200 with no `choices` is a provider hiccup, not an answer.
            # inception/mercury-2.5 does it on roughly one call in three and
            # succeeds on the retry; treating the KeyError as fatal cost it 16
            # of 23 round-4 sessions. Retry it like any other transient.
            choices = data.get("choices")
            if not choices:
                transient += 1
                if transient > MAX_TRANSIENT_RETRIES:
                    raise TransientExhausted(
                        "%s: returned 200 with no choices %d times"
                        % (wire_model, transient))
                wait = _transient_backoff(transient, None)
                print("  200 without choices on %s, retry %d/%d in %.1fs"
                      % (wire_model, transient, MAX_TRANSIENT_RETRIES, wait))
                time.sleep(wait)
                continue

            content = choices[0].get("message", {}).get("content") or ""
            return {
                "content": content,
                "model": data.get("model", model),
                "usage": data.get("usage", {}),
                "raw": data,
            }

        except (httpx.HTTPStatusError, httpx.RequestError, KeyError,
                json.JSONDecodeError, IndexError, RuntimeError) as e:
            # ModelBlocked joins these: a 403 is a standing fact about this
            # key and this model, so retrying it burns the backoff schedule to
            # rediscover the same answer three times.
            if isinstance(e, (AccountError, TransientExhausted, ModelBlocked)):
                raise
            # Timeouts and connection resets are transient too — a slow
            # provider should not burn the hard-error budget.
            if isinstance(e, (httpx.TimeoutException, httpx.ConnectError,
                              httpx.ReadError, httpx.RemoteProtocolError)):
                transient += 1
                if transient > MAX_TRANSIENT_RETRIES:
                    raise TransientExhausted(
                        "%s: %s after %d transient retries"
                        % (wire_model, type(e).__name__, transient - 1))
                wait = _transient_backoff(transient, None)
                print("  %s on %s, retry %d/%d in %.1fs"
                      % (type(e).__name__, wire_model, transient,
                         MAX_TRANSIENT_RETRIES, wait))
                time.sleep(wait)
                continue

            attempt += 1
            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "%s: request failed after %d attempts: %s"
                    % (wire_model, attempt, e))
            wait = RETRY_DELAY_SECONDS * attempt
            print(f"  Error: {e}. Retrying in {wait}s...")
            time.sleep(wait)


def generate_rp_response(
    model: str,
    system_prompt: str,
    conversation_context: str,
) -> dict:
    """Generate an RP response from a test model.

    Applies any per-model override from MODEL_CONFIG_OVERRIDES. This is where
    it belongs rather than in a caller: every path that produces a benchmarked
    reply comes through here, so a model that needs a flag to answer at all
    cannot be reached by a route that forgets it.
    """
    return chat_completion(model, system_prompt, conversation_context,
                           GENERATION_CONFIG)


def judge_response(
    judge_model: str,
    judge_system_prompt: str,
    eval_payload: str,
) -> dict:
    """Send an evaluation payload to a judge model and parse the JSON scores."""
    result = chat_completion(
        judge_model, judge_system_prompt, eval_payload, JUDGE_CONFIG
    )

    # Try to parse JSON from the response
    content = result["content"].strip()

    # Handle markdown code blocks
    if content.startswith("```"):
        # Strip ```json ... ```
        lines = content.split("\n")
        content = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        )

    try:
        scores = json.loads(content)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                scores = json.loads(content[start:end])
            except json.JSONDecodeError:
                scores = {"parse_error": True, "raw_content": result["content"]}
        else:
            scores = {"parse_error": True, "raw_content": result["content"]}

    result["scores"] = scores
    return result
