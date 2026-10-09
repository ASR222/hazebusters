"""Spoken advice (contract `audio`): Hindi advice -> Polly (Kajal, neural, hi-IN) -> s3://<bucket>/audio/{job_id}.mp3.

Stores the S3 key only; GetJob presigns a fresh GET URL on each read. Never writes under uploads/ (that prefix
triggers the processor). A Polly/S3 failure never fails the job: keys stay null and a caveat is added.
English audio: not yet (en_key stays null).
"""

import os
import time
import traceback

import boto3

REGION = os.environ.get("AWS_REGION", "ap-south-1")
VOICE = {"VoiceId": "Kajal", "Engine": "neural", "LanguageCode": "hi-IN", "OutputFormat": "mp3"}
CAVEAT = "Hindi audio unavailable"

_clients: dict = {}


def _client(name: str):
    if name not in _clients:
        _clients[name] = boto3.client(name, region_name=REGION)
    return _clients[name]


def key_for(job_id: str) -> str:
    return f"audio/{job_id}.mp3"


def synthesize(advice: dict, job_id: str, polly=None, s3=None, bucket: str | None = None) -> tuple[dict, list[str]]:
    """-> (contract `audio`, caveats)."""
    t0 = time.monotonic()
    try:
        polly = polly or _client("polly")
        s3 = s3 or _client("s3")
        bucket = bucket or os.environ["BUCKET_NAME"]
        speech = polly.synthesize_speech(Text=advice["hi"], **VOICE)
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
