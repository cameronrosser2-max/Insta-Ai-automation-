#!/usr/bin/env python3
"""
Lead Qualifier — evaluates and prioritizes blue-collar service business leads.

Given a list of businesses collected from any source (Instagram, Google Maps,
Facebook, local directories), this module:

  1. Evaluates each lead's website quality and design (reachability, HTTPS,
     mobile responsiveness, outdated-design signals, missing key pages).
  2. Scores each lead 0–100 on how likely they NEED a new website.
  3. Flags high-priority leads (no website, very poor design, or a strong
     offline presence — high reviews/followers — paired with a weak web one).
  4. Outputs a prioritized list (console table + CSV).

It needs no platform credentials. Feed it leads as dicts or via a CSV with the
LEAD_FIELDS columns below.

Usage:
    python lead_qualifier.py                 # runs a built-in demo
    python lead_qualifier.py leads.csv       # qualifies leads from a CSV
    python lead_qualifier.py leads.csv out.csv

Programmatic:
    from lead_qualifier import qualify_leads, print_report, write_report
    qualified = qualify_leads(my_list_of_dicts)
"""

import csv
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

from industries import INDUSTRIES, detect_industry

# Fields collected per business (the schema shared across every lead source).
LEAD_FIELDS = [
    "name", "instagram_username", "phone", "email", "website",
    "city", "state", "category", "follower_count", "review_count",
    "google_rating", "source",
]

# Output columns added by qualification.
QUALIFIED_FIELDS = LEAD_FIELDS + [
    "website_status", "needs_site_score", "priority", "reasons",
]

REQUEST_TIMEOUT = 12
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# A lead is "high priority" at or above this score.
HIGH_PRIORITY_THRESHOLD = 70
# A review count this high signals a real, established business.
STRONG_REVIEW_COUNT = 25
# A follower count this high signals real social proof.
STRONG_FOLLOWER_COUNT = 1000


# ── Website evaluation ──────────────────────────────────────────────────────

