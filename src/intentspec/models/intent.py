"""Intent dataclass — core abstraction for all commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml



class IntentValidationError(Exception):
    """Raised when intent.yaml fails validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} error(s)")


@dataclass
class Goal:
    description: str
    priority: str = "medium"
    success_criteria: str = ""


@dataclass
class Constraint:
    rule: str
    enforceable: bool = True


@dataclass
class NonNegotiable:
    rule: str
    severity: str = "hard"


@dataclass
class ToolPermission:
    name: str
    rationale: str = ""


@dataclass
class Boundary:
    scope: str
    out_of_scope: str


@dataclass
class Escalation:
    trigger: str
    method: str = ""


@dataclass
class FailureMode:
    mode: str
    mitigation: str


@dataclass
class AgentMetadata:
    status: str = "draft"
    owner: str = ""
    created: str = ""
    updated: str = ""
    review_cycle: str = "monthly"
    tags: list[str] = field(default_factory=list)


@dataclass
class Intent:
    """Parsed intent.yaml — the core model all commands operate on."""

    # Required
    version: str = "1.0"
    agent_name: str = ""
    agent_type: str = "custom"
    agent_description: str = ""

    # Optional intent blocks
    goals: list[Goal] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    non_negotiables: list[NonNegotiable] = field(default_factory=list)
    tools_allowed: list[ToolPermission] = field(default_factory=list)
    tools_denied: list[ToolPermission] = field(default_factory=list)
    boundaries: list[Boundary] = field(default_factory=list)
    escalation: Escalation | None = None
    failure_modes: list[FailureMode] = field(default_factory=list)
    sub_agents: list[str] = field(default_factory=list)
    extends: str = ""

    # Metadata
    metadata: AgentMetadata = field(default_factory=AgentMetadata)

    # Source tracking
    _source_path: Path | None = field(default=None, repr=False)
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_file(cls, path: Path | str) -> Intent:
        """Load and parse an intent.yaml file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"intent.yaml not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if raw is None:
            raise IntentValidationError(["File is empty"])

        return cls.from_dict(raw, source_path=path)

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_path: Path | None = None) -> Intent:
        """Parse an intent.yaml from a dict."""
        intent = cls()
        intent._raw = data
        intent._source_path = source_path

        # Version
        intent.version = data.get("version", "1.0")

        # Agent (required)
        agent = data.get("agent", {})
        intent.agent_name = agent.get("name", "")
        intent.agent_type = agent.get("type", "custom")
        intent.agent_description = agent.get("description", "")

        # Intent block
        intent_data = data.get("intent", {})

        # Goals
        for g in intent_data.get("goals", []):
            intent.goals.append(Goal(
                description=g.get("description", ""),
                priority=g.get("priority", "medium"),
                success_criteria=g.get("success_criteria", ""),
            ))

        # Constraints
        for c in intent_data.get("constraints", []):
            intent.constraints.append(Constraint(
                rule=c.get("rule", ""),
                enforceable=c.get("enforceable", True),
            ))

        # Non-negotiables
        for nn in intent_data.get("non_negotiables", []):
            intent.non_negotiables.append(NonNegotiable(
                rule=nn.get("rule", ""),
                severity=nn.get("severity", "hard"),
            ))

        # Tools
        tools = intent_data.get("tools", {})
        for t in tools.get("allowed", []):
            intent.tools_allowed.append(ToolPermission(
                name=t.get("name", ""),
                rationale=t.get("rationale", ""),
            ))
        for t in tools.get("denied", []):
            intent.tools_denied.append(ToolPermission(
                name=t.get("name", ""),
                rationale=t.get("rationale", ""),
            ))

        # Boundaries
        for b in intent_data.get("boundaries", []):
            intent.boundaries.append(Boundary(
                scope=b.get("scope", ""),
                out_of_scope=b.get("out_of_scope", ""),
            ))

        # Escalation
        esc = intent_data.get("escalation")
        if esc:
            intent.escalation = Escalation(
                trigger=esc.get("trigger", ""),
                method=esc.get("method", ""),
            )

        # Failure modes
        for fm in intent_data.get("failure_modes", []):
            intent.failure_modes.append(FailureMode(
                mode=fm.get("mode", ""),
                mitigation=fm.get("mitigation", ""),
            ))

        # Reserved
        intent.sub_agents = intent_data.get("sub_agents", [])
        intent.extends = intent_data.get("extends", "")

        # Metadata
        meta = data.get("metadata", {})
        intent.metadata = AgentMetadata(
            status=meta.get("status", "draft"),
            owner=meta.get("owner", ""),
            created=meta.get("created", ""),
            updated=meta.get("updated", ""),
            review_cycle=meta.get("review_cycle", "monthly"),
            tags=meta.get("tags", []),
        )

        return intent

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to dict."""
        result: dict[str, Any] = {
            "version": self.version,
            "agent": {
                "name": self.agent_name,
                "type": self.agent_type,
                "description": self.agent_description,
            },
            "intent": {},
        }

        intent_block = result["intent"]

        if self.goals:
            intent_block["goals"] = [
                {k: v for k, v in {
                    "description": g.description,
                    "priority": g.priority,
                    "success_criteria": g.success_criteria,
                }.items() if v}
                for g in self.goals
            ]

        if self.constraints:
            intent_block["constraints"] = [
                {"rule": c.rule, "enforceable": c.enforceable}
                for c in self.constraints
            ]

        if self.non_negotiables:
            intent_block["non_negotiables"] = [
                {"rule": nn.rule, "severity": nn.severity}
                for nn in self.non_negotiables
            ]

        if self.tools_allowed or self.tools_denied:
            tools: dict[str, Any] = {}
            if self.tools_allowed:
                tools["allowed"] = [
                    {"name": t.name, "rationale": t.rationale}
                    for t in self.tools_allowed
                ]
            if self.tools_denied:
                tools["denied"] = [
                    {"name": t.name, "rationale": t.rationale}
                    for t in self.tools_denied
                ]
            intent_block["tools"] = tools

        if self.boundaries:
            intent_block["boundaries"] = [
                {"scope": b.scope, "out_of_scope": b.out_of_scope}
                for b in self.boundaries
            ]

        if self.escalation:
            intent_block["escalation"] = {
                "trigger": self.escalation.trigger,
                "method": self.escalation.method,
            }

        if self.failure_modes:
            intent_block["failure_modes"] = [
                {"mode": fm.mode, "mitigation": fm.mitigation}
                for fm in self.failure_modes
            ]

        if self.metadata.status != "draft" or self.metadata.owner or self.metadata.tags:
            meta: dict[str, Any] = {}
            if self.metadata.status != "draft":
                meta["status"] = self.metadata.status
            if self.metadata.owner:
                meta["owner"] = self.metadata.owner
            if self.metadata.created:
                meta["created"] = self.metadata.created
            if self.metadata.updated:
                meta["updated"] = self.metadata.updated
            if self.metadata.review_cycle != "monthly":
                meta["review_cycle"] = self.metadata.review_cycle
            if self.metadata.tags:
                meta["tags"] = self.metadata.tags
            result["metadata"] = meta

        return result

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    @property
    def tool_names_allowed(self) -> set[str]:
        return {t.name for t in self.tools_allowed}

    @property
    def tool_names_denied(self) -> set[str]:
        return {t.name for t in self.tools_denied}

    @property
    def enforceable_constraints(self) -> list[Constraint]:
        return [c for c in self.constraints if c.enforceable]

    @property
    def hard_non_negotiables(self) -> list[NonNegotiable]:
        return [nn for nn in self.non_negotiables if nn.severity == "hard"]
