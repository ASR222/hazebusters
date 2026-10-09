"""Combine WAQI (measured) and CAMS (modelled) into the contract's `air`, `forecast_today` and `decision`.

Rules (CLAUDE.md §3; rule table with CPCB health statements in decision_rules.md):
- Source: measured if the station is <= 25 km away and updated < 3 h ago, else modelled. Both are returned.
- Confidence: high = same band in both and station <= 25 km; medium = only one of those;
  low = neither, or modelled only.
- Decision from the CPCB-style AQI: <= 100 yes, 101-200 limit, > 200 no (same for every profile;
  the profile only changes the advice wording).
- best_window: earliest 3-hour forecast slot still left today, clipped to the profile's hours
  (school 07-17, worker 06-19, general 06-21), forecast as "yes"; none -> null and
  reason_code "no_window_today".
- Modelled only (no station reading): CAMS PM is scaled by CAMS_CORRECTION before the AQI,
  the decision and the forecast, and a caveat says so.
"""

import math
from datetime import datetime, timedelta

from air import openmeteo, waqi

MAX_STATION_KM = 25.0
MAX_STATION_AGE = timedelta(hours=3)

# CAMS daily PM2.5 ran ~0.8x the ground stations: median CAMS/station ratio 0.78 (Delhi), 0.79 (Hyderabad),
# 0.81 (Patna), 2023-24 (ml/runs/cams_validation/summary.json, from ml/validate_cams.py; ml/RESULTS.md §2).
CAMS_CORRECTION = 1.25

# Hours (local) in which a profile would go outdoors; best_window is clipped to these.
PROFILE_WINDOWS = {"school": (7, 17), "worker": (6, 19), "general": (6, 21)}

# (upper AQI bound inclusive, outdoor, reason_code)
DECISION_RULES = ((100, "yes", "aqi_le_100"), (200, "limit", "aqi_101_200"), (math.inf, "no", "aqi_gt_200"))


def decide(aqi: int) -> tuple[str, str]:
    for upper, outdoor, code in DECISION_RULES:
        if aqi <= upper:
            return outdoor, code
    raise AssertionError("unreachable")


def _fresh(measured: dict, now: datetime) -> bool:
    return now - datetime.fromisoformat(measured["updated_at"]) < MAX_STATION_AGE


def choose_source(measured: dict | None, modelled: dict | None, now: datetime) -> str:
    if measured and measured["dist_km"] <= MAX_STATION_KM and _fresh(measured, now):
        return "measured"
    if modelled is None:
        if measured is None:
            raise ValueError("no air data: WAQI and Open-Meteo both unavailable")
        return "measured"  # CAMS failed; a far/stale station is better than nothing (flagged in caveats)
    return "modelled"


def confidence(measured: dict | None, modelled: dict | None) -> tuple[str, str]:
    if measured is None:
        return "low", "No station reading; CAMS model value only (~45 km grid)."
    if modelled is None:
        return "low", "CAMS model value unavailable; cannot cross-check the station."
    near = measured["dist_km"] <= MAX_STATION_KM
    agree = measured["band"] == modelled["band"]
    where = f"station {measured['dist_km']} km away"
    if near and agree:
        return "high", f"Station and CAMS agree on the band; {where}."
    if near:
        return "medium", f"Station and CAMS disagree on the band; {where}."
    if agree:
        return "medium", f"Station and CAMS agree on the band, but the {where} (> {MAX_STATION_KM:.0f} km)."
    return "low", f"Station and CAMS disagree on the band and the {where} (> {MAX_STATION_KM:.0f} km)."


def best_window(forecast: list[dict], now: datetime, profile: str = "general") -> dict | None:
    """Earliest "yes" slot still left today, clipped to the profile's outdoor hours."""
    lo, hi = PROFILE_WINDOWS[profile]
    for slot in forecast:
        start = datetime.fromisoformat(slot["time"])
        midnight = start.replace(hour=0, minute=0, second=0, microsecond=0)
        s = max(start, midnight + timedelta(hours=lo))
        e = min(start + timedelta(hours=3), midnight + timedelta(hours=hi))
        if s < e and e > now and decide(slot["aqi_cpcb"])[0] == "yes":
            return {"start": s.isoformat(), "end": e.isoformat()}
    return None


