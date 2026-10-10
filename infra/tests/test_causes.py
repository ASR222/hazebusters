"""Smoke/fire causes: preprocessing, per-clip aggregation, overlay, and fallback (fake ONNX session, fake S3)."""

import numpy as np
import pytest

import causes


class FakeSession:
    def __init__(self, logits=None, fail=False):
        self.logits, self.fail, self.inputs = logits, fail, []

    def run(self, names, feeds):
        self.inputs.append(feeds["input"])
        if self.fail:
            raise RuntimeError("onnx boom")
        n = len(feeds["input"])
        feats = np.random.default_rng(0).random((n, 1280, 7, 7), dtype=np.float32)
        return [feats, np.asarray(self.logits, dtype=np.float32)]


class FakeS3:
    def __init__(self, fail=False):
        self.fail, self.puts = fail, []

    def put_object(self, **kw):
        if self.fail:
            raise RuntimeError("s3 down")
        self.puts.append(kw)


def logit(p):
    return float(np.log(p / (1 - p)))


@pytest.fixture
def model(monkeypatch):
    head = {"weight": np.random.default_rng(1).standard_normal((2, 1280)).astype(np.float32),
            "bias": np.zeros(2, np.float32), "labels": ("smoke", "fire")}
    monkeypatch.setattr(causes, "_head", head)

    def use(logits=None, fail=False):
        s = FakeSession(logits, fail)
        monkeypatch.setattr(causes, "_session", s)
        return s
    return use


def frames(n, h=480, w=640):
    rng = np.random.default_rng(2)
    return [rng.integers(0, 256, (h, w, 3), dtype=np.uint8) for _ in range(n)]


# --- preprocessing ------------------------------------------------------------------------------


def test_preprocess_shape_dtype():
    x = causes.preprocess(frames(3, 360, 640))  # non-square frames are squashed, not cropped
    assert x.shape == (3, 3, 224, 224) and x.dtype == np.float32


def test_preprocess_normalisation():
    flat = [np.full((100, 300, 3), (255, 0, 128), dtype=np.uint8)]
    x = causes.preprocess(flat)[0]
    expected = (np.array([255, 0, 128]) / 255 - causes.MEAN) / causes.STD
    assert np.allclose(x, expected[:, None, None], atol=1e-5)  # every pixel, per channel (NCHW)


def test_preprocess_matches_eval_constants():
    assert causes.SIZE == (224, 224)
    assert causes.MEAN.tolist() == pytest.approx([0.485, 0.456, 0.406])
    assert causes.STD.tolist() == pytest.approx([0.229, 0.224, 0.225])


# --- aggregation --------------------------------------------------------------------------------


def test_aggregate_needs_two_frames_over_threshold():
    probs = np.array([[0.9, 0.1]] + [[0.1, 0.1]] * 9)  # one smoky frame of ten
    agg = causes.aggregate(probs)
    assert agg["smoke"] == {"present": False, "prob": 0.9, "mean": 0.18, "count": 1}
    probs[1, 0] = 0.4  # second frame just over the 0.359 threshold
    assert causes.aggregate(probs)["smoke"]["present"] is True


def test_aggregate_one_frame_enough_for_short_clips():
    assert causes.aggregate(np.array([[0.5, 0.1], [0.1, 0.1]]))["smoke"]["present"] is True


def test_aggregate_fire_threshold():
    probs = np.array([[0.1, 0.66]] * 5)
    assert causes.aggregate(probs)["fire"]["present"] is False
    assert causes.aggregate(np.array([[0.1, 0.667]] * 5))["fire"] == {"present": True, "prob": 0.667,
                                                                      "mean": 0.667, "count": 5}


# --- detect -------------------------------------------------------------------------------------


def test_detect_clear_clip(model):
    s = model([[logit(0.05), logit(0.01)]] * 4)
    out, cav, ran = causes.detect(frames(4), "job1", FakeS3(), "b")
    assert ran and cav == []
    assert out["smoke"] == {"present": False, "prob": 0.05} and out["fire"]["present"] is False
    assert out["gradcam_key"] is None and out["boxes"] == [] and out["vehicle_count"] is None
    assert out["frames_used"] == 4
    assert s.inputs[0].shape == (4, 3, 224, 224)


def test_detect_bgr_to_rgb(model):
    s = model([[0.0, 0.0]])
    blue_bgr = np.zeros((10, 10, 3), np.uint8)
    blue_bgr[..., 0] = 255  # pure blue in OpenCV's BGR order
    causes.detect([blue_bgr], "job1", FakeS3(), "b")
    x = s.inputs[0][0]
    assert x[2].mean() > x[0].mean()  # channel 2 (B in RGB order) is the bright one


def test_detect_smoke_writes_overlay(model):
    s3 = FakeS3()
    model([[logit(0.2), 0.0], [logit(0.8), 0.0], [logit(0.5), 0.0]])
    out, cav, ran = causes.detect(frames(3, 720, 1280), "job1", s3, "b")
    assert out["smoke"] == {"present": True, "prob": 0.8} and out["gradcam_key"] == "overlays/job1.jpg"
    (put,) = s3.puts
    assert put["Key"] == "overlays/job1.jpg" and put["ContentType"] == "image/jpeg" and put["Bucket"] == "b"
    assert put["Body"][:3] == b"\xff\xd8\xff"
    from PIL import Image
    import io
    assert Image.open(io.BytesIO(put["Body"])).size == (640, 360)  # <= 640 px wide, aspect kept


def test_overlay_failure_keeps_detection(model):
    model([[logit(0.8), 0.0]] * 3)
    out, cav, ran = causes.detect(frames(3), "job1", FakeS3(fail=True), "b")
    assert ran and cav == [] and out["smoke"]["present"] is True and out["gradcam_key"] is None


def test_model_error_falls_back_to_stub(model):
    model(fail=True)
    out, cav, ran = causes.detect(frames(5), "job1", FakeS3(), "b")
    assert not ran and cav == ["Smoke check unavailable for this clip"]
    assert out == causes.stub(5)


def test_model_not_loaded_falls_back(monkeypatch):
    monkeypatch.setattr(causes, "_session", None)
    out, cav, ran = causes.detect(frames(2), "job1", FakeS3(), "b")
    assert not ran and cav == [causes.UNAVAILABLE] and out["smoke"]["present"] is False


def test_load_failure_is_recorded(tmp_path, monkeypatch):
    monkeypatch.setattr(causes, "_session", None)
    causes.load(tmp_path)  # no model files there
    assert causes._session is None and causes._load_error is not None
