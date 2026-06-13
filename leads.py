#!/usr/bin/env python3
"""
leads.py — Lead model, website quality auditing, and lead scoring.

This module turns a raw business record (from any platform) into a qualified,
scored lead that tells you how likely the business needs a new website.

It depends only on the Python standard library so it can run anywhere — the
platform collectors (Instagram, Google Maps, …) live in collectors.py and are
optional.
"""

from __future__ import annotations

import csv
import re
import ssl
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# Browser-ish UA so sites don't reject us outright.
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Markers that strongly suggest an old / low-effort site.
_OUTDATED_MARKERS = [
    "<frameset", "<marquee", "<blink", "<font ", 'text/javascript"',
    "shockwave-flash", "application/x-shockwave-flash",
    "frontpage.com", "wix.com/free-website", "godaddy site builder",
    'name="generator" content="frontpage',
    'name="generator" content="adobe pagemill',
    'name="generator" content="microsoft word',
    "<table", "bgcolor=", 'align="center"',  # table-based layouts / inline presentation
]

# Page paths a credible service business is expected to have.
_KEY_PAGES = ["about", "contact", "service"]


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Lead:
    """A single business lead, collected from one of the platforms."""

    name: str
    category: str = ""
    source: str = ""                       # instagram | google_maps | facebook | directory
    instagram_username: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    city: str = ""
    state: str = ""
    follower_count: Optional[int] = None
    review_count: Optional[int] = None
    google_rating: Optional[float] = None

    # Filled in by qualify()
    website_status: str = ""               # none | unreachable | poor | dated | ok
    score: int = 0                         # 0–100, higher = more likely to need a site
    priority: str = ""                     # HIGH | MEDIUM | LOW
    flags: list[str] = field(default_factory=list)

    def dedup_key(self) -> str:
        """Stable identity used to merge/skip duplicates across platforms."""
        for v in (self.instagram_username, self.website, self.phone, self.name):
            if v:
                return re.sub(r"\s+", "", v.strip().lower())
        return ""


