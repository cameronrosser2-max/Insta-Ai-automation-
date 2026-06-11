#!/usr/bin/env python3
"""
lead_finder.py — Search, audit, score and prioritize website-redesign leads.

Targets blue-collar service businesses (roofers, plumbers, electricians, HVAC,
landscapers, tree services, painters, pressure washing, concrete, junk removal,
flooring, fencing, general contractors, mobile detailers, towing).

Pipeline
--------
1. Search each source (currently Google Maps) for each category × location.
2. Optionally enrich with Instagram (username + follower count).
3. Audit each business's website (HTTPS, mobile, freshness, key pages).
4. Score 0–100 on "needs a new website" + flag HIGH-priority leads.
5. Write a prioritized leads.csv and print a ranked table.

Usage
-----
    export GOOGLE_MAPS_API_KEY=...           # required for the live search
    python lead_finder.py --categories roofers plumbers \\
                          --locations "Austin, TX" "Round Rock, TX" \\
                          --max 20 --out leads.csv

If no GOOGLE_MAPS_API_KEY is set (and no other source is configured), the run
finds nothing and says so — it does not invent leads.
"""

from __future__ import annotations

import argparse
import csv
import logging

from lead import Lead, qualify
from sources import google_maps_search, instagram_enrich

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("josh.finder")

# Default categories — the blue-collar trades this tool targets.
DEFAULT_CATEGORIES = [
    "roofers", "plumbers", "electricians", "HVAC contractors", "landscapers",
    "tree services", "painters", "pressure washing", "concrete contractors",
    "junk removal", "flooring contractors", "fencing contractors",
    "general contractors", "mobile detailers", "towing services",
]

CSV_FIELDS = [
    "priority", "score", "name", "category", "website_status",
    "phone", "email", "website", "instagram", "city", "state",
    "google_rating", "review_count", "follower_count", "source", "flags",
]


def collect_leads(categories: list[str], locations: list[str], max_per: int) -> list[Lead]:
    """Run every source for each category × location and dedupe."""
    seen: dict[str, Lead] = {}
    for location in locations:
        for category in categories:
            for lead in google_maps_search(category, location, max_per):
                key = _dedupe_key(lead)
                if key not in seen:
                    seen[key] = lead
            # ── add more sources here (facebook_search, yelp_search, …) ──
    return list(seen.values())


def _dedupe_key(lead: Lead) -> str:
    if lead.phone:
        return "ph:" + "".join(c for c in lead.phone if c.isdigit())
    return f"nm:{lead.name.lower().strip()}|{lead.city.lower().strip()}"


def write_csv(leads: list[Lead], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for lead in leads:
            writer.writerow({
                "priority": lead.priority,
                "score": lead.score,
                "name": lead.name,
                "category": lead.category,
                "website_status": lead.website_status,
                "phone": lead.phone,
                "email": lead.email,
                "website": lead.website,
                "instagram": lead.instagram,
                "city": lead.city,
                "state": lead.state,
                "google_rating": lead.google_rating if lead.google_rating is not None else "",
                "review_count": lead.review_count,
                "follower_count": lead.follower_count,
                "source": lead.source,
                "flags": ";".join(lead.flags),
            })


def print_report(leads: list[Lead]) -> None:
    if not leads:
        print("\nNo leads found. (Check that GOOGLE_MAPS_API_KEY is set and a "
              "source is reachable — no leads were invented.)")
        return

    print(f"\n{'='*78}\nPRIORITIZED LEADS  ({len(leads)} total)\n{'='*78}")
    for rank, lead in enumerate(leads, 1):
        loc = ", ".join(b for b in [lead.city, lead.state] if b)
        rating = f"{lead.google_rating}★" if lead.google_rating else "—"
        print(
            f"\n{rank}. [{lead.priority}] score {lead.score}/100 — {lead.name}"
            f"  ({lead.category})"
        )
        print(f"     site:    {lead.website_status}  |  {lead.website or 'no website'}")
        print(f"     contact: {lead.contact_summary()}")
        print(f"     {loc or '—'}  |  {rating} · {lead.review_count} reviews"
              f"  |  src: {lead.source}")
        if lead.flags:
            print(f"     flags:   {', '.join(lead.flags)}")

    highs = sum(1 for l in leads if l.priority == "HIGH")
    print(f"\n{'-'*78}\n{highs} HIGH-priority lead(s). Full data → CSV.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Find & qualify website-redesign leads.")
    parser.add_argument("--categories", nargs="+", default=DEFAULT_CATEGORIES,
                        help="Business categories to search.")
    parser.add_argument("--locations", nargs="+", required=True,
                        help='Geographic areas, e.g. "Austin, TX".')
    parser.add_argument("--max", type=int, default=20,
                        help="Max results per category per location.")
    parser.add_argument("--out", default="leads.csv", help="Output CSV path.")
    parser.add_argument("--no-audit", action="store_true",
                        help="Skip live website audits (faster, less accurate).")
    parser.add_argument("--no-instagram", action="store_true",
                        help="Skip Instagram enrichment.")
    args = parser.parse_args()

    log.info("Lead finder starting…")
    leads = collect_leads(args.categories, args.locations, args.max)
    log.info(f"Collected {len(leads)} unique businesses. Qualifying…")

    if leads and not args.no_instagram:
        instagram_enrich(leads)

    for lead in leads:
        qualify(lead, run_audit=not args.no_audit)

    leads.sort(key=lambda l: l.score, reverse=True)

    if leads:
        write_csv(leads, args.out)
        log.info(f"Wrote {len(leads)} leads → {args.out}")
    print_report(leads)


if __name__ == "__main__":
    main()
