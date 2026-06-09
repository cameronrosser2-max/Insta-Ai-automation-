# industries.py
# Industry data used for lead detection and personalised messaging.
# Keys match those used in HASHTAGS (main.py) and in lead_qualifier.py.
#
# Each entry provides:
#   name           — human-readable industry label
#   pain_points    — common business pains, surfaced in cold messaging
#   roi_hook       — one-line value proposition for a new website
#   avg_job_value  — typical ticket size, used to frame ROI
#   keywords       — bio/profile keywords used by detect_industry()

INDUSTRIES = {
    "roofing": {
        "name": "roofing",
        "pain_points": [
            "storm season brings a flood of calls you can't all answer",
            "homeowners shop around and pick whoever shows up first online",
        ],
        "roi_hook": "a single re-roof covers a year of website costs many times over.",
        "avg_job_value": "$8,000–$25,000",
        "keywords": ["roof", "roofer", "roofing", "shingle", "re-roof"],
    },
    "plumbing": {
        "name": "plumbing",
        "pain_points": [
            "emergency calls go to whoever ranks first on Google",
            "customers can't tell you apart from the next plumber online",
        ],
        "roi_hook": "two extra emergency calls a month pays for the whole site.",
        "avg_job_value": "$300–$5,000",
        "keywords": ["plumb", "plumber", "plumbing", "drain", "water heater"],
    },
    "electrician": {
        "name": "electrical",
        "pain_points": [
            "homeowners want a licensed pro they can verify online",
            "you're losing panel-upgrade jobs to shops with better websites",
        ],
        "roi_hook": "one panel upgrade or EV charger install covers the site.",
        "avg_job_value": "$200–$6,000",
        "keywords": ["electric", "electrician", "sparky", "wiring", "panel"],
    },
    "hvac": {
        "name": "HVAC",
        "pain_points": [
            "customers can't find you when the AC dies in July",
            "slow shoulder seasons hurt cash flow",
        ],
        "roi_hook": "most HVAC sites pay for themselves with a single install.",
        "avg_job_value": "$3,000–$12,000",
        "keywords": ["hvac", "heating", "cooling", "air conditioning", "furnace"],
    },
    "landscaping": {
        "name": "landscaping",
        "pain_points": [
            "you rely on word-of-mouth and it dries up in winter",
            "higher-end clients check you out online before calling",
        ],
        "roi_hook": "one design/install contract pays for the site for years.",
        "avg_job_value": "$500–$15,000",
        "keywords": ["landscap", "lawn", "lawncare", "hardscape", "sod"],
    },
    "tree_service": {
        "name": "tree service",
        "pain_points": [
            "big removal jobs go to whoever looks most professional online",
            "insurance/storm work needs a credible web presence",
        ],
        "roi_hook": "one large removal covers your website for the year.",
        "avg_job_value": "$500–$8,000",
        "keywords": ["tree", "arborist", "tree service", "tree removal", "stump"],
    },
    "painting": {
        "name": "painting",
        "pain_points": [
            "before/after photos sell jobs but you've nowhere to show them",
            "homeowners compare painters online before requesting a quote",
        ],
        "roi_hook": "one repaint job covers the site many times over.",
        "avg_job_value": "$1,500–$10,000",
        "keywords": ["paint", "painter", "painting", "housepainter"],
    },
    "pressure_washing": {
        "name": "pressure washing",
        "pain_points": [
            "it's a visual service and you've no gallery to prove results",
            "neighbors search 'pressure washing near me' and find competitors",
        ],
        "roi_hook": "a handful of driveways a month and the site pays for itself.",
        "avg_job_value": "$150–$1,500",
        "keywords": ["pressure wash", "power wash", "softwash", "soft wash"],
    },
    "concrete": {
        "name": "concrete",
        "pain_points": [
            "driveway and patio jobs go to the most credible-looking contractor",
            "you can't showcase past pours to win bigger bids",
        ],
        "roi_hook": "one driveway pour covers the website for a year.",
        "avg_job_value": "$3,000–$20,000",
        "keywords": ["concrete", "masonry", "flatwork", "driveway", "patio"],
    },
    "junk_removal": {
        "name": "junk removal",
        "pain_points": [
            "this is an online-search business and you're invisible on Google",
            "customers book whoever they can find and trust fastest",
        ],
        "roi_hook": "a few extra hauls a month pays for the site easily.",
        "avg_job_value": "$150–$800",
        "keywords": ["junk removal", "hauling", "debris", "cleanout"],
    },
    "flooring": {
        "name": "flooring",
        "pain_points": [
            "buyers want to see your work before committing to a remodel",
            "you're losing big install jobs to shops with real websites",
        ],
        "roi_hook": "one install job covers the site many times over.",
        "avg_job_value": "$2,000–$15,000",
        "keywords": ["floor", "flooring", "hardwood", "tile", "lvp", "carpet"],
    },
    "fencing": {
        "name": "fencing",
        "pain_points": [
            "homeowners price-compare fence installers online first",
            "you've no easy way to show material and style options",
        ],
        "roi_hook": "one fence install covers the website for the year.",
        "avg_job_value": "$2,000–$12,000",
        "keywords": ["fence", "fencing", "fence install"],
    },
    "general_contractor": {
        "name": "general contracting",
        "pain_points": [
            "remodel clients vet you online before trusting you in their home",
            "you can't show a portfolio of completed projects",
        ],
        "roi_hook": "a single remodel project pays for years of website costs.",
        "avg_job_value": "$10,000–$100,000",
        "keywords": ["contractor", "remodel", "construction", "general contractor", "builder"],
    },
    "mobile_detailing": {
        "name": "mobile detailing",
        "pain_points": [
            "customers find detailers entirely through online search",
            "you've no online booking so leads slip away",
        ],
        "roi_hook": "a few extra details a month and the site pays for itself.",
        "avg_job_value": "$100–$500",
        "keywords": ["detail", "detailing", "mobile detail", "auto detail", "car detail"],
    },
    "towing": {
        "name": "towing",
        "pain_points": [
            "stranded drivers call whoever shows up first on Google",
            "you're missing roadside calls you'd win with better visibility",
        ],
        "roi_hook": "a handful of extra tows a month covers the site.",
        "avg_job_value": "$75–$500",
        "keywords": ["tow", "towing", "wrecker", "roadside", "recovery"],
    },
}


def detect_industry(text: str):
    """
    Given a block of text (e.g. an Instagram bio or business name), return the
    matching industry key from INDUSTRIES, or None if no match is found.
    The first industry with a keyword present in the text wins.
    """
    if not text:
        return None
    low = text.lower()
    best = None
    for key, data in INDUSTRIES.items():
        for kw in data.get("keywords", []):
            if kw in low:
                # Prefer longer keyword matches (more specific)
                if best is None or len(kw) > best[1]:
                    best = (key, len(kw))
    return best[0] if best else None


def get_industry_context(industry_key: str) -> dict:
    """
    Return the industry data dict for the given key, or an empty dict
    if the key is not found in INDUSTRIES.
    """
    return INDUSTRIES.get(industry_key, {})
