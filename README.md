# Josh — Lead Finder + Instagram Outreach

Tooling for selling websites to blue-collar service businesses (roofers,
plumbers, electricians, HVAC, landscapers, tree services, painters, pressure
washing, concrete, junk removal, flooring, fencing, general contractors,
mobile detailers, towing).

There are two stages:

| Stage | File | What it does |
|-------|------|--------------|
| **1. Find & qualify** | `lead_finder.py` | Search platforms, audit websites, score & prioritize leads → `leads.csv` |
| **2. Outreach** | `main.py` | Send personalized cold DMs on Instagram |

---

## 1. Lead Finder

Searches for businesses, audits their websites, and scores each on how likely
they are to need a **new website** — then prints a prioritized list and writes
`leads.csv`.

```bash
pip install -r requirements.txt
export GOOGLE_MAPS_API_KEY=...          # Places API enabled

python lead_finder.py \
    --categories roofers plumbers "HVAC contractors" \
    --locations "Austin, TX" "Round Rock, TX" \
    --max 20 --out leads.csv
```

**What it collects per lead:** name, phone, email, website, Instagram username,
city, state, category, follower count, review count, Google rating.

**Website audit** (`website_audit.py`, no API key needed) scores each site
0–100 on: HTTPS, mobile responsiveness, copyright freshness, presence of key
pages (contact / services / about / quote), and outdated markup
(table layouts, `<font>`, Flash).

**Qualification score** (`lead.py`) is 0–100, higher = better lead. The
strongest leads are busy businesses (many reviews, good rating) with **no
website or a poor one**. Flags include `NO_WEBSITE`, `VERY_POOR_DESIGN`,
`OUTDATED_SITE`, `NOT_MOBILE`, `MISSING_PAGES`, and
`HIGH_DEMAND_WEAK_WEB`. Priority is HIGH (≥70), MEDIUM (≥45), or LOW.

### Sources

| Source | Status | Needs |
|--------|--------|-------|
| Google Maps (Places API) | ✅ implemented | `GOOGLE_MAPS_API_KEY` |
| Instagram enrichment | ✅ optional | `IG_USERNAME`, `IG_PASSWORD` |
| Facebook / Yelp / directories | ➕ pluggable | no clean public API — add a function in `sources.py` |

If no source is configured the run reports **"No leads found"** rather than
inventing data.

---

## 2. Instagram DM Outreach

```bash
export IG_USERNAME=...
export IG_PASSWORD=...
python main.py
```

Scrapes trade hashtags and sends personalized cold DMs (≤30/day by default),
logging every contact to `dm_log.csv`. See the settings block at the top of
`main.py`. Industry-specific message copy lives in `industries.py`.

> **Note:** Automated DMing and scraping can violate platform Terms of
> Service. Use responsibly, stay within rate limits, and prefer official APIs.
