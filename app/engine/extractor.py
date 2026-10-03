"""
extractor.py - Structure Extraction Stage.
Extracts structured troubleshooting goals, actions, and imperative steps
strictly grounded in reference context (SIIS articles or supplied context).
Enforces zero-hallucination policy: does not invent ungrounded steps or actions.
"""

import json
from typing import Dict, Any, List, Optional
from app.config import SIIS_PATH


class StructureExtractor:
    """
    Extracts grounded troubleshooting structure from reference knowledge.
    Refuses to invent ungrounded troubleshooting instructions when no reference exists.
    """

    def __init__(self, siis_path=SIIS_PATH):
        self.articles: List[Dict[str, Any]] = []
        if siis_path.exists():
            try:
                with open(siis_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.articles = data.get("articles", [])
            except Exception as e:
                print(f"Warning: Could not load SIIS responses: {e}")

    def find_reference_article(self, normalized_query: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        Finds the best matching grounded reference article based on domain and substantive symptom overlap.
        Returns None if no grounded match is found (zero-hallucination guarantee).
        """
        words = set(normalized_query.lower().split())
        best_match = None
        highest_score = 0

        for article in self.articles:
            if article.get("domain", "").lower() != domain.lower():
                continue

            score = 0
            for symptom in article.get("symptoms", []):
                symptom_words = set(symptom.lower().split())
                overlap = len(words.intersection(symptom_words))
                if overlap > score:
                    score = overlap

            topic_words = set(article.get("topic", "").lower().split())
            if words.intersection(topic_words):
                score += 2

            if score > highest_score:
                highest_score = score
                best_match = article

        # Only return match if there was genuine grounded overlap
        if highest_score >= 1:
            return best_match

        return None

    def extract_structure(
        self,
        normalized_query: str,
        domain: str,
        custom_reference: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts structured goal, title, score, and actions strictly grounded in reference text.
        Returns None if no grounded reference exists to prevent hallucinating instructions.
        """
        article = self.find_reference_article(normalized_query, domain)

        if not article and not custom_reference:
            # Zero-hallucination: refuse to fabricate ungrounded actions
            return None

        topic = article.get("topic", domain)
        raw_actions = article.get("recommendedActions", [])

        # Assign confidence score based on grounded match
        confidence = 0.94 if article else 0.70

        # Topic formatting: strictly "Follow these steps to perform this <Topic> Troubleshooting"
        goal_text = f"Follow these steps to perform this {topic} Troubleshooting"

        # Title: strictly 2-3 words, sentence case
        title_map = {
            "Swipe Navigation": "Swipe navigation settings",
            "Battery Drain": "Battery fast drain",
            "Camera Focus": "Camera focus issue",
            "Device Performance": "Device performance lag"
        }
        title = title_map.get(topic, f"{topic} settings" if len(topic.split()) <= 2 else f"{domain} issue")
        title_words = title.split()
        if len(title_words) < 2:
            title = f"{title} settings"
        elif len(title_words) > 3:
            title = " ".join(title_words[:3])

        return {
            "goal": goal_text,
            "title": title,
            "score": confidence,
            "domain": domain,
            "topic": topic,
            "extractedActions": raw_actions
        }