def _to_int(value, default=0):
    """Best-effort parse of counts like '1,234' or '2.3k' into an int."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip().lower().replace(",", "")
    try:
        if s.endswith("k"):
            return int(float(s[:-1]) * 1_000)
        if s.endswith("m"):
            return int(float(s[:-1]) * 1_000_000)
        return int(float(s))
    except ValueError:
        return default


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def evaluate_website(url: str) -> dict:
    """
    Fetch and assess a website. Returns a dict describing its condition:
        reachable, https, mobile_responsive, outdated, missing_pages,
        status (human label), and detail flags/notes.
    Never raises — network problems are captured as findings.
    """
    result = {
        "url": url,
        "has_website": bool(url),
        "reachable": False,
        "https": False,
        "mobile_responsive": False,
        "outdated": False,
        "missing_pages": [],
        "status": "no website",
        "notes": [],
    }

    if not url:
        return result

    if requests is None:
        result["status"] = "unverified (requests not installed)"
        result["notes"].append("install 'requests' to enable live checks")
        return result

    target = _normalize_url(url)
    try:
        resp = requests.get(
            target,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
    except requests.exceptions.SSLError:
        result["notes"].append("SSL/certificate error")
        result["status"] = "broken/unreachable"
        return result
    except requests.exceptions.RequestException:
        result["status"] = "broken/unreachable"
        result["notes"].append("did not respond")
        return result

    if resp.status_code >= 400:
        result["status"] = "broken/unreachable"
        result["notes"].append(f"HTTP {resp.status_code}")
        return result

    result["reachable"] = True
    final_url = resp.url
    result["https"] = urlparse(final_url).scheme == "https"
    if not result["https"]:
        result["notes"].append("no HTTPS")

    html = resp.text or ""
    low = html.lower()

    # Mobile responsiveness — the single biggest "needs a rebuild" signal.
    result["mobile_responsive"] = 'name="viewport"' in low or "name='viewport'" in low
    if not result["mobile_responsive"]:
        result["notes"].append("not mobile-responsive (no viewport)")

    # Outdated-design signals.
    outdated_signals = []
    if "<frameset" in low or "<frame " in low:
        outdated_signals.append("frames")
    if re.search(r"<table[^>]*(?:role=[\"']?presentation|cellpadding|cellspacing)", low):
        outdated_signals.append("table-based layout")
    if ".swf" in low or "application/x-shockwave-flash" in low:
        outdated_signals.append("Flash content")
    if "<marquee" in low or "<blink" in low or "<font" in low:
        outdated_signals.append("deprecated HTML tags")
    if "frontpage" in low or 'generator" content="microsoft' in low:
        outdated_signals.append("legacy page builder")
    # Stale copyright year (2+ years old).
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)[^\d]{0,12}(20\d{2})", low)]
    if years:
        newest = max(years)
        if newest <= datetime.now().year - 2:
            outdated_signals.append(f"copyright {newest} (stale)")
    if not re.search(r"<!doctype html>", low):
        outdated_signals.append("legacy/no HTML5 doctype")

    result["outdated"] = bool(outdated_signals)
    result["notes"].extend(outdated_signals)

    # Missing key pages — look for links/anchors to the essentials.
    expected = {
        "contact": ["contact", "get a quote", "request", "estimate"],
        "about": ["about", "our story", "who we are"],
        "services": ["service", "what we do", "offerings"],
    }
    missing = []
    for page, terms in expected.items():
        if not any(t in low for t in terms):
            missing.append(page)
    result["missing_pages"] = missing
    if missing:
        result["notes"].append("missing pages: " + ", ".join(missing))

    # Thin/placeholder site.
    if len(html) < 1500:
        result["notes"].append("very thin content")
        result["outdated"] = True

    # Human-readable status label.
    if not result["mobile_responsive"] or result["outdated"]:
        result["status"] = "outdated / poor design"
    elif missing:
        result["status"] = "live but incomplete"
    else:
        result["status"] = "live / decent"

    return result


# ── Scoring ─────────────────────────────────────────────────────────────────

def score_lead(lead: dict, site: dict) -> dict:
    """
    Score a lead 0–100 on likelihood it needs a new website.
    Higher = better prospect. Returns {score, priority, reasons}.
    """
    score = 0
    reasons = []

    reviews = _to_int(lead.get("review_count"))
    followers = _to_int(lead.get("follower_count"))
    try:
        rating = float(lead.get("google_rating") or 0)
    except (TypeError, ValueError):
        rating = 0.0

    if not site["has_website"]:
        score += 55
        reasons.append("no website at all")
    else:
        if not site["reachable"]:
            score += 50
            reasons.append("website broken/unreachable")
        else:
            if not site["mobile_responsive"]:
                score += 22
                reasons.append("not mobile-responsive")
            if not site["https"]:
                score += 12
                reasons.append("no HTTPS")
            if site["outdated"]:
                score += 18
                reasons.append("outdated design")
            if site["missing_pages"]:
                score += min(12, 4 * len(site["missing_pages"]))
                reasons.append("missing key pages")

    # Strong offline/social presence + weak web = prime opportunity.
    established = reviews >= STRONG_REVIEW_COUNT or followers >= STRONG_FOLLOWER_COUNT
    weak_web = (not site["has_website"]) or (not site["reachable"]) \
        or (not site["mobile_responsive"]) or site["outdated"]
    if established and weak_web:
        score += 18
        if reviews >= STRONG_REVIEW_COUNT:
            reasons.append(f"{reviews} reviews but weak web presence")
        else:
            reasons.append(f"{followers} followers but weak web presence")

    # A high rating means a happy customer base worth capturing online.
    if rating >= 4.5 and weak_web:
        score += 6
        reasons.append(f"{rating}★ rating underserved online")

    # Reachable by phone/email/IG = actionable lead.
    if not any(lead.get(k) for k in ("phone", "email", "instagram_username")):
        score -= 10
        reasons.append("no contact method (hard to reach)")

    score = max(0, min(100, score))
    priority = "HIGH" if (score >= HIGH_PRIORITY_THRESHOLD or not site["has_website"]
                          or not site["reachable"]) else \
               "MEDIUM" if score >= 40 else "LOW"

    return {"score": score, "priority": priority, "reasons": reasons}


# ── Orchestration ───────────────────────────────────────────────────────────

def qualify_lead(lead: dict, check_site: bool = True) -> dict:
    """Qualify a single lead dict; returns a flat row with QUALIFIED_FIELDS."""
    row = {k: lead.get(k, "") for k in LEAD_FIELDS}

    # Infer category from name/bio if not provided.
    if not row.get("category"):
        guess = detect_industry(f"{lead.get('name','')} {lead.get('bio','')}")
        if guess:
            row["category"] = INDUSTRIES[guess]["name"]

    site = evaluate_website(_normalize_url(lead.get("website", ""))) if check_site \
        else evaluate_website("")
    scored = score_lead(lead, site)

    row["website_status"] = site["status"]
    row["needs_site_score"] = scored["score"]
    row["priority"] = scored["priority"]
    row["reasons"] = "; ".join(scored["reasons"]) or "—"
    return row


def qualify_leads(leads: list, check_sites: bool = True) -> list:
    """Qualify and prioritize a list of leads (highest score first)."""
    qualified = [qualify_lead(l, check_site=check_sites) for l in leads]
    qualified.sort(key=lambda r: r["needs_site_score"], reverse=True)
    return qualified


# ── Reporting ───────────────────────────────────────────────────────────────

def print_report(qualified: list) -> None:
    if not qualified:
        print("No new leads found.")
        return

    high = [r for r in qualified if r["priority"] == "HIGH"]
    print("\n" + "=" * 78)
    print(f"QUALIFIED LEADS — {len(qualified)} total, {len(high)} high-priority")
    print("=" * 78)

    for i, r in enumerate(qualified, 1):
        flag = "🔥" if r["priority"] == "HIGH" else "  "
        contact = r["phone"] or r["email"] or (
            f"@{r['instagram_username']}" if r["instagram_username"] else "no contact")
        loc = ", ".join(p for p in (r["city"], r["state"]) if p)
        print(f"\n{flag} {i}. {r['name'] or '(unknown)'}  [{r['priority']} · "
              f"score {r['needs_site_score']}]")
        print(f"     {r['category'] or 'uncategorized'}"
              f"{' · ' + loc if loc else ''}")
        print(f"     contact: {contact}"
              f"{'  ·  ' + r['website'] if r['website'] else ''}")
        print(f"     website: {r['website_status']}")
        print(f"     why:     {r['reasons']}")
    print("\n" + "=" * 78)


def write_report(qualified: list, path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=QUALIFIED_FIELDS)
        w.writeheader()
        for r in qualified:
            w.writerow({k: r.get(k, "") for k in QUALIFIED_FIELDS})
    print(f"\nPrioritized list written to {path}")


def load_leads_csv(path: str) -> list:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# ── Demo / CLI ──────────────────────────────────────────────────────────────

def _demo_leads() -> list:
    """A small illustrative sample showing the qualification output format."""
    return [
        {"name": "Summit Ridge Roofing", "instagram_username": "summitridgeroof",
         "phone": "(555) 201-8841", "email": "", "website": "",
         "city": "Boise", "state": "ID", "category": "roofing",
         "follower_count": 2200, "review_count": 58, "google_rating": 4.8,
         "source": "google_maps"},
        {"name": "Delgado Plumbing Co", "instagram_username": "delgadoplumbing",
         "phone": "(555) 776-3320", "email": "info@delgadoplumbing.com",
         "website": "http://example.com/", "city": "Mesa", "state": "AZ",
         "category": "plumbing", "follower_count": 540, "review_count": 31,
         "google_rating": 4.6, "source": "instagram"},
        {"name": "Bright Spark Electric", "instagram_username": "",
         "phone": "(555) 410-2299", "email": "", "website": "https://example.org",
         "city": "Austin", "state": "TX", "category": "electrician",
         "follower_count": 120, "review_count": 9, "google_rating": 4.2,
         "source": "facebook"},
    ]


def main(argv: list) -> int:
    if len(argv) > 1:
        in_path = argv[1]
        out_path = argv[2] if len(argv) > 2 else "qualified_leads.csv"
        leads = load_leads_csv(in_path)
        print(f"Loaded {len(leads)} leads from {in_path}")
    else:
        print("No input CSV given — running built-in demo so you can see the "
              "qualification output format.\n"
              "Usage: python lead_qualifier.py <leads.csv> [out.csv]")
        leads = _demo_leads()
        out_path = "qualified_leads.csv"

    qualified = qualify_leads(leads)
    print_report(qualified)
    write_report(qualified, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
