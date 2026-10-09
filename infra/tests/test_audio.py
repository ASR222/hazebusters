"""Polly + S3 audio (processor) and presigned audio URLs (GetJob), with fake clients: no AWS calls."""

import importlib.util
import io

import pytest

import audio
from conftest import INFRA

ADVICE = {"en": "Today: ...", "hi": "आज: बाहर की गतिविधि सीमित रखें।", "source": "template"}


class FakePolly:
    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    def synthesize_speech(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("polly down")
        return {"AudioStream": io.BytesIO(b"ID3fake-mp3")}


class FakeS3:
    def __init__(self):
        self.puts = []

    def put_object(self, **kw):
        self.puts.append(kw)


def test_success_writes_audio_key():
    polly, s3 = FakePolly(), FakeS3()
    out, caveats = audio.synthesize(ADVICE, "job1", polly=polly, s3=s3, bucket="b")
    assert out == {"hi_key": "audio/job1.mp3", "en_key": None} and caveats == []
    assert polly.calls == [{"Text": ADVICE["hi"], "VoiceId": "Kajal", "Engine": "neural",
                            "LanguageCode": "hi-IN", "OutputFormat": "mp3"}]
    assert s3.puts == [{"Bucket": "b", "Key": "audio/job1.mp3", "Body": b"ID3fake-mp3", "ContentType": "audio/mpeg"}]
    assert not s3.puts[0]["Key"].startswith("uploads/")


def test_polly_error_gives_null_keys_and_caveat():
    s3 = FakeS3()
    out, caveats = audio.synthesize(ADVICE, "job1", polly=FakePolly(fail=True), s3=s3, bucket="b")
    assert out == {"hi_key": None, "en_key": None}
    assert caveats == ["Hindi audio unavailable"]
    assert s3.puts == []


@pytest.fixture
def get_job():
    spec = importlib.util.spec_from_file_location("get_job_app", INFRA / "functions" / "get_job" / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_get_job_presigns_audio_key(get_job, monkeypatch):
    seen = []
    monkeypatch.setattr(get_job.s3, "generate_presigned_url",
                        lambda op, Params, ExpiresIn: seen.append((op, Params, ExpiresIn)) or "https://signed")
    urls = get_job.audio_urls({"audio": {"hi_key": "audio/job1.mp3", "en_key": None}})
    assert urls == {"hi": "https://signed", "en": None}
    assert seen == [("get_object", {"Bucket": "test-bucket", "Key": "audio/job1.mp3"}, 3600)]
    assert get_job.audio_urls(None) == {"hi": None, "en": None}
    assert get_job.audio_urls({"audio": {"hi_key": None, "en_key": None}}) == {"hi": None, "en": None}
