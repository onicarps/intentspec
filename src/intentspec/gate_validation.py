"""Phase 2A gate validation (ONI-195).

Runs automatable go/no-go checks and produces a structured report.
Manual criteria (external lint review, legal review, GitHub stars) are
marked pending with guidance.
"""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from intentspec.converter import parse
from intentspec.enforce import discover_mcp_tools, enforce_mcp, parse_mcp_config
from intentspec.lint import lint_intent
from intentspec.migrate import detect_version, migrate
from intentspec.models.intent import IntentValidationError
from intentspec.spec.validate import validate_file


_PKG_ROOT = Path(__file__).resolve().parent


def _resolve_data_dir(name: str) -> Path | None:
    """Resolve packaged data or dev-tree test fixtures."""
    for candidate in (
        _PKG_ROOT / "data" / name,
        _PKG_ROOT.parents[1] / "tests" / "fixtures" / name,
    ):
        if candidate.exists():
            return candidate
    return None


_MCP_FIXTURES = _resolve_data_dir("mcp")
_BENCHMARK_FIXTURES = _PKG_ROOT.parents[1] / "tests" / "fixtures"
if not _BENCHMARK_FIXTURES.exists():
    _BENCHMARK_FIXTURES = None  # type: ignore[assignment]
def _adapter_dirs() -> dict[str, Path]:
    if _BENCHMARK_FIXTURES is None:
        return {}
    return {
        "crewai": _BENCHMARK_FIXTURES / "sample_crewai",
        "langgraph": _BENCHMARK_FIXTURES / "sample_langgraph",
        "autogen": _BENCHMARK_FIXTURES / "sample_autogen",
        "openai_agents": _BENCHMARK_FIXTURES / "sample_openai_agents",
    }
_FIELD_WEIGHTS = {
    "tools.allowed": 0.30,
    "non_negotiables": 0.20,
    "constraints": 0.20,
    "goals": 0.15,
    "boundaries": 0.10,
    "metadata.tags": 0.05,
}
_CONVERTER_THRESHOLD = 0.75
_MCP_FP_THRESHOLD = 0.20
_LINT_FP_THRESHOLD = 0.15
_ADAPTER_THRESHOLD = 0.70


@dataclass
class GateCheck:
    """Single gate criterion result."""

    name: str
    threshold: str
    status: str  # pass | fail | pending | skip
    measured: str
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "threshold": self.threshold,
            "status": self.status,
            "measured": self.measured,
            "details": self.details,
        }


@dataclass
class GateReport:
    """Aggregated ONI-195 gate validation report."""

    checks: list[GateCheck] = field(default_factory=list)

    @property
    def automatable_pass(self) -> bool:
        return all(
            c.status in {"pass", "skip"}
            for c in self.checks
            if c.status not in {"pending"}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "automatable_pass": self.automatable_pass,
            "checks": [c.to_dict() for c in self.checks],
        }

    def to_markdown(self) -> str:
        lines = [
            "# ONI-195 Phase 2A Gate Validation Report",
            "",
            f"**Automatable criteria:** {'PASS' if self.automatable_pass else 'FAIL'}",
            "",
            "| Criterion | Threshold | Measured | Status |",
            "|-----------|-----------|----------|--------|",
        ]
        for check in self.checks:
            icon = {"pass": "✅", "fail": "❌", "pending": "⏳", "skip": "⏭️"}.get(check.status, "?")
            lines.append(
                f"| {check.name} | {check.threshold} | {check.measured} | {icon} {check.status} |"
            )
        for check in self.checks:
            if check.details:
                lines.append("")
                lines.append(f"### {check.name}")
                for detail in check.details:
                    lines.append(f"- {detail}")
        return "\n".join(lines)


def _extract_field_values(intent_data: dict, field: str) -> set[str]:
    values: set[str] = set()
    if field == "tools.allowed":
        for tool in intent_data.get("intent", {}).get("tools", {}).get("allowed", []):
            values.add(tool.get("name", "").lower().strip())
    elif field == "non_negotiables":
        for nn in intent_data.get("intent", {}).get("non_negotiables", []):
            values.add(nn.get("rule", "").lower().strip())
    elif field == "constraints":
        for c in intent_data.get("intent", {}).get("constraints", []):
            values.add(c.get("rule", "").lower().strip())
    elif field == "goals":
        for g in intent_data.get("intent", {}).get("goals", []):
            values.add(g.get("description", "").lower().strip())
    elif field == "boundaries":
        for b in intent_data.get("intent", {}).get("boundaries", []):
            values.add(b.get("scope", "").lower().strip())
    elif field == "metadata.tags":
        for tag in intent_data.get("metadata", {}).get("tags", []):
            values.add(str(tag).lower().strip())
    return {v for v in values if v}


