#!/usr/bin/env python3
"""
website_audit.py — Evaluate a business website's quality and design.

Given a URL, fetches the page and looks for signals that the site is missing,
broken, outdated, or poorly built — exactly the businesses most likely to buy
a new website. Returns a WebsiteAssessment with a 0–100 "needs new site" score
where higher = more likely to need a rebuild.

Uses only `requests` (HTML is parsed with lightweight regex / string checks),
so there's no headless-browser dependency. It can't measure JS-rendered layout,
but the structural signals below are reliable for the small-business sites this
project targets.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime

try:
    import requests
except ImportError:  # requests is optional until you actually run an audit
    requests = None

log = logging.getLogger("josh.audit")

# A real browser-ish UA — many small-business hosts block obvious bots.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Pages a credible service business site should link to.
_KEY_PAGES = {
    "contact": ["contact", "get a quote", "get quote", "request", "schedule", "book"],
    "services": ["services", "what we do", "our work", "solutions"],
    "about": ["about", "our story", "who we are", "meet the team"],
    "reviews": ["reviews", "testimonials", "what our customers", "5 star"],
}

# Tech / markup that signals an old, hand-built, or template-frozen site.
_OUTDATED_SIGNALS = [
    (r"<font\b", "uses deprecated <font> tags"),
    (r"<marquee\b", "uses <marquee>"),
    (r"<center\b", "uses deprecated <center> tags"),
    (r'<table[^>]*\bbgcolor', "table-based layout"),
    (r"frontpage", "built with Microsoft FrontPage"),
    (r"wix\.com|wixstatic", "free Wix template"),
    (r"weebly", "Weebly free builder"),
    (r"godaddy.*website.?builder|websitebuilder\.godaddy", "GoDaddy Website Builder"),
    (r"flash|shockwave", "references Flash"),
    (r"jquery[/-]1\.[0-9]", "very old jQuery 1.x"),
]


@dataclass
class WebsiteAssessment:
    url: str
    reachable: bool = False
    status_code: int | None = None
    has_ssl: bool = False
    mobile_responsive: bool = False
    copyright_year: int | None = None
    missing_pages: list[str] = field(default_factory=list)
    outdated_signals: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    needs_new_site_score: int = 0  # 0–100, higher = more likely needs a rebuild

    @property
    def summary(self) -> str:
        if not self.url:
            return "NO WEBSITE"
        if not self.reachable:
            return "WEBSITE BROKEN / UNREACHABLE"
        if self.needs_new_site_score >= 60:
            return "VERY POOR — strong rebuild candidate"
        if self.needs_new_site_score >= 35:
            return "OUTDATED / WEAK"
        if self.needs_new_site_score >= 15:
            return "DATED but functional"
        return "MODERN / HEALTHY"


def audit_website(url: str | None, timeout: int = 12) -> WebsiteAssessment:
    """Fetch `url` and score how badly the business needs a new website."""

    # No website at all is the strongest possible buy signal.
    if not url or not url.strip():
        a = WebsiteAssessment(url="")
        a.issues.append("No website on file")
        a.needs_new_site_score = 100
        return a

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    a = WebsiteAssessment(url=url)

    if requests is None:
        log.warning("`requests` not installed — cannot audit %s", url)
        a.issues.append("Audit skipped (requests not installed)")
        return a

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        a.status_code = resp.status_code
        a.reachable = resp.status_code < 400
        a.has_ssl = resp.url.lower().startswith("https://")
        html = resp.text or ""
    except requests.exceptions.SSLError:
        a.issues.append("SSL certificate error")
        a.reachable = False
        a.needs_new_site_score = 85
        return a
    except requests.exceptions.RequestException as e:
        a.issues.append(f"Unreachable: {type(e).__name__}")
        a.reachable = False
        a.needs_new_site_score = 90
        return a

    if not a.reachable:
        a.issues.append(f"HTTP {a.status_code} error")
        a.needs_new_site_score = 88
        return a

    html_lc = html.lower()

    # ── Mobile responsiveness: presence of a viewport meta tag ──────────────
    a.mobile_responsive = bool(
        re.search(r'<meta[^>]+name=["\']viewport["\']', html_lc)
    )
    if not a.mobile_responsive:
        a.issues.append("Not mobile-responsive (no viewport tag)")

    # ── SSL ─────────────────────────────────────────────────────────────────
    if not a.has_ssl:
        a.issues.append("No HTTPS / SSL")

    # ── Copyright / freshness ───────────────────────────────────────────────
    years = re.findall(r"(?:©|&copy;|copyright)\s*\D{0,8}(20[0-2]\d)", html_lc)
    if years:
        a.copyright_year = max(int(y) for y in years)
        stale = datetime.now().year - a.copyright_year
        if stale >= 3:
            a.issues.append(f"Stale copyright year ({a.copyright_year})")

    # ── Missing key pages ───────────────────────────────────────────────────
    for page, needles in _KEY_PAGES.items():
        if not any(n in html_lc for n in needles):
            a.missing_pages.append(page)
    if a.missing_pages:
        a.issues.append("Missing pages: " + ", ".join(a.missing_pages))

    # ── Outdated build signals ──────────────────────────────────────────────
    for pattern, label in _OUTDATED_SIGNALS:
        if re.search(pattern, html_lc):
            a.outdated_signals.append(label)
    if a.outdated_signals:
        a.issues.append("Outdated tech: " + "; ".join(a.outdated_signals))

    # ── Thin content ────────────────────────────────────────────────────────
    text_only = re.sub(r"<[^>]+>", " ", html)
    if len(text_only.split()) < 120:
        a.issues.append("Very thin content (likely placeholder/parked)")
        a.outdated_signals.append("thin/placeholder content")

    a.needs_new_site_score = _score_assessment(a)
    return a


def _score_assessment(a: WebsiteAssessment) -> int:
    """Combine the individual signals into a 0–100 score."""
    score = 0
    if not a.mobile_responsive:
        score += 35          # biggest single red flag in 2026
    if not a.has_ssl:
        score += 15
    if a.copyright_year:
        stale = datetime.now().year - a.copyright_year
        score += min(stale * 5, 20)
    score += min(len(a.missing_pages) * 8, 24)
    score += min(len(a.outdated_signals) * 12, 30)
    return max(0, min(score, 100))


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    target = sys.argv[1] if len(sys.argv) > 1 else None
    result = audit_website(target)
    print(f"\nURL:    {result.url or '(none)'}")
    print(f"Verdict: {result.summary}  (score {result.needs_new_site_score}/100)")
    for issue in result.issues:
        print(f"  - {issue}")
