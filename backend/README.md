# backend

Air logic for HazeBusters (`src/air/`): nearest WAQI station + CAMS via Open-Meteo, combined into the `air`, `forecast_today` and `decision` parts of [`contract.json`](contract.json). The CPCB-style AQI comes from the shared `cpcb-aqi` package (`../shared`).

```bash
uv sync
uv run pytest -q                       # HTTP mocked
uv run python -m air Ranchi Hyderabad  # live; WAQI_TOKEN from env or repo-root .env
```

Rules: `src/air/combine.py` (docstring) and `src/air/decision_rules.md`.
Credits: air-quality data from CAMS (Copernicus Atmosphere Monitoring Service) via Open-Meteo (non-commercial use, attribution required); station data from the World Air Quality Index project (aqicn.org).
