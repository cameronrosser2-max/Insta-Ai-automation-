# Lead-Gen Routine — Run Status

**Last run:** 2026-06-20 (scheduled routine)
**Result:** ❌ No leads found — the routine cannot collect or qualify leads as currently configured.

This file is overwritten on each scheduled run, so it always reflects the latest status.

---

## What the routine was asked to do

Search Instagram, Google Maps, Facebook, and local directories for blue-collar service
businesses (roofers, plumbers, electricians, HVAC, landscapers, tree services, painters,
pressure washing, concrete, junk removal, flooring, fencing, general contractors, mobile
detailers, towing), collect their contact details, evaluate their websites, score how
likely they need a new site, and output a prioritized lead list.

## Why no leads were produced

The blockers below are all configuration/infrastructure gaps, not transient errors:

1. **No target geography is configured.** Nothing in the repo or environment specifies
   *which cities/states* to target. The task requires "specified geographic areas," but
   none are defined anywhere (`main.py` hashtags have no location; no config file; no env var).

2. **No platform credentials.** `IG_USERNAME` / `IG_PASSWORD` are not set in the
   environment. There are no Google Maps, Facebook, or directory API keys either.

3. **The scraping dependency isn't installed.** `instagrapi` (the only dependency in
   `requirements.txt`) is not present in this environment, so even the existing script
   cannot run.

4. **The code doesn't implement this task.** `main.py` only scrapes Instagram *hashtags*
   and sends cold DMs. It has **no** Google Maps / Facebook / directory collection, and
   **no** website-quality evaluation or lead-scoring logic — which is the core of what
   was requested. `industries.py` is also still a stub (`INDUSTRIES = {}`).

5. **Web search is not a substitute.** General web search was verified working, but it
   surfaces businesses that *already* rank well and have polished websites — the exact
   inverse of a qualified lead (a business that *needs* a website). Identifying
   no-website / weak-web-presence businesses requires the platform listing data
   (e.g. Google Maps "website" field being empty) that the points above would provide.

## What's needed to make this routine actually produce leads

Provide the following and the routine can be built out / run:

- [ ] **Target areas** — list of cities/states (e.g. "Charlotte NC, Raleigh NC, Atlanta GA").
- [ ] **A data source with API access**, ideally one of:
  - Google Places / Google Maps Platform API key (best for finding businesses with no
    website — the API exposes whether a listing has a website), or
  - A lead-data provider (e.g. a Places-based scraper service) API key.
- [ ] **Instagram credentials** (`IG_USERNAME` / `IG_PASSWORD`) if Instagram sourcing is
  wanted — and confirmation on the cold-DM compliance approach (Instagram ToS / rate limits).
- [ ] **Decision on scope:** should I build the lead *qualification + scoring* pipeline
  (collect → check website quality → score → prioritized CSV), separate from the existing
  DM sender? This is a sizable feature and I held off rather than guess.

Reply in a session (or open an issue) with the target areas + which data source you want,
and I'll implement the collection + website-scoring + prioritized-output pipeline.
