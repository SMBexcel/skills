"""Fetch Dealstream search results straight to a dated CSV — no HTML saved.

Pages are fetched with a real Chrome TLS fingerprint (curl_cffi), parsed in
memory, and discarded — nothing is written to disk except the final CSV. This
keeps the user's machine clean and avoids leaving copies of listing HTML lying
around.

curl_cffi impersonates Chrome's TLS/JA3 handshake and HTTP/2 signature. Plain
curl (and Python's requests/urllib) have a distinct fingerprint that DataDome
flags on sight regardless of headers — this closes the biggest passive tell.

This does NOT make collection undetectable. DataDome also weighs request
cadence, volume, and the absence of subresource/JS loading. Stay low-volume and
personal-use. See SKILL.md / README.md.

Output:
  <out>/dealstream_deals_YYYY-MM-DD.csv   — all deals, with an `is_new` column
  <out>/dealstream_new_YYYY-MM-DD.csv     — only deals not in the previous run
The previous run is auto-detected as the most recent older dated CSV in <out>,
so KEEP old dated CSVs in the folder if you want the new-listing diff to work.

Usage (normally invoked via get-deals.sh, which forwards all args):
  python3 fetch_pages.py --cookies <file> [--out <dir>]
                         [--start <page>] [--max <n>]
                         [--min-delay <s>] [--max-delay <s>]
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import random
import re
import subprocess
import sys
import time
from pathlib import Path


def ensure_deps() -> None:
    missing = []
    try:
        import curl_cffi  # noqa: F401
    except ImportError:
        missing.append("curl_cffi")
    try:
        import bs4  # noqa: F401
        import lxml  # noqa: F401
    except ImportError:
        missing += ["beautifulsoup4", "lxml"]
    if missing:
        print(f"Installing {', '.join(missing)} (one-time)...", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "--quiet", *missing])


ensure_deps()
from curl_cffi import requests as creq  # noqa: E402

# Import the page parser from the sibling module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_dealstream import parse_page  # noqa: E402


FIELDS = [
    "page", "name", "price", "cash_flow", "location",
    "industry", "description", "detail_url", "flags", "is_new",
]


def make_session():
    """A session impersonating a recent Chrome, falling back across versions."""
    for target in ("chrome", "chrome124", "chrome120", "chrome110"):
        try:
            return creq.Session(impersonate=target)
        except Exception:
            continue
    print("WARNING: curl_cffi could not impersonate Chrome; TLS fingerprint will not "
          "match a browser. Update curl_cffi: pip install -U curl_cffi", file=sys.stderr)
    return creq.Session()


def is_challenge(text: str) -> bool:
    return len(text) < 5000 or "captcha-delivery" in text


def detect_total_pages(html: str) -> int:
    nums = [int(n) for n in re.findall(r"[?&]page=(\d+)", html)]
    return max(nums) if nums else 1


def human_delay(min_d: float, max_d: float) -> float:
    # Default 3-7s keeps a full ~76-page run in the 5-10 min range. ~1 in 10
    # flips gets a short extra pause so the cadence isn't a perfect metronome.
    s = random.uniform(min_d, max_d)
    if random.random() < 0.10:
        s += random.uniform(5, 12)
    return s


def fetch(session, page: int, headers: dict):
    return session.get(f"https://dealstream.com/search?page={page}", headers=headers, timeout=30)


def find_prior_csv(out_dir: Path, today_name: str) -> Path | None:
    """Most recent dated CSV in out_dir that isn't today's file."""
    dated = []
    for p in out_dir.glob("dealstream_deals_*.csv"):
        if p.name == today_name:
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
        if m:
            dated.append((m.group(1), p))
    if not dated:
        return None
    dated.sort()
    return dated[-1][1]


def write_outputs(rows: list[dict], out_dir: Path):
    """Write the dated CSV (+ an is_new column) and a new-only CSV. Returns a
    summary dict. Diffs against the most recent prior dated CSV by detail_url."""
    out_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    main_csv = out_dir / f"dealstream_deals_{today}.csv"

    prior = find_prior_csv(out_dir, main_csv.name)
    prior_urls: set[str] = set()
    prior_date = None
    if prior:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", prior.name)
        prior_date = m.group(1) if m else prior.name
        with prior.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("detail_url"):
                    prior_urls.add(r["detail_url"])

    new_rows = []
    for r in rows:
        if prior:
            r["is_new"] = "yes" if r["detail_url"] not in prior_urls else "no"
            if r["is_new"] == "yes":
                new_rows.append(r)
        else:
            r["is_new"] = ""  # first run, nothing to compare

    with main_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    new_csv = None
    if prior and new_rows:
        new_csv = out_dir / f"dealstream_new_{today}.csv"
        with new_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(new_rows)

    return {
        "main_csv": main_csv,
        "new_csv": new_csv,
        "total": len(rows),
        "new_count": len(new_rows) if prior else None,
        "prior_date": prior_date,
    }


def main() -> int:
    ap = argparse.ArgumentParser(prog="get-deals.sh", description="Fetch Dealstream deals to a dated CSV (no HTML saved).")
    ap.add_argument("--cookies", required=True, help="file containing the raw cookie: header value")
    ap.add_argument("--out", default="./dealstream-export", help="output dir for the CSV(s)")
    ap.add_argument("--start", type=int, default=1, help="start at this page")
    ap.add_argument("--max", type=int, default=500, help="safety ceiling on page count")
    ap.add_argument("--min-delay", type=float, default=3.0, dest="min_delay", help="min seconds between flips")
    ap.add_argument("--max-delay", type=float, default=7.0, dest="max_delay", help="max seconds between flips")
    args = ap.parse_args()

    cookies_file = Path(args.cookies)
    if not cookies_file.is_file():
        print(f"ERROR: cookies file not found: {cookies_file}", file=sys.stderr)
        return 2
    cookie_str = cookies_file.read_text(encoding="utf-8").replace("\n", "").replace("\r", "").strip()

    out_dir = Path(args.out)
    headers = {"Referer": "https://dealstream.com/search", "Cookie": cookie_str}
    session = make_session()

    seen: set[str] = set()
    rows: list[dict] = []
    partial = False

    # --- page 1: fetch (in memory) + detect total ---
    print("[1/?] Fetching page 1 to detect total page count...")
    try:
        r = fetch(session, 1, headers)
    except Exception as e:
        print(f"[FAIL] page 1 request error: {e}", file=sys.stderr)
        return 1
    if r.status_code != 200 or is_challenge(r.text):
        print(f"[FAIL] page 1 returned http={r.status_code} or DataDome challenge.", file=sys.stderr)
        print("Your cookies are likely stale, or your session is restricted. Refresh your", file=sys.stderr)
        print("dealstream.com browser tab, re-copy the cookie header, and re-run.", file=sys.stderr)
        return 1

    total = min(detect_total_pages(r.text), args.max)
    print(f"[OK]  page=1  http=200  size={len(r.text)}B")
    print(f"Total pages detected: {total}\n")

    # Parse page 1 (unless the user asked to start later)
    if args.start <= 1:
        for row in parse_page(r.text):
            if row["detail_url"] and row["detail_url"] not in seen:
                seen.add(row["detail_url"]); row["page"] = 1; rows.append(row)

    for page in range(max(args.start, 2), total + 1):
        delay = human_delay(args.min_delay, args.max_delay)
        try:
            r = fetch(session, page, headers)
        except Exception as e:
            print(f"[FAIL] page={page} request error: {e}", file=sys.stderr)
            partial = True
            break
        if r.status_code != 200 or is_challenge(r.text):
            print(f"[FAIL] page={page}  http={r.status_code}  size={len(r.text)}B — DataDome challenge or non-200.", file=sys.stderr)
            partial = True
            break
        n_before = len(rows)
        for row in parse_page(r.text):
            if row["detail_url"] and row["detail_url"] not in seen:
                seen.add(row["detail_url"]); row["page"] = page; rows.append(row)
        print(f"[OK]  page={page:>2}  http=200  size={len(r.text)}B  (+{len(rows)-n_before} deals)  sleep={delay:.1f}s")
        time.sleep(delay)

    if not rows:
        print("\nNo deals collected. Nothing written.", file=sys.stderr)
        return 1

    info = write_outputs(rows, out_dir)

    print(f"\nDone. {info['total']} deals -> {info['main_csv']}")
    if partial:
        print("NOTE: run ended early (DataDome challenge or error) — this CSV is PARTIAL.")
        print("      Refresh your cookie and re-run later to get the rest.")
    if info["prior_date"] is None:
        print("First run — no prior CSV to compare against.")
        print("Keep this CSV in the folder; the next run will diff against it to flag new listings.")
    else:
        print(f"Compared against {info['prior_date']}: {info['new_count']} new listing(s).")
        if info["new_csv"]:
            print(f"New-only listings -> {info['new_csv']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
