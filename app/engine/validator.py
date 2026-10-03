"""
validator.py - Strict Deterministic Validation & Zero URL Leakage Enforcement.
Rejects invalid outputs rather than silently repairing them:
- Goal pattern ("Follow these steps to perform this <Topic> Troubleshooting" / "Configuration")
- Title length (strictly 2-3 words)
- Description format (strictly 5-7 words, begins with 'It will')
- Score range (0.0 <= score <= 1.0)
- Action category hierarchy and critical sequencing (critical strictly last)
- Manual category restrictions (no actionable/validation deeplink)
- Zero URL Leakage (strictly rejects HTTP, HTTPS, www., and markdown links)
- Catalog Deeplink Integrity (verifies URIs exist in catalog or match allowed dummy_positive)
"""

import re
import json
from typing import Dict, Any, List, Tuple, Optional, Set
from pydantic import ValidationError
from app.schema import TroubleshootingGoal, Action, StepGroup
from app.config import DEEPLINKS_PATH


class OutputValidator:
    """
    Deterministic programmatic validator enforcing strict schema rules and deeplink integrity.
    Rejects invalid outputs explicitly without silent corruption.
    """

    # URL detection pattern
    URL_PATTERN = re.compile(
        r"(https?://[^\s]+|www\.[^\s]+|\[.*?\]\(https?://.*?\)|[a-zA-Z0-9.-]+\.(?:com|org|net|io|edu|gov)[^\s]*)",
        re.IGNORECASE
    )

    GOAL_PATTERN = re.compile(
        r"^Follow these steps to perform this (.+?) (Troubleshooting|Configuration)$",
        re.IGNORECASE
    )

    def __init__(self, catalog_path=DEEPLINKS_PATH):
        self.allowed_uris: Set[str] = {"bixby://dummy_positive"}
        if catalog_path and catalog_path.exists():
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("deeplinks", []):
                        if item.get("uri"):
                            self.allowed_uris.add(item["uri"])
                        if item.get("validationUri"):
                            self.allowed_uris.add(item["validationUri"])
            except Exception as e:
                print(f"Warning: Could not load catalog for validation: {e}")

    def check_url_leak(self, text: str) -> bool:
        """
        Returns True if a prohibited URL is detected.
        """
        if not text:
            return False
        return bool(self.URL_PATTERN.search(text))

    def validate_plan(
        self,
        plan_dict: Dict[str, Any]
    ) -> Tuple[bool, Optional[TroubleshootingGoal], List[str]]:
        """
        Strictly validates a troubleshooting plan dictionary against all hard requirements.
        Returns (is_valid, validated_pydantic_goal, list_of_errors).
        Rejects invalid plans without silent modification.
        """
        errors = []

        if not isinstance(plan_dict, dict):
            return False, None, ["Plan must be a JSON dictionary."]

        # 1. Goal format check
        goal = plan_dict.get("goal")
        if not goal or not isinstance(goal, str):
            errors.append("Missing or non-string 'goal' field.")
        elif self.check_url_leak(goal):
            errors.append(f"Prohibited URL leak detected in goal: '{goal}'.")
        elif not self.GOAL_PATTERN.match(goal.strip()):
            errors.append(
                f"Goal does not match required pattern 'Follow these steps to perform this <Topic> Troubleshooting/Configuration'. Got: '{goal}'"
            )

        # 2. Title length check (strictly 2-3 words)
        title = plan_dict.get("title")
        if not title or not isinstance(title, str):
            errors.append("Missing or non-string 'title' field.")
        elif self.check_url_leak(title):
            errors.append(f"Prohibited URL leak detected in title: '{title}'.")
        else:
            title_words = title.strip().split()
            if not (2 <= len(title_words) <= 3):
                errors.append(f"Title must contain strictly 2-3 words. Got {len(title_words)} words: '{title}'.")

        # 3. Score range check (0.0 <= score <= 1.0)
        score = plan_dict.get("score")
        if score is None or not isinstance(score, (int, float)):
            errors.append(f"Score must be a numeric value between 0.0 and 1.0. Got: {score}")
        elif not (0.0 <= float(score) <= 1.0):
            errors.append(f"Score out of bounds [0.0, 1.0]. Got: {score}")

        # 4. Actions validation
        actions = plan_dict.get("action")
        if not actions or not isinstance(actions, list) or len(actions) == 0:
            errors.append("Plan must contain at least one action.")
        else:
            critical_seen = False
            for idx, act in enumerate(actions):
                if not isinstance(act, dict):
                    errors.append(f"Action at index {idx} must be a dictionary.")
                    continue

                act_name = act.get("actionName")
                if not act_name or not isinstance(act_name, str):
                    errors.append(f"Action at index {idx} has missing or invalid 'actionName'.")

                category = act.get("category")
                if category not in ["auto", "critical", "manual"]:
                    errors.append(
                        f"Action '{act_name}' has invalid category '{category}'. Must be 'auto', 'critical', or 'manual'."
                    )
                else:
                    if category == "critical":
                        critical_seen = True
                    elif critical_seen and category in ["auto", "manual"]:
                        errors.append(
                            f"Sequencing violation: Non-critical action '{act_name}' ({category}) appears after a critical action."
                        )

                # Description check: strictly 5-7 words, starts with 'It will'
                desc = act.get("description")
                if not desc or not isinstance(desc, str):
                    errors.append(f"Action '{act_name}' has missing or non-string 'description'.")
                elif self.check_url_leak(desc):
                    errors.append(f"Prohibited URL leak detected in description: '{desc}'.")
                else:
                    trimmed_desc = desc.strip()
                    if not trimmed_desc.startswith("It will"):
                        errors.append(f"Description must start with 'It will'. Got: '{trimmed_desc}'")
                    desc_words = trimmed_desc.split()
                    if not (5 <= len(desc_words) <= 7):
                        errors.append(
                            f"Description must contain strictly 5-7 words. Got {len(desc_words)} words: '{trimmed_desc}'"
                        )

                # StepGroups check
                step_groups = act.get("stepGroups")
                if not step_groups or not isinstance(step_groups, list) or len(step_groups) == 0:
                    errors.append(f"Action '{act_name}' must contain at least one stepGroup.")
                else:
                    for sg_idx, sg in enumerate(step_groups):
                        if not isinstance(sg, dict):
                            errors.append(f"stepGroup at index {sg_idx} in '{act_name}' must be a dictionary.")
                            continue

                        steps = sg.get("steps")
                        if not steps or not isinstance(steps, list) or len(steps) == 0:
                            errors.append(f"stepGroup at index {sg_idx} in '{act_name}' must contain steps.")
                        else:
                            for s_idx, s in enumerate(steps):
                                if not s or not isinstance(s, str):
                                    errors.append(f"Step {s_idx} in '{act_name}' is empty or not a string.")
                                elif self.check_url_leak(s):
                                    errors.append(f"Prohibited URL leak detected in step: '{s}'.")

                        # Deeplink integrity checks
                        actionable_dl = sg.get("actionableDeeplink")
                        validation_dl = sg.get("validationDeeplink")

                        if category == "manual":
                            if actionable_dl is not None and actionable_dl != "":
                                errors.append(
                                    f"Manual action '{act_name}' must not contain an actionable deeplink. Got: '{actionable_dl}'"
                                )
                            if validation_dl is not None and validation_dl != "":
                                errors.append(
                                    f"Manual action '{act_name}' must not contain a validation deeplink. Got: '{validation_dl}'"
                                )
                        else:
                            # Verify actionable deeplink against catalog if present
                            if actionable_dl:
                                if self.check_url_leak(actionable_dl):
                                    errors.append(f"Prohibited URL format in deeplink: '{actionable_dl}'")
                                elif actionable_dl not in self.allowed_uris:
                                    errors.append(
                                        f"Deeplink integrity violation: URI '{actionable_dl}' does not exist in catalog."
                                    )

                            # Verify validation deeplink against catalog if present
                            if validation_dl:
                                if self.check_url_leak(validation_dl):
                                    errors.append(f"Prohibited URL format in validation deeplink: '{validation_dl}'")
                                elif validation_dl not in self.allowed_uris:
                                    errors.append(
                                        f"Validation deeplink integrity violation: URI '{validation_dl}' does not exist in catalog."
                                    )

        if errors:
            return False, None, errors

        # Final Pydantic construction
        try:
            pydantic_goal = TroubleshootingGoal(**plan_dict)
            return True, pydantic_goal, []
        except ValidationError as ve:
            return False, None, [str(err) for err in ve.errors()]
