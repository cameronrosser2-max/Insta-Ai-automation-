# industries.py
# Stub implementation — fill in INDUSTRIES with your industry data to enable
# personalised messaging. The keys must match those used in HASHTAGS (main.py).
#
# Example entry:
# INDUSTRIES = {
#     "hvac": {
#         "name": "HVAC",
#         "pain_points": ["customers can't find them online", "slow seasons hurt revenue"],
#         "roi_hook": "most HVAC sites pay for themselves with a single job.",
#         "avg_job_value": "$3,000–$8,000",
#     },
#     ...
# }

INDUSTRIES = {}


def detect_industry(text: str):
    """
    Given a block of text (e.g. an Instagram bio), return the matching
    industry key from INDUSTRIES, or None if no match is found.
    """
    return None


def get_industry_context(industry_key: str) -> dict:
    """
    Return the industry data dict for the given key, or an empty dict
    if the key is not found in INDUSTRIES.
    """
    return INDUSTRIES.get(industry_key, {})
