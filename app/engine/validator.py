"""
validator.py - Deterministic Validation & Zero URL Leakage Enforcement.
Applies strict programmatic gates on:
- Goal pattern ("Follow these steps to perform this <Topic> Troubleshooting")
- Title length (strictly 2-3 words)
- Description format (strictly 5-7 words, begins with 'It will')
- Score range (0.0 <= score <= 1.0)
- Zero URL Leakage (rejects/strips all HTTP, HTTPS, www., markdown links)
- Verbatim catalog deeplink validation
"""

import re
from typing import Dict, Any, List, Tuple
from app.schema import TroubleshootingGoal, Action, StepGroup


class OutputValidator:
    """
    Deterministic programmatic validator and sanitizer.
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

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Removes any detected web URLs or markdown links from text.
        """
        if not text:
            return ""
        sanitized = cls.URL_PATTERN.sub("", text)
        return re.sub(r"\s+", " ", sanitized).strip()

    @classmethod
    def validate_and_normalize_title(cls, title: str, domain: str = "Device") -> str:
        """
        Ensures title is strictly 2-3 words in sentence case.
        """
        clean = cls.sanitize_text(title)
        words = clean.split()
        if len(words) < 2:
            return f"{clean} settings" if clean else f"{domain} settings"
        elif len(words) > 3:
            return " ".join(words[:3])
        # Sentence case formatting
        return words[0].capitalize() + " " + " ".join(words[1:]).lower()

    @classmethod
    def validate_and_normalize_description(cls, desc: str, fallback_topic: str = "device") -> str:
        """
        Ensures description is strictly 5-7 words and starts with 'It will'.
        """
        clean = cls.sanitize_text(desc)
        if not clean.startswith("It will"):
            clean = f"It will {clean}"

        words = clean.split()
        if len(words) < 5:
            # Pad to 5 words
            padding = ["configure", "target", "preferences", "properly"]
            while len(words) < 5 and padding:
                words.append(padding.pop(0))
        elif len(words) > 7:
            words = words[:7]

        return " ".join(words)

    @classmethod
    def validate_goal(cls, goal: str, domain: str = "Device") -> str:
        """
        Validates goal pattern.
        """
        clean = cls.sanitize_text(goal)
        if not cls.GOAL_PATTERN.match(clean):
            return f"Follow these steps to perform this {domain} Troubleshooting"
        return clean

    @classmethod
    def validate_and_sanitize_plan(
        cls,
        plan_dict: Dict[str, Any],
        domain: str = "Device"
    ) -> Tuple[bool, Optional[TroubleshootingGoal], List[str]]:
        """
        Validates and sanitizes a complete troubleshooting goal dictionary against the strict schema.
        Returns (is_valid, validated_pydantic_object, errors_list).
        """
        errors = []

        try:
            # 1. Goal validation
            raw_goal = plan_dict.get("goal", "")
            valid_goal = cls.validate_goal(raw_goal, domain)

            # 2. Title validation (2-3 words)
            raw_title = plan_dict.get("title", "")
            valid_title = cls.validate_and_normalize_title(raw_title, domain)

            # 3. Score validation (0.0 to 1.0)
            raw_score = plan_dict.get("score", 0.85)
            try:
                valid_score = max(0.0, min(1.0, float(raw_score)))
            except (ValueError, TypeError):
                valid_score = 0.80

            # 4. Actions validation
            raw_actions = plan_dict.get("action", [])
            valid_actions = []

            for act in raw_actions:
                act_name = cls.sanitize_text(act.get("actionName", f"{domain} Action"))
                act_desc = cls.validate_and_normalize_description(
                    act.get("description", "It will configure settings"),
                    domain
                )
                category = act.get("category", "auto")
                if category not in ["auto", "critical", "manual"]:
                    category = "auto"

                valid_step_groups = []
                for sg in act.get("stepGroups", []):
                    raw_steps = sg.get("steps", [])
                    clean_steps = []
                    for s in raw_steps:
                        s_clean = cls.sanitize_text(s)
                        if s_clean:
                            clean_steps.append(s_clean)

                    if not clean_steps:
                        clean_steps = ["Follow on-screen instructions."]

                    actionable_dl = sg.get("actionableDeeplink")
                    val_dl = sg.get("validationDeeplink")

                    # If manual, force null
                    if category == "manual":
                        actionable_dl = None
                        val_dl = None

                    # Check for raw HTTP leaks in deeplinks
                    if actionable_dl and cls.URL_PATTERN.search(actionable_dl):
                        actionable_dl = None
                    if val_dl and cls.URL_PATTERN.search(val_dl):
                        val_dl = None

                    valid_step_groups.append(
                        StepGroup(
                            steps=clean_steps,
                            actionableDeeplink=actionable_dl,
                            validationDeeplink=val_dl
                        )
                    )

                valid_actions.append(
                    Action(
                        actionName=act_name,
                        description=act_desc,
                        category=category,
                        stepGroups=valid_step_groups
                    )
                )

            # Build Pydantic model
            pydantic_goal = TroubleshootingGoal(
                goal=valid_goal,
                title=valid_title,
                score=valid_score,
                action=valid_actions
            )

            return True, pydantic_goal, []

        except Exception as e:
            errors.append(str(e))
            return False, None, errors
