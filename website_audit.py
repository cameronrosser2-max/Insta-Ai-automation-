#!/usr/bin/env python3
"""
website_audit.py — Evaluate the quality of a business's website.

Given a URL, fetch the homepage and score it 0–100 on modern-web criteria
(HTTPS, mobile responsiveness, freshness, key pages, outdated markup). A LOW
score means the site is a strong candidate for a redesign — i.e. a good lead.

The companion scoring in lead.py inverts this: a poor website (or none at all)
raises the "needs a new website" qualification score.

No API key required. Uses `requests` + `beautifulsoup4`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Pages a credible service business is expected to have. We look for links
# whose href or text contains these tokens.
KEY_PAGES = {
    "contact":  ["contact", "get-in-touch", "reach-us"],
    "services": ["service", "what-we-do", "solutions"],
    "about":    ["about", "our-story", "who-we-are"],
    "quote":    ["quote", "estimate", "book", "schedule", "request"],
}

# Markup that signals an old, hand-rolled or builder-frozen site.
OUTDATED_MARKERS = [
    r"<font\b",                       # deprecated <font> tags
    r"<marquee\b",                    # ancient
    r"<center\b",                     # layout via <center>
    r'<table[^>]*\bwidth=',           # table-based layout
    r"\.swf\b",                       # Flash
    r"frameset",                      # framesets
    r'content=["\']text/html; charset=iso-8859-1',  # legacy encoding decl
]

REQUEST_TIMEOUT = 12
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


@dataclass
class WebsiteAudit:
    """Result of auditing a single website."""
    url: str
    reachable: bool = False
    status_code: int | None = None
    https: bool = False
    mobile_responsive: bool = False
    copyright_year: int | None = None
    years_stale: int | None = None
    missing_pages: list[str] = field(default_factory=list)
    found_pages: list[str] = field(default_factory=list)
    outdated_markup: bool = False
    quality_score: int = 0          # 0 (terrible) – 100 (great)
    notes: list[str] = field(default_factory=list)

    @property
    def is_poor(self) -> bool:
        """True if this site is a strong redesign candidate."""
        return self.quality_score < 50


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def audit_website(url: str) -> WebsiteAudit:
    """Fetch and score a website. Never raises — failures become a low score."""
    url = _normalize_url(url)
    audit = WebsiteAudit(url=url)

    if not url:
        audit.notes.append("No URL provided.")
        return audit

    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
    except requests.RequestException as e:
        audit.notes.append(f"Unreachable: {e.__class__.__name__}")
        return audit

    audit.reachable = True
    audit.status_code = resp.status_code
    audit.https = resp.url.lower().startswith("https://")

    if resp.status_code >= 400:
        audit.notes.append(f"HTTP {resp.status_code} error.")
        return audit

    html = resp.text or ""
    soup = BeautifulSoup(html, "html.parser")

    _check_mobile(audit, soup)
    _check_freshness(audit, soup.get_text(" ", strip=True))
    _check_key_pages(audit, soup)
    _check_outdated_markup(audit, html)

    audit.quality_score = _score_quality(audit)
    return audit


def _check_mobile(audit: WebsiteAudit, soup: BeautifulSoup) -> None:
    viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    audit.mobile_responsive = bool(
        viewport and "width=device-width" in (viewport.get("content") or "").lower()
    )
    if not audit.mobile_responsive:
        audit.notes.append("No mobile viewport meta — likely not responsive.")


def _check_freshness(audit: WebsiteAudit, text: str) -> None:
    years = [int(y) for y in re.findall(r"©?\s*(20\d{2})", text)]
    # Keep only plausible copyright years (not future, not absurdly old).
    this_year = datetime.now().year
    years = [y for y in years if 2000 <= y <= this_year]
    if years:
        audit.copyright_year = max(years)
        audit.years_stale = this_year - audit.copyright_year
        if audit.years_stale >= 2:
            audit.notes.append(
                f"Copyright shows {audit.copyright_year} "
                f"({audit.years_stale} yrs stale)."
            )


def _check_key_pages(audit: WebsiteAudit, soup: BeautifulSoup) -> None:
    hrefs = " ".join(
        (a.get("href") or "") + " " + a.get_text(" ", strip=True)
        for a in soup.find_all("a")
    ).lower()

    for page, tokens in KEY_PAGES.items():
        if any(tok in hrefs for tok in tokens):
            audit.found_pages.append(page)
        else:
            audit.missing_pages.append(page)
    if audit.missing_pages:
        audit.notes.append("Missing pages: " + ", ".join(audit.missing_pages) + ".")


def _check_outdated_markup(audit: WebsiteAudit, html: str) -> None:
    lowered = html.lower()
    audit.outdated_markup = any(re.search(p, lowered) for p in OUTDATED_MARKERS)
    if audit.outdated_markup:
        audit.notes.append("Outdated markup detected (table layout / Flash / <font>).")


def _score_quality(audit: WebsiteAudit) -> int:
    """Combine signals into a 0–100 site-quality score."""
    score = 100
    if not audit.https:
        score -= 15
    if not audit.mobile_responsive:
        score -= 30
    if audit.outdated_markup:
        score -= 25
    if audit.years_stale is not None:
        score -= min(20, audit.years_stale * 5)
    score -= 7 * len(audit.missing_pages)
    return max(0, min(100, score))


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    result = audit_website(target)
    print(f"\nAudit for {result.url}")
    print(f"  reachable:        {result.reachable} (HTTP {result.status_code})")
    print(f"  https:            {result.https}")
    print(f"  mobile responsive:{result.mobile_responsive}")
    print(f"  copyright year:   {result.copyright_year} (stale {result.years_stale})")
    print(f"  found pages:      {result.found_pages}")
    print(f"  missing pages:    {result.missing_pages}")
    print(f"  outdated markup:  {result.outdated_markup}")
    print(f"  QUALITY SCORE:    {result.quality_score}/100")
    print("  notes:")
    for n in result.notes:
        print(f"    - {n}")
