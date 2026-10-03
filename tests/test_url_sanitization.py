"""
test_url_sanitization.py - Tests for Zero URL Leakage and sanitization layer.
"""

from app.engine.validator import OutputValidator


def test_url_leak_detector_and_sanitizer():
    validator = OutputValidator()

    # Raw HTTP/HTTPS links
    assert validator.sanitize_text("Check https://samsung.com/help for details") == "Check for details"
    assert validator.sanitize_text("Visit http://support.device.org/fix now") == "Visit now"
    assert validator.sanitize_text("Go to www.example.com to see guide") == "Go to to see guide"
    assert validator.sanitize_text("Click [Help Guide](https://example.com/doc) here") == "Click here"


def test_plan_sanitization_removes_url_leaks():
    validator = OutputValidator()
    plan = {
        "goal": "Follow these steps to perform this Battery Troubleshooting https://leak.com",
        "title": "Battery fast drain www.bad.com",
        "score": 0.95,
        "action": [
            {
                "actionName": "Power Saving Mode",
                "description": "It will reduce background power consumption https://fake.url",
                "category": "auto",
                "stepGroups": [
                    {
                        "steps": [
                            "Open Settings.",
                            "Visit https://leak.com/info for details.",
                            "Enable Power saving."
                        ],
                        "actionableDeeplink": "bixby://masked/settings/battery/power_saving",
                        "validationDeeplink": None
                    }
                ]
            }
        ]
    }

    is_valid, validated_goal, errors = validator.validate_and_sanitize_plan(plan, domain="Battery")

    assert is_valid is True
    assert validated_goal is not None
    assert "https://" not in validated_goal.goal
    assert "www." not in validated_goal.title

    for step in validated_goal.action[0].stepGroups[0].steps:
        assert "https://" not in step
        assert "leak.com" not in step
