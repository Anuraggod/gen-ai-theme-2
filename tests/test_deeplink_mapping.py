"""
test_deeplink_mapping.py - Tests for Deeplink Mapping, Parent-Menu Protection, and Catalog Integrity.
"""

from app.engine.deeplink_mapper import DeeplinkMapper


def test_parent_menu_protection_regression():
    """
    CRITICAL REGRESSION TEST:
    If the target is 'Navigation Bar' and catalog has:
      - 'Display' (parent, depth=1)
      - 'Navigation Bar' (leaf child, depth=2)
    The mapper MUST choose 'Navigation Bar' leaf deeplink, NOT generic 'Display'.
    """
    mapper = DeeplinkMapper()
    match = mapper.find_best_deeplink(
        action_name="Navigation Bar Settings",
        target_keyword="navigation_bar",
        domain="Display",
        query_text="phone swipe navigation gesture direction"
    )

    assert match is not None
    assert match["uri"] == "bixby://masked/settings/display/navigation_bar"
    assert match["uri"] != "bixby://masked/settings/display"
    assert match["actionName"] == "Navigation Bar Settings"


def test_verbatim_catalog_integrity():
    """
    Ensures deeplink is copied EXACTLY without modification or character mutation.
    """
    mapper = DeeplinkMapper()
    mapped = mapper.map_action(
        action_dict={
            "actionName": "Power Saving Mode",
            "category": "auto",
            "targetScreenKeyword": "power_saving",
            "description": "It will reduce background power consumption",
            "steps": ["Open Settings.", "Tap Power saving."]
        },
        domain="Battery"
    )

    sg = mapped["stepGroups"][0]
    assert sg["actionableDeeplink"] == "bixby://masked/settings/battery/power_saving"
    assert sg["validationDeeplink"] == "bixby://masked/settings/battery/power_saving/verify"


def test_manual_action_omits_actionable_deeplink():
    """
    Manual physical actions MUST NOT contain an actionable deeplink.
    """
    mapper = DeeplinkMapper()
    mapped = mapper.map_action(
        action_dict={
            "actionName": "Clean Charging Port",
            "category": "manual",
            "targetScreenKeyword": None,
            "description": "It will remove port lint buildup",
            "steps": ["Inspect port.", "Clean with toothpick."]
        },
        domain="Battery"
    )

    sg = mapped["stepGroups"][0]
    assert sg["actionableDeeplink"] is None
    assert sg["validationDeeplink"] is None


def test_unindexed_screen_dummy_positive_fallback():
    """
    When an auto action opens a valid settings screen not indexed in catalog,
    it falls back to reserved bixby://dummy_positive.
    """
    mapper = DeeplinkMapper()
    mapped = mapper.map_action(
        action_dict={
            "actionName": "Unindexed SubFeature Screen",
            "category": "auto",
            "targetScreenKeyword": "unindexed_xyz",
            "description": "It will configure unindexed custom setting",
            "steps": ["Open Settings.", "Tap Unindexed."]
        },
        domain="Display"
    )

    sg = mapped["stepGroups"][0]
    assert sg["actionableDeeplink"] == "bixby://dummy_positive"
