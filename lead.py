#!/usr/bin/env python3
"""
lead.py — Lead data model + qualification scoring.

A `Lead` holds everything we collect about a prospect across sources. The
scoring function turns the lead's web presence + demand signals into a
0–100 "needs a new website" score and a priority flag.

Scoring philosophy
------------------
The best lead is a real, busy business (lots of reviews, good rating, active
on social) that has NO website or a bad one. They have demand and money but a
weak web presence — the easiest "yes" for a website pitch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from website_audit import WebsiteAudit, audit_website


@dataclass
class Lead:
    # ── identity / contact ──────────────────────────────────────────────
    name: str
    category: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    instagram: str = ""          # username without the @
    city: str = ""
    state: str = ""
    source: str = ""             # which platform we found them on

    # ── demand / presence signals ───────────────────────────────────────
    follower_count: int = 0
    review_count: int = 0
    google_rating: Optional[float] = None

    # ── derived (filled by qualify) ─────────────────────────────────────
    website_status: str = "unknown"   # none / poor / dated / good / unreachable
    audit: Optional[WebsiteAudit] = None
    score: int = 0                    # 0–100, higher = better lead
    priority: str = "LOW"             # HIGH / MEDIUM / LOW
    flags: list[str] = field(default_factory=list)

    def contact_summary(self) -> str:
        bits = [self.phone, self.email, self.website]
        if self.instagram:
            bits.append(f"@{self.instagram}")
        return " | ".join(b for b in bits if b) or "—"


def qualify(lead: Lead, run_audit: bool = True) -> Lead:
    """Score a lead in place and return it.

    `run_audit=False` skips the live website fetch (useful for tests or when
    offline) and scores purely on whether a website URL exists.
    """
    score = 0
    flags: list[str] = []

    # ── 1. Website presence (the dominant signal) ───────────────────────
    if not lead.website:
        lead.website_status = "none"
        score += 45
        flags.append("NO_WEBSITE")
    elif run_audit:
        audit = audit_website(lead.website)
        lead.audit = audit
        if not audit.reachable or (audit.status_code or 0) >= 400:
            lead.website_status = "unreachable"
            score += 40
            flags.append("SITE_UNREACHABLE")
        else:
            # Invert site quality: a 0/100 site contributes the full 40 pts.
            web_need = round((100 - audit.quality_score) * 0.40)
            score += web_need
            if audit.quality_score < 30:
                lead.website_status = "poor"
                flags.append("VERY_POOR_DESIGN")
            elif audit.quality_score < 60:
                lead.website_status = "dated"
                flags.append("OUTDATED_SITE")
            else:
                lead.website_status = "good"
            if not audit.mobile_responsive:
                flags.append("NOT_MOBILE")
            if audit.missing_pages:
                flags.append("MISSING_PAGES")
    else:
        lead.website_status = "has_site"

    # ── 2. Demand signals — busy businesses are worth more ──────────────
    if lead.review_count >= 50:
        score += 20
    elif lead.review_count >= 20:
        score += 12
    elif lead.review_count >= 5:
        score += 6

    if lead.google_rating is not None and lead.google_rating >= 4.0:
        score += 8   # reputable + busy = motivated, can afford it

    if lead.follower_count >= 1000:
        score += 6
    elif lead.follower_count >= 200:
        score += 3

    # ── 3. The money flag: high demand + weak web presence ──────────────
    weak_web = lead.website_status in ("none", "poor", "unreachable")
    if lead.review_count >= 20 and weak_web:
        score += 10
        flags.append("HIGH_DEMAND_WEAK_WEB")

    lead.score = max(0, min(100, score))
    lead.flags = flags
    lead.priority = (
        "HIGH" if lead.score >= 70
        else "MEDIUM" if lead.score >= 45
        else "LOW"
    )
    return lead
