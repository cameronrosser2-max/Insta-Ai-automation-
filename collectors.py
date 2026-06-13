#!/usr/bin/env python3
"""
collectors.py — Pluggable lead sources.

Each collector takes a target category + geography and returns a list of Lead
records. Every collector is optional and self-disabling: if its credentials or
API key are missing, it logs why and returns an empty list instead of crashing.
This lets the pipeline run with whatever sources you've actually configured.

Configure via environment variables:
    IG_USERNAME / IG_PASSWORD     -> Instagram (instagrapi)
    GOOGLE_MAPS_API_KEY           -> Google Maps / Places
    (Facebook & directory scraping require per-provider setup — see stubs.)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Iterable

from leads import Lead

log = logging.getLogger("josh.collectors")


# ─────────────────────────────────────────────────────────────────────────────
# Google Maps / Places  (official API — reliable, ToS-friendly)
# ─────────────────────────────────────────────────────────────────────────────

def collect_google_maps(category: str, location: str, limit: int = 20) -> list[Lead]:
    """
    Find businesses via the Google Places Text Search + Details APIs.
    Requires GOOGLE_MAPS_API_KEY. Returns [] (with a log line) if unset.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        log.info("  google_maps: skipped (set GOOGLE_MAPS_API_KEY to enable)")
        return []

    query = f"{category} in {location}"
    search_url = (
        "https://maps.googleapis.com/maps/api/place/textsearch/json?"
        + urllib.parse.urlencode({"query": query, "key": api_key})
    )

    leads: list[Lead] = []
    try:
        results = _get_json(search_url).get("results", [])[:limit]
    except Exception as e:
        log.warning(f"  google_maps: search failed: {e}")
        return []

    city, state = _split_location(location)
    for r in results:
        place_id = r.get("place_id")
        details = _place_details(place_id, api_key) if place_id else {}
        leads.append(Lead(
            name=r.get("name", ""),
            category=category,
            source="google_maps",
            phone=details.get("formatted_phone_number", ""),
            website=details.get("website", ""),
            city=city,
            state=state,
            review_count=r.get("user_ratings_total"),
            google_rating=r.get("rating"),
        ))
        time.sleep(0.2)  # be gentle with the API

    log.info(f"  google_maps: {len(leads)} businesses for '{query}'")
    return leads


def _place_details(place_id: str, api_key: str) -> dict:
    url = (
        "https://maps.googleapis.com/maps/api/place/details/json?"
        + urllib.parse.urlencode({
            "place_id": place_id,
            "fields": "formatted_phone_number,website",
            "key": api_key,
        })
    )
    try:
        return _get_json(url).get("result", {})
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Instagram  (instagrapi — optional dependency)
# ─────────────────────────────────────────────────────────────────────────────

def collect_instagram(hashtags: Iterable[str], category: str, limit: int = 30) -> list[Lead]:
    """
    Pull business accounts from hashtags. Requires IG_USERNAME / IG_PASSWORD and
    the `instagrapi` package. Returns [] (with a log line) if either is missing.
    """
    if not (os.environ.get("IG_USERNAME") and os.environ.get("IG_PASSWORD")):
        log.info("  instagram: skipped (set IG_USERNAME / IG_PASSWORD to enable)")
        return []
    try:
        from instagrapi import Client  # lazy: optional dep
    except ImportError:
        log.info("  instagram: skipped (run `pip install instagrapi` to enable)")
        return []

    cl = Client()
    cl.delay_range = [2, 5]
    try:
        cl.login(os.environ["IG_USERNAME"], os.environ["IG_PASSWORD"])
    except Exception as e:
        log.warning(f"  instagram: login failed: {e}")
        return []

    seen: dict[str, Lead] = {}
    for tag in hashtags:
        try:
            for media in cl.hashtag_medias_recent_v1(tag, amount=limit):
                u = media.user
                uname = (u.username or "").lower()
                if not uname or uname in seen:
                    continue
                info = _ig_user_details(cl, u.pk)
                seen[uname] = Lead(
                    name=u.full_name or u.username,
                    category=category,
                    source="instagram",
                    instagram_username=u.username,
                    email=info.get("email", ""),
                    phone=info.get("phone", ""),
                    website=info.get("website", ""),
                    follower_count=info.get("follower_count"),
                )
            time.sleep(3)
        except Exception as e:
            log.warning(f"  instagram: skipped #{tag}: {e}")

    log.info(f"  instagram: {len(seen)} accounts for {category}")
    return list(seen.values())


def _ig_user_details(cl, user_id) -> dict:
    """Best-effort pull of contact fields from an IG profile."""
    try:
        u = cl.user_info(user_id)
        return {
            "email": getattr(u, "public_email", "") or "",
            "phone": getattr(u, "public_phone_number", "") or "",
            "website": getattr(u, "external_url", "") or "",
            "follower_count": getattr(u, "follower_count", None),
        }
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Facebook & local directories
# ─────────────────────────────────────────────────────────────────────────────

def collect_facebook(category: str, location: str, limit: int = 20) -> list[Lead]:
    """
    Facebook Pages lead source.

    Facebook has no open business-search API; viable routes are the Graph API
    (Page access tokens, limited to pages you manage) or a licensed third-party
    data provider. Wire your provider's client in here and map results to Lead.
    Disabled until FACEBOOK_PROVIDER_KEY is configured.
    """
    if not os.environ.get("FACEBOOK_PROVIDER_KEY"):
        log.info("  facebook: skipped (no FACEBOOK_PROVIDER_KEY / provider configured)")
        return []
    log.info("  facebook: provider key set but no provider client wired — returning []")
    return []


def collect_directories(category: str, location: str, limit: int = 20) -> list[Lead]:
    """
    Local-directory lead source (Yelp, Yellow Pages, Angi, etc.).

    Yelp Fusion is the cleanest option. Set YELP_API_KEY to enable; other
    directories can be added as additional branches mapping their results to Lead.
    """
    api_key = os.environ.get("YELP_API_KEY")
    if not api_key:
        log.info("  directories: skipped (set YELP_API_KEY to enable Yelp Fusion)")
        return []

    city, state = _split_location(location)
    url = (
        "https://api.yelp.com/v3/businesses/search?"
        + urllib.parse.urlencode({"term": category, "location": location, "limit": limit})
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log.warning(f"  directories: Yelp search failed: {e}")
        return []

    leads: list[Lead] = []
    for b in data.get("businesses", []):
        phones = b.get("display_phone", "")
        leads.append(Lead(
            name=b.get("name", ""),
            category=category,
            source="directory",
            phone=phones,
            website=b.get("url", ""),   # Yelp URL; replace with real site if resolvable
            city=(b.get("location", {}).get("city") or city),
            state=(b.get("location", {}).get("state") or state),
            review_count=b.get("review_count"),
            google_rating=b.get("rating"),
        ))
    log.info(f"  directories: {len(leads)} businesses for '{category} in {location}'")
    return leads


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_json(url: str, timeout: float = 15.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "josh-lead-bot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _split_location(location: str) -> tuple[str, str]:
    """'Austin, TX' -> ('Austin', 'TX')."""
    parts = [p.strip() for p in re.split(r"[,/]", location) if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return (parts[0] if parts else ""), ""
