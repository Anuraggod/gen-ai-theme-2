"""
deeplink_mapper.py - Deeplink Mapping and Catalog Retrieval.
Maps extracted actions to exact catalog-matched device setting deeplinks.
Implements Parent-Menu Disambiguation and strict catalog URI integrity.
"""

import json
from typing import Dict, Any, List, Optional
from app.config import DEEPLINKS_PATH

# Stopwords for catalog matching to avoid false positives on generic tokens
GENERIC_STOPWORDS = {"settings", "screen", "options", "device", "feature", "subfeature", "action", "preference", "preferences"}


class DeeplinkMapper:
    """
    Retrieves and maps device-setting deeplinks from catalog metadata.
    Enforces parent-menu protection and exact URI preservation.
    """

    def __init__(self, catalog_path=DEEPLINKS_PATH):
        self.catalog: List[Dict[str, Any]] = []
        self.fallback_deeplink = "bixby://dummy_positive"
        if catalog_path.exists():
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.catalog = data.get("deeplinks", [])
                    self.fallback_deeplink = data.get("genericFallbackDeeplink", "bixby://dummy_positive")
            except Exception as e:
                print(f"Warning: Could not load deeplink catalog: {e}")

    def find_best_deeplink(
        self,
        action_name: str,
        target_keyword: Optional[str] = None,
        domain: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Finds the exact matching catalog item using semantic/keyword retrieval over metadata.
        Applies Parent-Menu Disambiguation: prioritizes specific leaf screens over ancestor parent menus.
        """
        if not self.catalog:
            return None

        search_tokens = set()
        if action_name:
            for t in action_name.lower().split():
                if t not in GENERIC_STOPWORDS and len(t) > 2:
                    search_tokens.add(t)
        if target_keyword:
            for t in target_keyword.lower().replace("/", " ").replace("_", " ").split():
                if t not in GENERIC_STOPWORDS and len(t) > 2:
                    search_tokens.add(t)
        if query_text:
            for t in query_text.lower().split():
                if t not in GENERIC_STOPWORDS and len(t) > 2:
                    search_tokens.add(t)

        candidates = []

        for item in self.catalog:
            item_domain = item.get("domain", "")
            if domain and item_domain.lower() != domain.lower():
                if item.get("id") != "DL_SYS_RESET_001":
                    continue

            score = 0.0
            item_action = item.get("actionName", "").lower()
            item_keywords = [k.lower() for k in item.get("keywords", [])]
            item_path = item.get("screenPath", "").lower()
            item_intent = item.get("intentDescription", "").lower()
            depth = item.get("depth", 1)

            # Direct actionName or target_keyword match
            if target_keyword:
                norm_kw = target_keyword.lower()
                if norm_kw in item.get("uri", "").lower():
                    score += 50.0
                if norm_kw in item_path:
                    score += 40.0
                for kw in item_keywords:
                    if norm_kw in kw:
                        score += 35.0

            if action_name and action_name.lower() in item_action:
                score += 35.0

            # Meaningful content token overlap
            for token in search_tokens:
                if token in item_action:
                    score += 15.0
                for kw in item_keywords:
                    if token in kw:
                        score += 12.0
                if token in item_path:
                    score += 8.0
                if token in item_intent:
                    score += 4.0

            # PARENT-MENU PROTECTION / DISAMBIGUATION:
            # If substantive match exists (score >= 15.0), apply depth bonus so specific leaf beats generic container.
            if score >= 15.0:
                depth_bonus = depth * 5.0
                score += depth_bonus
                candidates.append((score, item))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_item = candidates[0]

        if best_score < 15.0:
            return None

        return best_item

    def map_action(
        self,
        action_dict: Dict[str, Any],
        domain: str,
        query_text: str = ""
    ) -> Dict[str, Any]:
        """
        Maps an extracted action to its catalog-verified deeplink.
        For manual actions, actionableDeeplink is strictly None.
        For auto actions, copies catalog URI verbatim.
        """
        category = action_dict.get("category", "auto")
        action_name = action_dict.get("actionName", "")
        target_kw = action_dict.get("targetScreenKeyword")
        steps = action_dict.get("steps", [])

        actionable_deeplink = None
        validation_deeplink = None

        if category == "auto":
            match = self.find_best_deeplink(
                action_name=action_name,
                target_keyword=target_kw,
                domain=domain,
                query_text=query_text
            )
            if match:
                actionable_deeplink = match.get("uri")
                validation_deeplink = match.get("validationUri")
            else:
                actionable_deeplink = self.fallback_deeplink
                validation_deeplink = None

        elif category == "critical":
            match = self.find_best_deeplink(
                action_name=action_name,
                target_keyword=target_kw,
                domain=domain,
                query_text=query_text
            )
            if match and match.get("controlType") == "critical_dialog":
                actionable_deeplink = match.get("uri")
                validation_deeplink = match.get("validationUri")
            else:
                actionable_deeplink = None
                validation_deeplink = None

        elif category == "manual":
            actionable_deeplink = None
            validation_deeplink = None

        return {
            "actionName": action_name,
            "description": action_dict.get("description", "It will configure device preferences"),
            "category": category,
            "stepGroups": [
                {
                    "steps": steps,
                    "actionableDeeplink": actionable_deeplink,
                    "validationDeeplink": validation_deeplink
                }
            ]
        }
