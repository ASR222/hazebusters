# HazeBusters

Phone video → air quality estimate for places with no monitor. WeMakeDevs × AWS Environmental Hacks 2026 (Air track).

## Licences and credits

- **Ultralytics YOLO11n** (vehicle detection, COCO-pretrained; `ml/src/hazeml/yolo_export.py`, `vehicles.py`) is licensed under **AGPL-3.0** (https://github.com/ultralytics/ultralytics). Because we ship it, this repository must stay open source under AGPL-3.0-compatible terms. The weights (`yolo11n.pt` / `.onnx`) are downloaded at build time and are not committed.
- **Official station index** (`backend/src/air/official_stations.json`): derived from Kaggle "India AQI 2010–2024" by omsandeeppatil (https://www.kaggle.com/datasets/omsandeeppatil/indian-aqi-stations), licensed **CC BY-SA 4.0** (https://creativecommons.org/licenses/by-sa/4.0/). We kept only station code, city, state and coordinates (rounded) and dropped one station without coordinates (`backend/build_station_index.py`). **ShareAlike:** this derived file is shared under the same CC BY-SA 4.0 licence; the licence and source travel with it in the JSON's `source` / `licence` fields.
- **Air-quality data:** CAMS (Copernicus Atmosphere Monitoring Service) via Open-Meteo (non-commercial use, attribution required); live station readings from the World Air Quality Index project (aqicn.org).
