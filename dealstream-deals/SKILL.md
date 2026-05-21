---
name: dealstream-deals
description: Get a CSV of Dealstream business-for-sale listings using the user's own logged-out browser session. Captures name, asking price, cash flow, location, industry, description, and detail-page URL across all filtered result pages — no Firecrawl, no API key, no paid service. Use this skill when the user explicitly mentions Dealstream and says any of "get deals from dealstream", "download dealstream listings", "export dealstream deals", "pull dealstream deals to a CSV", "dealstream listings to spreadsheet", "aggregate dealstream for my buy-box", or any phrasing implying they want Dealstream search results in a spreadsheet. Do NOT trigger on generic "get me deals" or "download a website" — only on explicit Dealstream references. CLAUDE CODE ONLY — this skill runs shell commands from the user's own machine and cannot work in claude.ai. Walks the user through (0) an environment check, (1) a legal-posture briefing they must acknowledge, (2) applying filters in their browser BEFORE the run, and (3) copying their session cookie via DevTools for a single one-off run.
version: 1.0
---

# dealstream-deals

Gets your filtered Dealstream search results into a clean CSV by replaying your own logged-out browser session. No Firecrawl, no API key, no paid service — just curl + your cookies + a small parser.

> ## ⚠️ DANGER
>
> **Always check the target website's Terms of Service to see if automated data collection is allowed.** Only use this skill for personal use by serious business buyers — **any commercial use is prohibited**. Do not circumvent Dealstream listings at any point: always contact brokers through the source listing on dealstream.com, never around it.
>
> This skill ships with a built-in legal-posture briefing that runs every time you invoke it. You cannot skip it. If you decline the briefing, the skill stops.
>
> By installing and using this skill you accept that you are solely responsible for your compliance with Dealstream's Terms of Service and any applicable law. The author and SMBexcel disclaim all liability for misuse.
>
> **Not affiliated with Dealstream.** This is an independent, unofficial tool. It is not affiliated with, authorized by, endorsed by, sponsored by, or connected to Dealstream, Inc. in any way. "Dealstream" is a trademark of its respective owner, referenced here only descriptively to identify the website the tool works with (nominative fair use).

## When this skill fires

- "get deals from dealstream"
- "download dealstream listings"
- "export dealstream deals to a CSV"
- "pull dealstream deals matching my buy-box"
- Any request to collect deal listings from dealstream.com into a spreadsheet

If the user wants BizQuest, BizBuySell, or another broker site, this skill does NOT apply — Akamai Bot Manager (BizQuest, BizBuySell) requires a real browser, not cookie replay. Tell them so and stop.

## What this skill does NOT do

- Does not log the user into Dealstream (logged-out is the legal posture this skill is built for)
- Does not submit inquiries to brokers
- Does not republish, host, or redistribute the collected data
- Does not run on a schedule — it's a manual one-off triggered by the user

## Step 0 — Environment check (do this FIRST, before anything else)

