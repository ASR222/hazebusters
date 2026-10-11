# HazeBusters — how bad is the air where there's no monitor?

**Problem.** Ranchi has no official air-quality monitor. The nearest official station in our index is Jamshedpur, **~110 km** away, and it isn't reporting to WAQI either: on 11 Oct 2026 WAQI's geo feed answered "can not connect" there, and no reporting station showed within 25 km. Even big cities go dark: all **9 WAQI stations in Hyderabad last reported on 23 Jun 2026**. A school deciding whether today's assembly or PE can be outdoors has nothing to go on.

**What we built.** A phone web app (PWA):
1. **Air.** Your location goes to the nearest WAQI station (US AQI converted back to µg/m³) and to the CAMS forecast for the area via Open-Meteo (~45 km grid). Both become a CPCB-style AQI. The page always shows **which source was used, how far away it is and how confident we are**. If the station is more than 25 km away or more than 3 h old, it uses CAMS scaled ×1.25.
2. **Decision.** For a school or an outdoor worker: outdoor *yes / limit / no*, based on the worst 3-hour slot left in their hours, plus the **best window** today (or tomorrow).
3. **Advice** in **English and Hindi**, with **audio**, ready to share. The LLM only phrases numbers we computed, and falls back to a template.
4. **Clip (experimental).** A 10 s video goes through a quality gate (dark / blur / no sky). Then a smoke/fire classifier with a CAM heatmap, and a YOLO11n vehicle count. These are causes only: they never change the AQI, and the advice line is hedged ("possible smoke").

**AWS.** S3 (uploads, audio, CAM overlays), Lambda (a container image for the processor, plus API handlers), DynamoDB (jobs), API Gateway (HTTP API), **Amazon Bedrock** (Nova 2 Lite, Converse), **Amazon Polly** (neural Hindi and English), Amplify Hosting (PWA), SAM / CloudFormation, ECR. All in ap-south-1.

**Results (honest).**

| What we tested | Result |
|---|---|
| Phone image → AQI band (EfficientNet-B0 on TRAQID, unseen days) | **32.0%** accuracy vs a **47.5%** majority baseline (89% on the training days): it learns the day, not the haze → **dropped** |
| Random frame split vs leave-one-day-out (same features) | 63.3% vs 33.5%: a random split inflates accuracy by **~30 points** |
| CAMS vs ground stations, daily PM2.5 2023–24 | Reads ~0.8× stations (median 0.78 / 0.79 / 0.81 for Delhi / Hyderabad / Patna); catches only 67/201 (Delhi) and 46/133 (Patna) Very Poor/Severe days |
| CAMS ×1.25 | Same band: Delhi 56.2→63.2%, Patna 62.5→67.6%, but **Hyderabad 94.8→86.3% (worse)**. Very Poor/Severe caught: 125/201 and 80/133, with more false alarms (1→10, 8→20). Tuned in-sample |
| Smoke/fire classifier, D-Fire test (grouped split) | AP **smoke 0.979**, fire 0.982 |
| Same model on Pyro-SDIS (distant wildfire cameras) | Smoke recall 13.4%; AP 0.845, **below the 0.868 base rate** → doesn't transfer |
| Our own phone clips, smoke threshold 0.600 (23 clips, 1 duplicate excluded) | Smoke **6/7**, fire 2/2, indoor clip rejected; **5/13 no-smoke clips flagged** (city haze, bright sky) |

**Limitations.**
- **AQI method:** "CPCB-style" AQI from hourly PM2.5/PM10, not the official 24-hour, 3-or-more-pollutant AQI.
- **Data sources:** WAQI values are inverted with the 2012 EPA PM2.5 breakpoints. CAMS is a 45 km model.
- **×1.25 correction:** fitted on three cities and on PM2.5 only.
- **Smoke model:** trained on web and wildfire images. It flags city haze, and it has been tested on only 23 of our own clips.
- **Quality gate:** calibrated on 24 own clips with **thin margins**. The indoor clip kept 2 good frames against the 3 needed, and `fire_smoke_01` passes only 9/15 frames. Needs recalibrating as clips grow.
- **Health statements:** CPCB wording; only the Severe line is confirmed against an official source.
- **Licences:** TRAQID, India/Nepal and the Open-Meteo free tier are non-commercial.

**Roadmap.**
- **Data flywheel:** opt-in clips paired with the nearest reading become a labelled Indian haze/smoke set. We'd retrain with city haze as a negative, and recalibrate the gate and the CAMS correction per region.
- **School daily alerts:** a morning message with today's outdoor window.
- **More languages:** Bengali, Tamil, Telugu, Marathi.

**AI tools used.** Claude Code (code, experiments, docs) and Claude chat (planning, review). Commits carry no AI trailer; this is the disclosure.

**Credits.**
- **TRAQID:** Kathalkar et al., ICVGIP 2024.
- **India/Nepal air-pollution images** (Kaggle, CC BY-NC-SA 3.0 IGO) and **Eff-AQI** (Utomo et al., GoodIT '23).
- **D-Fire:** Venâncio et al. 2022, CC0.
- **Pyro-SDIS:** Pyronear, Apache-2.0.
- **India AQI 2010–2024 stations:** Kaggle, omsandeeppatil, CC BY-SA 4.0.
- **CAMS** (Copernicus) via **Open-Meteo**.
- **World Air Quality Index project** (aqicn.org).
- **Ultralytics YOLO11n:** AGPL-3.0.
- PyTorch / torchvision (EfficientNet-B0 ImageNet weights).
