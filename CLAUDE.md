# PROJECT CONTEXT — Environmental Hacks (Air track)

> Handoff for Claude Code or any new AI chat session. Read this fully before helping.
> Lives in the repo as `CLAUDE.md`. Last updated: Fri 9 Oct 2026 (pivot: no image-based AQI; air from WAQI + CAMS, §3/§4/§7).
> **Strategy is expected to change** as we build; when something here conflicts with what the
> user says now, the user wins — then update this file.

---

## 0. Working rules for AI sessions (read first)

- Datasets live at `$DATA_DIR` (= `/home/abhaysingh/datasets`), **outside the repo**. Read only CSVs; never browse image folders.
- Never commit data, model weights, `.env`, keys or secrets.
- Never add `Co-Authored-By` trailers or AI attribution to commits/PRs.
- Don't reuse anything from the old "AQI Vision" project (see §2).
- Prefer small, working, committed steps over big rewrites. Commit after each working step.
- User prefers concise, practical, informal answers.
- **Background monitors produced fake results** (made-up runs with plausible metrics). Only report metrics read from files on disk (`ml/runs/...`); run long jobs in the foreground or detached and verify on disk.

## 1. Who / what

- **User:** Abhay, B.Tech ECE, BIT Mesra (batch 2027). Python-first. Team of **3**.
- **Event:** WeMakeDevs × AWS **Environmental Hacks** (Bharat Builds Tour). Online, India. **Track: Air.** Own problem allowed.
- **Schedule (from the Schedule page, hours "being finalised"):**
  - Thu 8 Oct — Kickoff: the clock starts online, teams form, repos are created. **Exact start time not announced yet — watch the Schedule page + WeMakeDevs Discord. No commits before it.**
  - Fri 9 Oct — Build day. Sat 10 Oct — optional in-person day at DTU Delhi (8 AM–8 PM); online continues.
  - Sun 11 Oct — last day to submit (exact time TBA — assume early in the day until announced).
- Prizes per track: ₹2,00,000 + $2,000 AWS credits. Top 5 Builder Center blogs: AirPods.
- **Real goal:** Amazon **fast-track interview** (max 10 per hackathon; 2027/2028 grads; decided separately from prizes; needs Builder Center student verification).
- Judging: idea & impact (small problem solved well), built on AWS, design & usability, execution ("one feature that runs beats five that almost do"), 3-min demo video.

## 2. Hard rules (violating these = disqualification)

