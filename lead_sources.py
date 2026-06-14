#!/usr/bin/env python3
"""
lead_sources.py — Search adapters that pull raw leads from each platform.

Every adapter returns a list[Lead] (un-qualified). Adapters degrade gracefully:
if the required credentials / API keys aren't configured, they log a clear
message and return [] rather than crashing, so you can run the pipeline with
whatever sources you have set up.

Configured via environment variables:
    IG_USERNAME / IG_PASSWORD     → Instagram (instagrapi)
    GOOGLE_MAPS_API_KEY           → Google Maps (Places API)
    FACEBOOK_*, directory APIs    → see the stubs below

Instagram bios and Google Places `website` fields feed straight into the
website audit, so these two sources alone produce fully-qualified leads.
"""

import os
import re
import time
import random
import logging

from leads import Lead
from industries import INDUSTRIES, detect_industry

log = logging.getLogger("josh.sources")

# ── Shared contact extraction ────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+|[a-z0-9-]+\.(?:com|net|org|co|biz)\b)", re.I)


def extract_contacts(text: str) -> dict:
    """Pull email / phone / website out of a free-text blob (e.g. an IG bio)."""
    text = text or ""
    email = _EMAIL_RE.search(text)
    phone = _PHONE_RE.search(text)
    url = _URL_RE.search(text)
    site = url.group(0) if url else ""
    # Don't treat the email address as a website match.
    if email and site and email.group(0) in site:
        site = ""
    return {
        "email": email.group(0) if email else "",
        "phone": phone.group(0) if phone else "",
        "website": site,
    }


# ── Instagram ────────────────────────────────────────────────────────────────

def search_instagram(categories: list[str], per_hashtag: int = 30,
                     max_per_category: int = 40) -> list[Lead]:
    """
    Scrape business accounts from each category's hashtags. Requires IG creds.
    Pulls the user's bio to extract phone/email/website for the audit.
    """
    user = os.environ.get("IG_USERNAME")
    pwd = os.environ.get("IG_PASSWORD")
    if not (user and pwd):
        log.info("Instagram: IG_USERNAME / IG_PASSWORD not set — skipping.")
        return []

    try:
        from instagrapi import Client
    except ImportError:
        log.warning("Instagram: instagrapi not installed — skipping.")
        return []

    # Reuse the project's hashtag map if available.
    try:
        from main import HASHTAGS
    except Exception:
        HASHTAGS = {}

    cl = Client()
    cl.delay_range = [2, 5]
    try:
        if os.path.exists("ig_session.json"):
            cl.load_settings("ig_session.json")
        cl.login(user, pwd)
        cl.dump_settings("ig_session.json")
    except Exception as e:
        log.warning("Instagram login failed: %s — skipping.", e)
        return []

    leads: dict[str, Lead] = {}
    for cat in categories:
        tags = HASHTAGS.get(cat) or [INDUSTRIES.get(cat, {}).get("name", cat).lower().replace(" ", "")]
        found_in_cat = 0
        for tag in tags:
            if found_in_cat >= max_per_category:
                break
            try:
                medias = cl.hashtag_medias_recent_v1(tag, amount=per_hashtag)
            except Exception as e:
                log.warning("Instagram: #%s skipped (%s)", tag, e)
                continue

            for media in medias:
                u = media.user
                uname = (u.username or "").lower()
                if not uname or uname in leads:
                    continue
                # Fetch full profile for bio + external url (best-effort).
                bio, external = "", ""
                try:
                    info = cl.user_info(u.pk)
                    bio = info.biography or ""
                    external = str(info.external_url or "")
                    followers = info.follower_count or 0
                    full_name = info.full_name or u.full_name or u.username
                except Exception:
                    followers = 0
                    full_name = u.full_name or u.username

                contacts = extract_contacts(bio)
                website = external or contacts["website"]
                leads[uname] = Lead(
                    business_name=full_name,
                    ig_username=u.username,
                    phone=contacts["phone"],
                    email=contacts["email"],
                    website=website,
                    category=cat or detect_industry(f"{full_name} {bio}") or "",
                    source="instagram",
                    follower_count=followers,
                )
                found_in_cat += 1
                if found_in_cat >= max_per_category:
                    break
                time.sleep(random.uniform(1, 3))
            time.sleep(random.uniform(3, 6))

    log.info("Instagram: %d unique leads.", len(leads))
    return list(leads.values())


# ── Google Maps (Places API) ─────────────────────────────────────────────────

