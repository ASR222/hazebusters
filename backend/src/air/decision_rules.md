# Outdoor decision rules

Applied to the CPCB-style AQI (CLAUDE.md §5) of the chosen source (`air.used`), and to each 3-hour forecast slot for `best_window`. Code: `DECISION_RULES` in `combine.py`. The same thresholds apply to every profile (school / worker / general); the profile only changes the advice wording.

| CPCB AQI | Category | CPCB health statement | `outdoor` | `reason_code` |
|---|---|---|---|---|
| 0–50 | Good | Minimal impact | yes | `aqi_le_100` |
| 51–100 | Satisfactory | Minor breathing discomfort to sensitive people | yes | `aqi_le_100` |
| 101–200 | Moderate | Breathing discomfort to the people with lungs, asthma and heart diseases | limit | `aqi_101_200` |
| 201–300 | Poor | Breathing discomfort to most people on prolonged exposure | no | `aqi_gt_200` |
| 301–400 | Very Poor | Respiratory illness on prolonged exposure | no | `aqi_gt_200` |
| 401–500 | Severe | Affects healthy people and seriously impacts those with existing diseases | no | `aqi_gt_200` |

**Source of the health statements:** Central Pollution Control Board (CPCB), *National Air Quality Index* (October 2014), table of AQI categories and possible health impacts.
Verification status (9 Oct 2026): the Severe wording matches a CAQM NCR AQI bulletin (2025) seen in search results; the other rows use the widely cited CPCB wording, because the primary PDF couldn't be fetched (the CAQM PDF needs JavaScript and the NIUA mirror refused the connection). Check the wording against the CPCB document before quoting it in the app or writeup.

**Our mapping (a product choice, not a CPCB rule):** "yes" while CPCB says impact is at most minor for sensitive people; "limit" (shorter, lighter outdoor activity) once sensitive groups are affected; "no" once most people are affected on prolonged exposure.
