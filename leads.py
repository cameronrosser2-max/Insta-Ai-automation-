#!/usr/bin/env python3
"""
Lead generation & qualification for blue-collar service businesses.

This module turns raw business listings (from Instagram, Google Maps, Facebook,
or local directories) into a *prioritized list of website-sales leads*. It does
four things:

    1. Holds a normalized Lead record with every field we care about.
    2. Evaluates each business's website quality (reachable? secure? mobile?
       outdated? missing key pages?).
    3. Scores how likely the business needs a new website.
    4. Flags high-priority leads and exports a sorted CSV / prints a summary.

Data collection itself lives in pluggable "sources" (see SOURCES below). The
Instagram source reuses the scraper in main.py; Google Maps / Facebook /
directory sources are thin adapters you enable by supplying an API key. Every
source just has to yield Lead objects — qualification is identical regardless of
where a lead came from.

Run directly to qualify whatever sources are configured:

    python3 leads.py                # uses all enabled sources
    python3 leads.py --demo         # qualify built-in sample leads (no network)

Nothing here sends DMs or contacts anyone; it only researches and ranks.
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from industries import detect_industry

log = logging.getLogger("josh.leads")

OUTPUT_FILE = "qualified_leads.csv"
HTTP_TIMEOUT = 12          # seconds per website check
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Target categories — blue-collar service businesses that buy local websites.
TARGET_CATEGORIES = {
    "roofing", "plumbing", "electrician", "hvac", "landscaping", "tree_service",
    "painting", "pressure_washing", "concrete", "junk_removal", "flooring",
    "fencing", "general_contractor", "mobile_detailing", "towing",
}

# Pages a credible local service site is expected to have.
KEY_PAGES = ("about", "contact", "service", "review", "gallery", "quote", "estimate")


# ────────────────────────────── Lead record ────────────────────────────────

@dataclass
class Lead:
    """One business and everything we've collected about it."""

    name: str
    category: str = ""
    source: str = ""                    # where we found it: instagram/maps/...
    instagram_username: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    city: str = ""
    state: str = ""
    follower_count: Optional[int] = None
    review_count: Optional[int] = None
    google_rating: Optional[float] = None

    # Filled in by qualification:
    website_status: str = ""            # human-readable verdict
    score: int = 0                      # 0–100, higher = better lead
    priority: str = ""                  # high / medium / low
    reasons: list[str] = field(default_factory=list)

    def normalized(self) -> "Lead":
        """Best-effort cleanup + category detection from name/bio."""
        self.instagram_username = self.instagram_username.lstrip("@").strip()
        self.website = self.website.strip()
        self.state = self.state.strip().upper()[:2]
        if not self.category:
            guessed = detect_industry(f"{self.name} {self.email} {self.website}")
            if guessed:
                self.category = guessed
        return self


# ───────────────────────── Website quality check ───────────────────────────

@dataclass
class WebsiteAssessment:
    has_website: bool = False
    reachable: bool = False
    https: bool = False
    mobile_friendly: bool = False       # has a responsive viewport meta tag
    looks_outdated: bool = False        # old copyright year / legacy markup
    missing_key_pages: bool = False
    copyright_year: Optional[int] = None
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.has_website:
            return "NO WEBSITE"
        if not self.reachable:
            return "website unreachable / broken"
        bits = []
        bits.append("HTTPS" if self.https else "no HTTPS")
        bits.append("mobile-friendly" if self.mobile_friendly else "not mobile-friendly")
        if self.copyright_year:
            bits.append(f"©{self.copyright_year}")
        if self.looks_outdated:
            bits.append("outdated")
        if self.missing_key_pages:
            bits.append("missing key pages")
        return ", ".join(bits)


def evaluate_website(url: str) -> WebsiteAssessment:
    """
    Fetch a site and judge its quality from real signals only.

    We never invent data: if the page can't be fetched we say so. Heuristics are
    deliberately conservative (a missing viewport tag, a stale copyright year,
    legacy <table>/<font> markup, absence of the usual local-service pages).
    """
    a = WebsiteAssessment()
    if not url:
        a.notes.append("no website on record")
        return a

    a.has_website = True
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    html = ""
    final_url = url
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT, context=ctx) as resp:
            final_url = resp.geturl()
            a.reachable = True
            a.https = final_url.startswith("https://")
            raw = resp.read(400_000)  # cap; landing page is enough
            html = raw.decode(resp.headers.get_content_charset() or "utf-8", "ignore")
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError) as e:
        a.notes.append(f"fetch failed: {e}")
        return a
    except Exception as e:  # noqa: BLE001 - never let one bad site crash a run
        a.notes.append(f"fetch error: {e}")
        return a

    low = html.lower()

    # Mobile-friendliness: responsive sites declare a viewport.
    a.mobile_friendly = 'name="viewport"' in low and "width=device-width" in low
    if not a.mobile_friendly:
        a.notes.append("no responsive viewport meta tag")

    # Copyright / freshness signal.
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\D{0,12}(20\d{2})", low)]
    if years:
        a.copyright_year = max(years)
        if a.copyright_year < datetime.now().year - 2:
            a.looks_outdated = True
            a.notes.append(f"copyright {a.copyright_year} is stale")

    # Legacy markup is a strong "old site" tell.
    if re.search(r"<font\b|<marquee\b|<center\b|<table[^>]+border=", low):
        a.looks_outdated = True
        a.notes.append("legacy HTML markup")

    # Key pages: look for links/anchors hinting at the usual local-service pages.
    found = {p for p in KEY_PAGES if p in low}
    if len(found) < 2:
        a.missing_key_pages = True
        a.notes.append("few/no standard pages (about/contact/services)")

    return a