def combine(measured: dict | None, modelled: dict | None, forecast: list[dict], now: datetime,
            profile: str = "general", corrected: bool = False, waqi_note: str | None = None) -> dict:
    """-> {"air", "forecast_today", "decision", "caveats"} (contract fragments).

    `corrected`: modelled/forecast PM were already scaled by CAMS_CORRECTION (modelled only)."""
    if profile not in PROFILE_WINDOWS:
        raise ValueError(f"unknown profile {profile!r}; choose from {sorted(PROFILE_WINDOWS)}")
    used = choose_source(measured, modelled, now)
    chosen = measured if used == "measured" else modelled
    level, reason = confidence(measured, modelled)
    outdoor, code = decide(chosen["aqi_cpcb"])
    window = best_window(forecast, now, profile)
    if window is None:
        code = "no_window_today"

    caveats = ["CPCB-style AQI from hourly PM (official CPCB AQI uses 24-h averages and >= 3 pollutants)."]
    if modelled is not None:
        caveats.append("CAMS is a model value for a ~45 km grid cell, not a measurement.")
    if corrected:
        caveats.append(f"No station reading, so CAMS PM2.5/PM10 were scaled x{CAMS_CORRECTION} before the AQI and "
                       "decision: CAMS read about 0.8x ground stations in Delhi, Hyderabad and Patna (daily PM2.5, 2023-24).")
    if measured is None:
        caveats.append(waqi_note or "No WAQI station reading available.")
    else:
        caveats.append("WAQI US AQI sub-indices converted back to µg/m³ (US EPA 2012 breakpoints).")
        if measured["dist_km"] > MAX_STATION_KM:
            caveats.append(f"Nearest station is {measured['dist_km']} km away.")
        if not _fresh(measured, now):
            caveats.append(f"Nearest station last updated {measured['updated_at']}.")

    return {
        "air": {"measured": measured, "modelled": modelled, "aqi_cpcb": chosen["aqi_cpcb"], "band": chosen["band"],
                "used": used, "confidence": level, "confidence_reason": reason},
        "forecast_today": forecast,
        "decision": {"outdoor": outdoor, "best_window": window, "reason_code": code},
        "caveats": list(dict.fromkeys(caveats)),
    }


def air_for(lat: float, lon: float, token: str | None, now: datetime | None = None, profile: str = "general") -> dict:
    """Fetch both sources and combine. A failing source becomes None plus a caveat."""
    now = now or datetime.now().astimezone()
    measured, waqi_note = None, None
    if token:
        try:
            measured = waqi.parse(waqi.fetch(lat, lon, token), lat, lon)
            if measured is None:
                waqi_note = "Nearest WAQI station reports no PM2.5 or PM10."
        except Exception as e:  # network / API error: fall back to CAMS
            waqi_note = f"WAQI unavailable ({type(e).__name__}: {e})."
    else:
        waqi_note = "WAQI not queried (no WAQI_TOKEN)."
    scale = CAMS_CORRECTION if measured is None else 1.0
    modelled, forecast, notes = None, [], []
    try:
        hours = openmeteo.parse_hourly(openmeteo.fetch(lat, lon))
        modelled, forecast = openmeteo.modelled_now(hours, now, scale), openmeteo.forecast_3h(hours, scale)
    except Exception as e:
        notes.append(f"Open-Meteo unavailable ({type(e).__name__}: {e}).")
    out = combine(measured, modelled, forecast, now, profile,
                  corrected=measured is None and modelled is not None, waqi_note=waqi_note)
    out["caveats"] = list(dict.fromkeys(out["caveats"] + notes))
    return out
