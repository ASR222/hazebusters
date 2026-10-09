"""Advice text (contract `advice`): template EN + HI keyed by decision.outdoor.

Extension point: Bedrock via Strands phrases the same computed numbers; this template stays the fallback.
Health wording follows the CPCB category statements in backend/src/air/decision_rules.md; no new numbers.
Times are written as spoken words at the source in both languages ("सुबह 9 बजे से दोपहर 12 बजे तक",
"from 9 AM to 12 noon"), so the same text reads naturally on screen and in Polly; spoken_times() converts
"HH:MM" left in free text (e.g. future Bedrock output). The CPCB-scale note lives in the result's caveats.
"""

import re
from datetime import datetime

# outdoor -> (recommendation, health statement or None), each as (en, hi)
TEMPLATES = {
    "yes": (("Air is fine for outdoor activity.", "बाहर की गतिविधियों के लिए हवा ठीक है।"),
            None),
    "limit": (("Limit outdoor activity: keep it short and light.", "बाहर की गतिविधि सीमित रखें, कम समय और हल्की।"),
              ("People with lung or heart disease or asthma may feel breathing discomfort.",
               "फेफड़ों या दिल की बीमारी या दमा वाले लोगों को साँस लेने में तकलीफ़ हो सकती है।")),
    "no": (("Keep activities indoors.", "गतिविधियाँ घर के अंदर रखें।"),
           ("Most people may feel breathing discomfort on prolonged exposure.",
            "ज़्यादा देर बाहर रहने पर ज़्यादातर लोगों को साँस लेने में तकलीफ़ हो सकती है।")),
}
# The AQI is the current reading; when the decision is for tomorrow, say "right now" and prefix the advice.
AQI_SENTENCE = {"today": ("Today's AQI is {aqi}.", "आज हवा का AQI {aqi} है।"),
                "tomorrow": ("The AQI right now is {aqi}.", "अभी हवा का AQI {aqi} है।")}
TOMORROW = ("Tomorrow, ", "कल ")
WINDOW = ("Best time: {span}.", "सबसे अच्छा समय: {span}।")

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


def english_time(hour: int, minute: int = 0) -> str:
    """09:00 -> "9 AM"; 09:30 -> "9:30 AM"; 12:00 -> "12 noon"; 00:00 -> "12 midnight"; 15:00 -> "3 PM"."""
    if minute == 0 and hour in (0, 12):
        return "12 midnight" if hour == 0 else "12 noon"
    h12 = hour % 12 or 12
    clock = f"{h12}:{minute:02d}" if minute else f"{h12}"
    return f"{clock} {'AM' if hour < 12 else 'PM'}"


def english_range(start: tuple[int, int], end: tuple[int, int]) -> str:
    """(9, 0), (12, 0) -> "from 9 AM to 12 noon"."""
    return f"from {english_time(*start)} to {english_time(*end)}"


SPEAK_TIME = {"hi": hindi_time, "en": english_time}
SPEAK_RANGE = {"hi": hindi_range, "en": english_range}
# One pass (range first, else a lone time), so spoken output like "9:30 AM" is never converted twice.
_CLOCK = re.compile(r"\b(\d{1,2}):(\d{2})(?:\s*[–—\-:]\s*(\d{1,2}):(\d{2}))?\b")


def _speak(m: re.Match, lang: str) -> str:
    start = (int(m[1]), int(m[2]))
    return SPEAK_RANGE[lang](start, (int(m[3]), int(m[4]))) if m[3] else SPEAK_TIME[lang](*start)


def spoken_times(text: str, lang: str = "hi") -> str:
    """Replace "09:00–12:00" / "09:00:12:00" ranges and lone "09:30" with spoken times in `lang`."""
    return _CLOCK.sub(lambda m: _speak(m, lang), text)


def _hm(iso: str) -> tuple[int, int]:
    t = datetime.fromisoformat(iso)
    return t.hour, t.minute


def _lower_first(s: str) -> str:
    return s[:1].lower() + s[1:]


def build(air: dict, profile: str) -> tuple[dict, dict[str, list[str]]]:
    """-> (contract `advice`, {"en": sections, "hi": sections} for speech).

    Sections: AQI + recommendation, health statement, best window. `air`: output of air.combine.air_for."""
    d = air["decision"]
    aqi = air["air"]["aqi_cpcb"]
    rec, health = TEMPLATES[d["outdoor"]]
    sections = {}
    for i, lang in enumerate(("en", "hi")):
        r = rec[i] if d["for"] == "today" else TOMORROW[i] + (_lower_first(rec[i]) if lang == "en" else rec[i])
        parts = [f"{AQI_SENTENCE[d['for']][i].format(aqi=aqi)} {r}"]
        if health:
            parts.append(health[i])
        if (w := d["best_window"]) and d["outdoor"] != "yes":
            parts.append(WINDOW[i].format(span=SPEAK_RANGE[lang](_hm(w["start"]), _hm(w["end"]))))
        sections[lang] = parts
    return {"en": " ".join(sections["en"]), "hi": " ".join(sections["hi"]), "source": "template"}, sections


def generate(air: dict, profile: str) -> dict:
    return build(air, profile)[0]
