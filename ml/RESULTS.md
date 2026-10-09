# ML results

All numbers are copied from files in `ml/runs/` (gitignored; regenerate with the commands below).

## 1. Image → AQI band: negative result (Thu 8 Oct 2026)

**Question:** can a phone/dashcam image tell the CPCB-style AQI band (Good/Satisfactory · Moderate/Poor · Very Poor/Severe) on a day or place the model hasn't seen?
**Answer on our data: no.** This is why the product doesn't estimate AQI from images (CLAUDE.md §3/§4).

Data: TRAQID day/front (13,789 frames, **17 dates**, Hyderabad dashcam); India/Nepal `All_img` (12,240 frames, 115 moments, 8 locations incl. Biratnagar, Nepal). Labels recomputed from PM2.5/PM10 with `hazeml.aqi`.

### 1a. Fine-tuned EfficientNet-B0, frozen date split
Run: `ml/runs/20261008-174356_efficientnet_b0_s0/` (`uv run python -m hazeml.train --seed 0`).

| split | accuracy | majority baseline | macro-F1 | band-2 recall |
|---|---|---|---|---|
| test (5 dates, 2,771 frames) | **32.0%** | 47.5% | 0.312 | 57.3% |
| val (2 dates, 1,361 frames) | 22.2% | 47.4% | 0.175 | 2.7% |
| its own train dates (eval preprocessing) | 89.0% | 47.2% | 0.881 | 95.9% |

Mean confidence on test 0.80 (confidently wrong). Per test date: 50.3% / 42.9% / **9.4%** / 43.4% / 15.1%. 89% on train dates rules out a pipeline bug: the model memorises each day's look, not haze. Seeds 1–2 were stopped once this was clear.

### 1b. Probes (no CNN training; `uv run python -m hazeml.probes features && ... run`)
Logistic regression, balanced class weights, standardised; C fixed (0.1 embeddings, 1.0 handcrafted), not tuned. Baseline = majority class of each training fold. "Group" = majority vote per held-out date (TRAQID) or moment (India/Nepal). Source: `ml/runs/probes/summary.md`.

| probe | task | level | n | macro-F1 | accuracy | baseline | top-class recall |
|---|---|---|---|---|---|---|---|
| frozen B0 embeddings, leave-one-date-out | 3-band | frame | 13789 | 0.318 | 33.5% | 33.7% | 33.6% |
| | 3-band | date | 17 | 0.373 | 41.2% | 47.1% | 33.3% |
| | VP/Severe vs rest | frame | 13789 | 0.512 | 63.2% | 83.4% | 40.9% |
| | VP/Severe vs rest | date | 17 | 0.595 | 76.5% | 82.4% | 33.3% |
| handcrafted (dark channel, contrast, saturation, brightness), LODO | 3-band | frame | 13789 | 0.336 | 36.1% | 33.7% | 46.4% |
| | 3-band | date | 17 | 0.342 | 41.2% | 47.1% | 66.7% |
| | VP/Severe vs rest | frame | 13789 | 0.469 | 51.6% | 83.4% | 66.1% |
| | VP/Severe vs rest | date | 17 | 0.564 | 58.8% | 82.4% | 100.0% |
| handcrafted + humidity, LODO | 3-band | frame | 13789 | 0.464 | 52.8% | 33.7% | 28.5% |
| | 3-band | date | 17 | 0.398 | 47.1% | 47.1% | 0.0% |
| | VP/Severe vs rest | frame | 13789 | 0.497 | 56.2% | 83.4% | 60.6% |
| | VP/Severe vs rest | date | 17 | 0.530 | 58.8% | 82.4% | 66.7% |
| frozen B0 embeddings, **random 5-fold over frames** (leaky) | 3-band | frame | 13789 | 0.601 | 63.3% | 47.3% | 59.2% |
| | 3-band | date | 17 | 1.000 | 100.0% | 52.9% | 100.0% |
| | VP/Severe vs rest | frame | 13789 | 0.663 | 76.2% | 83.4% | 66.1% |
| | VP/Severe vs rest | date | 17 | 1.000 | 100.0% | 82.4% | 100.0% |
| India/Nepal frozen B0 embeddings, leave-one-city-out | 3-band | frame | 12240 | 0.204 | 20.0% | 2.8% | 8.6% |
| | 3-band | moment | 115 | 0.144 | 13.0% | 3.5% | 2.4% |
| | VP/Severe vs rest | frame | 12240 | 0.293 | 34.8% | 60.7% | 8.6% |
| | VP/Severe vs rest | moment | 115 | 0.266 | 33.0% | 63.5% | 4.8% |

**Takeaways**
- 65% of TRAQID's band variance (70% of AQI variance) is **between dates** → ~17 independent samples.
- Leaving out whole dates, image features sit at the baseline. Humidity (a weather reading) adds frame-level signal, but date-level accuracy stays at the baseline and no Very Poor/Severe day is found.
- The **random frame split inflates accuracy by ~30 points** (63.3% vs 33.5%) — a random split would have produced a convincing false result.
- India/Nepal leave-one-city-out is **inverted** (clean cities called polluted and vice versa; Delhi 4.5%): each city is nearly one band, so the model learns the city. The per-fold majority baseline is degenerate there (held-out city's band is never the training majority); against 3-class chance (~33%) 20% is still below.

## 2. CAMS (Open-Meteo) vs ground stations

_Pending — `ml/validate_cams.py`._
