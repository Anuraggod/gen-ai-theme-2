"""
sequencer.py - Action Sequencing and Categorization Stage.
Orders actions according to hierarchy:
1. Normal / Auto actions first
2. Manual physical interventions where appropriate
3. Critical / Disruptive actions strictly last
"""

from typing import List, Dict, Any


class ActionSequencer:
    """
    Enforces category hierarchy and ordering constraints across actions.
    """

    @staticmethod
    def sequence_actions(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Orders actions: auto -> manual -> critical (last).
        Preserves relative order within the same category.
        """
        auto_actions = []
        manual_actions = []
        critical_actions = []

        for action in actions:
            category = action.get("category", "auto")
            if category == "auto":
                auto_actions.append(action)
            elif category == "manual":
                # Ensure manual action stepGroups have null deeplink
                for sg in action.get("stepGroups", []):
                    sg["actionableDeeplink"] = None
                manual_actions.append(action)
            elif category == "critical":
                critical_actions.append(action)
            else:
                # Default unknown category to auto
                action["category"] = "auto"
                auto_actions.append(action)

        # auto first, manual where appropriate, critical strictly last
        return auto_actions + manual_actions + critical_actions
