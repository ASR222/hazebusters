"""Advice text (contract `advice`): template EN + HI keyed by decision.outdoor.

Extension point: Bedrock via Strands phrases the same computed numbers; this template stays the fallback.
Health wording follows the CPCB category statements in backend/src/air/decision_rules.md; no new numbers.
Hindi times are written as spoken words at the source ("सुबह 9 बजे से दोपहर 12 बजे तक"), so the same text reads
naturally on screen and in Polly; spoken_times() converts "HH:MM" left in free text (e.g. future Bedrock output).
"""

import re
from datetime import datetime

# outdoor -> (recommendation, health statement or None), each as (en, hi)
TEMPLATES = {
    "yes": (("Air is fine for outdoor activity (CPCB-style AQI {aqi}).",
             "बाहर की गतिविधियों के लिए हवा ठीक है (CPCB-शैली AQI {aqi})।"),
            None),
    "limit": (("Limit outdoor activity: keep it short and light (CPCB-style AQI {aqi}).",
               "बाहर की गतिविधि सीमित रखें: कम समय और हल्की (CPCB-शैली AQI {aqi})।"),
              ("People with lung or heart disease or asthma may feel breathing discomfort.",
               "फेफड़ों या दिल की बीमारी या दमा वाले लोगों को साँस लेने में तकलीफ़ हो सकती है।")),
    "no": (("Keep activities indoors (CPCB-style AQI {aqi}).",
            "गतिविधियाँ घर के अंदर रखें (CPCB-शैली AQI {aqi})।"),
           ("Most people may feel breathing discomfort on prolonged exposure.",
            "ज़्यादा देर बाहर रहने पर ज़्यादातर लोगों को साँस लेने में तकलीफ़ हो सकती है।")),
}
DAY = {"today": ("Today", "आज"), "tomorrow": ("Tomorrow", "कल")}

# Period word by hour (24 h): 4-11 morning, 12-15 afternoon, 16-18 evening, 19-3 night.
PERIODS = ((4, 11, "सुबह"), (12, 15, "दोपहर"), (16, 18, "शाम"))


def hindi_period(hour: int) -> str:
    return next((word for lo, hi, word in PERIODS if lo <= hour <= hi), "रात")


def hindi_clock(hour: int, minute: int = 0) -> str:
    """Spoken clock time without the period: 9:00 -> "9 बजे", 9:30 -> "9 बजकर 30 मिनट", 0:00 -> "12 बजे"."""
    h12 = hour % 12 or 12
    return f"{h12} बजकर {minute} मिनट" if minute else f"{h12} बजे"


def hindi_time(hour: int, minute: int = 0) -> str:
    """09:00 -> "सुबह 9 बजे"; 12:00 -> "दोपहर 12 बजे"; 00:00 -> "रात 12 बजे"."""
    return f"{hindi_period(hour)} {hindi_clock(hour, minute)}"


def hindi_range(start: tuple[int, int], end: tuple[int, int]) -> str:
    """(9, 0), (12, 0) -> "सुबह 9 बजे से दोपहर 12 बजे तक"."""
    return f"{hindi_time(*start)} से {hindi_time(*end)} तक"


_RANGE = re.compile(r"\b(\d{1,2}):(\d{2})\s*[–—\-:]\s*(\d{1,2}):(\d{2})\b")
_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")


def spoken_times(text: str) -> str:
    """Replace "09:00–12:00" / "09:00:12:00" ranges and lone "09:30" in Hindi text with spoken Hindi times."""
    text = _RANGE.sub(lambda m: hindi_range((int(m[1]), int(m[2])), (int(m[3]), int(m[4]))), text)
    return _TIME.sub(lambda m: hindi_time(int(m[1]), int(m[2])), text)


def _hm(iso: str) -> tuple[int, int]:
    t = datetime.fromisoformat(iso)
    return t.hour, t.minute


def build(air: dict, profile: str) -> tuple[dict, list[str]]:
    """-> (contract `advice`, Hindi sections for speech: recommendation, health statement, best window).

    `air`: output of air.combine.air_for (uses air.aqi_cpcb and decision)."""
    d = air["decision"]
    aqi = air["air"]["aqi_cpcb"]
    rec, health = TEMPLATES[d["outdoor"]]
    day_en, day_hi = DAY[d["for"]]
    en = [f"{day_en}: {rec[0].format(aqi=aqi)}"]
    hi = [f"{day_hi}: {rec[1].format(aqi=aqi)}"]
    if health:
        en.append(health[0])
        hi.append(health[1])
    if (w := d["best_window"]) and d["outdoor"] != "yes":
        start, end = _hm(w["start"]), _hm(w["end"])
        en.append(f"Best window: {start[0]:02d}:{start[1]:02d}–{end[0]:02d}:{end[1]:02d}.")
        hi.append(f"सबसे अच्छा समय: {hindi_range(start, end)}।")
    return {"en": " ".join(en), "hi": " ".join(hi), "source": "template"}, hi


def generate(air: dict, profile: str) -> dict:
    return build(air, profile)[0]
