# industries.py
# Industry context used for (a) detecting a business's trade from free text
# (bio / name / website) and (b) personalising outreach in main.py.
#
# Keys are the canonical category identifiers used across the project
# (HASHTAGS in main.py, TARGET_CATEGORIES in leads.py).

INDUSTRIES = {
    "roofing": {
        "name": "Roofing",
        "pain_points": [
            "storm season means leads come in bursts and a slow site loses them",
            "homeowners check you out online before they ever call",
        ],
        "roi_hook": "one roof replacement usually covers a whole year of website cost.",
        "avg_job_value": "$8,000–$25,000",
        "keywords": ["roof", "roofing", "roofer", "shingle", "gutter"],
    },
    "plumbing": {
        "name": "Plumbing",
        "pain_points": [
            "emergency jobs go to whoever shows up first on Google",
            "customers can't book you after hours without a website",
        ],
        "roi_hook": "a couple of extra service calls a month pays for the site.",
        "avg_job_value": "$300–$3,000",
        "keywords": ["plumb", "plumber", "plumbing", "drain", "sewer", "water heater"],
    },
    "electrician": {
        "name": "Electrical",
        "pain_points": [
            "people want to see your license and reviews before letting you in",
            "panel and rewire jobs go to the contractor who looks established online",
        ],
        "roi_hook": "one panel upgrade covers the website easily.",
        "avg_job_value": "$200–$5,000",
        "keywords": ["electric", "electrician", "electrical", "wiring", "sparky"],
    },
    "hvac": {
        "name": "HVAC",
        "pain_points": [
            "customers can't find them online",
            "slow seasons hurt revenue and a site keeps the phone ringing",
        ],
        "roi_hook": "most HVAC sites pay for themselves with a single install.",
        "avg_job_value": "$3,000–$8,000",
        "keywords": ["hvac", "heating", "cooling", "air condition", "ac repair", "furnace"],
    },
    "landscaping": {
        "name": "Landscaping & Lawn Care",
        "pain_points": [
            "before/after photos sell the work but there's nowhere to show them",
            "recurring maintenance contracts are hard to win without a site",
        ],
        "roi_hook": "one seasonal contract covers the website.",
        "avg_job_value": "$500–$10,000",
        "keywords": ["landscap", "lawn", "lawncare", "hardscape", "irrigation"],
    },
    "tree_service": {
        "name": "Tree Service",
        "pain_points": [
            "high-ticket removals go to whoever looks most credible online",
            "insurance and credentials need somewhere to live online",
        ],
        "roi_hook": "one large removal more than covers the site.",
        "avg_job_value": "$500–$5,000",
        "keywords": ["tree service", "tree removal", "arborist", "stump", "tree trimming"],
    },
    "painting": {
        "name": "Painting",
        "pain_points": [
            "portfolios live on a phone instead of a website",
            "estimates get lost without an online quote form",
        ],
        "roi_hook": "one interior repaint covers a year of website cost.",
        "avg_job_value": "$1,500–$10,000",
        "keywords": ["paint", "painter", "painting", "housepainter"],
    },
    "pressure_washing": {
        "name": "Pressure Washing",
        "pain_points": [
            "it's a visual service with nowhere to show before/after shots",
            "competitors with simple sites get the Google calls",
        ],
        "roi_hook": "a handful of driveways pays for the whole site.",
        "avg_job_value": "$150–$1,500",
        "keywords": ["pressure wash", "power wash", "softwash", "soft wash"],
    },
    "concrete": {
        "name": "Concrete & Masonry",
        "pain_points": [
            "big driveway and patio jobs go to contractors who look established",
            "no website means no way to show past pours",
        ],
        "roi_hook": "one driveway pour covers the website.",
        "avg_job_value": "$2,000–$15,000",
        "keywords": ["concrete", "masonry", "mason", "driveway", "patio", "foundation"],
    },
    "junk_removal": {
        "name": "Junk Removal",
        "pain_points": [
            "it's an impulse, search-driven service — no site means no calls",
            "online booking wins jobs while you're on a run",
        ],
        "roi_hook": "a few extra hauls a month covers the site.",
        "avg_job_value": "$150–$800",
        "keywords": ["junk removal", "junk haul", "hauling", "debris removal", "cleanout"],
    },
    "flooring": {
        "name": "Flooring",
        "pain_points": [
            "customers want to browse materials and past installs first",
            "showroom-style galleries need a real website",
        ],
        "roi_hook": "one flooring job covers the website.",
        "avg_job_value": "$2,000–$15,000",
        "keywords": ["floor", "flooring", "hardwood", "tile", "laminate", "lvp"],
    },
    "fencing": {
        "name": "Fencing",
        "pain_points": [
            "homeowners compare fence styles and quotes online first",
            "no site means missing out on neighborhood word-of-mouth searches",
        ],
        "roi_hook": "one fence install covers the website.",
        "avg_job_value": "$2,000–$12,000",
        "keywords": ["fence", "fencing", "fence install", "fence company"],
    },
    "general_contractor": {
        "name": "General Contracting",
        "pain_points": [
            "remodels are high-trust — clients vet you online before signing",
            "a portfolio site separates you from the unlicensed guys",
        ],
        "roi_hook": "one remodel covers years of website cost.",
        "avg_job_value": "$10,000–$100,000",
        "keywords": ["general contractor", "remodel", "construction", "contractor", "renovation"],
    },
    "mobile_detailing": {
        "name": "Mobile Detailing",
        "pain_points": [
            "it's booking-driven — no online scheduler means lost jobs",
            "before/after shots and packages need a home online",
        ],
        "roi_hook": "a few extra details a month covers the site.",
        "avg_job_value": "$100–$500",
        "keywords": ["detailing", "auto detail", "mobile detail", "car detail", "ceramic coating"],
    },
    "towing": {
        "name": "Towing",
        "pain_points": [
            "stranded drivers search and call the first result — speed is everything",
            "no website means losing 24/7 emergency calls to competitors",
        ],
        "roi_hook": "a handful of extra tows a month covers the site.",
        "avg_job_value": "$75–$500",
        "keywords": ["tow", "towing", "wrecker", "roadside", "recovery"],
    },
}


def detect_industry(text: str):
    """
    Given a block of text (e.g. an Instagram bio, business name, or website),
    return the best-matching industry key from INDUSTRIES, or None if no
    keyword matches.
    """
    if not text:
        return None
    low = text.lower()
    best_key = None
    best_hits = 0
    for key, data in INDUSTRIES.items():
        hits = sum(1 for kw in data.get("keywords", []) if kw in low)
        if hits > best_hits:
            best_key, best_hits = key, hits
    return best_key


def get_industry_context(industry_key: str) -> dict:
    """
    Return the industry data dict for the given key, or an empty dict
    if the key is not found in INDUSTRIES.
    """
    return INDUSTRIES.get(industry_key, {})
