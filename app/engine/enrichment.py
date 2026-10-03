"""
enrichment.py - Query Enrichment Stage.
Transforms colloquial, unstructured, or ambiguous customer complaints
into normalized technical intents and generates 8-10 distinct semantic variations across registers.
"""

import re
from typing import List, Dict, Any, Tuple


# Slang & Colloquialisms normalization patterns
COLLOQUIAL_MAP = {
    r"\bswipe\s+thing\b": "swipe navigation gesture",
    r"\bswiping\b": "swipe gesture navigation",
    r"\b(moves|moving|goes|going)\s+(up\s+and\s+down|vertically)\b": "moving vertically",
    r"\b(up\s+and\s+down)\b": "moving vertically",
    r"\b(left\s+and\s+right)\b": "horizontally",
    r"\b(dies|dying|draining|drains)\s+(super\s+fast|very\s+fast|fast|quickly)\b": "drains rapidly",
    r"\bfuzzy\b": "blurry out of focus",
    r"\blaggy\b": "system lag UI stutter",
    r"\bfreezing\b": "system freeze sluggish performance",
    r"\b(wont|won't)\s+focus\b": "autofocus failure",
    r"\bpower\s+saver\b": "power saving mode",
    r"\bbatry\b": "battery",
    r"\bphon\b": "phone",
    r"\bcamra\b": "camera",
    r"\bblury\b": "blurry",
    r"\bnavigaton\b": "navigation",
    r"\bgesturs\b": "gestures"
}

# Domain keywords mapping
DOMAIN_KEYWORDS = {
    "Display": [
        "swipe", "navigation", "gesture", "gestures", "screen", "display",
        "brightness", "dark mode", "timeout", "orientation", "vertical", "horizontal"
    ],
    "Battery": [
        "battery", "drain", "charge", "power", "saving", "saver", "percentage",
        "dying", "depletion", "discharge", "sleeping apps"
    ],
    "Camera": [
        "camera", "photo", "picture", "blurry", "focus", "autofocus",
        "lens", "fuzzy", "shutter", "resolution"
    ],
    "Performance": [
        "lag", "laggy", "slow", "freeze", "freezing", "stutter", "ram",
        "memory", "storage", "cache", "clean", "reset", "sluggish"
    ]
}


