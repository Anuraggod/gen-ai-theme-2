"""
test_url_sanitization.py - Tests for Zero URL Leakage Detection and Strict Plan Rejection.
"""

from app.engine.validator import OutputValidator


def test_url_leak_detector():
    validator = OutputValidator()

    # Raw HTTP/HTTPS links
    assert validator.check_url_leak("Check https://samsung.com/help for details") is True
    assert validator.check_url_leak("Visit http://support.device.org/fix now") is True
    assert validator.check_url_leak("Go to www.example.com to see guide") is True
    assert validator.check_url_leak("Click [Help Guide](https://example.com/doc) here") is True
    assert validator.check_url_leak("Navigate to and open Settings.") is False


def test_plan_with_url_leak_is_strictly_rejected():
    validator = OutputValidator()
    plan_with_url = {
        "goal": "Follow these steps to perform this Battery Troubleshooting",
        "title": "Battery fast drain",
        "score": 0.95,
        "action": [
            {
                "actionName": "Power Saving Mode",
                "description": "It will reduce background power consumption",
                "category": "auto",
                "stepGroups": [
                    {
                        "steps": [
                            "Open Settings.",
                            "Visit https://leak.com/info for details.",  # Prohibited URL leak
                            "Enable Power saving."
                        ],
                        "actionableDeeplink": "bixby://masked/settings/battery/power_saving",
                        "validationDeeplink": None
                    }
                ]
            }
        ]
    }

    is_valid, validated_goal, errors = validator.validate_plan(plan_with_url)

    # Must be strictly rejected
    assert is_valid is False
    assert validated_goal is None
    assert any("Prohibited URL leak detected in step" in err for err in errors)
