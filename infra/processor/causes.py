"""Visible causes (contract `causes`): EfficientNet-B0 smoke/fire classifier (ONNX) over the sampled frames.

Model: ml/runs/smokefire/20261009-220554_efficientnet_b0_s0 (smokefire.onnx, head.npz, export_report.json, copied
to models/, gitignored). Preprocessing matches the ML eval path (hazeml.data.eval_transform with the checkpoint's
"preprocess"): RGB, whole frame squashed to 224x224 (bilinear, antialiased), /255, ImageNet mean/std, NCHW.
Outputs: final conv features (CAM) + logits for (smoke, fire); sigmoid -> probabilities.

Per clip: prob = max over frames; present = >= 2 frames over the threshold (>= 1 if fewer than 3 frames).
If something is present, a CAM overlay of the best frame goes to s3 overlays/{job_id}.jpg (never uploads/).
Causes never change the AQI. Boxes and vehicle count wait for YOLO (boxes = [], vehicle_count = null).
"""

import io
import json
import os
import time
from pathlib import Path

import numpy as np
from PIL import Image

import cam

MODEL_DIR = Path(__file__).resolve().parent / "models"
LABELS = ("smoke", "fire")
THRESHOLDS = {"smoke": 0.359, "fire": 0.667}  # max F1 on val (ml run report.md)
SIZE = (224, 224)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
OVERLAY_MAX_W = 640
UNAVAILABLE = "Smoke check unavailable for this clip"

_session = None
_head = None
_load_error: Exception | None = None


def load(model_dir: Path | None = None) -> None:
    """Load the ONNX session + CAM head into the module cache. Called lazily by detect() on the first invocation
    (not at import: a slow cold start inside Lambda's 10 s init phase timed out and forced a re-init). A failure
    is kept, reported per clip, and retried on the next invocation."""
    global _session, _head, _load_error
    t0 = time.monotonic()
    try:
        model_dir = model_dir or MODEL_DIR
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = os.cpu_count() or 1
        _session = ort.InferenceSession(str(model_dir / "smokefire.onnx"), opts, providers=["CPUExecutionProvider"])
        with np.load(model_dir / "head.npz") as h:
            _head = {"weight": h["weight"], "bias": h["bias"], "labels": tuple(str(x) for x in h["labels"])}
        if _head["labels"] != LABELS:
            raise ValueError(f"head labels {_head['labels']} != {LABELS}")
        _load_error = None
        print(json.dumps({"causes": "model_loaded", "ms": round((time.monotonic() - t0) * 1000)}))
    except Exception as e:
        _session, _head, _load_error = None, None, e
        print(json.dumps({"causes": "model_load_failed", "reason": f"{type(e).__name__}: {e}"}))


def preprocess(rgb_frames: list[np.ndarray]) -> np.ndarray:
    """HxWx3 uint8 RGB frames -> (N, 3, 224, 224) float32, normalised like the ML eval transform."""
    out = []
    for f in rgb_frames:
        img = Image.fromarray(f).resize(SIZE, Image.Resampling.BILINEAR)  # (w, h); square, so order doesn't matter
        out.append((np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD)
    return np.stack(out).transpose(0, 3, 1, 2).astype(np.float32)


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def aggregate(probs: np.ndarray) -> dict:
    """(N, 2) per-frame probabilities -> {label: {present, prob, mean, count}}."""
    n = len(probs)
    need = 2 if n >= 3 else 1
    out = {}
    for j, label in enumerate(LABELS):
        p = probs[:, j]
        count = int((p >= THRESHOLDS[label]).sum())
        out[label] = {"present": count >= need, "prob": round(float(p.max()), 3),
                      "mean": round(float(p.mean()), 3), "count": count}
    return out


def stub(n_frames: int) -> dict:
    return {
        "frames_used": n_frames,
        "frames_rejected": 0,
        "reject_reasons": [],
        "smoke": {"present": False, "prob": 0.0},
        "fire": {"present": False, "prob": 0.0},
        "boxes": [],
        "vehicle_count": None,
        "gradcam_key": None,
    }


def overlay_jpeg(rgb: np.ndarray, features: np.ndarray, label: int) -> bytes:
    """CAM overlay of one frame, at most OVERLAY_MAX_W px wide, as JPEG bytes."""
    h, w = rgb.shape[:2]
    if w > OVERLAY_MAX_W:
        rgb = np.asarray(Image.fromarray(rgb).resize((OVERLAY_MAX_W, round(h * OVERLAY_MAX_W / w)),
                                                     Image.Resampling.BILINEAR))
    img = Image.fromarray(cam.overlay(rgb, cam.cam(features, _head["weight"], label)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def detect(bgr_frames: list[np.ndarray], job_id: str, s3, bucket: str) -> tuple[dict, list[str], bool]:
    """-> (contract `causes`, caveats, model_ran). Never raises: on model failure, stub causes + UNAVAILABLE caveat;
    an overlay failure only leaves gradcam_key null."""
    t0 = time.monotonic()
    try:
        if _session is None:
            load()
        if _session is None:
            raise RuntimeError(f"model not loaded: {_load_error!r}")
        rgb = [np.ascontiguousarray(f[..., ::-1]) for f in bgr_frames]  # OpenCV decodes BGR
        features, logits = _session.run(["features", "logits"], {"input": preprocess(rgb)})
        probs = sigmoid(logits)
        agg = aggregate(probs)
        ms = round((time.monotonic() - t0) * 1000)
        print(json.dumps({"causes": "ok", "frames": len(rgb), "model_ms": ms,
                          **{k: {"max": v["prob"], "mean": v["mean"], "count": v["count"], "present": v["present"]}
                             for k, v in agg.items()}}))
        out = stub(len(rgb))
        for label in LABELS:
            out[label] = {"present": agg[label]["present"], "prob": agg[label]["prob"]}
    except Exception as e:
        print(json.dumps({"causes": "failed", "reason": f"{type(e).__name__}: {e}"}))
        return stub(len(bgr_frames)), [UNAVAILABLE], False
    present = [j for j, label in enumerate(LABELS) if agg[label]["present"]]
    if present:
        try:
            j = max(present, key=lambda k: agg[LABELS[k]]["prob"])  # the stronger label among those present
            i = int(np.argmax(probs[:, j]))  # its best frame
            key = f"overlays/{job_id}.jpg"
            body = overlay_jpeg(rgb[i], features[i], j)
            s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="image/jpeg")
            out["gradcam_key"] = key
            print(json.dumps({"overlay": key, "label": LABELS[j], "frame": i, "bytes": len(body)}))
        except Exception as e:
            print(json.dumps({"overlay": "failed", "reason": f"{type(e).__name__}: {e}"}))
    return out, [], True