# ──────────────────────────── Lead scoring ─────────────────────────────────

def score_lead(lead: Lead, a: WebsiteAssessment) -> Lead:
    """
    Score 0–100 on *likelihood this business needs a new website*. Higher is a
    hotter lead. Also sets priority and the human-readable reasons behind it.
    """
    score = 0
    reasons: list[str] = []

    # ── Website condition (the core signal) ──
    if not a.has_website:
        score += 55
        reasons.append("no website at all")
    elif not a.reachable:
        score += 50
        reasons.append("website is broken/unreachable")
    else:
        if not a.https:
            score += 12
            reasons.append("no HTTPS (insecure)")
        if not a.mobile_friendly:
            score += 18
            reasons.append("not mobile-friendly")
        if a.looks_outdated:
            score += 20
            reasons.append("outdated design")
        if a.missing_key_pages:
            score += 10
            reasons.append("missing key pages")

    # ── Demand signal: real customer demand but thin web presence ──
    reviews = lead.review_count or 0
    if reviews >= 50:
        score += 18
        reasons.append(f"{reviews} reviews = strong demand")
    elif reviews >= 15:
        score += 10
        reasons.append(f"{reviews} reviews")

    if lead.google_rating is not None and lead.google_rating >= 4.5 and reviews >= 15:
        score += 6
        reasons.append(f"{lead.google_rating}★ reputation worth showcasing")

    # ── Reachability: a lead we can actually contact is worth more ──
    if lead.phone:
        score += 4
    if lead.email:
        score += 4
    if lead.instagram_username:
        score += 3

    # ── Active-but-no-site: posting on IG with no website is a prime tell ──
    if (lead.follower_count or 0) >= 500 and not a.has_website:
        score += 8
        reasons.append("active on Instagram but no website")

    lead.score = max(0, min(100, score))
    lead.reasons = reasons
    lead.website_status = a.summary()

    # ── Priority + high-value flags ──
    high_flag = (
        not a.has_website
        or not a.reachable
        or (a.looks_outdated and reviews >= 15)
        or (reviews >= 50 and (not a.mobile_friendly or not a.https))
    )
    if high_flag or lead.score >= 70:
        lead.priority = "high"
    elif lead.score >= 45:
        lead.priority = "medium"
    else:
        lead.priority = "low"

    return lead


def qualify_leads(leads: Iterable[Lead]) -> list[Lead]:
    """Normalize, evaluate, score, dedupe, and sort leads (best first)."""
    seen: set[str] = set()
    out: list[Lead] = []
    for lead in leads:
        lead = lead.normalized()
        key = (lead.instagram_username or lead.website or lead.name).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        assessment = evaluate_website(lead.website)
        out.append(score_lead(lead, assessment))
        log.info("  qualified %-28s score=%3d  %s",
                 lead.name[:28], lead.score, lead.priority.upper())
    out.sort(key=lambda l: l.score, reverse=True)
    return out


# ──────────────────────────── Output / export ──────────────────────────────

CSV_FIELDS = [
    "score", "priority", "name", "category", "city", "state",
    "phone", "email", "instagram_username", "website", "website_status",
    "follower_count", "review_count", "google_rating", "source", "reasons",
]


def export_csv(leads: list[Lead], path: str = OUTPUT_FILE) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            row = asdict(lead)
            row["reasons"] = "; ".join(lead.reasons)
            writer.writerow(row)
    log.info("Wrote %d leads → %s", len(leads), path)


