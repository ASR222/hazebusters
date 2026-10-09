"""Live check: `uv run python -m air Ranchi Hyderabad` prints the combined air JSON per place.

WAQI_TOKEN comes from the environment or the repo-root .env (never printed).
"""

import json
import os
import sys
from pathlib import Path

from air.combine import air_for

PLACES = {"Ranchi": (23.3441, 85.3096), "Hyderabad": (17.3850, 78.4867), "Delhi": (28.6139, 77.2090), "Patna": (25.5941, 85.1376)}


def _token() -> str | None:
    if os.environ.get("WAQI_TOKEN"):
        return os.environ["WAQI_TOKEN"]
    env = Path(__file__).resolve().parents[3] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("WAQI_TOKEN="):
                return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


def main(places: list[str]) -> None:
    token = _token()
    for place in places or ["Ranchi", "Hyderabad"]:
        lat, lon = PLACES[place]
        out = {"location": {"lat": lat, "lon": lon, "place": place}} | air_for(lat, lon, token)
        print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
