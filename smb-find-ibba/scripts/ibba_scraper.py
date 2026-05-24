#!/usr/bin/env python3
"""
IBBA business-broker directory scraper.

Two stages:
  1) enumerate  -> hit the public /wp-json/brokers/geo endpoint once and dump
                   every broker (name, company, city, state, zip, profile URL)
                   to <out>/ibba_brokers.csv
  2) emails     -> visit each profile page and pull the contact details
                   (email, phone, website) out of the page's hidden form
                   fields, writing <out>/ibba_contacts.csv

`run` does both. The emails stage is RESUMABLE: re-running skips any profile
URL already present in the output file, so you can stop/restart freely, and any
errored profiles get retried on the next run.

No third-party dependencies — Python standard library only.

Usage:
  python3 ibba_scraper.py run                 # enumerate + scrape emails
  python3 ibba_scraper.py enumerate           # just build the broker list
  python3 ibba_scraper.py emails              # just scrape emails (needs list)
  python3 ibba_scraper.py emails --limit 50   # cap profiles (for testing)
  python3 ibba_scraper.py run --out ./my-dir  # choose the output directory

Be a good citizen: this hits a live site. Defaults are deliberately gentle
(6 workers, small jittered delay, retries). Don't crank the workers way up.
"""

import argparse
import csv
import gzip
import io
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# One geo query centered on the continental US with a radius big enough to
# cover everything the directory returns in a single response.
GEO_URL = (
    "https://www.ibba.org/wp-json/brokers/geo"
    "?lat=39.5&lng=-98.35&miles=6000&specialties=&cbi="
)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Hidden Gravity Forms fields on each profile carry the broker's own details.
HIDDEN_INPUT_RE = re.compile(
    r"name='input_(\d+)'[^>]*class='gform_hidden'[^>]*value='([^']*)'"
)
# Field map for the broker contact form (form id 4) on profile pages.
FIELD_MAP = {"6": "name", "7": "company", "8": "phone", "9": "website", "10": "email"}

BROKER_FIELDS = [
    "name", "company", "city", "state", "zip", "url",
    "cbi", "mami", "master_cbi", "membership",
]
CONTACT_FIELDS = [
    "name", "company", "email", "phone", "website",
    "city", "state", "zip", "cbi", "url", "status",
]

_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, file=sys.stderr, flush=True)


def fetch(url, timeout=30, retries=3):
    """GET a URL with a browser UA, gzip support, and basic backoff retries."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/json,*/*",
                    "Accept-Encoding": "gzip",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                return raw.decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1) + random.random())
    raise last_err


# --------------------------------------------------------------------------- #
# Stage 1: enumerate brokers
# --------------------------------------------------------------------------- #
def enumerate_brokers(brokers_csv):
    log("Fetching broker directory from geo endpoint ...")
    data = json.loads(fetch(GEO_URL, timeout=120))
    feats = data.get("features", [])
    rows = []
    seen = set()

    def s(v):
        return (v or "").strip() if isinstance(v, str) else ("" if v is None else str(v))

    for f in feats:
        p = (f.get("geometry") or {}).get("properties") or {}
        url = s(p.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append({
            "name": s(p.get("name")),
            "company": s(p.get("company")),
            "city": s(p.get("city")),
            "state": s(p.get("state")),
            "zip": s(p.get("zip")),
            "url": url,
            "cbi": s(p.get("cbi")),
            "mami": s(p.get("mami")),
            "master_cbi": s(p.get("master_cbi")),
            "membership": s(p.get("membership")),
        })
    with open(brokers_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=BROKER_FIELDS)
        w.writeheader()
        w.writerows(rows)
    log(f"Wrote {len(rows)} brokers -> {brokers_csv}")
    return rows


def load_brokers(brokers_csv):
    if not os.path.exists(brokers_csv):
        return None
    with open(brokers_csv, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- #
# Stage 2: scrape contact details from profile pages
# --------------------------------------------------------------------------- #
def parse_profile(html):
    """Pull contact fields out of a profile page's hidden form inputs."""
    out = {}
    for idx, val in HIDDEN_INPUT_RE.findall(html):
        key = FIELD_MAP.get(idx)
        if key and val and not out.get(key):
            out[key] = val.strip()
    # Fallback: if the mapped email field was empty/missing, take the first
    # real email on the page that isn't an asset filename.
    if not out.get("email"):
        for m in EMAIL_RE.findall(html):
            if not re.search(r"\.(png|jpe?g|gif|svg|webp)$", m, re.I):
                out["email"] = m
                break
    return out