@dataclass
class WebsiteAudit:
    reachable: bool = False
    https: bool = False
    mobile_responsive: bool = False
    looks_outdated: bool = False
    missing_pages: list[str] = field(default_factory=list)
    note: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Website quality evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _fetch(url: str, timeout: float) -> tuple[int, str]:
    """Return (status_code, lowercased_html). Raises on hard failure."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        raw = resp.read(200_000)  # first ~200 KB is plenty to judge a homepage
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.status, raw.decode(charset, errors="replace").lower()


def evaluate_website(url: str, timeout: float = 10.0) -> WebsiteAudit:
    """
    Fetch a homepage and judge its quality. Network failures degrade gracefully
    into an "unreachable" audit rather than raising.
    """
    audit = WebsiteAudit()
    if not url:
        audit.note = "no website"
        return audit

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        status, html = _fetch(url, timeout)
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ConnectionError, ValueError) as e:
        # Retry once over http:// if https failed — old sites often lack TLS.
        if url.startswith("https://"):
            try:
                status, html = _fetch("http://" + url[len("https://"):], timeout)
                audit.note = "no https"
            except Exception:
                audit.note = f"unreachable: {type(e).__name__}"
                return audit
        else:
            audit.note = f"unreachable: {type(e).__name__}"
            return audit
    except Exception as e:  # pragma: no cover - defensive
        audit.note = f"unreachable: {type(e).__name__}"
        return audit

    if status >= 400:
        audit.note = f"http {status}"
        return audit

    audit.reachable = True
    audit.https = url.startswith("https://") and audit.note != "no https"

    # Mobile responsiveness: a real responsive site declares a viewport.
    audit.mobile_responsive = bool(
        re.search(r'<meta[^>]+name=["\']viewport["\']', html)
    )

    # Outdated design signals.
    audit.looks_outdated = any(m in html for m in _OUTDATED_MARKERS)

    # Missing key pages — look for links pointing at expected sections.
    for page in _KEY_PAGES:
        if not re.search(rf'href=["\'][^"\']*{page}', html):
            audit.missing_pages.append(page)

    return audit


# ─────────────────────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────────────────────

def qualify(lead: Lead, audit_timeout: float = 10.0) -> Lead:
    """
    Score a lead 0–100 on how likely it needs a new website, set its
    website_status / priority, and attach human-readable flags.
    Mutates and returns the lead.
    """
    score = 0
    flags: list[str] = []

    has_reviews = (lead.review_count or 0) >= 10
    well_reviewed = (lead.review_count or 0) >= 25
    decent_following = (lead.follower_count or 0) >= 1000

    if not lead.website:
        # No website at all — the strongest buying signal.
        lead.website_status = "none"
        score += 60
        flags.append("no-website")
    else:
        audit = evaluate_website(lead.website, timeout=audit_timeout)
        if not audit.reachable:
            lead.website_status = "unreachable"
            score += 55
            flags.append(f"site-down ({audit.note})")
        else:
            problems = 0
            if not audit.mobile_responsive:
                score += 25
                problems += 1
                flags.append("not-mobile")
            if audit.looks_outdated:
                score += 20
                problems += 1
                flags.append("outdated-design")
            if not audit.https:
                score += 10
                problems += 1
                flags.append("no-https")
            if audit.missing_pages:
                score += 5 * len(audit.missing_pages)
                flags.append("missing:" + "/".join(audit.missing_pages))

            if problems >= 2:
                lead.website_status = "poor"
            elif problems == 1 or audit.missing_pages:
                lead.website_status = "dated"
            else:
                lead.website_status = "ok"

    # Online-presence context.
    if not has_reviews and not decent_following:
        score += 10
        flags.append("low-online-presence")

    # Best-fit prospect: proven demand (lots of reviews) but weak web presence.
    weak_web = lead.website_status in ("none", "unreachable", "poor")
    if well_reviewed and weak_web:
        score += 15
        flags.append("HIGH-VALUE: many reviews, weak web")

    lead.score = max(0, min(100, score))
    lead.flags = flags

    if lead.score >= 70 or (well_reviewed and weak_web):
        lead.priority = "HIGH"
    elif lead.score >= 40:
        lead.priority = "MEDIUM"
    else:
        lead.priority = "LOW"

    return lead


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation & output
# ─────────────────────────────────────────────────────────────────────────────

def dedupe(leads: list[Lead]) -> list[Lead]:
    """Merge duplicate businesses found across platforms, keeping richest record."""
    by_key: dict[str, Lead] = {}
    for lead in leads:
        key = lead.dedup_key()
        if not key:
            continue
        if key not in by_key:
            by_key[key] = lead
        else:
            # Fill blank fields on the existing record from the new one.
            existing = by_key[key]
            for fname, fval in asdict(lead).items():
                if fname in ("flags", "score", "priority", "website_status"):
                    continue
                if not getattr(existing, fname) and fval:
                    setattr(existing, fname, fval)
    return list(by_key.values())


def prioritize(leads: list[Lead]) -> list[Lead]:
    """Return leads sorted best-prospect-first."""
    rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "": 3}
    return sorted(leads, key=lambda l: (rank.get(l.priority, 3), -l.score, -(l.review_count or 0)))


_CSV_FIELDS = [
    "priority", "score", "name", "category", "source", "website_status",
    "instagram_username", "phone", "email", "website", "city", "state",
    "follower_count", "review_count", "google_rating", "flags",
]


def write_csv(leads: list[Lead], path: str = "qualified_leads.csv") -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for lead in leads:
            row = {k: getattr(lead, k) for k in _CSV_FIELDS if k != "flags"}
            row["flags"] = "; ".join(lead.flags)
            writer.writerow(row)


def format_report(leads: list[Lead], limit: int = 50) -> str:
    """Build a human-readable prioritized list for the console."""
    if not leads:
        return "No new leads found."

    lines = [
        f"Qualified {len(leads)} lead(s) — {datetime.now():%Y-%m-%d %H:%M}",
        "=" * 72,
    ]
    for i, l in enumerate(prioritize(leads)[:limit], 1):
        contact = " | ".join(
            p for p in (
                f"@{l.instagram_username}" if l.instagram_username else "",
                l.phone, l.email, l.website or "no website",
            ) if p
        )
        loc = ", ".join(p for p in (l.city, l.state) if p)
        reviews = f"{l.review_count}★@{l.google_rating}" if l.review_count else "—"
        lines.append(
            f"{i:>2}. [{l.priority:^6}] {l.score:>3}  {l.name}  ({l.category}, {loc or 'location n/a'})"
        )
        lines.append(f"      web: {l.website_status or 'unknown'}  reviews: {reviews}  via: {l.source}")
        lines.append(f"      {contact}")
        if l.flags:
            lines.append(f"      flags: {', '.join(l.flags)}")
    return "\n".join(lines)
