"""CAMS global PM forecast via the Open-Meteo Air Quality API.

Docs (checked 9 Oct 2026): https://open-meteo.com/en/docs/air-quality-api
- pm10, pm2_5 hourly in µg/m³; CAMS global domain is 0.4° (~45 km), 3-hourly, updated every 12 h.
- Free for non-commercial use; attribution to CAMS and Open-Meteo required.
"""

from datetime import datetime, timedelta, timezone

from cpcb_aqi import aqi_band, cpcb_aqi

from air import http

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
SOURCE = "CAMS via Open-Meteo"
GRID_KM = 45
TIMEZONE = "Asia/Kolkata"


def fetch(lat: float, lon: float) -> dict:
    return http.get_json(URL, {
        "latitude": lat, "longitude": lon, "hourly": "pm10,pm2_5",
        "timezone": TIMEZONE, "forecast_days": 1, "domains": "cams_global",
    })


def parse_hourly(payload: dict) -> list[dict]:
    """[{time: aware datetime (local), pm25, pm10}] for today, None where CAMS has no value."""
    tz = timezone(timedelta(seconds=payload.get("utc_offset_seconds", 0)))
    h = payload["hourly"]
    return [
        {"time": datetime.fromisoformat(t).replace(tzinfo=tz), "pm25": pm25, "pm10": pm10}
        for t, pm25, pm10 in zip(h["time"], h["pm2_5"], h["pm10"])
    ]


def _aqi(pm25, pm10) -> tuple[int, int] | tuple[None, None]:
    value = cpcb_aqi(pm25, pm10)
    if value is None:
        return None, None
    aqi = round(value)
    return aqi, aqi_band(aqi)


def _r(x):
    return None if x is None else round(x, 1)


def modelled_now(hours: list[dict], now: datetime) -> dict | None:
    """Latest hour at or before `now` that has a value (falls back to the first hour of the day)."""
    usable = [h for h in hours if h["pm25"] is not None or h["pm10"] is not None]
    if not usable:
        return None
    past = [h for h in usable if h["time"] <= now]
    h = past[-1] if past else usable[0]
    aqi, band = _aqi(h["pm25"], h["pm10"])
    return {"source": SOURCE, "grid_km": GRID_KM, "valid_at": h["time"].isoformat(),
            "pm25": _r(h["pm25"]), "pm10": _r(h["pm10"]), "aqi_cpcb": aqi, "band": band}


def forecast_3h(hours: list[dict]) -> list[dict]:
    """Today's 3-hour slots (00, 03, ... 21): mean PM per slot -> CPCB-style AQI from PM2.5 and PM10."""
    slots: dict[datetime, list[dict]] = {}
    for h in hours:
        start = h["time"].replace(hour=h["time"].hour - h["time"].hour % 3)
        slots.setdefault(start, []).append(h)

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    out = []
    for start, hs in sorted(slots.items()):
        pm25, pm10 = mean([h["pm25"] for h in hs]), mean([h["pm10"] for h in hs])
        aqi, band = _aqi(pm25, pm10)
        if aqi is not None:
            out.append({"time": start.isoformat(), "pm25": _r(pm25), "aqi_cpcb": aqi, "band": band})
    return out
