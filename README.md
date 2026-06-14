# Josh — Blue-Collar Lead Gen + Outreach

Finds and qualifies blue-collar service businesses (roofers, plumbers,
electricians, HVAC, landscapers, tree services, painters, pressure washing,
concrete, junk removal, flooring, fencing, general contractors, mobile
detailers, towing), then optionally cold-DMs them on Instagram selling website
services.

There are two stages:

| Stage | Entry point | What it does |
|-------|-------------|--------------|
| **1. Find & qualify leads** | `find_leads.py` | Search platforms → collect contacts → audit websites → score & prioritize |
| **2. Outreach** | `main.py` | Send personalized cold DMs on Instagram |

## 1. Find & qualify leads

```bash
python find_leads.py --categories roofing,plumbing,hvac \
                     --locations "Austin, TX" "Dallas, TX"
```

For each business it collects: name, Instagram handle, phone, email, website,
city/state, category, follower count, review count, and Google rating. It then:

- **Audits each website** (`website_audit.py`): reachability, HTTPS, mobile
  responsiveness, copyright freshness, missing key pages (contact/services/
  about/reviews), and outdated tech (Flash, table layouts, free Wix/Weebly
  templates, ancient jQuery, thin/parked content).
- **Scores each lead 0–100** on how likely it needs a new website — weighting
  website weakness heavily and boosting businesses with proven demand (lots of
  reviews / followers) but a weak web presence.
- **Flags high-priority leads**: `NO WEBSITE`, `WEBSITE BROKEN`,
  `VERY POOR SITE`, `HIGH REVIEWS + WEAK WEB`, `STRONG IG + WEAK WEB`,
  `NOT MOBILE-FRIENDLY`.

Output: a prioritized console report plus `qualified_leads.csv`.

### Configuring sources

Each source is enabled by its credentials (set as environment variables).
Missing credentials are skipped with a log message — the pipeline still runs.

| Source | Env var(s) | Status |
|--------|-----------|--------|
| Instagram | `IG_USERNAME`, `IG_PASSWORD` | Implemented (instagrapi) |
| Google Maps | `GOOGLE_MAPS_API_KEY` | Implemented (Places API) |
| Facebook | `FB_ACCESS_TOKEN` | Stub — wire your approved Graph API flow |
| Directories (Yelp, etc.) | `YELP_API_KEY` | Stub — add Yelp Fusion / others |

Instagram and Google Maps alone produce fully-qualified leads. The Facebook and
directory adapters are documented stubs ready to be filled in (`lead_sources.py`)
— direct scraping of those platforms violates their ToS, so they expect an
approved API flow.

### Useful flags

- `--categories` comma-separated industry keys (default: all)
- `--locations "City, ST" ...` target areas (required for Maps/directory search)
- `--no-audit` skip live website fetches (faster; still scores no-website leads)
- `--out PATH` output CSV (default `qualified_leads.csv`)
- `--top N` how many leads to print (default 25)

## 2. Outreach (`main.py`)

Sends rate-limited, personalized cold DMs from the hashtag-scraped accounts.
See the settings block at the top of `main.py` (daily limits, delays, hashtags).

## Install

```bash
pip install -r requirements.txt
```
