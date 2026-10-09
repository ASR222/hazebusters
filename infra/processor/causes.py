"""Visible causes (contract `causes`). STUB: fixed dummy values until the ONNX models land.

Extension point: replace detect() with quality gate -> EfficientNet-B0 smoke/fire/clear (+ Grad-CAM to S3,
never under uploads/) -> YOLO11n boxes + vehicle count. Causes never change the AQI.
"""

import numpy as np

CAVEATS = ["Visible causes are placeholder values: the smoke/fire and vehicle models are not wired in yet."]


def detect(frames: list[np.ndarray]) -> dict:
    return {
        "frames_used": len(frames),
        "frames_rejected": 0,
        "reject_reasons": [],
        "smoke": {"present": False, "prob": 0.0},
        "fire": {"present": False, "prob": 0.0},
        "boxes": [],
        "vehicle_count": 0,
        "gradcam_key": None,
    }
