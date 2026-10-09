"""Hindi spoken times and advice sections (pure functions)."""

import pytest

import advice


@pytest.mark.parametrize("h, m, expected", [
    (9, 0, "सुबह 9 बजे"),
    (4, 0, "सुबह 4 बजे"),
    (12, 0, "दोपहर 12 बजे"),   # noon
    (15, 0, "दोपहर 3 बजे"),
    (17, 0, "शाम 5 बजे"),
    (19, 0, "रात 7 बजे"),
    (0, 0, "रात 12 बजे"),      # midnight
    (3, 0, "रात 3 बजे"),
    (9, 30, "सुबह 9 बजकर 30 मिनट"),
    (7, 5, "सुबह 7 बजकर 5 मिनट"),
])
def test_hindi_time(h, m, expected):
    assert advice.hindi_time(h, m) == expected


def test_hindi_range():
    assert advice.hindi_range((9, 0), (12, 0)) == "सुबह 9 बजे से दोपहर 12 बजे तक"
    assert advice.hindi_range((9, 30), (12, 15)) == "सुबह 9 बजकर 30 मिनट से दोपहर 12 बजकर 15 मिनट तक"
    assert advice.hindi_range((21, 0), (0, 0)) == "रात 9 बजे से रात 12 बजे तक"


@pytest.mark.parametrize("text, expected", [
    ("समय: 09:00–12:00।", "समय: सुबह 9 बजे से दोपहर 12 बजे तक।"),
    ("समय: 09:00:12:00।", "समय: सुबह 9 बजे से दोपहर 12 बजे तक।"),
    ("समय: 16:30 - 18:00", "समय: शाम 4 बजकर 30 मिनट से शाम 6 बजे तक"),
    ("अभी 00:00 है", "अभी रात 12 बजे है"),
    ("AQI 122 है", "AQI 122 है"),
])
def test_spoken_times(text, expected):
    assert advice.spoken_times(text) == expected


def _air(outdoor, window, day="today"):
    return {"air": {"aqi_cpcb": 122},
            "decision": {"for": day, "outdoor": outdoor, "best_window": window, "reason_code": "x"}}


def test_build_formats_hindi_window_at_source():
    window = {"start": "2026-10-10T09:00:00+05:30", "end": "2026-10-10T12:00:00+05:30"}
    out, sections = advice.build(_air("limit", window), "school")
    assert out["source"] == "template"
    assert out["en"].endswith("Best window: 09:00–12:00.")
    assert sections[-1] == "सबसे अच्छा समय: सुबह 9 बजे से दोपहर 12 बजे तक।"
    assert out["hi"] == " ".join(sections) and len(sections) == 3
    assert ":00" not in out["hi"]


def test_build_yes_has_one_section():
    out, sections = advice.build(_air("yes", None), "general")
    assert len(sections) == 1 and out["hi"].startswith("आज: ")
