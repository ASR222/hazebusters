"""Spoken advice (contract `audio`): Hindi advice -> Polly (Kajal, neural, hi-IN) -> s3://<bucket>/audio/{job_id}.mp3.

Speech is SSML: rate 90%, a 450 ms break after each sentence end, 200 ms after commas, 600 ms between advice
sections (recommendation -> health statement -> best window). Stores the S3 key only; GetJob presigns a fresh
GET URL on each read. Never writes under uploads/ (that prefix triggers the processor). A Polly/S3 failure never fails the job: keys stay null and a caveat is added.
English audio: not yet (en_key stays null).
"""

import os
import re
import time
import traceback
from xml.sax.saxutils import escape

import boto3

from advice import spoken_times

REGION = os.environ.get("AWS_REGION", "ap-south-1")
VOICE = {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN", "OutputFormat": "mp3", "TextType": "ssml"}
RATE = "90%"
BREAK_SENTENCE, BREAK_COMMA, BREAK_SECTION = "450ms", "200ms", "600ms"

_SENTENCE_END = re.compile(r"([।?!.])(?=\s|$)")
_COMMA = re.compile(r",(?=\s)")
CAVEAT = "Hindi audio unavailable"

_clients: dict = {}


def _client(name: str):
    if name not in _clients:
        _clients[name] = boto3.client(name, region_name=REGION)
    return _clients[name]


def key_for(job_id: str) -> str:
    return f"audio/{job_id}.mp3"


def _section_ssml(text: str) -> str:
    text = escape(spoken_times(text.strip()))
    text = _COMMA.sub(f',<break time="{BREAK_COMMA}"/>', text)
    text = _SENTENCE_END.sub(rf'\1<break time="{BREAK_SENTENCE}"/>', text)
    # The section break replaces a trailing sentence break.
    return text.removesuffix(f'<break time="{BREAK_SENTENCE}"/>')


def to_ssml(sections: str | list[str]) -> str:
    """Plain Hindi text (or its sections) -> SSML for Polly. Escapes &, <, > before adding tags."""
    parts = [sections] if isinstance(sections, str) else sections
    body = f'<break time="{BREAK_SECTION}"/>'.join(_section_ssml(p) for p in parts if p.strip())
    return f'<speak><prosody rate="{RATE}">{body}</prosody></speak>'


def synthesize(hi: str | list[str], job_id: str, polly=None, s3=None, bucket: str | None = None) -> tuple[dict, list[str]]:
    """`hi`: Hindi advice text, or its sections (advice.build). -> (contract `audio`, caveats)."""
    t0 = time.monotonic()
    try:
        polly = polly or _client("polly")
        s3 = s3 or _client("s3")
        bucket = bucket or os.environ["BUCKET_NAME"]
        speech = polly.synthesize_speech(Text=to_ssml(hi), **VOICE)
        mp3 = speech["AudioStream"].read()
        if not mp3:
            raise ValueError("Polly returned empty audio")
        key = key_for(job_id)
        s3.put_object(Bucket=bucket, Key=key, Body=mp3, ContentType="audio/mpeg")
        print(f'{{"audio": "ok", "key": "{key}", "bytes": {len(mp3)}, "ms": {(time.monotonic() - t0) * 1000:.0f}}}')
        return {"hi_key": key, "en_key": None}, []
    except Exception:
        traceback.print_exc()
        return {"hi_key": None, "en_key": None}, [CAVEAT]