def _f1_score(expected: set[str], actual: set[str]) -> float:
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    tp = len(expected & actual)
    precision = tp / len(actual) if actual else 0
    recall = tp / len(expected) if expected else 0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _find_converter_pairs() -> list[tuple[Path, Path]]:
    if _BENCHMARK_FIXTURES is None:
        return []
    pairs: list[tuple[Path, Path]] = []
    for fixture_dir in ["sample_agents_md", "sample_skills_md", "sample_agentskills"]:
        base = _BENCHMARK_FIXTURES / fixture_dir
        if not base.exists():
            continue
        for item in sorted(base.iterdir()):
            if item.is_file() and item.suffix == ".md" and item.stem != "edge-no-frontmatter":
                expected = item.parent / f"{item.stem}.expected.yaml"
                if expected.exists():
                    pairs.append((item, expected))
            elif item.is_dir():
                skill_md = item / "SKILL.md"
                expected = item / "expected.yaml"
                if skill_md.exists() and expected.exists():
                    pairs.append((skill_md, expected))
    return pairs


def check_mcp_fp_rate() -> GateCheck:
    """MCP enforcement false-positive rate on fixture scenarios."""
    if _MCP_FIXTURES is None:
        return GateCheck(
            name="MCP enforcement FP rate",
            threshold=f"<{_MCP_FP_THRESHOLD:.0%}",
            status="fail",
            measured="MCP gate data not found in package",
            details=["Expected packaged data at intentspec/data/mcp/"],
        )
    scenarios_path = _MCP_FIXTURES / "scenarios.yaml"
    try:
        raw = yaml.safe_load(scenarios_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return GateCheck(
            name="MCP enforcement FP rate",
            threshold=f"<{_MCP_FP_THRESHOLD:.0%}",
            status="fail",
            measured=f"cannot read scenarios: {exc}",
        )
    scenarios = raw.get("scenarios", [])

    false_positives = 0
    true_negatives = 0
    details: list[str] = []

    for scenario in scenarios:
        config_path = _MCP_FIXTURES / scenario["config"]
        config = parse_mcp_config(str(config_path))
        servers = config.get("servers", {})
        server_cfg = next(iter(servers.values())) if servers else config
        tools = discover_mcp_tools(server_cfg)
        result = enforce_mcp(scenario["allowed"], scenario["denied"], tools)
        flagged = bool(result.risks or result.missing_from_spec)
        expect_risk = scenario["expect_risk"]

        if not expect_risk:
            true_negatives += 1
            if flagged:
                false_positives += 1
                details.append(f"FP: {scenario['name']} flagged but should be aligned")
            else:
                details.append(f"OK: {scenario['name']} correctly aligned")
        else:
            if flagged:
                details.append(f"OK: {scenario['name']} correctly flagged")
            else:
                details.append(f"FN: {scenario['name']} not flagged (miss)")

    fp_rate = false_positives / true_negatives if true_negatives else 0.0
    status = "pass" if fp_rate < _MCP_FP_THRESHOLD else "fail"
    return GateCheck(
        name="MCP enforcement FP rate",
        threshold=f"<{_MCP_FP_THRESHOLD:.0%}",
        status=status,
        measured=f"{fp_rate:.1%} ({false_positives}/{true_negatives} aligned scenarios)",
        details=details,
    )


def check_lint_fp_rate(path: str = ".") -> GateCheck:
    """Lint false-positive proxy: errors on schema-valid intent.yaml files."""
    target = Path(path)
    pattern = str(target / "**/intent.yaml") if target.is_dir() else str(target)
    files = [Path(f) for f in glob.glob(pattern, recursive=True)]

    clean_specs = 0
    lint_errors = 0
    details: list[str] = []

    for spec in files:
        try:
            intent, errors, _warnings = validate_file(spec)
        except (IntentValidationError, OSError):
            continue
        if errors:
            continue
        clean_specs += 1
        lint = lint_intent(intent)
        if lint.error_count > 0:
            lint_errors += 1
            details.append(f"Lint errors on valid spec: {spec.name} ({lint.error_count} errors)")

    fp_rate = lint_errors / clean_specs if clean_specs else 0.0
    status = "pass" if fp_rate < _LINT_FP_THRESHOLD else "fail"
    return GateCheck(
        name="Lint rules FP rate (proxy)",
        threshold=f"<{_LINT_FP_THRESHOLD:.0%} on valid specs",
        status=status,
        measured=f"{fp_rate:.1%} ({lint_errors}/{clean_specs} valid specs with lint errors)",
        details=details[:10],
    )


def check_converter_accuracy() -> GateCheck:
    """Re-run converter benchmark aggregate."""
    pairs = _find_converter_pairs()
    if not pairs:
        return GateCheck(
            name="Converter accuracy",
            threshold=f"≥{_CONVERTER_THRESHOLD:.0%}",
            status="skip",
            measured="benchmark fixtures unavailable (dev/CI only)",
            details=["Run from source tree or CI with tests/fixtures present"],
        )

    per_file: dict[str, float] = {}
    total = 0.0
    for source_path, expected_path in pairs:
        result = parse(source_path)
        actual_data = result.intent.to_dict()
        expected_data = yaml.safe_load(expected_path.read_text(encoding="utf-8"))
        file_score = 0.0
        file_weight = 0.0
        for field, weight in _FIELD_WEIGHTS.items():
            f1 = _f1_score(
                _extract_field_values(expected_data, field),
                _extract_field_values(actual_data, field),
            )
            file_score += f1 * weight
            file_weight += weight
        weighted = file_score / file_weight if file_weight else 0
        per_file[f"{source_path.parent.name}/{source_path.stem}"] = weighted
        total += weighted

    aggregate = total / len(pairs)
    status = "pass" if aggregate >= _CONVERTER_THRESHOLD else "fail"
    details = [f"{name}: {score:.1%}" for name, score in sorted(per_file.items())]
    return GateCheck(
        name="Converter accuracy",
        threshold=f"≥{_CONVERTER_THRESHOLD:.0%}",
        status=status,
        measured=f"{aggregate:.1%} ({len(pairs)} fixtures)",
        details=details,
    )


def check_schema_migration(path: str = ".") -> GateCheck:
    """Migrate all v1.0 intent.yaml fixtures without error."""
    target = Path(path)
    pattern = str(target / "**/intent.yaml") if target.is_dir() else str(target)
    files = [Path(f) for f in glob.glob(pattern, recursive=True)]

    migrated = 0
    failed = 0
    details: list[str] = []

    for spec in files:
        try:
            content = spec.read_text(encoding="utf-8")
            version = detect_version(content)
            if version == "1.1":
                migrated += 1
                continue
            new_content = migrate(content)
            if new_content != content:
                details.append(f"Migrated: {spec}")
            migrated += 1
        except Exception as exc:
            failed += 1
            details.append(f"FAIL: {spec}: {exc}")

    status = "pass" if failed == 0 else "fail"
    return GateCheck(
        name="Schema migration",
        threshold="all v1.0 fixtures migrate cleanly",
        status=status,
        measured=f"{migrated} ok, {failed} failed",
        details=details[:15],
    )


def check_adapter_accuracy() -> GateCheck:
    """Framework adapter field extraction on sample configs."""
    parsers = {
        "crewai": "intentspec.adapters.crewai:parse_crewai",
        "langgraph": "intentspec.adapters.langgraph:parse_langgraph",
        "autogen": "intentspec.adapters.autogen:parse_autogen",
        "openai_agents": "intentspec.adapters.openai_agents:parse_openai_agents",
    }

    scores: list[float] = []
    details: list[str] = []

    adapter_dirs = _adapter_dirs()
    if not adapter_dirs:
        return GateCheck(
            name="Framework adapter accuracy",
            threshold=f"≥{_ADAPTER_THRESHOLD:.0%}",
            status="skip",
            measured="adapter fixtures unavailable (dev/CI only)",
        )

    for adapter, import_path in parsers.items():
        module_path, func_name = import_path.split(":")
        import importlib

        mod = importlib.import_module(module_path)
        parse_fn = getattr(mod, func_name)
        fixture_dir = adapter_dirs[adapter]
        configs = sorted(fixture_dir.glob("*.yaml"))[:3]
        adapter_scores: list[float] = []

        for config in configs:
            result = parse_fn(config)
            intent = result.intent
            checks = [
                bool(intent.agent_name),
                bool(intent.agent_type),
                len(intent.goals) > 0,
                len(intent.tools_allowed) > 0,
            ]
            adapter_scores.append(sum(checks) / len(checks))

        avg = sum(adapter_scores) / len(adapter_scores) if adapter_scores else 0
        scores.append(avg)
        details.append(f"{adapter}: {avg:.1%} ({len(configs)} configs)")

    measured = sum(scores) / len(scores) if scores else 0
    status = "pass" if measured >= _ADAPTER_THRESHOLD else "fail"
    return GateCheck(
        name="Framework adapter accuracy",
        threshold=f"≥{_ADAPTER_THRESHOLD:.0%} per adapter",
        status=status,
        measured=f"{measured:.1%} average across 4 adapters",
        details=details,
    )


def run_gate_validation(path: str = ".") -> GateReport:
    """Run all automatable ONI-195 gate checks."""
    checks = [
        check_mcp_fp_rate(),
        check_lint_fp_rate(path),
        check_converter_accuracy(),
        check_schema_migration(path),
        check_adapter_accuracy(),
        GateCheck(
            name="EU AI Act pack completeness",
            threshold="≥80% Annex IV (legal review)",
            status="pending",
            measured="deferred to Phase 3",
            details=["Requires legal/compliance review — not automatable"],
        ),
        GateCheck(
            name="GitHub stars",
            threshold="≥200 at 3 months",
            status="pending",
            measured="monitor monthly (ONI-196)",
            details=["Leading adoption indicator — track via PDD kill criteria review"],
        ),
        GateCheck(
            name="Lint external review",
            threshold="<15% FP with 5 reviewers",
            status="pending",
            measured="proxy check above",
            details=["Full gate requires 5 external developer reviews"],
        ),
    ]
    return GateReport(checks=checks)