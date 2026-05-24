#!/usr/bin/env bash
# Collect Dealstream search results across all filtered pages.
#
# Thin wrapper around fetch_pages.py, which uses curl_cffi to impersonate
# Chrome's TLS/JA3 + HTTP/2 fingerprint (far harder for DataDome to flag than
# plain curl). Replays the user's logged-out browser session cookies,
# auto-detects total page count, fetches + parses each page IN MEMORY (no HTML
# saved to disk), writes a date-stamped CSV, and diffs against the prior run to
# flag new listings. Default pacing 3-7s/flip (~5-10 min for a full run).
#
# Usage:
#   get-deals.sh --cookies <file> [--out <dir>] [--start <page>] [--max <n>] \
#                [--min-delay <s>] [--max-delay <s>]
#
# Cookie file: a plain text file containing the raw `cookie:` header value
# from a real browser request to dealstream.com/search (no newline needed).
# The user captures this via DevTools (see SKILL.md Step 3).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required but not found on PATH." >&2
  exit 2
fi

# Forward all arguments to the Python fetcher (handles curl_cffi auto-install,
# Chrome impersonation, page detection, pacing, and DataDome halting).
exec python3 "$SCRIPT_DIR/fetch_pages.py" "$@"