This skill only works in **Claude Code** (or any agent with a real shell that can run `curl` from the user's own machine and write to their local disk). Before doing anything else, confirm you have shell access via the Bash tool with outbound network access.

If you do NOT have that — e.g. you are running inside **claude.ai**, Cowork, or any chat environment without local code execution — STOP immediately, show the user this, and end:

> ⚠️ **This skill needs Claude Code — it can't run here.**
>
> dealstream-deals runs `curl` from your own computer to collect listings. That only works in Claude Code (the CLI), where commands execute on your machine using your own network session. It cannot work in claude.ai because that environment has no shell and no access to your browser session — the request would come from Anthropic's servers, get a mismatched IP, and be blocked.
>
> To use this skill: install Claude Code, drop this skill into `~/.claude/skills/dealstream-deals/`, and ask again there. Setup: https://github.com/SMBexcel/skills

Do not attempt to proceed, simulate the collection, or paste-and-parse HTML in a non-Code environment. Just stop.

## Step 1 — Brief the user on legal posture

Once the environment check passes, show the user this verbatim and wait for a yes/no:

> **Quick legal posture briefing — Dealstream**
>
> This skill is built for lightweight personal use to extract publicly available data from a website. Use this skill at your own risk. Consider making an account at Dealstream or contacting them for a data license if available.
>
> **Lower-risk, personal use:**
> - Personal deal-sourcing for your own SMB search
> - Sharing a few interesting deals manually with a small private group (e.g. Slack with 3 fellow searchers)
> - Always clicking through to the source listing on dealstream.com to actually contact the broker
>
> **Danger zone — do not:**
> - Republishing Dealstream's listing descriptions verbatim on a public website
> - Selling the CSV as a product or as part of a paid service
> - Automating any contact-form submissions to Dealstream's brokers
>
> Personal use = lower practical risk, but not zero. Commercial use = danger zone, consider contacting Dealstream for a data license.
>
> **You must also agree:** you will **never circumvent Dealstream's brokers or listing pages**. You will always go through the official listing on dealstream.com to contact a broker, and will never use this data to route around the broker or Dealstream.
>
> Do you understand and agree to the above, including the no-circumvention commitment? Reply `yes` to proceed.

If the user does not reply yes, stop. Do not proceed.

## Step 2 — Guide the user to filter in the browser

Filters live in the user's session cookie, not in the URL, so the user must apply filters in their browser BEFORE we capture the cookie. Show:

> Apply your filters in your browser first — they'll travel with your session cookie. We can't filter after the fact without re-running.
>
> 1. Open https://dealstream.com/search in your browser
>    **Important: do NOT log in.** Stay as a Site Visitor.
> 2. In the category selector, choose **"All Businesses"** (or whichever business category you want — Manufacturing, Healthcare, etc.)
> 3. Click into the filter panel, then:
>    - **Country / Geography** → pick United States (or your target)
>    - **Minimum Cash Flow** → enter your floor (e.g. `500000` for $500K SDE)
>    - Any other filters that matter to your buy-box (industry, asking range, etc.)
> 4. Apply / submit the filters. Wait for results to reload.
> 5. Scroll to the bottom of the results page. Note the **total number of pages** (e.g. "Page 1 of 76"). You don't have to tell me — the run auto-detects this from the page.
>
> Reply `ready` when filters are applied and the results page is showing.

Wait for the user to confirm.

## Step 3 — Capture the session cookie

Show:

> Now grab your session cookie so the tool can replay your filtered session and pass DataDome's bot check:
>
> 1. With the filtered results page open, press **F12** (or right-click → Inspect) to open DevTools
> 2. Click the **Network** tab. Make sure recording is on (the red circle).
> 3. Click any page number in the results pagination — e.g. page 2 — to trigger a new request
> 4. In the Network list, click the request whose name starts with `search?page=` (it should be the first or second entry, type "Doc")
> 5. In the right pane, scroll to **Request Headers** (NOT Response Headers)
> 6. Find the line that starts with `cookie:` — copy the **entire value** after `cookie:` (it's a long string of `key=value; key=value; ...`)
> 7. Paste it as your next reply.

Wait for the user to paste the cookie string.

Save the cookie to a user-CWD location like `./dealstream-export/cookies.txt` so the user can see and rotate the file.

## Step 4 — Run it

The skill bundles three scripts in `~/.claude/skills/dealstream-deals/scripts/`:

- **`get-deals.sh`** — thin wrapper; checks for `python3` and forwards all args to `fetch_pages.py`. This is the documented entry point.
- **`fetch_pages.py`** — the whole pipeline in one pass: fetches each page using **`curl_cffi`** (impersonates Chrome's TLS/JA3 + HTTP/2 fingerprint — plain curl/requests have an obvious non-browser fingerprint DataDome flags on sight), parses it **in memory**, dedupes, and writes a dated CSV. **No HTML is saved to disk** — nothing is left on the user's machine except the CSV. Auto-installs `curl_cffi` + `beautifulsoup4` on first run.
- **`parse_dealstream.py`** — the parser module `fetch_pages.py` imports; extracts name, price, cash_flow, location, industry, description, detail_url, flags from one page's HTML.

It runs as a single command:

```bash
SKILL_DIR=~/.claude/skills/dealstream-deals
mkdir -p ./dealstream-export
# (save the user's cookie to ./dealstream-export/cookies.txt first — see Step 3)

bash "$SKILL_DIR/scripts/get-deals.sh" --cookies ./dealstream-export/cookies.txt --out ./dealstream-export
```

`fetch_pages.py` will:
1. Fetch page 1, parse total page count from pagination
2. Loop remaining pages with human-shaped pacing (default 3-7s per flip, ~1 in 10 a slightly longer pause) — a ~76-page run lands in roughly 5-10 minutes
3. Parse each page in memory and dedupe by `detail_url` (no HTML written to disk)
4. Halt if a response is <5KB or contains `captcha-delivery` (DataDome challenge → session restricted → user needs to refresh cookies); writes a PARTIAL CSV with whatever was collected
5. Write `./dealstream-export/dealstream_deals_YYYY-MM-DD.csv` (date-stamped)
6. **Diff against the most recent prior dated CSV** in the folder: adds an `is_new` column and writes `dealstream_new_YYYY-MM-DD.csv` containing only listings not seen last run

**Pacing / detection tradeoff (tell the user if relevant):**
- Default 3-7s pacing keeps a full run in the 5-10 min range. The Chrome TLS fingerprint (curl_cffi) is now the main protection, so timing matters a bit less than it used to.
- If they get challenged or want to be more cautious, suggest `--min-delay 8 --max-delay 20`.
- Running this **may still get the user's session temporarily restricted by Dealstream** — DataDome also weighs volume and lack of JS/asset loading, not just fingerprint and timing. A restriction usually clears within hours and is tied to the IP/cookie. Do not promise it's undetectable.
- They only need DevTools open briefly to copy the cookie (Step 3), then can close it.

## Step 5 — Hand off and remind

After the CSV is written, `fetch_pages.py` prints the path, total count, and (if a prior dated CSV existed) the number of new listings. Relay that to the user:

1. Tell the user the absolute path to the dated CSV and the total deal count
2. If the diff ran, tell them how many are new since the last run, and the path to `dealstream_new_YYYY-MM-DD.csv`
3. Show the first 3 rows as a sanity check
4. Remind them of the legal lane AND to keep prior CSVs:

> CSV is at `<absolute path>` with X deals. (Y new since <prior date>, listed in `dealstream_new_<date>.csv`.)
>
> Keep the old dated CSVs in this folder — the next run automatically diffs against the most recent one to flag new listings. If you delete them, the next run can't tell you what's new.
>
> Reminder: this is for **your personal deal-sourcing**. Don't post it publicly, don't sell it, don't republish the descriptions verbatim, and contact each broker through Dealstream's own site (the `detail_url` column) — never around it.

## Failure modes and how to handle them

**Page 1 returns <5KB or contains `captcha-delivery`**
→ The cookie is dead OR the user's session is restricted. Tell them to refresh their dealstream.com tab in the browser, then re-copy the cookie. Loop back to Step 3. If they were just restricted, they may need to wait a few hours or use a different network.

**Page count auto-detect fails (no pagination found)**
→ The user probably has only 1 page of results. Proceed with N=1.

**DataDome challenges mid-run**
→ `fetch_pages.py` stops and writes a PARTIAL dated CSV with whatever it collected. Tell the user it's partial, to refresh their cookie, wait a bit, and re-run later. (There's no HTML cache to resume from — a re-run re-fetches from page 1. Runs are only ~5-10 min, so this is fine.)

**Parser returns 0 listings on a page**
→ Could be the last partial page (normal) OR Dealstream changed their HTML structure (parser broken). Check by viewing the page in browser — if listings are visible there but not parsed, the CSS selectors in `parse_dealstream.py` need updating.

**Cookies have weird characters that break shell quoting**
→ Already handled — `fetch_pages.py` reads cookies from a file (newlines stripped), never from the command line, so `$` and `;` in the cookie can't break anything. Always save the cookie to `./dealstream-export/cookies.txt` and pass `--cookies` that path.

## Distribution notes (for the skill author, not the end user)

This skill is designed to be packaged and shared with other SMB searchers. To distribute:

- Bundle the entire `~/.claude/skills/dealstream-deals/` directory
- Recipients install by copying it to their own `~/.claude/skills/` — **Claude Code only**, it cannot run in claude.ai
- Dependencies: `python3` (does the fetching + parsing), plus two pip packages auto-installed on first run — `curl_cffi` (Chrome TLS impersonation) and `beautifulsoup4` (HTML parsing). No `curl` binary needed anymore.
- License under MIT (see `LICENSE` in this folder)
- See `~/.claude/skills/dealstream-deals/README.md` for end-user install instructions

Update cadence: if Dealstream changes their search-page HTML, update the CSS selectors in `scripts/parse_dealstream.py`. Spot-check quarterly.

---

## Changelog

- **1.0** — Initial release. Cookie-replay collection via curl_cffi (Chrome TLS/JA3 + HTTP/2 impersonation), in-memory parsing (no HTML written to disk), date-stamped CSV output, automatic diff against the prior run to flag new listings (`is_new` column + new-only CSV), auto-detect page count, human-shaped pacing (3-7s default, tunable), DataDome challenge halting with partial-CSV save, claude.ai environment guard. Dependencies (`curl_cffi`, `beautifulsoup4`) auto-install on first run.
