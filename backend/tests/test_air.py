"""Air module tests. All HTTP is mocked; payloads are synthetic but follow the documented shapes."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from air import combine, http, openmeteo, waqi

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime(2026, 10, 9, 10, 20, tzinfo=IST)
RANCHI = (23.3441, 85.3096)


# --- WAQI ----------------------------------------------------------------------------


@pytest.mark.parametrize("aqi, conc", [(0, 0.0), (50, 12.0), (51, 12.1), (100, 35.4), (151, 55.5), (200, 150.4),
                                       (300, 250.4), (500, 500.4)])
def test_pm25_inversion_breakpoints(aqi, conc):
    assert waqi.us_aqi_to_conc(aqi, waqi.PM25_US_2012) == pytest.approx(conc)


@pytest.mark.parametrize("aqi, conc", [(50, 54), (100, 154), (150, 254), (200, 354), (300, 424), (400, 504)])
def test_pm10_inversion_breakpoints(aqi, conc):
    assert waqi.us_aqi_to_conc(aqi, waqi.PM10_US) == pytest.approx(conc)


def test_inversion_round_trip():
    # Forward EPA formula for 80 µg/m³ PM2.5 (Unhealthy row) gives AQI ~163.8; inverting returns 80.
    forward = 151 + (80 - 55.5) * (200 - 151) / (150.4 - 55.5)
    assert waqi.us_aqi_to_conc(forward, waqi.PM25_US_2012) == pytest.approx(80)


def test_haversine_known_distance():
    # Ranchi -> Jamshedpur is ~107 km great-circle.
    assert waqi.haversine_km(*RANCHI, 22.8046, 86.2029) == pytest.approx(107, abs=3)


def waqi_payload(pm25=163, pm10=120, geo=(23.36, 85.33), iso="2026-10-09T09:00:00+05:30", status="ok"):
    iaqi = {"t": {"v": 29}, "h": {"v": 70}}
    if pm25 is not None:
        iaqi["pm25"] = {"v": pm25}
    if pm10 is not None:
        iaqi["pm10"] = {"v": pm10}
    return {"status": status, "data": {"aqi": max(v for v in (pm25, pm10, 0) if isinstance(v, (int, float))),
                                       "city": {"geo": list(geo), "name": "Test Station, Ranchi"},
                                       "iaqi": iaqi, "time": {"iso": iso}}}


def test_waqi_parse_converts_then_applies_cpcb():
    m = waqi.parse(waqi_payload(), *RANCHI)
    # PM2.5 US AQI 163 -> ~78.7 µg/m³ -> CPCB sub-index ~162 (Moderate); PM10 US 120 -> 155 + 19*99/49 = 193.4 µg/m³ -> ~162.
    assert m["pm25"] == pytest.approx(78.7, abs=0.1)
    assert m["pm10"] == pytest.approx(193.4, abs=0.1)
    assert 101 <= m["aqi_cpcb"] <= 200 and m["band"] == 1
    assert m["dist_km"] < 5
    assert m["source"] == "WAQI" and m["updated_at"] == "2026-10-09T09:00:00+05:30"


def test_waqi_parse_handles_missing_and_offline_values():
    assert waqi.parse(waqi_payload(pm25=None, pm10=None), *RANCHI) is None
    assert waqi.parse(waqi_payload(pm25="-", pm10=None), *RANCHI) is None
    only10 = waqi.parse(waqi_payload(pm25=None, pm10=100), *RANCHI)
    assert only10["pm25"] is None and only10["pm10"] == pytest.approx(154)


def test_waqi_error_status_raises():
    with pytest.raises(waqi.WaqiError, match="Invalid key"):
        waqi.parse({"status": "error", "data": "Invalid key"}, *RANCHI)


# --- Open-Meteo -----------------------------------------------------------------------------


def openmeteo_payload(pm25=None, pm10=None, days=1):
    n = 24 * days
    pm25 = pm25 or [20.0 + i % 24 for i in range(n)]
    pm10 = pm10 or [40.0 + i % 24 for i in range(n)]
    times = [f"2026-10-{9 + i // 24:02d}T{i % 24:02d}:00" for i in range(n)]
    return {"utc_offset_seconds": 19800, "hourly_units": {"pm2_5": "μg/m³", "pm10": "μg/m³"},
            "hourly": {"time": times, "pm2_5": pm25, "pm10": pm10}}


def test_openmeteo_request_params(monkeypatch):
    seen = {}
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10: seen.update(url=url, params=params) or {})
    openmeteo.fetch(*RANCHI)
    assert seen["url"] == openmeteo.URL
    assert seen["params"]["hourly"] == "pm10,pm2_5"
    assert seen["params"]["timezone"] == "Asia/Kolkata"
    assert seen["params"]["forecast_days"] == 2  # today + tomorrow


def test_modelled_now_uses_current_hour():
    m = openmeteo.modelled_now(openmeteo.parse_hourly(openmeteo_payload()), NOW)
    assert m["valid_at"] == "2026-10-09T10:00:00+05:30"
    assert m["pm25"] == 30.0 and m["pm10"] == 50.0
    assert m["aqi_cpcb"] == 50 and m["band"] == 0  # PM2.5 30 -> 50, PM10 50 -> 50


def test_modelled_now_skips_missing_hours():
    pm25 = [20.0] * 24
    pm25[10] = None
    pm10 = [40.0] * 24
    pm10[10] = None
    m = openmeteo.modelled_now(openmeteo.parse_hourly(openmeteo_payload(pm25, pm10)), NOW)
    assert m["valid_at"] == "2026-10-09T09:00:00+05:30"


def test_forecast_3h_means_and_aqi_from_both_pm():
    f = openmeteo.forecast_3h(openmeteo.parse_hourly(openmeteo_payload()))
    assert [s["time"][11:16] for s in f] == ["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]
    assert f[0]["pm25"] == 21.0  # mean of 20, 21, 22
    # Slot 21:00: PM2.5 mean 42 -> 70; PM10 mean 62 -> 62 -> AQI = max = 70.
    assert f[-1]["aqi_cpcb"] == 70 and f[-1]["band"] == 0


# --- combine --------------------------------------------------------------------------------


def meas(dist=10.0, band=1, aqi=150, age_h=1.0):
    return {"source": "WAQI", "station": "S", "dist_km": dist, "updated_at": (NOW - timedelta(hours=age_h)).isoformat(),
            "pm25": 70.0, "pm10": 100.0, "aqi_cpcb": aqi, "band": band}


def modl(band=1, aqi=140):
    return {"source": openmeteo.SOURCE, "grid_km": 45, "valid_at": NOW.isoformat(), "pm25": 65.0, "pm10": 90.0,
            "aqi_cpcb": aqi, "band": band}


@pytest.mark.parametrize("m, expected", [
    (meas(dist=10, age_h=1), "measured"),
    (meas(dist=25, age_h=2.9), "measured"),
    (meas(dist=25.1, age_h=1), "modelled"),
    (meas(dist=10, age_h=3), "modelled"),
    (None, "modelled"),
])
def test_choose_source(m, expected):
    assert combine.choose_source(m, modl(), NOW) == expected


def test_choose_source_falls_back_to_far_station_when_cams_missing():
    assert combine.choose_source(meas(dist=80), None, NOW) == "measured"
    with pytest.raises(ValueError):
        combine.choose_source(None, None, NOW)


@pytest.mark.parametrize("m, mo, level", [
    (meas(dist=10, band=1), modl(band=1), "high"),
    (meas(dist=10, band=2), modl(band=1), "medium"),
    (meas(dist=60, band=1), modl(band=1), "medium"),
    (meas(dist=60, band=2), modl(band=1), "low"),
    (None, modl(), "low"),
])
def test_confidence(m, mo, level):
    assert combine.confidence(m, mo)[0] == level


@pytest.mark.parametrize("aqi, outdoor", [(0, "yes"), (100, "yes"), (101, "limit"), (200, "limit"), (201, "no"), (480, "no")])
def test_decision_thresholds(aqi, outdoor):
    assert combine.decide(aqi)[0] == outdoor


def slot(hour, aqi, day=0):
    t = NOW.replace(hour=hour, minute=0) + timedelta(days=day)
    return {"time": t.isoformat(), "pm25": 0, "aqi_cpcb": aqi, "band": 0}


def hm(ts):
    return ts[11:16]


def test_decision_uses_worst_slot_until_end_of_hours():
    # 10:20, school (07-17): slots overlapping 10:20-17:00 are 09 (80), 12 (150), 15 (90); 18 (250) is after hours.
    d = combine.decision(60, [slot(9, 80), slot(12, 150), slot(15, 90), slot(18, 250)], NOW, "school")
    assert d["for"] == "today"
    assert (d["outdoor"], d["reason_code"]) == ("limit", "aqi_101_200")
    assert (hm(d["best_window"]["start"]), hm(d["best_window"]["end"])) == ("10:20", "12:00")


def test_current_reading_counts_inside_hours():
    d = combine.decision(230, [slot(9, 60), slot(12, 60), slot(15, 60)], NOW, "school")
    assert d["outdoor"] == "no" and d["best_window"] is not None


def test_before_hours_uses_today_without_current_reading():
    early = NOW.replace(hour=5, minute=0)
    d = combine.decision(300, [slot(6, 80), slot(9, 90), slot(12, 90), slot(15, 90)], early, "school")
    assert d["for"] == "today" and d["outdoor"] == "yes"
    assert (hm(d["best_window"]["start"]), hm(d["best_window"]["end"])) == ("07:00", "09:00")


def test_after_hours_switches_to_tomorrow():
    evening = NOW.replace(hour=18, minute=30)
    forecast = [slot(15, 50), slot(18, 50), slot(6, 80, 1), slot(9, 150, 1), slot(12, 90, 1), slot(15, 70, 1), slot(18, 400, 1)]
    d = combine.decision(300, forecast, evening, "school")
    assert d["for"] == "tomorrow"
    assert d["outdoor"] == "limit"  # worst of tomorrow 07-17 is 150; today's 300 and tomorrow 18:00 don't count
    assert d["best_window"] == {"start": "2026-10-10T07:00:00+05:30", "end": "2026-10-10T09:00:00+05:30"}


@pytest.mark.parametrize("now_hour, day", [(10, "today"), (19, "tomorrow")])
def test_no_window_reason_code(now_hour, day):
    forecast = [slot(h, 250, d) for d in (0, 1) for h in range(0, 24, 3)]
    d = combine.decision(250, forecast, NOW.replace(hour=now_hour), "school")
    assert d["for"] == day and d["best_window"] is None and d["reason_code"] == f"no_window_{day}"


@pytest.mark.parametrize("profile, expected", [("school", None), ("worker", ("18:00", "19:00")), ("general", ("18:00", "21:00"))])
def test_evening_slot_depends_on_profile(profile, expected):
    d = combine.decision(50, [slot(18, 70)], NOW.replace(hour=17, minute=30), profile)
    w = d["best_window"] if d["for"] == "today" else None
    assert (w and (hm(w["start"]), hm(w["end"]))) == expected


def test_night_slots_never_count():
    forecast = [slot(0, 20), slot(21, 20), slot(0, 20, 1), slot(21, 20, 1)]
    for p in combine.PROFILE_WINDOWS:
        assert combine.decision(20, forecast, NOW.replace(hour=5), p)["best_window"] is None


def test_combine_uses_chosen_source_and_keeps_both():
    out = combine.combine(meas(dist=60, aqi=150, band=1), modl(aqi=240, band=1), [slot(15, 90)], NOW)
    air = out["air"]
    assert air["used"] == "modelled" and air["aqi_cpcb"] == 240
    assert air["measured"]["aqi_cpcb"] == 150 and air["modelled"]["aqi_cpcb"] == 240
    assert out["decision"]["outdoor"] == "no" and out["decision"]["reason_code"] == "aqi_gt_200"
    assert any("60" in c for c in out["caveats"])


def test_air_for_end_to_end_with_mocked_http(monkeypatch):
    def fake_get_json(url, params=None, timeout=10):
        return waqi_payload(geo=(22.80, 86.20)) if "waqi" in url else openmeteo_payload()
    monkeypatch.setattr(http, "get_json", fake_get_json)
    out = combine.air_for(*RANCHI, token="t", now=NOW)
    assert out["air"]["used"] == "modelled"  # station ~107 km away
    assert out["air"]["measured"]["dist_km"] > 100
    assert out["air"]["confidence"] in {"medium", "low"}
    assert len(out["forecast_today"]) == 8


def test_air_for_without_token_is_modelled_only(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10: openmeteo_payload())
    out = combine.air_for(*RANCHI, token=None, now=NOW)
    assert out["air"]["measured"] is None and out["air"]["confidence"] == "low"
    assert any("WAQI_TOKEN" in c for c in out["caveats"])


def test_output_matches_contract_keys(monkeypatch):
    contract = json.loads((Path(__file__).resolve().parents[1] / "contract.json").read_text())
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10:
                        waqi_payload() if "waqi" in url else openmeteo_payload())
    out = combine.air_for(*RANCHI, token="t", now=NOW)
    assert set(out["air"]) == set(contract["air"])
    assert set(out["air"]["measured"]) == set(contract["air"]["measured"])
    assert set(out["air"]["modelled"]) == set(contract["air"]["modelled"])
    assert set(out["forecast_today"][0]) == set(contract["forecast_today"][0])
    assert set(out) >= {"air", "forecast_today", "forecast_tomorrow", "decision", "caveats"}
    assert set(out["decision"]) == set(contract["decision"])
    assert set(out["decision"]["best_window"] or contract["decision"]["best_window"]) == {"start", "end"}


# --- profile windows, correction, caveats ------------------------------------------------------


def test_unknown_profile_rejected():
    with pytest.raises(ValueError):
        combine.combine(meas(), modl(), [], NOW, profile="pilot")


def test_modelled_only_is_scaled_by_correction(monkeypatch):
    from cpcb_aqi import cpcb_aqi
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10: openmeteo_payload())
    out = combine.air_for(*RANCHI, token=None, now=NOW)
    m = out["air"]["modelled"]
    # Raw CAMS at 10:00 is PM2.5 30, PM10 50 -> scaled x1.25.
    assert m["pm25"] == pytest.approx(30 * combine.CAMS_CORRECTION)
    assert m["pm10"] == pytest.approx(50 * combine.CAMS_CORRECTION)
    assert m["aqi_cpcb"] == round(cpcb_aqi(37.5, 62.5))
    assert out["air"]["aqi_cpcb"] == m["aqi_cpcb"]
    assert out["forecast_today"][0]["pm25"] == pytest.approx(21.0 * combine.CAMS_CORRECTION, abs=0.06)  # rounded to 0.1
    assert sum("scaled x1.25" in c for c in out["caveats"]) == 1


def test_far_station_still_gets_correction(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10:
                        waqi_payload(geo=(22.80, 86.20)) if "waqi" in url else openmeteo_payload())
    out = combine.air_for(*RANCHI, token="t", now=NOW)
    assert out["air"]["used"] == "modelled"  # station ~107 km away
    assert out["air"]["measured"] is not None
    assert out["air"]["modelled"]["pm25"] == pytest.approx(30 * combine.CAMS_CORRECTION)
    assert sum("scaled x1.25" in c for c in out["caveats"]) == 1


def test_stale_station_still_gets_correction(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10:
                        waqi_payload(iso="2026-10-09T05:00:00+05:30") if "waqi" in url else openmeteo_payload())
    out = combine.air_for(*RANCHI, token="t", now=NOW)
    assert out["air"]["used"] == "modelled" and out["air"]["modelled"]["pm25"] == pytest.approx(37.5)


def test_near_fresh_station_disables_correction(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10:
                        waqi_payload() if "waqi" in url else openmeteo_payload())
    out = combine.air_for(*RANCHI, token="t", now=NOW)
    assert out["air"]["used"] == "measured"
    assert out["air"]["modelled"]["pm25"] == 30.0
    assert not any("scaled" in c for c in out["caveats"])


def test_caveats_have_no_duplicates_and_one_waqi_reason(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10: openmeteo_payload())
    out = combine.air_for(*RANCHI, token=None, now=NOW)
    assert len(out["caveats"]) == len(set(out["caveats"]))
    assert [c for c in out["caveats"] if "WAQI" in c] == ["WAQI not queried (no WAQI_TOKEN)."]


def test_forecast_tomorrow_split_by_date(monkeypatch):
    contract = json.loads((Path(__file__).resolve().parents[1] / "contract.json").read_text())
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10: openmeteo_payload(days=2))
    out = combine.air_for(*RANCHI, token=None, now=NOW)
    assert [s["time"][:10] for s in out["forecast_today"]] == ["2026-10-09"] * 8
    assert [s["time"][:10] for s in out["forecast_tomorrow"]] == ["2026-10-10"] * 8
    assert set(out["forecast_tomorrow"][0]) == set(contract["forecast_tomorrow"][0])


def test_forecast_tomorrow_empty_without_data(monkeypatch):
    monkeypatch.setattr(http, "get_json", lambda url, params=None, timeout=10: openmeteo_payload(days=1))
    assert combine.air_for(*RANCHI, token=None, now=NOW)["forecast_tomorrow"] == []
