# PROJECT CONTEXT — Environmental Hacks (Air track)

> Handoff for Claude Code or any new AI chat session. Read this fully before helping.
> Lives in the repo as `CLAUDE.md`. Last updated: Thu 8 Oct 2026 (after kickoff: TRAQID split findings in §4).
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

**Phone video → AQI estimate for places with no air-quality monitor, plus *why* the air is bad and *what to do*.**

Pitch: *"Most of India has no air quality monitor. We turned every phone into one — and it tells you what to do."*

- **Names:** repo folder is `hazebusters`. Confirm final **team name** and **product name** (not "AQI Vision"; candidate product name: SmogSight).
- **Hero user:** a **school** deciding whether today's PE/assembly go outdoors. Second profile: outdoor/gig worker. Plus general.

### User flow
1. Pick profile (school / outdoor worker / general).
2. Record/upload 5–15 s video in a PWA.
3. Backend samples ~1 frame/s → **quality gate** rejects bad frames (night, no sky, blur, indoor).
4. **CNN** → CPCB band per frame → averaged → band + **confidence**.
5. **YOLO** → smoke/burning boxes + vehicle count.
6. Context: **nearest live station reading + distance** (WAQI), and a **seasonal line** for the city if one exists (§6.3).
7. **LLM** (Bedrock via Strands Agents) writes short advice for the profile, **English + Hindi**; template fallback.
8. Optional: Grad-CAM heatmap; "report burning" draft linking to the official complaint channel (never claim auto-sending to government).

### Winning points
- Works where monitors don't (data-shadow pitch, §6.4). Explains *why* and *what to do*.
- **Honest ML:** date-based split, majority baseline, confidence, quality gate refusing bad input, out-of-domain test.
- AWS clearly visible end-to-end. Demo "aha": film outdoors → result + cause + Hindi advice in ~30 s.
- Avoid: feature bloat, shaky demo, claiming 95%+ accuracy.

## 4. ML design (decided)

