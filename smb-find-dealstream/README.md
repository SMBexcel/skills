# smb-find-dealstream

**Get filtered Dealstream listings into a CSV — guided, legally-briefed, no paid tools.**

> Apply filters in your browser. Hand over your session cookie. Get a clean CSV of every matching deal. The skill handles the dance with DataDome and the parsing.

`v1.0` · MIT · by [David Schreiber](https://www.smbexcel.com)

---

> ## ⚠️ DANGER
>
> **Always check the target website's Terms of Service to see if automated data collection is allowed.** Only use this skill for personal use by serious business buyers — **any commercial use is prohibited**. Do not circumvent Dealstream listings at any point: always contact brokers through the source listing on dealstream.com, never around it.
>
> This skill ships with a built-in legal-posture briefing that runs every time you invoke it. You cannot skip it. If you decline the briefing, the skill stops.
>
> By installing and using this skill you accept that you are solely responsible for your compliance with Dealstream's Terms of Service and any applicable law. The author and SMBexcel disclaim all liability for misuse.
>
> **Not affiliated with Dealstream.** This is an independent, unofficial tool. It is not affiliated with, authorized by, endorsed by, sponsored by, or connected to Dealstream, Inc. in any way. "Dealstream" is a trademark of its respective owner, referenced here only descriptively to identify the website the tool works with (nominative fair use).

---

> ## 🖥️ Claude Code only
>
> **This skill does not work in claude.ai.** It runs `curl` from your own computer using your own browser session — that only works in Claude Code (the CLI). In claude.ai there's no shell and no access to your network session, so the request would come from Anthropic's servers, get a mismatched IP, and be blocked. The skill detects a non-Code environment on first touch and tells you to switch to Claude Code.

---

## The problem

[Dealstream.com](https://dealstream.com) lists thousands of businesses for sale, but if you want a side-by-side spreadsheet of every deal matching your buy-box, you're scrolling 76 paginated result pages by hand. There's no export button. No public API. Filter state lives in a session cookie, so URL-based pagination won't reproduce it. And DataDome bot protection blocks any naive request that doesn't look like a real browser.

Paid tools (Firecrawl, Apify) work, but cost credits per page and shift the legal exposure to a third party using *their* infrastructure to extract *Dealstream's* data — a posture that's harder to defend than what a real human visitor is allowed to do.

## What this skill does

Walks you through a one-time, browser-session-backed run over your already-filtered Dealstream search results. The session cookie you paste comes from your real, logged-out browser — DataDome already cleared you, so the tool just replays your access for the pages your filter selected.

Output: a CSV with one row per unique deal, including:

- **name** — the listing title
- **price** — asking price (or blank for "Make Offer" deals, which is ~33% of listings)
- **cash_flow** — seller's discretionary earnings / EBITDA as shown on the listing card
- **location** — city/state for US deals, country for international
- **industry** — Dealstream's category tag
- **description** — the ~1-paragraph preview shown on the search result card (no need to click into each one)
- **detail_url** — direct link back to the source listing on dealstream.com
- **flags** — Dealstream's badges: "Real Estate Included", "Management Will Stay", "Seller Financing", "New Arrival", "Relocatable"

---

## What you get

- **Cookie-replay collection.** No paid Firecrawl/Apify credits. Free.
- **Chrome TLS fingerprint.** Uses `curl_cffi` to impersonate Chrome's TLS/JA3 + HTTP/2 signature, instead of plain curl (which has an obvious non-browser fingerprint that DataDome flags on sight). The biggest single anti-detection lever — though still not a guarantee (see Failure modes).
- **Guided flow.** Environment check → legal briefing → browser filters → cookie capture → run → CSV. Claude walks you through it.
- **Filter inheritance via cookies.** Whatever you filtered in the browser (geography, min cash flow, industry, asking range) carries through automatically — no URL params needed.
- **Auto page-count detection.** The tool reads pagination from page 1 and loops the rest. No guessing.
- **DataDome challenge detection.** If the session goes stale mid-run, the tool halts cleanly, saves a partial CSV, and tells you to refresh cookies. No silent failures.
- **Human-shaped pacing** between requests (default 3-7s, occasional slightly longer pause). A full run lands in ~5-10 minutes. Tune with `--min-delay` / `--max-delay`. No pacing makes automated collection undetectable (see Failure modes).
- **No HTML saved to disk.** Pages are parsed in memory and discarded — the only file written is the CSV. Nothing bloats your machine, no copies of listing HTML left lying around.
- **Date-stamped output.** Each run writes `dealstream_deals_YYYY-MM-DD.csv`, so runs never overwrite each other.
- **New-listing diff.** Each run compares against your most recent prior dated CSV, adds an `is_new` column, and writes `dealstream_new_YYYY-MM-DD.csv` with just the listings that weren't there last time. Keep your old dated CSVs in the folder for this to work.

---

## Install

> Reminder: **Claude Code only.** Installing this in claude.ai will not work — see the note at the top.

### Quickest path — direct zip download

1. **Download:** [dealstream-deals-v1.0.zip](https://github.com/SMBexcel/skills/raw/main/smb-find-dealstream/dealstream-deals-v1.0.zip) (committed in this folder — single click, no Release page needed).
2. **Unzip** — you'll get a `dealstream-deals/` folder (legacy name in the v1.0 archive) containing `SKILL.md` and `scripts/`. Rename it to `smb-find-dealstream/`.
3. **Drop the renamed folder into your Claude Code skills directory:**
   - `~/.claude/skills/smb-find-dealstream/`
4. **Smoke test** — in any new Claude Code chat say: *"get deals from dealstream for my buy-box"*. The skill will start with the environment check and legal briefing.

### Alternative — clone the whole repo

```bash
git clone https://github.com/SMBexcel/skills.git
cp -R skills/smb-find-dealstream ~/.claude/skills/
```

### Alternative — copy just the files

If you'd rather not download a zip or clone, you can view each file directly in this folder ([`SKILL.md`](./SKILL.md), [`scripts/`](./scripts)) and save them into `~/.claude/skills/smb-find-dealstream/` manually.

---

## Requirements

- **Claude Code** (the CLI) — this skill cannot run in claude.ai
- **macOS or Linux** with `bash` and `python3` (already installed on virtually every Mac)
- **A web browser** with DevTools (Chrome, Firefox, Safari, Edge — anything)
- `curl_cffi` (Chrome TLS impersonation) + `beautifulsoup4` + `lxml` — all auto-installed via `pip3 install --user` on first run if missing

No API keys, no external accounts, no paid services.

---

## How to use it

In any new Claude Code chat:

```
> get deals from dealstream for my buy-box
```

The skill walks you through:

0. **Environment check** — confirms you're in Claude Code. If not, it stops and tells you to switch.
1. **Legal briefing** — a short summary of what's defensible and what isn't, plus a no-circumvention commitment. You acknowledge with `yes`.
2. **Apply filters in your browser** — open dealstream.com/search (logged out!), click All Businesses → Country → Min Cash Flow, and apply.
3. **Copy the session cookie** — F12 → Network tab → click any page link → copy the `cookie:` request header.
4. **Run** — one command; auto-detects total pages, fetches + parses each in memory (no HTML saved), pacing ~5-10 min total, halts on DataDome challenge.
5. **CSV hand-off** — Claude reports the path, total count, how many are new since your last run, and a 3-row sanity check.

Output (in whatever directory you ran the chat from):
- `./dealstream-export/dealstream_deals_YYYY-MM-DD.csv` — all deals, with an `is_new` column
- `./dealstream-export/dealstream_new_YYYY-MM-DD.csv` — only listings new since your previous run (if a prior dated CSV is present)

**Keep your old dated CSVs in the folder** — the new-listing diff compares against the most recent one. Delete them and the next run can't tell you what's new.

---

## Legal posture (the short version)

This skill is built for lightweight personal use to extract publicly available data from a website. **Use this skill at your own risk.** Consider making an account at Dealstream or contacting them for a data license if available.

**Lower-risk, personal use:**
- Personal deal-sourcing for your own SMB search
- Sharing a few interesting deals manually with a small private group
- Using the CSV as a research input to your acquisition pipeline

**Danger zone — do not:**
- Republish the descriptions verbatim on a public website
- Sell the CSV as a product or as part of a paid service
- Automate any contact-form submissions

If you want to do anything commercial with Dealstream data, the right path is to email `legal@dealstream.com` and ask about a data license, not run this skill at scale.

The full legal briefing is shown by the skill at runtime — you can't skip it.

---

## Failure modes

- **Cookie expired between copy and run** → DataDome challenge on page 1; skill halts and tells you to refresh your browser tab and re-copy. Sessions last a few hours.
- **DataDome challenges you mid-run** (e.g. on page 40 of 76) → skill stops and writes a PARTIAL dated CSV with whatever it collected. Refresh your cookie, wait a bit, and re-run later (a re-run starts fresh — runs are only ~5-10 min).
- **Parser returns 0 listings on a page** → either the last partial page (normal) or Dealstream changed their markup. Open the page in your browser; if listings are visible there, the CSS selectors in `scripts/parse_dealstream.py` need updating. Open an issue on the SMBexcel/skills repo.
- **Filters didn't apply** → you'll see worldwide results instead of filtered ones. Re-do Step 2 of the flow.
- **CSV missing prices on ~33% of rows** → not a bug. Dealstream hides "Make Offer" listings' prices. Cash flow is still shown.
- **Tried to run it in claude.ai** → it won't work; the skill stops at the environment check. Use Claude Code.
- **Your Dealstream session got restricted / challenged** → DataDome fingerprints the connection (TLS signature, request cadence, lack of asset loading). The Chrome TLS impersonation closes the biggest tell, but volume and lack of JS/asset loading still register. A restriction is usually temporary (hours), tied to your IP/cookie, and often clears after you solve a CAPTCHA on a normal visit. To lower the odds: use a slower pace (`--min-delay 8 --max-delay 20`), don't re-run back-to-back, and close DevTools after copying your cookie. No pacing makes automated collection undetectable — stay low-volume and personal-use.

---

## Newsletter

The build notes, the post-Bright Data legal background, and the next skill before it lands here:

**→ [www.smbexcel.com](https://www.smbexcel.com)**

---

## Changelog

- **1.0** — Initial release. Cookie-replay collection via curl_cffi (Chrome TLS/JA3 + HTTP/2 impersonation), in-memory parsing (no HTML written to disk), date-stamped CSV output, automatic diff against the prior run to flag new listings (`is_new` column + new-only CSV), auto-detect page count, human-shaped pacing (3-7s default, tunable), DataDome challenge halting with partial-CSV save, claude.ai environment guard. Dependencies (`curl_cffi`, `beautifulsoup4`) auto-install on first run.

---

_MIT licensed. © 2026 David Schreiber._
