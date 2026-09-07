from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class IntentProposal(BaseModel):
    name: str
    create: bool = False
    confidence: float = 0.5


class EntityProposal(BaseModel):
    name: str
    type: str = "application"
    create: bool = True
    confidence: float = 0.5
    metadata: dict = Field(default_factory=dict)


class ProviderProposal(BaseModel):
    name: str
    create: bool = False


class FlowProposal(BaseModel):
    create: bool = True
    name: str | None = None


class ActionProposal(BaseModel):
    type: str = "shell"
    command: str | None = None
    argv: list[str] = Field(default_factory=list)
    parameters: dict = Field(default_factory=dict)
    extra: dict = Field(default_factory=dict)


class HermesProposal(BaseModel):
    intent: IntentProposal | None = None
    entities: list[EntityProposal] = Field(default_factory=list)
    provider: ProviderProposal | None = None
    flow: FlowProposal | None = None
    actions: list[ActionProposal] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    reason: str = ""


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMResult(BaseModel):
    proposal: HermesProposal
    raw: dict = Field(default_factory=dict)
    usage: LLMUsage = Field(default_factory=LLMUsage)
    model: str = ""


class LLMProvider(Protocol):
    def generate_structured(self, payload: dict) -> LLMResult: ...

    def ping(self) -> bool: ...