class QueryEnricher:
    """
    Enriches and normalizes raw user troubleshooting queries.
    Generates 8-10 distinct variations across defined linguistic registers.
    """

    def __init__(self):
        self.colloquial_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in COLLOQUIAL_MAP.items()
        ]

    def normalize_query(self, raw_query: str) -> str:
        """
        Cleans and normalizes query text into standard technical terminology.
        """
        normalized = raw_query.strip()
        # Clean extra punctuation
        normalized = re.sub(r"[^\w\s\-\']", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        for pattern, replacement in self.colloquial_patterns:
            normalized = pattern.sub(replacement, normalized)

        return re.sub(r"\s+", " ", normalized).strip()

    def detect_domain(self, query: str) -> str:
        """
        Detects primary device domain from query keywords.
        Defaults to Display if ambiguous.
        """
        lowered = query.lower()
        domain_scores = {d: 0 for d in DOMAIN_KEYWORDS}

        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in lowered:
                    domain_scores[domain] += 1

        best_domain = max(domain_scores, key=domain_scores.get)
        if domain_scores[best_domain] == 0:
            return "Display"
        return best_domain

    def generate_variations(self, raw_query: str, domain: str) -> List[Dict[str, str]]:
        """
        Generates 8-10 distinct query variations covering multiple registers:
        1. Formal / Technical
        2. Casual / Conversational
        3. Keyword-Only
        4. Frustrated / Emotional
        5. Typo-Inclusive
        6. Intent-Focused
        7. Question-Form
        8. Symptom-Description
        9. Action-Oriented
        10. Contextual / Device-specific
        """
        normalized = self.normalize_query(raw_query)
        words = [w for w in re.findall(r"\b\w+\b", normalized.lower()) if len(w) > 2]
        keywords_str = " ".join(words[:5])

        if domain == "Display":
            variations = [
                {"register": "formal", "text": f"Device touch interface orientation abnormal: {normalized}."},
                {"register": "casual", "text": f"My phone swipe gestures are acting up: {raw_query}."},
                {"register": "keyword", "text": f"navigation gestures swipe direction {keywords_str}"},
                {"register": "frustrated", "text": f"Why is my screen swipe broken and moving wrong direction, fix this!"},
                {"register": "typo", "text": f"phne swip gesture navgation issue {keywords_str}"},
                {"register": "intent", "text": f"How to change and configure swipe gesture navigation preferences."},
                {"register": "question", "text": f"Where in settings can I fix the swipe gesture direction?"},
                {"register": "symptom", "text": f"Swipe gesture navigation moving in unexpected orientation."},
                {"register": "action_oriented", "text": f"Adjust navigation bar settings to restore horizontal swipe gestures."},
                {"register": "contextual", "text": f"After recent update phone swipe navigation gestures inverted vertically."}
            ]
        elif domain == "Battery":
            variations = [
                {"register": "formal", "text": f"High rate of battery discharge and power drain: {normalized}."},
                {"register": "casual", "text": f"My phone battery is dying way too fast during normal use."},
                {"register": "keyword", "text": f"battery drain fast power saving mode {keywords_str}"},
                {"register": "frustrated", "text": f"The battery is dropping rapidly in just hours, this is ridiculous!"},
                {"register": "typo", "text": f"batry draning vry fast power saver {keywords_str}"},
                {"register": "intent", "text": f"How to enable battery saver and limit background app power usage."},
                {"register": "question", "text": f"Why is my battery draining so quickly and how to stop it?"},
                {"register": "symptom", "text": f"Rapid battery percentage drop and short device runtime."},
                {"register": "action_oriented", "text": f"Enable power saving limits and inspect sleeping apps in device care."},
                {"register": "contextual", "text": f"Phone battery drains rapidly even on standby mode."}
            ]
        elif domain == "Camera":
            variations = [
                {"register": "formal", "text": f"Camera optical focus degradation: {normalized}."},
                {"register": "casual", "text": f"Camera photos look blurry and it wont focus at all."},
                {"register": "keyword", "text": f"camera blurry autofocus reset settings {keywords_str}"},
                {"register": "frustrated", "text": f"Every photo I take is out of focus and completely ruined!"},
                {"register": "typo", "text": f"camra blury and out of focs lens {keywords_str}"},
                {"register": "intent", "text": f"How to clean lens and reset camera autofocus calibration."},
                {"register": "question", "text": f"How do I fix a blurry out of focus phone camera?"},
                {"register": "symptom", "text": f"Camera preview remains blurry with autofocus failure."},
                {"register": "action_oriented", "text": f"Wipe camera lens and restore camera settings to default."},
                {"register": "contextual", "text": f"Camera produces blurry images after opening standard photo mode."}
            ]
        else:  # Performance
            variations = [
                {"register": "formal", "text": f"System responsiveness degraded with frame latency: {normalized}."},
                {"register": "casual", "text": f"My phone is super laggy and keeps freezing constantly."},
                {"register": "keyword", "text": f"phone lag slow clean memory storage {keywords_str}"},
                {"register": "frustrated", "text": f"The whole UI is stuttering and apps take forever to open!"},
                {"register": "typo", "text": f"phon laging and frezing slow ram {keywords_str}"},
                {"register": "intent", "text": f"How to clear RAM memory and delete storage cache to boost speed."},
                {"register": "question", "text": "What steps can optimize device performance and stop freezing?"},
                {"register": "symptom", "text": "Sluggish app launching, high memory pressure, and UI stutter."},
                {"register": "action_oriented", "text": "Optimize device memory and clean storage cached data."},
                {"register": "contextual", "text": "Device experiences heavy lag and app slowdown during multitasking."}
            ]

        return variations[:10]

    def enrich(self, raw_query: str, domain_hint: str = None) -> Dict[str, Any]:
        """
        Full enrichment execution pipeline.
        """
        domain = domain_hint if domain_hint and domain_hint in DOMAIN_KEYWORDS else self.detect_domain(raw_query)
        normalized = self.normalize_query(raw_query)
        variations = self.generate_variations(raw_query, domain)

        return {
            "rawQuery": raw_query,
            "normalizedQuery": normalized,
            "domain": domain,
            "variations": variations,
            "variationCount": len(variations)
        }
