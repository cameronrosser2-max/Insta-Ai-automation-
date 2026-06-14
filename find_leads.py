#!/usr/bin/env python3
"""
find_leads.py — Search, qualify, and prioritize blue-collar service leads.

Pipeline:
  1. Search each configured platform (Instagram, Google Maps, Facebook,
     local directories) for businesses in the target categories + areas.
  2. Collect name, IG handle, phone, email, website, city/state, category,
     followers, review count, and Google rating.
  3. Audit each website's quality (mobile-friendliness, SSL, freshness,
     missing pages, outdated tech).
  4. Score each lead on how likely it needs a new website.
  5. Flag high-priority leads (no site / very poor site / strong reputation
     but weak web presence) and output a prioritized list.

Usage:
  python find_leads.py --categories roofing,plumbing,hvac \\
                       --locations "Austin, TX" "Dallas, TX"

  # Default categories = all; default locations from --locations or env.

Configure sources via environment variables (see lead_sources.py):
  IG_USERNAME, IG_PASSWORD, GOOGLE_MAPS_API_KEY, FB_ACCESS_TOKEN, YELP_API_KEY
"""

import sys
import argparse
import logging

from industries import INDUSTRIES
from lead_sources import gather_leads
from leads import qualify_leads, write_leads_csv, print_report, LEADS_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("josh.find")


def parse_args(argv):
    p = argparse.ArgumentParser(description="Find & qualify blue-collar service leads.")
    p.add_argument(
        "--categories",
        default="",
        help="Comma-separated industry keys (default: all). "
             "Options: " + ", ".join(INDUSTRIES.keys()),
    )
    p.add_argument(
        "--locations",
        nargs="*",
        default=[],
        help='Target areas, e.g. --locations "Austin, TX" "Dallas, TX"',
    )
    p.add_argument(
        "--no-audit",
        action="store_true",
        help="Skip live website audits (faster; scores no-website leads only).",
    )
    p.add_argument("--out", default=LEADS_FILE, help="Output CSV path.")
    p.add_argument("--top", type=int, default=25, help="How many to print to console.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])

    categories = (
        [c.strip() for c in args.categories.split(",") if c.strip()]
        if args.categories
        else list(INDUSTRIES.keys())
    )
    unknown = [c for c in categories if c not in INDUSTRIES]
    if unknown:
        log.warning("Unknown categories ignored: %s", ", ".join(unknown))
        categories = [c for c in categories if c in INDUSTRIES]

    locations = args.locations or []

    log.info("Searching %d categories across %d locations…",
             len(categories), len(locations) or 0)
    if not locations:
        log.info("No --locations given: Google Maps / directory sources need "
                 "locations; Instagram (hashtag) search will still run if configured.")

    raw = gather_leads(categories, locations)
    if not raw:
        print("\nNo new leads found. (No sources returned results — check that "
              "IG_USERNAME/IG_PASSWORD, GOOGLE_MAPS_API_KEY, etc. are configured "
              "and that --locations were provided.)")
        return 0

    log.info("Collected %d raw leads — qualifying…", len(raw))
    qualified = qualify_leads(raw, audit=not args.no_audit)

    write_leads_csv(qualified, args.out)
    print_report(qualified, top=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
