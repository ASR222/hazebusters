# HazeBusters

Phone video → air quality estimate for places with no monitor. WeMakeDevs × AWS Environmental Hacks 2026 (Air track).

## Licences and credits

- **Ultralytics YOLO11n** (vehicle detection, COCO-pretrained; `ml/src/hazeml/yolo_export.py`, `vehicles.py`) is licensed under **AGPL-3.0** (https://github.com/ultralytics/ultralytics). Because we ship it, this repository must stay open source under AGPL-3.0-compatible terms. The weights (`yolo11n.pt` / `.onnx`) are downloaded at build time and are not committed.
