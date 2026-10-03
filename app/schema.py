"""
schema.py - Data contract and Pydantic models for Smart Guided Troubleshooting Engine.
Adheres strictly to the specification data hierarchy and constraints.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class StepGroup(BaseModel):
    steps: List[str] = Field(
        ...,
        description="List of step-by-step imperative UI interactions for this physical screen. No URLs allowed."
    )
    actionableDeeplink: Optional[str] = Field(
        default=None,
        description="Exact catalog-matched URI (e.g. bixby://masked/...) or bixby://dummy_positive, or None for manual."
    )
    validationDeeplink: Optional[str] = Field(
        default=None,
        description="Exact catalog-matched validation URI or None."
    )

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: List[str]) -> List[str]:
        if not v or len(v) == 0:
            raise ValueError("stepGroups must contain at least one step.")
        url_pattern = re.compile(r"(https?://|www\.|\.com|\.org|\.net|markdown:)", re.IGNORECASE)
        for idx, step in enumerate(v):
            if not step or not step.strip():
                raise ValueError(f"Step at index {idx} cannot be empty.")
            if url_pattern.search(step):
                raise ValueError(f"URL leak detected in step: '{step}'. Raw URLs are strictly prohibited.")
        return [s.strip() for s in v]


class Action(BaseModel):
    actionName: str = Field(
        ...,
        description="Represents exactly one physical screen or feature (not one per tap)."
    )
    description: str = Field(
        ...,
        description="Action description: exactly 5-7 words, starting with 'It will'."
    )
    category: Literal["auto", "critical", "manual"] = Field(
        ...,
        description="Action category: 'auto' (normal config), 'critical' (disruptive/reboot/reset), 'manual' (physical)."
    )
    stepGroups: List[StepGroup] = Field(
        ...,
        description="Step groups containing interaction steps and matched deeplinks."
    )

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed.startswith("It will"):
            raise ValueError(f"Description must start with 'It will'. Got: '{trimmed}'")
        words = trimmed.split()
        if not (5 <= len(words) <= 7):
            raise ValueError(f"Description must contain exactly 5-7 words. Got {len(words)} words: '{trimmed}'")
        return trimmed

    @model_validator(mode="after")
    def validate_manual_category_deeplink(self) -> "Action":
        if self.category == "manual":
            for sg in self.stepGroups:
                if sg.actionableDeeplink is not None and sg.actionableDeeplink.strip() != "":
                    raise ValueError(f"Manual action '{self.actionName}' must not contain an actionable deeplink.")
        return self


class TroubleshootingGoal(BaseModel):
    goal: str = Field(
        ...,
        description="Must follow format: 'Follow these steps to perform this <Topic> Troubleshooting' or '... Configuration'."
    )
    title: str = Field(
        ...,
        description="Issue title: strictly 2-3 words in sentence case."
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score strictly between 0.0 and 1.0."
    )
    action: List[Action] = Field(
        ...,
        description="List of physical troubleshooting actions. Critical actions must appear last."
    )

    @field_validator("goal")
    @classmethod
    def validate_goal_pattern(cls, v: str) -> str:
        trimmed = v.strip()
        pattern = re.compile(r"^Follow these steps to perform this (.+?) (Troubleshooting|Configuration)$", re.IGNORECASE)
        if not pattern.match(trimmed):
            raise ValueError(
                f"Goal must match pattern 'Follow these steps to perform this <Topic> Troubleshooting' or '... Configuration'. Got: '{trimmed}'"
            )
        return trimmed

    @field_validator("title")
    @classmethod
    def validate_title_length(cls, v: str) -> str:
        trimmed = v.strip()
        words = trimmed.split()
        if not (2 <= len(words) <= 3):
            raise ValueError(f"Title must contain exactly 2-3 words. Got {len(words)} words: '{trimmed}'")
        return trimmed

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Score must be between 0.0 and 1.0. Got: {v}")
        return round(float(v), 4)

    @model_validator(mode="after")
    def validate_action_sequencing(self) -> "TroubleshootingGoal":
        if not self.action:
            raise ValueError("Troubleshooting plan must contain at least one action.")
        
        # Verify critical actions are ordered last
        critical_seen = False
        for act in self.action:
            if act.category == "critical":
                critical_seen = True
            elif critical_seen and act.category in ["auto", "manual"]:
                raise ValueError(
                    f"Sequencing violation: Non-critical action '{act.actionName}' ({act.category}) cannot appear after critical actions."
                )
        return self


class TroubleshootRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
        description="Natural language customer complaint or troubleshooting inquiry."
    )
    domain: Optional[str] = Field(
        default=None,
        description="Optional device domain hint (e.g. Battery, Display, Camera, Performance)."
    )
    referenceContext: Optional[str] = Field(
        default=None,
        description="Optional ground-truth reference text / SIIS snippet provided in request."
    )


class TroubleshootResponse(BaseModel):
    contexts: List[TroubleshootingGoal] = Field(
        ...,
        description="List of validated troubleshooting goals matching the request."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Operational metadata (cache status, execution latency, query variations)."
    )


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    catalog_items_loaded: int
    cache_size: int
