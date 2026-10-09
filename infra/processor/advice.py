"""Advice text (contract `advice`): template EN + HI keyed by decision.outdoor.

Extension point: Bedrock via Strands phrases the same computed numbers; this template stays the fallback.
Health wording follows the CPCB category statements in backend/src/air/decision_rules.md; no new numbers.
"""

from datetime import datetime

TEMPLATES = {
    "yes": ("Air is fine for outdoor activity (CPCB-style AQI {aqi}).",
            "बाहर की गतिविधियों के लिए हवा ठीक है (CPCB-शैली AQI {aqi})।"),
    "limit": ("Limit outdoor activity: keep it short and light (CPCB-style AQI {aqi}). People with lung or heart "
              "disease or asthma may feel breathing discomfort.",
              "बाहर की गतिविधि सीमित रखें: कम समय और हल्की (CPCB-शैली AQI {aqi})। फेफड़ों या दिल की बीमारी या दमा "
              "वाले लोगों को साँस लेने में तकलीफ़ हो सकती है।"),
    "no": ("Keep activities indoors (CPCB-style AQI {aqi}). Most people may feel breathing discomfort on "
           "prolonged exposure.",
           "गतिविधियाँ घर के अंदर रखें (CPCB-शैली AQI {aqi})। ज़्यादा देर बाहर रहने पर ज़्यादातर लोगों को साँस "
           "लेने में तकलीफ़ हो सकती है।"),
}
DAY = {"today": ("Today", "आज"), "tomorrow": ("Tomorrow", "कल")}


def _hhmm(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%H:%M")


def generate(air: dict, profile: str) -> dict:
    """`air`: output of air.combine.air_for (uses air.aqi_cpcb and decision)."""
    d = air["decision"]
    aqi = air["air"]["aqi_cpcb"]
    en, hi = (t.format(aqi=aqi) for t in TEMPLATES[d["outdoor"]])
    day_en, day_hi = DAY[d["for"]]
    en, hi = f"{day_en}: {en}", f"{day_hi}: {hi}"
    if (w := d["best_window"]) and d["outdoor"] != "yes":
        span = f"{_hhmm(w['start'])}–{_hhmm(w['end'])}"
        en += f" Best window: {span}."
        hi += f" सबसे अच्छा समय: {span}।"
    return {"en": en, "hi": hi, "source": "template"}
