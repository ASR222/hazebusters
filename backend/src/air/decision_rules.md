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

## Best window (per profile)

`best_window` = the earliest 3-hour forecast slot still left today whose AQI is "yes", clipped to the profile's outdoor hours (local time). If there is none, `best_window` is null and `reason_code` is `no_window_today`.

| profile | hours |
|---|---|
| school | 07:00–17:00 |
| worker | 06:00–19:00 |
| general | 06:00–21:00 |

## CAMS correction (modelled only)

When there is no station reading, CAMS PM2.5/PM10 are multiplied by **1.25** before the AQI, the decision and the forecast (`CAMS_CORRECTION` in `combine.py`). Basis: CAMS daily PM2.5 ran at a median 0.78× (Delhi), 0.79× (Hyderabad) and 0.81× (Patna) of ground stations in 2023–24 (`ml/runs/cams_validation/summary.json`, `ml/RESULTS.md` §2). Validated on those three cities and on PM2.5 only; applying the same factor to PM10 is an assumption.
