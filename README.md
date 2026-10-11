# HazeBusters

**Most places have no monitor nearby. We tell you how far your nearest reading really is, what's polluting the air around you, and what to do today, in Hindi.**

WeMakeDevs × AWS Environmental Hacks 2026 (Air track). **Live demo:** https://main.dxwuap9t49si3.amplifyapp.com
Write-up (problem, results, limitations, credits): [`docs/WRITEUP.md`](docs/WRITEUP.md).

## What it does
1. Pick a profile (school / outdoor worker / general) and share your location.
2. **Air.** You get a CPCB-style AQI from the nearest WAQI station and the CAMS forecast (via Open-Meteo), with the source, its distance and a confidence level. If the station is more than 25 km away or more than 3 h old, it uses CAMS scaled ×1.25.
3. **Decision.** Outdoor yes / limit / no for the rest of the profile's hours (or tomorrow's), plus the best window.
4. **Advice** in English and Hindi, with audio. Bedrock only phrases our numbers, and falls back to a template.
5. **Optional 10 s clip (experimental).** Quality gate, then a smoke/fire classifier with a CAM heatmap, and a YOLO11n vehicle count. Causes never change the AQI.

## Architecture (AWS, ap-south-1)
```
PWA (Amplify Hosting)
  └─► API Gateway (HTTP API) ─► Lambda: create job (DynamoDB) + presigned S3 upload URL
PWA uploads clip ─► S3 uploads/ ─(event)─► Lambda container image (ECR) "processor":
      frames ~1/s → quality gate → smoke/fire ONNX + CAM, YOLO11n ONNX (vehicles)
      → air: WAQI + Open-Meteo/CAMS → CPCB-style AQI, source, confidence, decision, best window
      → advice: Amazon Bedrock (Nova 2 Lite, Converse; template fallback) → Amazon Polly (hi-IN / en-IN)
      → result in DynamoDB; overlays/ and audio/ in S3 (7-day lifecycle)
PWA polls ◄─ API Gateway ◄─ Lambda: get job (presigned audio + CAM URLs)
```
Infrastructure as code: AWS SAM / CloudFormation (`infra/template.yaml`).

## Repo layout
| Path | What |
|---|---|
| `frontend/` | PWA (plain HTML/CSS/JS, no build step) |
| `infra/` | SAM template, Lambda handlers (`functions/`), container processor (`processor/`), e2e test |
| `backend/` | Air logic (`src/air/`: WAQI, Open-Meteo/CAMS, combine, decision rules), API contract (`contract.json`), official station index |
| `shared/` | `cpcb_aqi`: the CPCB-style AQI from PM2.5/PM10 (no dependencies), used by `backend/` and `ml/` |
| `ml/` | Experiments and models: image→AQI (dropped), CAMS validation, smoke/fire classifier, YOLO export, own-clip scoring; results in `ml/RESULTS.md` |
| `design/` | UI design notes |
| `docs/` | Write-up |

## Run the tests
```bash
cd shared && uv run pytest -q
cd backend && uv run pytest -q          # HTTP mocked
cd ml && uv run pytest -q               # data-dependent tests skip without $DATA_DIR
cd infra && uv run --no-project --with pytest --with boto3 --with numpy --with pillow --with onnxruntime==1.31.0 pytest -q tests
```

## Deploy
- **Models:** they aren't in git. Produce them with `ml/` (`hazeml.train_smokefire` + `hazeml.export_onnx`, `hazeml.yolo_export`), then copy `smokefire.onnx`, `head.npz`, `export_report.json` and `yolo11n.onnx` into `infra/processor/models/`.
- **Backend:** from `infra/`, run `sam build && sam deploy` (first time: `sam deploy --guided`). The WAQI token is a NoEcho stack parameter. Keep `samconfig.toml` out of git; it's gitignored.
- **Frontend:** set `API_BASE` in `frontend/config.js` to the stack's `ApiUrl` output, bump `CACHE_VERSION` in `sw.js`, then upload the zip to Amplify Hosting (steps in `frontend/README.md`).
- **Never commit:** `.env`, tokens, account IDs, datasets, clips or model weights.

## Credits
- **TRAQID:** Kathalkar et al., ICVGIP 2024 (research use).
- **India/Nepal air-pollution images:** Kaggle, CC BY-NC-SA 3.0 IGO, with Eff-AQI (Utomo et al., GoodIT '23).
- **D-Fire:** Venâncio et al. 2022, CC0.
- **Pyro-SDIS:** Pyronear, Apache-2.0.
- **CAMS** (Copernicus Atmosphere Monitoring Service) via **Open-Meteo** (non-commercial use, attribution required).
- **Live station readings:** World Air Quality Index project (aqicn.org).
- **PyTorch / torchvision** (EfficientNet-B0 ImageNet weights).
- **Official station index** (`backend/src/air/official_stations.json`): derived from Kaggle "India AQI 2010–2024" by omsandeeppatil (https://www.kaggle.com/datasets/omsandeeppatil/indian-aqi-stations), licensed **CC BY-SA 4.0** (https://creativecommons.org/licenses/by-sa/4.0/). We kept only station code, city, state and coordinates (rounded) and dropped one station without coordinates (`backend/build_station_index.py`). **ShareAlike:** this derived file is shared under the same CC BY-SA 4.0 licence; the licence and source travel with it in the JSON's `source` / `licence` fields.
- **AI tools:** Claude Code and Claude chat were used for code, experiments and docs (see `docs/WRITEUP.md`).

## Licence
- **Ultralytics YOLO11n** (vehicle detection, COCO-pretrained; `ml/src/hazeml/yolo_export.py`, `vehicles.py`, `infra/processor/vehicles.py`) is licensed under **AGPL-3.0** (https://github.com/ultralytics/ultralytics). Because we ship it, this repository must stay open source under AGPL-3.0-compatible terms. The weights are downloaded at build time and not committed.
- **Our code** is intended to be released under **AGPL-3.0**; a `LICENSE` file still has to be added.
- **Data:** the image datasets above (TRAQID, India/Nepal) and the Open-Meteo free tier are **non-commercial**. Commercial use needs permission or our own data.