- **Training data: TRAQID only, daytime (`Day_or_Night == Day`), front view only.** The app's quality gate rejects night frames, so training matches real use and drops the noisiest half. After the filter: **13,789 frames from only 17 calendar dates** (2022-10 → 2024-07). Loader: `ml/src/hazeml/traqid.py` (`load_traqid()`, reads only the CSV).
- **Time-of-day confound:** the worst air (21–23 Dec 2023) was filmed on **morning drives**; most other frames are late afternoon (15:00–18:00). Very Poor/Severe share: **43% of frames before 11:00 vs 9% from 15:00** (July mornings are mostly clean, so it's not absolute). The CNN can learn "morning light = bad air" → use strong colour/brightness/contrast augmentation, report accuracy by morning vs evening, and lean on the OOD test + own clips.
- **Model:** pretrained **EfficientNet-B0 or MobileNetV3**, fine-tuned, 224 px, mixed precision, batch ~32 (reduce on OOM).
- **Classes: 3 CPCB bands** — Good/Satisfactory (0–100), Moderate/Poor (101–300), Very Poor/Severe (301+). Use **class weights** (Very Poor/Severe is only ~12% of TRAQID).
- **Multimodal variant (Fri):** CNN embedding ⊕ [mean saturation, contrast, dark-channel, brightness, temperature, humidity, season, YOLO vehicle count] → MLP head. TRAQID only. **No `hour`** (it encodes the time-of-day confound above). **`season` is risky**: with 17 dates it nearly identifies the collection trip (all Very Poor/Severe-heavy dates are Winter/Dec) → include only if an ablation without it is also reported. **Compare vs image-only on the same split; keep the winner.** Image-only stays the runtime fallback.
- **Never feed station AQI/PM as a model input** (it's the label; the model would copy it). Station reading is shown separately.
- **No 3-stream CNN** (old project's design): too slow for video on Lambda, doubtful gain, too close to the old project. Optional Sat ablation only if ahead.
- **YOLO:** yolov8n / yolo11n (Ultralytics, **AGPL** — repo stays open source), fine-tuned for smoke/fire; vehicles from pretrained COCO classes.
- **LLM only phrases** numbers our pipeline computed. Never estimates AQI or invents numbers/health claims.
- **Export to ONNX** for Lambda.
- **Compute:** train locally on **RTX 4050 (6 GB, ~5 GB free)** in WSL; Kaggle/Colab as backup or for a teammate's parallel experiment. Optional speed-up: pre-resize TRAQID images to 256 px once into `$DATA_DIR/traqid_256/`.

### Evaluation (be honest)
- **TRAQID split by calendar date** (from `created_at`): hold out ~20% of dates as test (plus a val split). Random splits leak (frames 5 s apart).
  - **Frozen in `ml/splits/traqid_dates.json`** (committed; dates only). Chosen by exhaustive search for ~70/10/20 rows with each split's band mix close to overall: train 9,657 rows / 10 dates, val 1,361 / 2 (2022-10-26, 2024-03-06), test 2,771 / 5 (2023-01-30, 02-01, 02-08, 2023-12-21, 2024-03-02). Don't change it once results are reported; `python -m hazeml.traqid --make-split` regenerates.
  - **Very Poor/Severe test recall rests mostly on one morning (21 Dec 2023, ~430 of ~460 band-2 test rows)** → expect it to swing; say so.
  - **21 Dec is in test while 22–23 Dec (same smog episode) are in train** — no shared frames, but shared weather/lighting. Keeping the episode together left too little band 2 in train or test; disclose it in the writeup.
- **India/Nepal = out-of-domain test set, not training.** Recompute CPCB labels (§5), evaluate the TRAQID-trained model on it. Pitch line: *"Trained in Hyderabad, tested on 7 other Indian cities."* If ever used for training, split by **moment** (location+date+hour), not image.
- Report: **macro-F1**, accuracy vs **majority baseline** (≈52% on all TRAQID 3-band; **≈47% after the day-only filter** — use 47% for our numbers; per split 47.2/47.4/47.5%), **within-one-band accuracy**, and **recall for Very Poor/Severe** separately.
- Sanity check: agreement between our recomputed TRAQID labels and its own `aqi_cat`.
- Rough expectation: ~65–80% on held-out TRAQID dates; lower out-of-domain and on our own clips. Collect 20–30 own clips/photos as a real-world test set.

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
  india-nepal/  Combined_Dataset/All_img/ (use this only) + IND_and_Nep_AQI_Dataset.csv
  pm25vision/   dropped — not used (safe to delete, 1.1 GB)
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
PWA uploads video ─► S3 ─(event)─► Lambda container image (ONNX: quality gate + CNN + YOLO, frame sampling)
                                     ├─► DynamoDB (results, history)
                                     ├─► WAQI (nearest station) + weather API
                                     └─► Bedrock via Strands Agents (advice EN + HI; template fallback)
PWA fetches result ◄─ API Gateway ◄─ Lambda
```
- Deploy with **SAM CLI**; image pushed to **ECR** (no Docker Hub account needed; base image `public.ecr.aws/lambda/python`). Skip SageMaker.
- One region for everything — pick one where the Bedrock model is available (us-east-1 widest). Request model access early.
- Free Tier + up to $200 credits; zero-spend / small budget alert set.
- Show the flow on screen in the demo video.

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

- **Thu (after kickoff):** `git init` + first commit (CLAUDE.md, .gitignore, README skeleton); create GitHub repo, add teammates. §5 label function + TRAQID day/front loader + date split; baseline image-only CNN; AWS skeleton (S3, Lambda, API); confirm WAQI + Bedrock.
- **Fri:** video → frames → quality gate → CNN → averaged band + confidence end-to-end; YOLO; multimodal vs image-only; India/Nepal OOD numbers; ONNX.
- **Sat:** PWA polish; LLM advice (EN/HI); nearest station + seasonal line; deploy; test with non-team users; cut anything not working by Sat night.
- **Sun:** film demo outdoors; 3-min video (AWS visible); writeup (AI tools listed, citations); blog; submit early.

## 11. Status (Thu 8 Oct, ~07:30 IST, pre-kickoff)

Done: WSL basics, base packages, GPU/PyTorch, Docker, AWS CLI + SAM, Node, datasets downloaded, Claude attribution off, stations dataset checked.
Remaining before kickoff: project files in `~/hazebusters` (CLAUDE.md, .gitignore, .env — **no git commit yet**), open the WSL session in Claude Desktop, optional 256 px pre-resize, WAQI token test + Ranchi check, Bedrock model access, own test photos/clips, final names.

## 12. Open items

- Kickoff time and exact Sunday deadline (Schedule page / Discord).
- Final team + product names.
- Live Ranchi station check (pitch wording).
- Image-only vs multimodal (Friday comparison).
- Later, for the semester project: native app, 3-stream ablation, own labelled Indian dataset.
