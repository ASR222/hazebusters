"""Spoken advice (contract `audio`). STUB: no audio yet.

Extension point: Polly (Hindi voice) -> S3 under audio/{job_id}/ (never uploads/) -> return the keys.
"""


def synthesize(advice: dict, job_id: str) -> dict:
    return {"hi_key": None, "en_key": None}
