# industries.py
# Industry data for the blue-collar / trade service businesses we target.
# The keys are used across the project (HASHTAGS in main.py, lead categories
# in lead_sources.py, and personalised messaging via build_message).

INDUSTRIES = {
    "roofing": {
        "name": "Roofing",
        "keywords": ["roof", "roofing", "roofer", "shingle", "re-roof", "gutter"],
        "pain_points": [
            "storm-season leads dry up without a strong online presence",
            "homeowners check reviews and websites before calling a roofer",
        ],
        "roi_hook": "one roofing job usually covers a year of website costs.",
        "avg_job_value": "$8,000–$25,000",
    },
    "plumbing": {
        "name": "Plumbing",
        "keywords": ["plumb", "plumbing", "plumber", "drain", "water heater", "rooter"],
        "pain_points": [
            "emergency calls go to whoever shows up first on Google",
            "no website means losing after-hours search traffic",
        ],
        "roi_hook": "most plumbing sites pay for themselves with a couple of calls.",
        "avg_job_value": "$300–$5,000",
    },
    "electrician": {
        "name": "Electrical",
        "keywords": ["electric", "electrical", "electrician", "sparky", "wiring", "panel"],
        "pain_points": [
            "customers can't find them online",
            "competitors with better sites win the bigger jobs",
        ],
        "roi_hook": "a single panel upgrade often pays for the whole site.",
        "avg_job_value": "$500–$10,000",
    },
    "hvac": {
        "name": "HVAC",
        "keywords": ["hvac", "heating", "cooling", "air condition", "ac repair", "furnace"],
        "pain_points": [
            "slow seasons hurt revenue without steady online leads",
            "homeowners compare HVAC companies online before buying",
        ],
        "roi_hook": "most HVAC sites pay for themselves with a single install.",
        "avg_job_value": "$3,000–$12,000",
    },
    "landscaping": {
        "name": "Landscaping & Lawn Care",
        "keywords": ["landscap", "lawn", "lawn care", "hardscape", "irrigation", "sod"],
        "pain_points": [
            "word-of-mouth dries up in the off-season",
            "high-end design clients expect a polished website",
        ],
        "roi_hook": "one design-build project covers years of hosting.",
        "avg_job_value": "$2,000–$30,000",
    },
    "tree_service": {
        "name": "Tree Service",
        "keywords": ["tree", "arborist", "tree removal", "stump", "tree trimming"],
        "pain_points": [
            "storm work goes to whoever ranks on Google first",
            "big removals need trust a website helps build",
        ],
        "roi_hook": "a single large removal covers the site many times over.",
        "avg_job_value": "$500–$8,000",
    },
    "painting": {
        "name": "Painting",
        "keywords": ["paint", "painting", "painter", "house painter", "cabinet refinish"],
        "pain_points": [
            "a portfolio site is the easiest way to win bids",
            "customers want to see before/after photos before calling",
        ],
        "roi_hook": "one repaint job usually pays for the whole website.",
        "avg_job_value": "$2,000–$10,000",
    },
    "pressure_washing": {
        "name": "Pressure Washing",
        "keywords": ["pressure wash", "power wash", "soft wash", "exterior cleaning"],
        "pain_points": [
            "it's a visual service that sells itself with photos",
            "most competitors have no real website at all",
        ],
        "roi_hook": "a few extra jobs a month easily covers a website.",
        "avg_job_value": "$200–$1,500",
    },
    "concrete": {
        "name": "Concrete & Masonry",
        "keywords": ["concrete", "masonry", "driveway", "patio", "foundation", "paver"],
        "pain_points": [
            "big pours go to contractors who look established online",
            "homeowners research before committing to concrete work",
        ],
        "roi_hook": "one driveway pour covers years of website costs.",
        "avg_job_value": "$3,000–$25,000",
    },
    "junk_removal": {
        "name": "Junk Removal",
        "keywords": ["junk removal", "junk hauling", "hauling", "debris removal", "cleanout"],
        "pain_points": [
            "it's a same-day, search-driven business",
            "no website means losing every 'junk removal near me' search",
        ],
        "roi_hook": "a couple of extra hauls a week pays for the site.",
        "avg_job_value": "$150–$800",
    },
    "flooring": {
        "name": "Flooring",
        "keywords": ["floor", "flooring", "hardwood", "tile", "lvp", "carpet", "epoxy"],
        "pain_points": [
            "customers want to browse product and photos before calling",
            "a portfolio site wins the bigger remodel jobs",
        ],
        "roi_hook": "one whole-home install covers the website many times over.",
        "avg_job_value": "$2,000–$15,000",
    },
    "fencing": {
        "name": "Fencing",
        "keywords": ["fence", "fencing", "fence install", "wood fence", "vinyl fence"],
        "pain_points": [
            "seasonal demand makes online leads critical",
            "homeowners compare fencing companies online first",
        ],
        "roi_hook": "one fence install easily covers the website.",
        "avg_job_value": "$2,000–$12,000",
    },
    "general_contractor": {
        "name": "General Contracting",
        "keywords": ["general contractor", "remodel", "renovation", "construction", "builder", "home addition"],
        "pain_points": [
            "big remodels require trust a strong site builds",
            "referrals slow down without an online presence to back them up",
        ],
        "roi_hook": "a single remodel covers the website for years.",
        "avg_job_value": "$10,000–$150,000",
    },
    "mobile_detailing": {
        "name": "Mobile Detailing",
        "keywords": ["detail", "detailing", "auto detail", "mobile detail", "ceramic coating"],
        "pain_points": [
            "booking by DM is messy — a site with online booking wins",
            "ceramic coating clients expect a professional web presence",
        ],
        "roi_hook": "a few coating jobs a month covers the whole site.",
        "avg_job_value": "$150–$2,000",
    },
    "towing": {
        "name": "Towing",
        "keywords": ["tow", "towing", "wrecker", "roadside", "recovery"],
        "pain_points": [
            "it's a 24/7 search-driven business",
            "no website means losing every roadside-emergency search",
        ],
        "roi_hook": "a handful of extra tows a month pays for the site.",
        "avg_job_value": "$75–$500",
    },
}


def detect_industry(text: str):
    """
    Given a block of text (e.g. an Instagram bio or business name), return the
    matching industry key from INDUSTRIES, or None if no match is found.

    Matching is keyword-based and case-insensitive. The industry with the most
    keyword hits wins; ties are broken by the first match found.
    """
    if not text:
        return None

    text_lc = text.lower()
    best_key = None
    best_hits = 0

    for key, data in INDUSTRIES.items():
        hits = sum(1 for kw in data.get("keywords", []) if kw in text_lc)
        if hits > best_hits:
            best_hits = hits
            best_key = key

    return best_key


def get_industry_context(industry_key: str) -> dict:
    """
    Return the industry data dict for the given key, or an empty dict
    if the key is not found in INDUSTRIES.
    """
    return INDUSTRIES.get(industry_key, {})
