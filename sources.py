#!/usr/bin/env python3
"""
sources.py — Pluggable lead sources.

Each source function takes a search query + location and yields `Lead`
objects with whatever fields it can populate. Sources are gated behind the
credentials they need and fail gracefully (return [] + a log line) when those
credentials are missing, so the pipeline keeps running.

Currently implemented
----------------------
- Google Maps (official Places API)  → name, phone, website, rating, reviews,
                                        city, state, category.
- Instagram (instagrapi, optional)   → enriches a lead with IG username +
                                        follower count by name search.

Why not Facebook / Yelp / generic directories?
-----------------------------------------------
Those have no clean, ToS-compliant public API for cold prospecting. Google
Maps (Places) is the highest-signal, fully-supported source for blue-collar
service businesses — it carries phone, website, rating and review count in
one call. Add more sources by writing another function with the same shape
and registering it in lead_finder.py.
"""

from __future__ import annotations

import logging
import os
import time

import requests

from lead import Lead

log = logging.getLogger("josh.sources")

PLACES_TEXT_SEARCH = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS = "https://maps.googleapis.com/maps/api/place/details/json"


# ───────────────────────── Google Maps (Places API) ────────────────────────

def google_maps_search(query: str, location: str, max_results: int = 20) -> list[Lead]:
    """Search Google Places for `query` in `location` (e.g. "roofers", "Austin, TX").

    Requires env var GOOGLE_MAPS_API_KEY (Places API enabled). Returns [] with
    a warning if the key is missing.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        log.warning("GOOGLE_MAPS_API_KEY not set — skipping Google Maps source.")
        return []

    leads: list[Lead] = []
    params = {"query": f"{query} in {location}", "key": api_key}

    while len(leads) < max_results:
        try:
            resp = requests.get(PLACES_TEXT_SEARCH, params=params, timeout=15)
            data = resp.json()
        except requests.RequestException as e:
            log.warning(f"Places text search failed: {e}")
            break

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            log.warning(f"Places API status={status}: {data.get('error_message', '')}")
            break

        for place in data.get("results", []):
            if len(leads) >= max_results:
                break
            lead = _lead_from_place(place, api_key, category=query)
            if lead:
                leads.append(lead)

        token = data.get("next_page_token")
        if not token or len(leads) >= max_results:
            break
        # next_page_token needs a short delay before it becomes valid.
        time.sleep(2)
        params = {"pagetoken": token, "key": api_key}

    log.info(f"Google Maps: {len(leads)} leads for '{query}' in {location}.")
    return leads


def _lead_from_place(place: dict, api_key: str, category: str) -> Lead | None:
    place_id = place.get("place_id")
    if not place_id:
        return None

    lead = Lead(
        name=place.get("name", ""),
        category=category,
        google_rating=place.get("rating"),
        review_count=place.get("user_ratings_total", 0) or 0,
        source="google_maps",
    )

    # Place Details gives us phone + website + structured address.
    try:
        resp = requests.get(
            PLACES_DETAILS,
            params={
                "place_id": place_id,
                "fields": "formatted_phone_number,website,address_components",
                "key": api_key,
            },
            timeout=15,
        )
        details = resp.json().get("result", {})
    except requests.RequestException as e:
        log.debug(f"Place details failed for {lead.name}: {e}")
        details = {}

    lead.phone = details.get("formatted_phone_number", "")
    lead.website = details.get("website", "")
    lead.city, lead.state = _city_state(details.get("address_components", []))
    return lead


def _city_state(components: list[dict]) -> tuple[str, str]:
    city = state = ""
    for comp in components:
        types = comp.get("types", [])
        if "locality" in types:
            city = comp.get("long_name", "")
        elif "administrative_area_level_1" in types:
            state = comp.get("short_name", "")
    return city, state


# ─────────────────────── Instagram enrichment (optional) ───────────────────

def instagram_enrich(leads: list[Lead]) -> None:
    """Best-effort: attach IG username + follower count by searching the
    business name. Mutates leads in place. No-op if instagrapi/creds missing.
    """
    ig_user = os.environ.get("IG_USERNAME")
    ig_pass = os.environ.get("IG_PASSWORD")
    if not (ig_user and ig_pass):
        log.info("IG_USERNAME/IG_PASSWORD not set — skipping Instagram enrichment.")
        return

    try:
        from instagrapi import Client
    except ImportError:
        log.warning("instagrapi not installed — skipping Instagram enrichment.")
        return

    try:
        cl = Client()
        cl.delay_range = [2, 5]
        cl.login(ig_user, ig_pass)
    except Exception as e:
        log.warning(f"Instagram login failed — skipping enrichment: {e}")
        return

    for lead in leads:
        if lead.instagram:
            continue
        try:
            hits = cl.search_users(lead.name)
            if hits:
                top = hits[0]
                lead.instagram = top.username
                info = cl.user_info(top.pk)
                lead.follower_count = getattr(info, "follower_count", 0) or 0
            time.sleep(3)
        except Exception as e:
            log.debug(f"IG enrich failed for {lead.name}: {e}")