def load_done_urls(contacts_csv):
    """URLs already scraped (any status) so we can resume without redoing them."""
    done = set()
    if os.path.exists(contacts_csv):
        with open(contacts_csv, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("url"):
                    done.add(row["url"])
    return done


def scrape_emails(brokers_csv, contacts_csv, workers=6, delay=0.5, limit=None):
    brokers = load_brokers(brokers_csv)
    if not brokers:
        log("No broker list found. Run `enumerate` first.")
        sys.exit(1)

    done = load_done_urls(contacts_csv)
    todo = [b for b in brokers if b["url"] not in done]
    if limit:
        todo = todo[:limit]
    log(f"{len(brokers)} brokers total | {len(done)} already done | {len(todo)} to scrape")
    if not todo:
        log("Nothing to do.")
        return

    new_file = not os.path.exists(contacts_csv)
    fh = open(contacts_csv, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(fh, fieldnames=CONTACT_FIELDS)
    if new_file:
        writer.writeheader()
    write_lock = threading.Lock()
    counter = {"done": 0, "ok": 0, "noemail": 0, "err": 0}

    def work(b):
        time.sleep(delay * random.random())
        row = {
            "name": b["name"], "company": b["company"], "email": "", "phone": "",
            "website": "", "city": b["city"], "state": b["state"], "zip": b["zip"],
            "cbi": b["cbi"], "url": b["url"], "status": "",
        }
        try:
            html = fetch(b["url"])
            info = parse_profile(html)
            row["email"] = info.get("email", "")
            row["phone"] = info.get("phone", "")
            row["website"] = info.get("website", "")
            if info.get("company") and not row["company"]:
                row["company"] = info["company"]
            row["status"] = "ok" if row["email"] else "no_email"
        except Exception as e:  # noqa: BLE001 - record the failure, keep going
            row["status"] = f"error: {type(e).__name__}"
        return row

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(work, b) for b in todo]
        for fut in as_completed(futures):
            row = fut.result()
            with write_lock:
                writer.writerow(row)
                fh.flush()
                counter["done"] += 1
                if row["status"] == "ok":
                    counter["ok"] += 1
                elif row["status"] == "no_email":
                    counter["noemail"] += 1
                else:
                    counter["err"] += 1
                if counter["done"] % 25 == 0 or counter["done"] == len(todo):
                    log(f"  {counter['done']}/{len(todo)} "
                        f"(emails: {counter['ok']}, no-email: {counter['noemail']}, "
                        f"errors: {counter['err']})")
    fh.close()
    log(f"Done. Wrote/updated {contacts_csv}")
    log(f"  emails found: {counter['ok']} | no email: {counter['noemail']} | errors: {counter['err']}")
    if counter["err"]:
        log("  Re-run `emails` to retry the errored profiles (it resumes automatically).")


def main():
    ap = argparse.ArgumentParser(description="IBBA broker directory scraper")
    ap.add_argument("command", choices=["run", "enumerate", "emails"],
                    help="run = enumerate then scrape emails")
    ap.add_argument("--out", default="./ibba-export", help="output directory (default ./ibba-export)")
    ap.add_argument("--workers", type=int, default=6, help="concurrent profile fetches (default 6)")
    ap.add_argument("--delay", type=float, default=0.5, help="max jitter delay per request, seconds")
    ap.add_argument("--limit", type=int, default=None, help="cap number of profiles (for testing)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    brokers_csv = os.path.join(args.out, "ibba_brokers.csv")
    contacts_csv = os.path.join(args.out, "ibba_contacts.csv")

    if args.command in ("run", "enumerate"):
        enumerate_brokers(brokers_csv)
    if args.command in ("run", "emails"):
        scrape_emails(brokers_csv, contacts_csv, workers=args.workers,
                      delay=args.delay, limit=args.limit)


if __name__ == "__main__":
    main()
