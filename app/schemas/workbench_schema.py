"""句格工作台跨端 JSON contract。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorkbenchSlotConstraintV1(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    pos: int = Field(ge=0)
    kind: Literal[
        "code_digit",
        "literal_char",
        "final_anchor",
        "initial_anchor",
        "tone_class",
    ]
    digit: str | None = None
    literal: str | None = None
    ref: str | None = None
    ref_jyutping: str | None = Field(default=None, alias="refJyutping")
    tone_class: Literal["ping", "ze"] | None = Field(default=None, alias="toneClass")

    @model_validator(mode="after")
    def validate_kind_payload(self) -> "WorkbenchSlotConstraintV1":
        required = {
            "code_digit": self.digit,
            "literal_char": self.literal,
            "final_anchor": self.ref,
            "initial_anchor": self.ref,
            "tone_class": self.tone_class,
        }
        if required[self.kind] is None:
            raise ValueError(f"{self.kind} slot is missing its payload")
        return self


class ReplacementPlanV1(BaseModel):
    """Neutral plan accepted by both Portable and PWA planners."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    version: Literal[1] = 1
    selection_version: int = Field(alias="selectionVersion", ge=0)
    width: int = Field(ge=1, le=4)
    mode: Literal["m1", "m2", "m3"]
    slots: list[WorkbenchSlotConstraintV1]
    semantic_intent: Literal["ranked", "direct_only", "off"] = Field(
        alias="semanticIntent"
    )
    semantic_seed: str | None = Field(default=None, alias="semanticSeed", min_length=1, max_length=4)
    limit: int = Field(ge=1, le=120)

    @model_validator(mode="after")
    def validate_slot_positions(self) -> "ReplacementPlanV1":
        if any(slot.pos >= self.width for slot in self.slots):
            raise ValueError("slot position must fit selection width")
        return self


class CandidateReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "tone_exact",
        "tone_loose",
        "literal_match",
        "same_final",
        "same_initial",
        "direct_syn",
        "semantic_related",
        "frequency_rank",
        "relaxed_constraint",
    ]
    positions: list[int] = Field(default_factory=list, max_length=4)
    source: str | None = None


class WorkbenchCandidate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    literal: str = Field(min_length=1, max_length=4)
    jyutping: str
    code: str
    group: Literal["direct_syn", "semantic_related", "sound_only"]
    reasons: list[CandidateReason] = Field(min_length=1)
    source_rank: int = Field(alias="sourceRank", ge=0)
    relaxation_id: str | None = Field(default=None, alias="relaxationId")


class CandidateGroups(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direct_syn: list[WorkbenchCandidate]
    semantic_related: list[WorkbenchCandidate]
    sound_only: list[WorkbenchCandidate]


class RelaxationSuggestion(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1)
    kind: Literal[
        "semantic_ranked",
        "remove_final",
        "remove_initial",
        "remove_code",
        "loosen_mode",
    ]
    positions: list[int] = Field(default_factory=list, max_length=4)
    from_value: str | None = Field(default=None, alias="from")
    to_value: str | None = Field(default=None, alias="to")
    candidate_count: int = Field(alias="candidateCount", ge=1)
    plan: ReplacementPlanV1


class WorkbenchCandidateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    version: Literal[1] = 1
    selection_version: int = Field(alias="selectionVersion", ge=0)
    exact: CandidateGroups
    relaxation: RelaxationSuggestion | None = None


class LineReadingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface: str = Field(min_length=1, max_length=64)


class LineReadingChoiceResponse(BaseModel):
    jyutping: str
    code: str
    initial: str
    final: str


class LineReadingSlotResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    surface: str
    kind: Literal["resolved", "unresolved", "punctuation"]
    choices: list[LineReadingChoiceResponse]
    needs_choice: bool = Field(alias="needsChoice")


__all__ = [
    "CandidateReason",
    "CandidateGroups",
    "LineReadingChoiceResponse",
    "LineReadingSlotResponse",
    "LineReadingsRequest",
    "RelaxationSuggestion",
    "ReplacementPlanV1",
    "WorkbenchCandidate",
    "WorkbenchCandidateResponse",
    "WorkbenchSlotConstraintV1",
]
