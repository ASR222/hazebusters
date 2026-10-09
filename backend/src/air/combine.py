"""Combine WAQI (measured) and CAMS (modelled) into the contract's `air`, `forecast_today` and `decision`.

Rules (CLAUDE.md §3; rule table with CPCB health statements in decision_rules.md):
- Source: measured if the station is <= 25 km away and updated < 3 h ago, else modelled. Both are returned.
- Confidence: high = same band in both and station <= 25 km; medium = only one of those;
  low = neither, or modelled only.
- Decision from the CPCB-style AQI: <= 100 yes, 101-200 limit, > 200 no (same for every profile;
  the profile only changes the advice wording).
- best_window: earliest 3-hour slot today, not yet over, forecast as "yes".
"""

import math
from datetime import datetime, timedelta

from air import openmeteo, waqi

MAX_STATION_KM = 25.0
MAX_STATION_AGE = timedelta(hours=3)

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


def best_window(forecast: list[dict], now: datetime) -> dict | None:
    for slot in forecast:
        start = datetime.fromisoformat(slot["time"])
        end = start + timedelta(hours=3)
        if end > now and decide(slot["aqi_cpcb"])[0] == "yes":
            return {"start": start.isoformat(), "end": end.isoformat()}
    return None


def combine(measured: dict | None, modelled: dict | None, forecast: list[dict], now: datetime) -> dict:
    """-> {"air", "forecast_today", "decision", "caveats"} (contract fragments)."""
    used = choose_source(measured, modelled, now)
    chosen = measured if used == "measured" else modelled
    level, reason = confidence(measured, modelled)
    outdoor, code = decide(chosen["aqi_cpcb"])

    caveats = ["CPCB-style AQI from hourly PM (official CPCB AQI uses 24-h averages and >= 3 pollutants)."]
    if modelled is not None:
        caveats.append("CAMS is a model value for a ~45 km grid cell, not a measurement.")
    if measured is None:
        caveats.append("No WAQI station reading available.")
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
        "decision": {"outdoor": outdoor, "best_window": best_window(forecast, now), "reason_code": code},
        "caveats": caveats,
    }


def air_for(lat: float, lon: float, token: str | None, now: datetime | None = None) -> dict:
    """Fetch both sources and combine. A failing source becomes None plus a caveat."""
    now = now or datetime.now().astimezone()
    notes = []
    measured = None
    if token:
        try:
            measured = waqi.parse(waqi.fetch(lat, lon, token), lat, lon)
        except Exception as e:  # network / API error: fall back to CAMS
            notes.append(f"WAQI unavailable ({type(e).__name__}: {e}).")
    else:
        notes.append("WAQI not queried (no WAQI_TOKEN).")
    modelled, forecast = None, []
    try:
        hours = openmeteo.parse_hourly(openmeteo.fetch(lat, lon))
        modelled, forecast = openmeteo.modelled_now(hours, now), openmeteo.forecast_3h(hours)
    except Exception as e:
        notes.append(f"Open-Meteo unavailable ({type(e).__name__}: {e}).")
    out = combine(measured, modelled, forecast, now)
    out["caveats"] += notes
    return out
