#!/usr/bin/env python3
"""
leads.py — Lead data model, qualification scoring, and prioritized output.

A "lead" is a blue-collar service business found on Instagram, Google Maps,
Facebook, or a local directory. This module enriches each lead with a website
audit, scores how likely it is to need a new website, flags high-priority
prospects, and writes a prioritized CSV + console report.
"""

import csv
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

from website_audit import audit_website, WebsiteAssessment
from industries import INDUSTRIES, detect_industry

log = logging.getLogger("josh.leads")

LEADS_FILE = "qualified_leads.csv"


@dataclass
class Lead:
    # ── Identity / contact ──────────────────────────────────────────────────
    business_name: str = ""
    ig_username: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    city: str = ""
    state: str = ""
    category: str = ""          # industry key, e.g. "roofing"
    source: str = ""            # "instagram" | "google_maps" | "facebook" | "directory"

    # ── Online-presence metrics ─────────────────────────────────────────────
    follower_count: int = 0
    review_count: int = 0
    google_rating: float = 0.0

    # ── Derived (filled by qualify) ─────────────────────────────────────────
    website_status: str = ""
    website_score: int = 0      # 0–100 from the website audit
    qualification_score: int = 0  # 0–100 overall "should we pitch them" score
    priority: str = ""          # "HIGH" | "MEDIUM" | "LOW"
    flags: list[str] = field(default_factory=list)

    @property
    def category_name(self) -> str:
        return INDUSTRIES.get(self.category, {}).get("name", self.category or "Unknown")


def qualify_lead(lead: Lead, audit: bool = True) -> Lead:
    """Enrich a single lead: classify category, audit website, score, flag."""

    # Infer category from name/handle if the source didn't supply one.
    if not lead.category:
        lead.category = detect_industry(
            f"{lead.business_name} {lead.ig_username}"
        ) or ""

    assessment: WebsiteAssessment
    if audit:
        assessment = audit_website(lead.website)
        lead.website_status = assessment.summary
    else:
        # No live check requested: we only know "has a site" vs "doesn't".
        assessment = WebsiteAssessment(url=lead.website or "")
        if lead.website:
            assessment.reachable = True  # assume up; we didn't verify
            assessment.needs_new_site_score = 0
            lead.website_status = "Has website (not audited)"
        else:
            assessment.needs_new_site_score = 100
            lead.website_status = "NO WEBSITE"

    lead.website_score = assessment.needs_new_site_score

    lead.qualification_score = _score_lead(lead, assessment)
    lead.flags = _flag_lead(lead, assessment)
    lead.priority = _priority(lead.qualification_score)
    return lead


def _score_lead(lead: Lead, a: WebsiteAssessment) -> int:
    """
    0–100: how strong a website-services prospect this business is.

    Website weakness is the core driver, but we boost businesses that clearly
    have demand (lots of reviews/followers) yet a weak web presence — those are
    the most lucrative and easiest to convince.
    """
    score = 0

    # Website weakness (the main signal) — up to 60 pts.
    score += round(a.needs_new_site_score * 0.60)

    # Demonstrated demand but weak web presence = high value.
    if lead.review_count >= 25 and a.needs_new_site_score >= 35:
        score += 18
    elif lead.review_count >= 10 and a.needs_new_site_score >= 35:
        score += 10

    # An engaged IG following with no/poor website converts well.
    if lead.follower_count >= 1000 and a.needs_new_site_score >= 35:
        score += 12
    elif lead.follower_count >= 300 and a.needs_new_site_score >= 35:
        score += 6

    # Solid reputation (high rating) is easier to sell to — they reinvest.
    if lead.google_rating >= 4.5 and lead.review_count >= 10:
        score += 6

    # Reachable contact info means we can actually close them.
    if lead.phone or lead.email:
        score += 4

    return max(0, min(score, 100))


def _flag_lead(lead: Lead, a: WebsiteAssessment) -> list[str]:
    """Human-readable flags highlighting why a lead is (or isn't) hot."""
    flags = []

    if not lead.website:
        flags.append("NO WEBSITE")
    elif not a.reachable:
        flags.append("WEBSITE BROKEN")
    elif a.needs_new_site_score >= 60:
        flags.append("VERY POOR SITE")

    if lead.review_count >= 25 and a.needs_new_site_score >= 35:
        flags.append("HIGH REVIEWS + WEAK WEB")

    if lead.follower_count >= 1000 and a.needs_new_site_score >= 35:
        flags.append("STRONG IG + WEAK WEB")

    if not a.mobile_responsive and a.reachable and lead.website:
        flags.append("NOT MOBILE-FRIENDLY")

    return flags


def _priority(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 45:
        return "MEDIUM"
    return "LOW"


def qualify_leads(leads: list[Lead], audit: bool = True) -> list[Lead]:
    """Qualify and return leads sorted by qualification score (desc)."""
    qualified = []
    for i, lead in enumerate(leads, 1):
        log.info("Qualifying %d/%d: %s", i, len(leads), lead.business_name or lead.ig_username)
        qualify_lead(lead, audit=audit)
        qualified.append(lead)
    qualified.sort(key=lambda l: l.qualification_score, reverse=True)
    return qualified


# ── Output ──────────────────────────────────────────────────────────────────

_CSV_FIELDS = [
    "priority", "qualification_score", "business_name", "category",
    "phone", "email", "website", "website_status", "website_score",
    "ig_username", "follower_count", "review_count", "google_rating",
    "city", "state", "source", "flags",
]


def write_leads_csv(leads: list[Lead], path: str = LEADS_FILE) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for lead in leads:
            row = asdict(lead)
            row["category"] = lead.category_name
            row["flags"] = "; ".join(lead.flags)
            writer.writerow({k: row.get(k, "") for k in _CSV_FIELDS})
    log.info("Wrote %d qualified leads → %s", len(leads), path)


def print_report(leads: list[Lead], top: int = 25) -> None:
    """Print a prioritized, human-readable summary to the console."""
    if not leads:
        print("\nNo new leads found.")
        return

    high = [l for l in leads if l.priority == "HIGH"]
    med = [l for l in leads if l.priority == "MEDIUM"]

    print("\n" + "=" * 72)
    print(f"  QUALIFIED LEADS — {len(leads)} total "
          f"({len(high)} HIGH, {len(med)} MEDIUM priority)")
    print("=" * 72)

    for lead in leads[:top]:
        contact = lead.phone or lead.email or (f"@{lead.ig_username}" if lead.ig_username else "—")
        loc = ", ".join(p for p in (lead.city, lead.state) if p)
        print(
            f"\n[{lead.priority:<6}] {lead.qualification_score:>3}/100  "
            f"{lead.business_name or '@' + lead.ig_username}"
        )
        print(f"         {lead.category_name} · {loc or 'location n/a'} · via {lead.source}")
        print(f"         Contact: {contact}")
        print(f"         Website: {lead.website or '(none)'} — {lead.website_status}")
        if lead.review_count or lead.google_rating or lead.follower_count:
            print(
                f"         Presence: {lead.google_rating or '—'}★ "
                f"({lead.review_count} reviews) · {lead.follower_count} IG followers"
            )
        if lead.flags:
            print(f"         ⚑ {' | '.join(lead.flags)}")

    if len(leads) > top:
        print(f"\n  …and {len(leads) - top} more in {LEADS_FILE}")
    print("=" * 72)
