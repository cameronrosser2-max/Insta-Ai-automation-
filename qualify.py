#!/usr/bin/env python3
"""
qualify.py — Lead search & qualification pipeline.

Searches every configured platform (Instagram, Google Maps, Facebook, local
directories) for blue-collar service businesses in your target areas, collects
their contact + presence data, audits each website, scores how likely they need
a new site, and prints a prioritized list (also written to qualified_leads.csv).

Run:
    python qualify.py
    python qualify.py --areas "Austin, TX;Dallas, TX" --categories roofing,plumbing

With no platform credentials/keys configured, every source self-disables and the
run reports "No new leads found." — wire up keys (see collectors.py) to get data.
"""

from __future__ import annotations

import argparse
import logging
import os

import collectors
import leads as leadlib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("josh.qualify")

# Target blue-collar categories -> Instagram hashtags / search terms.
CATEGORIES: dict[str, list[str]] = {
    "roofing":          ["roofingcontractor", "roofer", "roofingbusiness"],
    "plumbing":         ["plumber", "plumbinglife", "plumbingbusiness"],
    "electrician":      ["electrician", "electricianlife", "sparky"],
    "hvac":             ["hvaclife", "hvaccontractor", "heatingandcooling"],
    "landscaping":      ["landscaper", "lawncare", "landscapingbusiness"],
    "tree service":     ["treeservice", "treeremoval", "arborist"],
    "painting":         ["paintingcontractor", "housepainter", "paintingbusiness"],
    "pressure washing": ["pressurewashing", "softwash", "pressurewashingbusiness"],
    "concrete":         ["concretecontractor", "concretework", "masonrywork"],
    "junk removal":     ["junkremoval", "junkhauling", "junkremovalbusiness"],
    "flooring":         ["flooringcontractor", "flooringinstall", "flooringbusiness"],
    "fencing":          ["fencingcontractor", "fenceinstall", "fencingbusiness"],
    "general contractor": ["generalcontractor", "remodelingcontractor", "homebuilder"],
    "mobile detailing": ["mobiledetailing", "autodetailing", "cardetailing"],
    "towing":           ["towingservice", "towtruck", "roadsideassistance"],
}

DEFAULT_AREAS = ["Austin, TX"]


def search_and_qualify(areas: list[str], categories: dict[str, list[str]],
                       per_source_limit: int, audit_timeout: float) -> list[leadlib.Lead]:
    raw: list[leadlib.Lead] = []

    for area in areas:
        log.info(f"── Area: {area} ──")
        for category, hashtags in categories.items():
            log.info(f" {category}:")
            raw += collectors.collect_google_maps(category, area, per_source_limit)
            raw += collectors.collect_directories(category, area, per_source_limit)
            raw += collectors.collect_facebook(category, area, per_source_limit)
            raw += collectors.collect_instagram(hashtags, category, per_source_limit)

    if not raw:
        return []

    merged = leadlib.dedupe(raw)
    log.info(f"Collected {len(raw)} records → {len(merged)} unique businesses. Auditing websites…")

    for lead in merged:
        leadlib.qualify(lead, audit_timeout=audit_timeout)

    return leadlib.prioritize(merged)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search & qualify blue-collar service leads.")
    parser.add_argument("--areas", default=os.environ.get("TARGET_AREAS", ";".join(DEFAULT_AREAS)),
                        help="Semicolon-separated geographies, e.g. 'Austin, TX;Dallas, TX'")
    parser.add_argument("--categories", default="",
                        help="Comma-separated subset of categories (default: all)")
    parser.add_argument("--limit", type=int, default=20, help="Max results per source/category")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-site audit timeout (s)")
    parser.add_argument("--out", default="qualified_leads.csv", help="Output CSV path")
    args = parser.parse_args()

    areas = [a.strip() for a in args.areas.split(";") if a.strip()]
    if args.categories:
        wanted = {c.strip().lower() for c in args.categories.split(",")}
        cats = {k: v for k, v in CATEGORIES.items() if k in wanted}
    else:
        cats = CATEGORIES

    qualified = search_and_qualify(areas, cats, args.limit, args.timeout)

    print()
    print(leadlib.format_report(qualified))

    if qualified:
        leadlib.write_csv(qualified, args.out)
        highs = sum(1 for l in qualified if l.priority == "HIGH")
        print(f"\nSaved {len(qualified)} leads to {args.out}  ({highs} HIGH-priority).")


if __name__ == "__main__":
    main()
