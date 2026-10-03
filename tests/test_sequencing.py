"""
test_sequencing.py - Tests for Action Sequencing and hierarchy enforcement.
"""

from app.engine.sequencer import ActionSequencer


def test_action_sequencing_hierarchy():
    """
    Critical actions must appear strictly last: auto -> manual -> critical.
    """
    sequencer = ActionSequencer()
    raw_actions = [
        {"actionName": "Factory Data Reset", "category": "critical", "stepGroups": [{"steps": ["Reset."]}]},
        {"actionName": "Power Saving Mode", "category": "auto", "stepGroups": [{"steps": ["Enable."]}]},
        {"actionName": "Clean Port", "category": "manual", "stepGroups": [{"steps": ["Clean."]}]}
    ]

    sequenced = sequencer.sequence_actions(raw_actions)

    assert sequenced[0]["category"] == "auto"
    assert sequenced[1]["category"] == "manual"
    assert sequenced[2]["category"] == "critical"
    assert sequenced[2]["actionName"] == "Factory Data Reset"