def print_report(leads: list[Lead]) -> None:
    if not leads:
        print("No new leads found.")
        return
    highs = [l for l in leads if l.priority == "high"]
    print(f"\n{'='*70}\nQUALIFIED LEADS — {len(leads)} total, {len(highs)} high-priority\n{'='*70}")
    for l in leads:
        flag = "🔥" if l.priority == "high" else ("•" if l.priority == "medium" else " ")
        loc = ", ".join(p for p in (l.city, l.state) if p)
        contact = l.phone or l.email or (f"@{l.instagram_username}" if l.instagram_username else "—")
        print(f"{flag} [{l.score:3d}] {l.name} ({l.category or 'n/a'}) {loc}")
        print(f"      contact: {contact}   web: {l.website_status}")
        if l.reasons:
            print(f"      why: {'; '.join(l.reasons)}")


# ──────────────────────────── Lead sources ─────────────────────────────────
#
# Each source is a callable returning an iterable of Lead objects. Add one and
# register it in SOURCES; qualification handles the rest. Sources that need
# credentials should yield nothing (and log a hint) when unconfigured, so a run
# never crashes just because one platform isn't set up.

def instagram_source() -> Iterable[Lead]:
    """Reuse the Instagram scraper from main.py and pull contact info from bios."""
    import os
    if not (os.environ.get("IG_USERNAME") and os.environ.get("IG_PASSWORD")):
        log.info("Instagram source skipped (IG_USERNAME / IG_PASSWORD not set).")
        return []
    try:
        from main import get_client, scrape_accounts, HASHTAGS
    except Exception as e:  # noqa: BLE001
        log.warning("Instagram source unavailable: %s", e)
        return []

    cl = get_client()
    leads: list[Lead] = []
    for industry in HASHTAGS:
        for acct in scrape_accounts(cl, industry):
            try:
                info = cl.user_info(acct["user_id"])
                bio = (info.biography or "")
                website = info.external_url or _first(bio, r"https?://\S+")
                leads.append(Lead(
                    name=acct["full_name"],
                    category=industry,
                    source="instagram",
                    instagram_username=acct["username"],
                    follower_count=getattr(info, "follower_count", None),
                    email=_first(bio, r"[\w.+-]+@[\w-]+\.[\w.-]+"),
                    phone=_first(bio, r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
                    website=website or "",
                ))
            except Exception as e:  # noqa: BLE001
                log.debug("skip %s: %s", acct["username"], e)
    return leads


def google_maps_source() -> Iterable[Lead]:
    """
    Google Places adapter. Set GOOGLE_MAPS_API_KEY and GEO_AREAS (e.g.
    'Springfield MO; Tulsa OK') to enable. Yields nothing until configured.
    """
    import os
    if not os.environ.get("GOOGLE_MAPS_API_KEY"):
        log.info("Google Maps source skipped (GOOGLE_MAPS_API_KEY not set).")
        return []
    # Intentionally left as an integration point: wire the Places Text Search
    # + Place Details endpoints here, mapping each result to a Lead with
    # review_count, google_rating, phone, website, city, state.
    log.info("Google Maps source configured but not yet implemented.")
    return []


# Register sources here. Order doesn't matter; results are merged + deduped.
SOURCES = [instagram_source, google_maps_source]


def _first(text: str, pattern: str) -> str:
    m = re.search(pattern, text or "")
    return m.group(0) if m else ""


# ──────────────────────────────── CLI ──────────────────────────────────────

def _demo_leads() -> list[Lead]:
    """Synthetic fixtures (clearly fake) to exercise scoring without network."""
    return [
        Lead(name="Apex Roofing Co", category="roofing", source="demo",
             phone="555-0101", review_count=87, google_rating=4.8,
             follower_count=1200, website=""),  # no site, lots of reviews
        Lead(name="Sunrise Plumbing", category="plumbing", source="demo",
             email="info@sunriseplumbing.example", review_count=22,
             google_rating=4.6, website="http://sunriseplumbing.example"),
        Lead(name="Modern HVAC Pros", category="hvac", source="demo",
             review_count=140, google_rating=4.9,
             website="https://modernhvacpros.example"),
    ]


def run(demo: bool = False) -> list[Lead]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s",
                        datefmt="%H:%M:%S")
    log.info("Lead qualification starting…")

    if demo:
        raw: list[Lead] = _demo_leads()
    else:
        raw = []
        for source in SOURCES:
            try:
                raw.extend(source())
            except Exception as e:  # noqa: BLE001
                log.warning("source %s failed: %s", getattr(source, "__name__", source), e)

    if not raw:
        log.info("No leads collected — confirm sources are configured (see SOURCES).")
        print("No new leads found.")
        return []

    leads = qualify_leads(raw)
    export_csv(leads)
    print_report(leads)
    return leads


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qualify blue-collar website leads.")
    parser.add_argument("--demo", action="store_true",
                        help="qualify built-in sample leads (no network/credentials)")
    args = parser.parse_args()
    run(demo=args.demo)
    sys.exit(0)
