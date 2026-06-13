# Josh — Lead Qualification & Instagram Outreach

Finds and qualifies blue-collar service businesses (roofing, plumbing, HVAC,
electrical, landscaping, tree service, painting, pressure washing, concrete,
junk removal, flooring, fencing, general contractors, mobile detailing, towing)
that are likely to need a new website — then optionally DMs them.

## Two pipelines

| File | What it does |
|------|--------------|
| `qualify.py` | **Search + qualify.** Pulls businesses from every configured platform, audits their websites, scores how badly they need a new site, prints a prioritized list, and writes `qualified_leads.csv`. |
| `main.py` | **Outreach.** Sends personalized Instagram cold DMs (existing tool). |

Supporting modules: `leads.py` (lead model, website auditing, scoring) and
`collectors.py` (one self-disabling collector per platform).

## Quick start

```bash
pip install -r requirements.txt          # instagrapi only needed for IG
python qualify.py --areas "Austin, TX;Dallas, TX" --categories roofing,plumbing
```

The core qualification engine (website audit + scoring + CSV/report) runs on the
Python standard library alone. Each data source is **opt-in** — set the relevant
credentials and it turns on; leave them unset and it self-disables with a log
line. With nothing configured, a run reports **"No new leads found."**

## Configuring data sources (env vars)

| Source | Variable(s) | Notes |
|--------|-------------|-------|
| Google Maps | `GOOGLE_MAPS_API_KEY` | Places Text Search + Details. Most reliable, ToS-friendly. |
| Local directories | `YELP_API_KEY` | Yelp Fusion. Add other directories in `collectors.py`. |
| Instagram | `IG_USERNAME`, `IG_PASSWORD` | Needs `instagrapi`. Pulls accounts from hashtags. |
| Facebook | `FACEBOOK_PROVIDER_KEY` | Stub — no open business-search API; wire a Graph API token or licensed data provider in `collect_facebook`. |

```bash
export GOOGLE_MAPS_API_KEY=...
export TARGET_AREAS="Austin, TX;San Antonio, TX"   # optional default for --areas
python qualify.py
```

## How leads are scored (0–100, higher = better prospect)

| Signal | Points | Status |
|--------|-------:|--------|
| No website at all | +60 | `none` |
| Website unreachable / dead | +55 | `unreachable` |
| Not mobile-responsive (no viewport) | +25 | contributes to `poor`/`dated` |
| Outdated design markers (tables, `<font>`, FrontPage, etc.) | +20 | |
| No HTTPS | +10 | |
| Missing key pages (about/contact/services) | +5 each | |
| Low online presence (few reviews + small following) | +10 | |
| **Proven demand but weak web** (25+ reviews + no/poor site) | +15 | flagged **HIGH-VALUE** |

Priority: **HIGH** ≥ 70 (or high-value flag) · **MEDIUM** ≥ 40 · **LOW** otherwise.

Output columns: priority, score, name, category, source, website status,
Instagram, phone, email, website, city, state, followers, reviews, rating, flags.
