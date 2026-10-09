"""Bedrock (Converse) advice: structured facts in, {"en", "hi"} out, validated before use.

The model only phrases facts our pipeline computed (CLAUDE.md §4): every number in its output must already be in the
facts, the AQI must appear in both languages, Hindi must be Devanagari, and length is capped. Any failure raises
AdviceRejected (or the boto error), and advice.build falls back to the template.
"""

import json
import os
import re
import time

import boto3
from botocore.config import Config

REGION = os.environ.get("AWS_REGION", "ap-south-1")
MAX_CHARS = 700
MAX_TOKENS = 700

SYSTEM = """You write short outdoor air-quality advice for one place in India, in English and in Hindi.

You get a JSON object of facts computed by our pipeline. Rules:
- Write 2-3 sentences in English and 2-3 sentences in Hindi with the same meaning.
- Hindi: Devanagari script, simple everyday Hindi (not formal or Sanskritised). Write "AQI" as is. Use Western digits (0-9).
- Start by stating the AQI number. Then the recommendation for the profile (school / outdoor worker / general public)
  that matches `outdoor`: yes = outdoor activity is fine; limit = keep outdoor activity short and light; no = keep
  activities indoors. If `for` is "tomorrow", the recommendation is for tomorrow and the AQI is the reading right now.
- Use only numbers that appear in the facts. Never invent numbers, pollutant values, durations or forecasts.
- Health: say nothing beyond `health_statement_en` (CPCB statement for this category). Do not add medical advice.
- If `best_window` is given, mention it using exactly `best_window.en` in English and `best_window.hi` in Hindi
  (times are already written as spoken words; do not convert them to digits like 09:00).
- If `confidence` is "low", you may say the reading is an estimate; do not explain models or stations otherwise.
- Mention visible causes only if `causes.available` is true and something is present.
- Plain text only: no markdown, no emoji, no lists, no "|" characters.

Reply with only a JSON object: {"en": "...", "hi": "..."}"""

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")

_client = None


class AdviceRejected(ValueError):
    pass


def model_id() -> str | None:
    return os.environ.get("BEDROCK_MODEL_ID") or None


def client():
    global _client
    if _client is None:
        cfg = Config(connect_timeout=8, read_timeout=8, retries={"total_max_attempts": 2, "mode": "standard"})
        _client = boto3.client("bedrock-runtime", region_name=REGION, config=cfg)
    return _client


def parse(text: str) -> dict:
    try:
        out = json.loads(_FENCE.sub("", text.strip()))
    except json.JSONDecodeError as e:
        raise AdviceRejected(f"not JSON: {e}") from None
    if not isinstance(out, dict):
        raise AdviceRejected("JSON is not an object")
    return out


def validate(out: dict, facts: dict) -> dict:
    """-> {"en", "hi"} stripped, or raise AdviceRejected with the reason."""
    texts = {}
    for lang in ("en", "hi"):
        t = out.get(lang)
        if not isinstance(t, str) or not t.strip():
            raise AdviceRejected(f"missing or empty {lang}")
        t = t.strip()
        if len(t) > MAX_CHARS:
            raise AdviceRejected(f"{lang} too long ({len(t)} > {MAX_CHARS} chars)")
        texts[lang] = t
    if not _DEVANAGARI.search(texts["hi"]):
        raise AdviceRejected("hi has no Devanagari")
    aqi = str(facts["aqi"])
    allowed = set(_NUMBER.findall(json.dumps(facts, ensure_ascii=False)))
    for lang, t in texts.items():
        found = _NUMBER.findall(t)
        if aqi not in found:
            raise AdviceRejected(f"AQI {aqi} missing from {lang}")
        if extra := sorted(set(found) - allowed):
            raise AdviceRejected(f"{lang} has numbers not in the facts: {extra}")
    return texts


def advise(facts: dict, bedrock=None) -> dict:
    """Facts -> validated {"en", "hi"}. Raises on any failure (caller falls back to the template)."""
    mid = model_id()
    if not mid:
        raise AdviceRejected("BEDROCK_MODEL_ID not set")
    t0 = time.monotonic()
    resp = (bedrock or client()).converse(
        modelId=mid,
        system=[{"text": SYSTEM}],
        messages=[{"role": "user", "content": [{"text": json.dumps(facts, ensure_ascii=False)}]}],
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0.3},
    )
    ms = round((time.monotonic() - t0) * 1000)
    usage = resp.get("usage", {})
    print(json.dumps({"bedrock": "response", "ms": ms, "latency_ms": resp.get("metrics", {}).get("latencyMs"),
                      "stop": resp.get("stopReason"), "in_tokens": usage.get("inputTokens"),
                      "out_tokens": usage.get("outputTokens")}))
    if resp.get("stopReason") == "max_tokens":
        raise AdviceRejected("hit max_tokens")
    text = "".join(c.get("text", "") for c in resp["output"]["message"]["content"])
    return validate(parse(text), facts)
