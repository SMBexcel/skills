"""Parse a saved Dealstream search-results HTML page into structured rows.

Each "All Matching Deals" card on Dealstream's /search page renders as:

  <a class="card card-body mb-3 listingInfo ... post" href="/d/biz-sale/.../xyz">
    <div id="post_xyz">
      <div class="postsummary listingInfo">
        ...
        <h2 class="link-secondary"><span class="headline_*">NAME</span></h2>
        <aside class="b">
          <span title="Location">  ...<icon/>LOCATION   </span>
          <span title="Industry">  ...<icon/>INDUSTRY   </span>
          <span title="...flag...">...<icon/>...        </span>   # repeated
        </aside>
        <p><span class="body_*">DESCRIPTION</span></p>
        <div class="h2">$PRICE</div>
        <div class="h6">Cash Flow: $X</div>
      </div>
    </div>
  </a>

If Dealstream changes their markup, update the CSS selectors below.

Usage:
  python3 parse_dealstream.py <page.html>           # prints first 3 rows
  python3 parse_dealstream.py <page.html> --json    # dumps all rows as JSON
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("bs4 not installed. Install with: pip3 install --user beautifulsoup4 lxml", file=sys.stderr)
    sys.exit(1)


def text(el) -> str:
    return el.get_text(" ", strip=True) if el else ""


def parse_card(card) -> dict:
    href = card.get("href", "")
    detail_url = "https://dealstream.com" + href if href.startswith("/") else href

    # Name: span inside h2.link-secondary (class is "headline_<post-id>")
    name_el = card.select_one("h2.link-secondary span") or card.select_one("h2.link-secondary")
    name = text(name_el)

    # Location / industry / flags: aside.b > span with title attribute
    location = industry = ""
    flags: list[str] = []
    for sp in card.select("aside.b > span"):
        title = sp.get("title", "")
        value = text(sp)
        if title == "Location":
            location = value
        elif title == "Industry":
            industry = value
        elif title:
            flags.append(title)

    # Description: span class="body_<post-id>" inside a <p>
    desc_el = card.select_one('p span[class^="body_"]') or card.select_one("p")
    description = text(desc_el)

    # Price: first div.h2 containing a currency marker
    price = ""
    for div in card.select("div.h2"):
        t = text(div)
        if any(c in t for c in ("$", "€", "£", "¥", "₹", "R$", "C$", "A$", "CHF")):
            price = t
            break

    # Cash flow: div.h6 starting with "Cash Flow:"
    cash_flow = ""
    for div in card.select("div.h6"):
        t = text(div)
        if "Cash Flow" in t:
            cash_flow = t.replace("Cash Flow:", "").strip()
            break

    return {
        "name": name,
        "price": price,
        "cash_flow": cash_flow,
        "location": location,
        "industry": industry,
        "description": description,
        "detail_url": detail_url,
        "flags": "; ".join(flags),
    }


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("a.card.card-body.mb-3.listingInfo.post")
    return [parse_card(c) for c in cards]


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(2)

    path = Path(args[0])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(2)

    rows = parse_page(path.read_text(encoding="utf-8"))
    as_json = "--json" in args

    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    print(f"{path.name}: {len(rows)} listings\n")
    for i, r in enumerate(rows[:3], 1):
        print(f"--- Row {i} ---")
        for k, v in r.items():
            v = (v[:120] + "…") if len(v) > 120 else v
            print(f"  {k:12s}: {v}")
        print()


if __name__ == "__main__":
    main()