def search_google_maps(categories: list[str], locations: list[str],
                       max_per_query: int = 20) -> list[Lead]:
    """
    Use the Google Places Text Search + Details API to find businesses by
    category and location. Requires GOOGLE_MAPS_API_KEY. This is the richest
    source for phone / website / rating / review_count.
    """
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        log.info("Google Maps: GOOGLE_MAPS_API_KEY not set — skipping.")
        return []

    try:
        import requests
    except ImportError:
        log.warning("Google Maps: requests not installed — skipping.")
        return []

    leads: dict[str, Lead] = {}
    for cat in categories:
        cat_name = INDUSTRIES.get(cat, {}).get("name", cat)
        for loc in locations:
            query = f"{cat_name} in {loc}"
            try:
                resp = requests.get(
                    "https://maps.googleapis.com/maps/api/place/textsearch/json",
                    params={"query": query, "key": key},
                    timeout=15,
                )
                results = resp.json().get("results", [])[:max_per_query]
            except Exception as e:
                log.warning("Google Maps: query '%s' failed (%s)", query, e)
                continue

            city, state = _split_location(loc)
            for place in results:
                pid = place.get("place_id")
                if not pid or pid in leads:
                    continue
                details = _places_details(requests, pid, key)
                site = details.get("website", "")
                leads[pid] = Lead(
                    business_name=details.get("name") or place.get("name", ""),
                    phone=details.get("formatted_phone_number", ""),
                    website=site,
                    city=city,
                    state=state,
                    category=cat,
                    source="google_maps",
                    review_count=details.get("user_ratings_total", 0) or place.get("user_ratings_total", 0) or 0,
                    google_rating=details.get("rating", 0.0) or place.get("rating", 0.0) or 0.0,
                )
            time.sleep(0.5)  # be polite to the API

    log.info("Google Maps: %d unique leads.", len(leads))
    return list(leads.values())


def _places_details(requests, place_id: str, key: str) -> dict:
    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": place_id,
                "fields": "name,formatted_phone_number,website,rating,user_ratings_total",
                "key": key,
            },
            timeout=15,
        )
        return resp.json().get("result", {})
    except Exception:
        return {}


def _split_location(loc: str) -> tuple[str, str]:
    parts = [p.strip() for p in loc.split(",")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return loc.strip(), ""


# ── Facebook ─────────────────────────────────────────────────────────────────

def search_facebook(categories: list[str], locations: list[str]) -> list[Lead]:
    """
    Placeholder for Facebook Pages search.

    Facebook's Graph API requires a reviewed app with the relevant permissions,
    and direct page scraping violates their ToS. Wire your approved Graph API
    flow in here (read FB_ACCESS_TOKEN from the environment) and map results
    onto the Lead model. Returns [] until configured.
    """
    if not os.environ.get("FB_ACCESS_TOKEN"):
        log.info("Facebook: FB_ACCESS_TOKEN not set — skipping (see lead_sources.py).")
        return []
    log.info("Facebook: configured token present but no adapter implemented yet.")
    return []


# ── Local directories ────────────────────────────────────────────────────────

def search_directories(categories: list[str], locations: list[str]) -> list[Lead]:
    """
    Placeholder for local-directory sources (Yelp Fusion, Yellow Pages, BBB,
    Angi, Thumbtack, etc.). Yelp's Fusion API is the easiest to add: read
    YELP_API_KEY from the environment, hit /businesses/search, and map results
    onto the Lead model (name, phone, rating, review_count, location). Returns
    [] until configured.
    """
    if not os.environ.get("YELP_API_KEY"):
        log.info("Directories: YELP_API_KEY not set — skipping (see lead_sources.py).")
        return []
    log.info("Directories: configured key present but no adapter implemented yet.")
    return []


# ── Aggregator ───────────────────────────────────────────────────────────────

def gather_leads(categories: list[str], locations: list[str]) -> list[Lead]:
    """Run every configured source and merge results, de-duped by name+phone."""
    all_leads: list[Lead] = []
    all_leads += search_instagram(categories)
    all_leads += search_google_maps(categories, locations)
    all_leads += search_facebook(categories, locations)
    all_leads += search_directories(categories, locations)
    return _dedupe(all_leads)


def _dedupe(leads: list[Lead]) -> list[Lead]:
    seen: dict[str, Lead] = {}
    for lead in leads:
        key = (lead.business_name.lower().strip(), re.sub(r"\D", "", lead.phone))
        key_str = key[0] + "|" + key[1]
        if key_str in seen:
            # Merge: keep the richest record.
            existing = seen[key_str]
            existing.phone = existing.phone or lead.phone
            existing.email = existing.email or lead.email
            existing.website = existing.website or lead.website
            existing.ig_username = existing.ig_username or lead.ig_username
            existing.review_count = max(existing.review_count, lead.review_count)
            existing.google_rating = max(existing.google_rating, lead.google_rating)
            existing.follower_count = max(existing.follower_count, lead.follower_count)
        else:
            seen[key_str] = lead
    return list(seen.values())
