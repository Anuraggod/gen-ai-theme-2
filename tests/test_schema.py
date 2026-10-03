"""
test_schema.py - Tests for Pydantic data contract validation rules.
"""

import pytest
from pydantic import ValidationError
from app.schema import TroubleshootingGoal, Action, StepGroup


def test_valid_schema_instantiation():
    goal = TroubleshootingGoal(
        goal="Follow these steps to perform this Swipe Navigation Troubleshooting",
        title="Swipe navigation settings",
        score=0.95,
        action=[
            Action(
                actionName="Navigation Bar Settings",
                description="It will configure navigation preferences",
                category="auto",
                stepGroups=[
                    StepGroup(
                        steps=["Open Settings.", "Tap Display.", "Tap Navigation bar."],
                        actionableDeeplink="bixby://masked/settings/display/navigation_bar",
                        validationDeeplink="bixby://masked/settings/display/navigation_bar/verify"
                    )
                ]
            ),
            Action(
                actionName="Restart in Safe Mode",
                description="It will isolate conflicting applications",
                category="critical",
                stepGroups=[
                    StepGroup(
                        steps=["Press power button.", "Select Safe mode."],
                        actionableDeeplink=None,
                        validationDeeplink=None
                    )
                ]
            )
        ]
    )
    assert goal.title == "Swipe navigation settings"
    assert goal.score == 0.95
    assert len(goal.action) == 2


def test_invalid_goal_pattern():
    with pytest.raises(ValidationError):
        TroubleshootingGoal(
            goal="Here is how you troubleshoot swipe navigation",  # Invalid goal pattern
            title="Swipe navigation settings",
            score=0.9,
            action=[
                Action(
                    actionName="Display Settings",
                    description="It will configure navigation preferences",
                    category="auto",
                    stepGroups=[StepGroup(steps=["Open Settings."])]
                )
            ]
        )


def test_invalid_title_length():
    # 1 word title (invalid: requires 2-3 words)
    with pytest.raises(ValidationError):
        TroubleshootingGoal(
            goal="Follow these steps to perform this Swipe Navigation Troubleshooting",
            title="Navigation",
            score=0.9,
            action=[
                Action(
                    actionName="Display Settings",
                    description="It will configure navigation preferences",
                    category="auto",
                    stepGroups=[StepGroup(steps=["Open Settings."])]
                )
            ]
        )

    # 4 word title (invalid: requires 2-3 words)
    with pytest.raises(ValidationError):
        TroubleshootingGoal(
            goal="Follow these steps to perform this Swipe Navigation Troubleshooting",
            title="Swipe navigation settings screen issue",
            score=0.9,
            action=[
                Action(
                    actionName="Display Settings",
                    description="It will configure navigation preferences",
                    category="auto",
                    stepGroups=[StepGroup(steps=["Open Settings."])]
                )
            ]
        )


def test_invalid_description():
    # Doesn't start with 'It will'
    with pytest.raises(ValidationError):
        Action(
            actionName="Display Settings",
            description="Configure your device navigation preferences now",
            category="auto",
            stepGroups=[StepGroup(steps=["Open Settings."])]
        )

    # Starts with 'It will' but only 4 words (requires 5-7 words)
    with pytest.raises(ValidationError):
        Action(
            actionName="Display Settings",
            description="It will fix things",
            category="auto",
            stepGroups=[StepGroup(steps=["Open Settings."])]
        )

    # Starts with 'It will' but has 8 words (requires 5-7 words)
    with pytest.raises(ValidationError):
        Action(
            actionName="Display Settings",
            description="It will quickly and thoroughly configure all device navigation preferences",
            category="auto",
            stepGroups=[StepGroup(steps=["Open Settings."])]
        )


def test_invalid_score_bounds():
    with pytest.raises(ValidationError):
        TroubleshootingGoal(
            goal="Follow these steps to perform this Swipe Navigation Troubleshooting",
            title="Swipe navigation settings",
            score=1.5,  # Out of bounds
            action=[
                Action(
                    actionName="Display Settings",
                    description="It will configure navigation preferences",
                    category="auto",
                    stepGroups=[StepGroup(steps=["Open Settings."])]
                )
            ]
        )

    with pytest.raises(ValidationError):
        TroubleshootingGoal(
            goal="Follow these steps to perform this Swipe Navigation Troubleshooting",
            title="Swipe navigation settings",
            score=-0.1,  # Out of bounds
            action=[
                Action(
                    actionName="Display Settings",
                    description="It will configure navigation preferences",
                    category="auto",
                    stepGroups=[StepGroup(steps=["Open Settings."])]
                )
            ]
        )


def test_manual_action_prohibits_deeplink():
    with pytest.raises(ValidationError):
        Action(
            actionName="Clean Charging Port",
            description="It will clean physical charging debris",
            category="manual",
            stepGroups=[
                StepGroup(
                    steps=["Clean port with brush."],
                    actionableDeeplink="bixby://masked/settings/battery"  # Invalid on manual
                )
            ]
        )


def test_critical_action_ordering_rule():
    # Non-critical action after critical action is invalid
    with pytest.raises(ValidationError):
        TroubleshootingGoal(
            goal="Follow these steps to perform this Device Troubleshooting",
            title="Device system reset",
            score=0.9,
            action=[
                Action(
                    actionName="Factory Reset",
                    description="It will restore original factory system",
                    category="critical",
                    stepGroups=[StepGroup(steps=["Perform factory reset."])]
                ),
                Action(
                    actionName="Display Settings",
                    description="It will configure navigation preferences",
                    category="auto",  # Invalid after critical
                    stepGroups=[StepGroup(steps=["Open Settings."])]
                )
            ]
        )