1. **Build only after the clock starts.** No project code before kickoff. Planning, learning, downloading/inspecting data = allowed. Exploration scripts written before kickoff must be **rewritten in the repo after kickoff**, not copied in.
2. **No old projects.** The academic minor project ("AQI Vision", https://github.com/ASR222/AQI_project) **must not be reused**: no code, no weights (`aqi_model.keras`), no frontend, not the name. Ideas/knowledge are fine.
3. Fresh repo after kickoff; commit early and often (history must match event dates).
4. **Must use AWS** (an AWS open-source tool such as Strands Agents / SAM CLI, or deploy on AWS) **and the demo video must show it.**
5. Submission = public repo + YouTube video **≤ 3 min** (public/unlisted, test signed-out) + short writeup (problem, build, where AWS fits). Judges see only the submission.
6. **List AI coding tools used** in the writeup (Claude Code etc.) even though commits carry no AI trailer. Credit everything not written by us.
7. Each member registers individually and verifies student status on Builder Center.

## 3. The product

**Product:** For a place with no monitor nearby: how bad the air likely is today, how far that number comes from, what's visibly polluting nearby, and what to do, in Hindi.

- **Names:** repo folder is `hazebusters`. Confirm final **team name** and **product name** (not "AQI Vision"; candidate product name: SmogSight).
- **Hero user:** a **school** deciding whether today's PE/assembly go outdoors. Second profile: outdoor/gig worker. Plus general.

**Flow:**
1. Pick a profile.
2. Record a 10 s clip with location.
3. Air: nearest WAQI station (US AQI → µg/m³ → §5) plus the CAMS model value for the area via Open-Meteo (~45 km, µg/m³ → §5). Pick a source with the 25 km / 3 h rule. Confidence comes from agreement and distance.
4. Decision for the profile from the AQI number plus today's 3-hourly forecast (outdoor yes/limit/no, best window).
5. Clip → quality gate → EfficientNet-B0 smoke/fire/clear classifier + CAM heatmap, and YOLO11n smoke/fire boxes + vehicle count. Causes only; they never change the AQI.
6. Seasonal line.
7. Bedrock/Strands advice in EN/HI (template fallback), plus Polly Hindi audio.
8. Optional report-burning draft.

**No image-based AQI:** see §4 and ml/RESULTS.md.

**Pitch:** "Most places have no monitor nearby. We tell you how far your nearest reading really is, what's polluting the air around you, and what to do today, in Hindi."

**Credits:** CAMS + Open-Meteo (non-commercial).

API response shape: `backend/contract.json` (`air.measured` can be null, e.g. Ranchi).

## 4. ML design

### Current image models (Fri) — causes only, never AQI
- **Image → AQI is an experiment only, not in the product.** It failed on unseen days and cities (seed-0 CNN 32% vs 47.5% baseline; frozen-embedding / handcrafted probes at baseline; India/Nepal leave-one-city-out inverted). Numbers: `ml/RESULTS.md`.
- **Smoke/fire classifier (trained Fri):** EfficientNet-B0, 2 sigmoid outputs (smoke, fire; "clear" = neither), whole frame squashed to 224×224, trained on **D-Fire** (CC0) with the dHash + AoF-sequence grouped split `ml/splits/dfire.json`. Code: `hazeml/train_smokefire.py`, `smokefire_data.py`, `export_onnx.py`. D-Fire test AP smoke 0.979 / fire 0.982 (thresholds from val: smoke 0.359, fire 0.667). **External Pyro-SDIS: smoke recall 13.4%, FPR 20.5%, AP 0.845 below the 0.868 base rate → doesn't transfer to distant wildfire plumes.** ONNX (features + logits) verified vs torch (max diff 2.1e-4). Heatmap = **CAM** in numpy (`hazeml/cam.py`) from the ONNX features + `head.npz`, not Grad-CAM (no gradients needed on Lambda). Details: `ml/RESULTS.md` §3.
- **YOLO11n** (Ultralytics, **AGPL** — repo stays open source), fine-tuned for smoke/fire; vehicles from pretrained COCO classes. Output: smoke/fire boxes + vehicle count.
- The quality gate (night, no sky, blur, indoor) runs before both models; their outputs feed `causes` in `backend/contract.json` and never change the AQI.
- **LLM only phrases** numbers our pipeline computed. Never estimates AQI or invents numbers/health claims.
- **Export to ONNX** for Lambda.
- **Compute:** train locally on **RTX 4050 (6 GB, ~5 GB free)** in WSL; Kaggle/Colab as backup or for a teammate's parallel experiment. Optional speed-up: pre-resize TRAQID images to 256 px once into `$DATA_DIR/traqid_256/`.
- **No 3-stream CNN** (old project's design): too slow for video on Lambda, doubtful gain, too close to the old project. Optional Sat ablation only if ahead.

### Image → AQI (experiment only; archived — see `ml/RESULTS.md`)
- **Training data: TRAQID only, daytime (`Day_or_Night == Day`), front view only.** The app's quality gate rejects night frames, so training matches real use and drops the noisiest half. After the filter: **13,789 frames from only 17 calendar dates** (2022-10 → 2024-07). Loader: `ml/src/hazeml/traqid.py` (`load_traqid()`, reads only the CSV).
- **Time-of-day confound:** the worst air (21–23 Dec 2023) was filmed on **morning drives**; most other frames are late afternoon (15:00–18:00). Very Poor/Severe share: **43% of frames before 11:00 vs 9% from 15:00** (July mornings are mostly clean, so it's not absolute). The CNN can learn "morning light = bad air" → use strong colour/brightness/contrast augmentation, report accuracy by morning vs evening, and lean on the OOD test + own clips.
- **Model:** pretrained **EfficientNet-B0 or MobileNetV3**, fine-tuned, 224 px, mixed precision, batch ~32 (reduce on OOM).
- **Classes: 3 CPCB bands** — Good/Satisfactory (0–100), Moderate/Poor (101–300), Very Poor/Severe (301+). Use **class weights** (Very Poor/Severe is only ~12% of TRAQID).
- **Multimodal variant (Fri):** CNN embedding ⊕ [mean saturation, contrast, dark-channel, brightness, temperature, humidity, season, YOLO vehicle count] → MLP head. TRAQID only. **No `hour`** (it encodes the time-of-day confound above). **`season` is risky**: with 17 dates it nearly identifies the collection trip (all Very Poor/Severe-heavy dates are Winter/Dec) → include only if an ablation without it is also reported. **Compare vs image-only on the same split; keep the winner.** Image-only stays the runtime fallback.
- **Never feed station AQI/PM as a model input** (it's the label; the model would copy it). Station reading is shown separately.

### Image → AQI evaluation (be honest; archived)
- **TRAQID split by calendar date** (from `created_at`): hold out ~20% of dates as test (plus a val split). Random splits leak (frames 5 s apart).
  - **Frozen in `ml/splits/traqid_dates.json`** (committed; dates only). Chosen by exhaustive search for ~70/10/20 rows with each split's band mix close to overall: train 9,657 rows / 10 dates, val 1,361 / 2 (2022-10-26, 2024-03-06), test 2,771 / 5 (2023-01-30, 02-01, 02-08, 2023-12-21, 2024-03-02). Don't change it once results are reported; `python -m hazeml.traqid --make-split` regenerates.
  - **Very Poor/Severe test recall rests mostly on one morning (21 Dec 2023, ~430 of ~460 band-2 test rows)** → expect it to swing; say so.
  - **21 Dec is in test while 22–23 Dec (same smog episode) are in train** — no shared frames, but shared weather/lighting. Keeping the episode together left too little band 2 in train or test; disclose it in the writeup.
- **India/Nepal = out-of-domain test set, not training.** Recompute CPCB labels (§5), evaluate the TRAQID-trained model on it. Pitch line: *"Trained in Hyderabad, tested on 7 other Indian cities."* If ever used for training, split by **moment** (location+date+hour), not image.
- Report: **macro-F1**, accuracy vs **majority baseline** (≈52% on all TRAQID 3-band; **≈47% after the day-only filter** — use 47% for our numbers; per split 47.2/47.4/47.5%), **within-one-band accuracy**, and **recall for Very Poor/Severe** separately.
- Sanity check: agreement between our recomputed TRAQID labels and its own `aqi_cat`.
- **Result (Thu, EfficientNet-B0, seed 0, `ml/runs/20261008-174356_efficientnet_b0_s0/`): test accuracy 32.0% vs 47.5% majority baseline** (macro-F1 0.312, band-2 recall 57%, confidently wrong: mean confidence 0.80); val 22%. Same checkpoint on its **train dates: 89%** (82–100% per date) → no pipeline bug; **the model learns the day, not haze**. Frames within a date are highly correlated (a single band covers a median ~78% of a date's frames, 47–99%; ≥94% on 4 of 17 dates), so there are effectively ~17 independent samples. Seeds 1–2 not run (stopped). **Probes (Thu night) confirmed it:** no image signal transfers to unseen dates or cities → image→AQI dropped from the product. Details in `ml/RESULTS.md` (raw files in `ml/runs/probes/`, gitignored).
- Old rough expectation (now unrealistic for TRAQID-only): ~65–80% on held-out TRAQID dates; lower out-of-domain and on our own clips. Collect 20–30 own clips/photos as a real-world test set.

## 5. Label mapping — CPCB-style AQI (first thing to code after kickoff)

Ignore datasets' own class labels; recompute from raw PM2.5 / PM10 with one shared function.

| AQI | Category | PM2.5 (µg/m³) | PM10 (µg/m³) |
|---|---|---|---|
| 0–50 | Good | 0–30 | 0–50 |
| 51–100 | Satisfactory | 31–60 | 51–100 |
| 101–200 | Moderate | 61–90 | 101–250 |
| 201–300 | Poor | 91–120 | 251–350 |
| 301–400 | Very Poor | 121–250 | 351–430 |
| 401–500 | Severe | 250+ | 430+ |

Sub-index = linear interpolation within the row; **AQI = max(sub-index PM2.5, sub-index PM10)** (use whichever pollutants exist); then category → 3 bands. Call it "CPCB-style AQI" in the writeup (official AQI uses 24-h averages and ≥3 pollutants).

## 6. Data

### 6.1 On disk (WSL, outside the repo)
```
~/datasets/
  traqid/       front/<Image>.png, rear/<Image>.png (flat folders), TRAQID.csv
  india-nepal/  "Air Pollution Image Dataset/Air Pollution Image Dataset/Combined_Dataset/"
                  All_img/ (use this only) + IND_and_Nep_AQI_Dataset.csv  (loader: ml/src/hazeml/india_nepal.py)
  pm25vision/   dropped — not used (safe to delete, 1.1 GB)
  dfire_hf/     D-Fire (CC0) parquet from HF mirror badsaarow/d-fire, 21,527 imgs (ml/download_datasets.py); split: ml/splits/dfire.json
  pyro_sdis/    Pyro-SDIS (Apache-2.0) parquet from pyronear/pyro-sdis, 12,378 imgs, smoke only, camera + date columns
  stations/     one folder per state, one CSV per station + stations.csv (8.4 GB)
  cpcb_2015_2020/  city_day, city_hour, station_day, station_hour, stations CSVs (Kaggle rohanrao/air-quality-data-in-india)
```
`cpcb_2015_2020` is **only a unit test for the §5 label function**: on rows where PM2.5/PM10 drive the AQI, our CPCB-style AQI should match its `AQI` / `AQI_Bucket` columns. Not used for training or seasonal context. Reference for the full CPCB method: Kaggle notebook "Calculating AQI (Air Quality Index) Tutorial" by rohanrao — read, don't copy; credit if followed closely. Check the dataset's licence on Kaggle before citing.
`.env` in the repo (gitignored): `DATA_DIR=/home/abhaysingh/datasets`, `WAQI_TOKEN=...`

### 6.2 Image datasets
| Dataset | Role | Facts | Licence / credit |
|---|---|---|---|
| **TRAQID** (Kathalkar et al., ICVGIP 2024, doi 10.1145/3702250.3702260; data on india-data.org) | **Training (only)** | 26,678 rows. CSV columns: `created_at, Image, PM2.5, PM10, Temperature, Humidity, aqi, Season, Day_or_Night, aqi_cat`. Image file = `front/<Image>.png` / `rear/<Image>.png`; collection day comes from `created_at`. 6-class counts: Satisfactory 13,033 · Moderate 7,453 · Poor 2,283 · Very Poor 2,233 · Severe 932 · Good 744. 3-band: 51.6% / 36.5% / 11.9%. Hyderabad dashcam, frames every 5 s, ~half night. | India Data agreement: research use, **no commercial use without consent**, attribution, no misrepresentation; faces/plates blurred |
| **India/Nepal** (Kaggle, doi 10.34740/KAGGLE/DS/3152196) | **Out-of-domain test** | Use only `Combined_Dataset/All_img` (12,240 imgs); other folders are copies. Only **115 distinct location+date+hour moments** → heavy near-duplicates. Authors' split (`Dataset_for_AQI_Classification/*.csv`) **leaks — don't use**. Its AQI column uses US bands and can disagree with raw PM2.5 → recompute per §5. | **CC BY-NC-SA 3.0 IGO**. Cite dataset + Eff-AQI (Utomo et al., GoodIT '23, doi 10.1145/3582515.3609531) + Future Internet 2023 paper |
| PM25Vision | **Dropped** | Its `pm25` field is a US AQI value, not µg/m³ | — |

### 6.3 Seasonal context (stations dataset)
- Source: Kaggle "India AQI 2010–2024" (omsandeeppatil/indian-aqi-stations), 546 stations, **CC BY-SA 4.0**.
- Built (as pre-kickoff exploration): city × month **median daily PM2.5**, city-day = mean of that city's stations. Medians peak Nov–Dec (Delhi ~216 µg/m³).
- Coverage: **Delhi** 43 stations (15–16 yrs/month), **Hyderabad** 12 (9–10 yrs), **Patna** 4 (2019–2024, 5 yrs). **No Ranchi station**; Jharkhand only JH01 Jamshedpur (31% PM2.5 coverage) and JH02 Dhanbad (from 2023).
- **After kickoff:** rewrite as `ml/build_seasonal_lookup.py` → `backend/data/seasonal_lookup.json`; use §5 mapping (PM2.5 and PM10 if available) so labels match the model; optionally restrict to 2018+ (Delhi's network grew over time). JSON carries `source`, `licence: CC BY-SA 4.0`, `metric`, and per city `lat/lon` + per month `pm25, p75, days, category`. Credit in README.
- App use: nearest lookup city **within ~50 km** of the user, else hide the line (Ranchi gets none). Wording: *"A typical November day here: Very Poor (PM2.5 ≈ 216)."* — never call it the AQI.

### 6.4 Pitch data
- Line (true for this dataset): *"In this 546-station dataset, Jharkhand has 2 stations and none in Ranchi."* UrbanEmissions NCAP bulletins (2015–2023) also had no Ranchi.
- **Before the demo, check WAQI live for a Ranchi station.** None → "no official monitor in Ranchi". One → "a city of 1.5M relies on a single recently added monitor".

### 6.5 Live readings
WAQI API (free token); backup OpenAQ v3. Sanity-check values (live CPCB data is unvalidated).

Rejected: data.gov.in real-time AQI (no API, 502s, snapshot only); adityarc19/aqi-india (tabular, no licence, ends 2020); Kaggle "India AQI 2024" (city-level, unclear source); IJEP 2024 "Image to Insight" paper (ignored).

**Repo data rules:** never commit datasets, images, relabelled CSVs or weights. README gives download steps + citations. Commit relabel/lookup **scripts**; the tiny CC BY-SA seasonal JSON may be committed with its licence + credit. Code licence: open source (AGPL-compatible because of Ultralytics). Both training/test image datasets are non-commercial → a future startup needs permission or our own data.

## 7. AWS architecture

```
PWA (Amplify Hosting)
  └─► API Gateway ─► Lambda: presigned S3 URL
PWA uploads video ─► S3 ─(event)─► Lambda container image (ONNX: quality gate + smoke/fire/clear CNN + YOLO11n, frame sampling)
                                     ├─► DynamoDB (results, history)
                                     ├─► WAQI (nearest station) + Open-Meteo Air Quality (CAMS global, ~45 km) for measured + modelled PM
                                     ├─► Bedrock via Strands Agents (advice EN + HI; template fallback)
                                     └─► Polly (Hindi audio of the advice) ─► S3 (audio key in the result)
PWA fetches result ◄─ API Gateway ◄─ Lambda
```
- Deploy with **SAM CLI**; image pushed to **ECR** (no Docker Hub account needed; base image `public.ecr.aws/lambda/python`). Skip SageMaker.
- One region for everything — pick one where the Bedrock model is available (us-east-1 widest). Request model access early.
- Free Tier + up to $200 credits; zero-spend / small budget alert set.
- Show the flow on screen in the demo video.
- Air logic lives in `backend/src/air/` (WAQI, Open-Meteo, combine); response shape in `backend/contract.json`. Open-Meteo is free for non-commercial use and needs CAMS + Open-Meteo attribution.

## 8. Dev environment (Abhay's laptop)

- **WSL2 Ubuntu** on Windows; repo at `~/hazebusters` (inside WSL filesystem, not `/mnt/c`). `.wslconfig`: memory 10 GB, swap 8 GB.
- GPU: RTX 4050 6 GB via Windows NVIDIA driver; `nvidia-smi` works in WSL. PyTorch CUDA build installed per pytorch.org; Python via **uv**.
- **Docker Desktop** with WSL integration (the old `podman-docker` shim was removed — `docker` must be real Docker for SAM).
- AWS CLI v2 configured with an **IAM user** (`hackathon-dev`, not root); SAM CLI installed; Node via nvm (LTS).
- Claude Code: Desktop app **WSL session** on `~/hazebusters` (integrated terminal + file pane are unavailable in WSL sessions → use **Open in editor** = VS Code Remote-WSL for terminal/files; diff review works in Desktop). Commit attribution disabled in `~/.claude/settings.json` (`attribution.commit/pr = ""`).
- `.gitignore`: `.env .venv/ data/ node_modules/ __pycache__/ .aws-sam/ runs/ *.onnx *.pt *.pth *.keras *.zip`

## 9. Team split

- **ML:** §5 label function, TRAQID loader + date split, CNN, haze features, YOLO, ONNX export, evaluation (incl. India/Nepal OOD test), seasonal lookup script.
- **Backend/AWS:** S3/Lambda/DynamoDB/API Gateway via SAM, WAQI + weather, nearest-city seasonal helper, Bedrock/Strands advice.
- **Frontend + story:** PWA (profile picker, camera/upload, result, advice), demo video, writeup, Builder Center blog.

## 10. Day plan

- **Thu (done):** repo + first commit; §5 label function; TRAQID loader + frozen date split; baseline image→AQI CNN; probes → image→AQI dropped (`ml/RESULTS.md`).
- **Fri:** air backend (`backend/src/air/`: WAQI + Open-Meteo/CAMS + combine + decision) with tests and live checks; `backend/contract.json`; optional CAMS-vs-stations validation; pick a smoke/fire dataset and start the smoke/fire/clear classifier + YOLO11n; AWS skeleton (S3, Lambda, API).
- **Sat:** quality gate + causes end-to-end; Grad-CAM; seasonal line; Bedrock/Strands advice (EN/HI) + Polly; PWA; deploy; ONNX; test with non-team users; cut anything not working by Sat night.
- **Sun:** film demo outdoors; 3-min video (AWS visible); writeup (AI tools listed, citations incl. CAMS/Open-Meteo); blog; submit early.

## 11. Status (Fri 9 Oct → early Sat 10 Oct)

Done (Thu): repo and branches (`ml/aqi-labels` → PR #1; `ml/traqid-loader` → PR #2, which also contains #1's commit — merge #1 first or close it), §5 function + tests (matches CPCB city_day on 74% of categories / 85% of bands; misses are almost all one category off, consistent with daily vs rolling averaging), TRAQID loader + split, CNN + probes (negative result), India/Nepal loader.
Done (Fri): pivot docs; `ml/RESULTS.md`; §5 function moved to `shared/` (`cpcb_aqi`, used by ml + backend); `backend/contract.json`; `backend/src/air/` (WAQI, Open-Meteo/CAMS, combine); CAMS vs stations validation (CAMS ≈ 0.8× stations, misses ~2/3 of Very Poor/Severe days in Delhi/Patna).
Air rules now: measured if station ≤ 25 km and < 3 h old, else modelled; **whenever `used == modelled` → CAMS PM ×1.25** (from the validation; PM2.5-based, PM10 assumed; helps Delhi/Patna, **hurts Hyderabad** — `ml/RESULTS.md` §2b); decision = worst slot over the profile's remaining hours today (school 07–17, worker 06–19, general 06–21), or tomorrow's hours after they end (`decision.for`); `no_window_today` / `no_window_tomorrow` if no "yes" slot. Details: `backend/src/air/decision_rules.md`.
Done (Fri night): `forecast_tomorrow`; D-Fire + Pyro-SDIS downloaded and extracted (`$DATA_DIR/dfire_hf`, `$DATA_DIR/pyro_sdis`) — **D-Fire came from the Hugging Face mirror `badsaarow/d-fire`** (the official OneDrive links block scripted downloads; counts match the README); D-Fire split v2 (no consecutive-frame leaks ≤ 15; **the 10% group cap was hit 4 times**); smoke/fire model trained + ONNX + CAM: **D-Fire test AP smoke 0.979 / fire 0.982; Pyro-SDIS smoke recall 13.4%, so it doesn't transfer yet** (`ml/RESULTS.md` §3).
Tests: backend 62, shared 50, ml 33 (all passing).
Env notes: PyTorch is installed in the `ml/` uv project (cu128), not system-wide; WSL currently sees 7 GB RAM, not the 10 GB in `.wslconfig`. **`WAQI_TOKEN` in `.env` is empty.**
Remaining: WAQI token + live test + Ranchi check, Bedrock model access, **Bedrock/Strands advice (EN/HI, template fallback)**, Polly, **seasonal lookup script + JSON** (§6.3), quality gate, YOLO11n (vehicles + smoke/fire boxes), AWS skeleton, PWA, **own test clips (the smoke model's real test)**, final names, **merging PRs #1 then #2**.

## 12. Open items

- Exact Sunday submission deadline (time) — Schedule page / Discord.
- Final team + product names.
- **WAQI live untested** (no token yet); includes the live Ranchi station check (pitch wording).
- Owners for the PWA and the SAM/AWS deploy.
- Later, for the semester project: native app, 3-stream ablation, own labelled Indian dataset.
