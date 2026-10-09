"""End-to-end test against the deployed stack (stdlib only).

    python infra/e2e_test.py path/to/test.mp4 path/to/test.webm [--api URL] [--stack hazebusters]

Per clip: POST /jobs (Ranchi, school) -> PUT the clip to the presigned URL -> poll GET /jobs/{id} every 2 s
until done/failed (60 s) -> print the JSON and check it against backend/contract.json. Exit 1 on any failure.
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RANCHI = (23.3441, 85.3096)
TYPES = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"}
CONTRACT = Path(__file__).resolve().parents[1] / "backend" / "contract.json"
REGION = "ap-south-1"


def api_url(stack: str) -> str:
    out = subprocess.run(["aws", "cloudformation", "describe-stacks", "--stack-name", stack, "--region", REGION,
                          "--query", "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue", "--output", "text"],
                         check=True, capture_output=True, text=True)
    return out.stdout.strip()


def request(method: str, url: str, body: bytes | None = None, headers: dict | None = None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def key_diff(expected, actual, path="") -> list[str]:
    """Keys of the contract missing from / extra in the result (nested dicts; null result values allowed)."""
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return []
    errs = [f"missing {path}{k}" for k in expected if k not in actual]
    errs += [f"extra {path}{k}" for k in actual if k not in expected]
    for k in expected.keys() & actual.keys():
        errs += key_diff(expected[k], actual[k], f"{path}{k}.")
    return errs


def check(result: dict) -> list[str]:
    errs = key_diff(json.loads(CONTRACT.read_text()), result)
    if not 8 <= result["causes"]["frames_used"] <= 12:
        errs.append(f"frames_used = {result['causes']['frames_used']} (expected ~10)")
    air = result["air"]
    if not isinstance(air["aqi_cpcb"], (int, float)):
        errs.append(f"air.aqi_cpcb = {air['aqi_cpcb']!r}")
    src = air[air["used"]]
    if not src or not all(isinstance(src.get(k), (int, float)) for k in ("pm25", "aqi_cpcb", "band")):
        errs.append(f"air.{air['used']} lacks numbers: {src!r}")
    for lang in ("en", "hi"):
        if not (result["advice"].get(lang) or "").strip():
            errs.append(f"advice.{lang} empty")
    return errs


def run(api: str, clip: Path) -> bool:
    ctype = TYPES[clip.suffix]
    t0 = time.monotonic()
    status, body = request("POST", f"{api}/jobs", json.dumps(
        {"lat": RANCHI[0], "lon": RANCHI[1], "profile": "school", "content_type": ctype}).encode(),
        {"Content-Type": "application/json"})
    if status != 201:
        print(f"[{clip.name}] POST /jobs -> {status}: {body.decode()}")
        return False
    job = json.loads(body)
    status, body = request("PUT", job["upload_url"], clip.read_bytes(), {"Content-Type": ctype})
    if status != 200:
        print(f"[{clip.name}] PUT upload -> {status}: {body.decode()[:500]}")
        return False
    t_up = time.monotonic()
    deadline = t_up + 60
    while time.monotonic() < deadline:
        time.sleep(2)
        status, body = request("GET", f"{api}/jobs/{job['job_id']}")
        got = json.loads(body)
        if status == 200 and got["status"] in ("done", "failed"):
            break
    else:
        print(f"[{clip.name}] timed out after 60 s; last: {body.decode()}")
        return False
    print(json.dumps(got, indent=2, ensure_ascii=False))
    print(f"[{clip.name}] job {job['job_id']}: {got['status']} — upload->result {time.monotonic() - t_up:.1f} s "
          f"(polled every 2 s), total {time.monotonic() - t0:.1f} s")
    if got["status"] != "done":
        print(f"[{clip.name}] FAILED: {got['error']}")
        return False
    errs = check(got["result"])
    print(f"[{clip.name}] checks: " + ("OK" if not errs else "; ".join(errs)))
    return not errs


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("clips", nargs="+", type=Path)
    p.add_argument("--api", help="HTTP API base URL (default: the stack's ApiUrl output)")
    p.add_argument("--stack", default="hazebusters")
    args = p.parse_args()
    api = (args.api or api_url(args.stack)).rstrip("/")
    results = [run(api, clip) for clip in args.clips]
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
