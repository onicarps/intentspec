"""Tests for src/intentspec/converter/agents_md.py.

Covers every parser branch per architecture §4.1 and the validation
contract assertions VAL-AGENTSMD-001 through VAL-AGENTSMD-027
(except LLM, SKILL.md, agentskills, and interactive-review
assertions which belong to other features).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import yaml

from intentspec.converter import parse
from intentspec.converter.agents_md import parse_agents_md

FIXTURES = Path(__file__).parent / "fixtures" / "sample_agents_md"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _fixture(name: str) -> Path:
    return FIXTURES / name


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["intentspec", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Agent name extraction
# ---------------------------------------------------------------------------

class TestAgentName:
    def test_h1_to_agent_name_kebab_cased(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        assert r.intent.agent_name == "kubernetes-contributor-agent"
        assert r.confidences["agent.name"] == 0.85
        assert r.sources["agent.name"].extractor == "rule"
        assert r.sources["agent.name"].line == 1

    def test_h1_strips_you_are_prefix(self, tmp_path):
        md = tmp_path / "research.md"
        md.write_text("# You are a Research Agent\n\ndesc\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert r.intent.agent_name == "research-agent"
        assert r.confidences["agent.name"] == 0.85

    def test_h1_strips_you_are_an_prefix(self, tmp_path):
        md = tmp_path / "maintainer.md"
        md.write_text("# You are an AI Maintainer\n\ndesc\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert r.intent.agent_name == "ai-maintainer"

    def test_filename_fallback_when_no_h1(self, tmp_path):
        md = tmp_path / "My_Agent.md"
        md.write_text("No heading here.\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert r.intent.agent_name == "my-agent"
        assert r.confidences["agent.name"] == 0.50
        assert r.sources["agent.name"].extractor == "default"

    def test_kebab_case_normalisation(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("#  Coding & Review  Agent  \n\ndesc\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert r.intent.agent_name == "coding-review-agent"


# ---------------------------------------------------------------------------
# Agent description
# ---------------------------------------------------------------------------

class TestAgentDescription:
    def test_description_from_first_paragraph(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        assert "Kubernetes" in r.intent.agent_description
        assert r.confidences["agent.description"] == 0.80
        assert r.sources["agent.description"].line is not None

    def test_description_truncated_at_sentence_boundary(self, tmp_path):
        long_desc = "Primary function here. " + "very " * 60 + "long tail. Second sentence here."
        md = tmp_path / "test.md"
        md.write_text(f"# Test Agent\n\n{long_desc}\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert len(r.intent.agent_description) <= 200
        assert r.intent.agent_description.endswith(".")

    def test_description_truncated_at_word_boundary(self, tmp_path):
        long_desc = "A" * 300
        md = tmp_path / "test.md"
        md.write_text(f"# Test Agent\n\n{long_desc}\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert len(r.intent.agent_description) <= 200

    def test_description_missing_gives_placeholder(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# Test Agent\n\n## Goals\n- foo\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert r.intent.agent_description
        assert r.confidences["agent.description"] <= 0.40


# ---------------------------------------------------------------------------
# Goals extraction
# ---------------------------------------------------------------------------

class TestGoalsExtraction:
    def test_goals_from_goals_section(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        assert len(r.intent.goals) == 3
        assert all(g.priority == "medium" for g in r.intent.goals)

    def test_goals_from_purpose_section(self):
        r = parse_agents_md(_fixture("promptfoo.md"))
        assert len(r.intent.goals) == 3

    def test_goals_from_mission_section(self):
        r = parse_agents_md(_fixture("vercel-ai.md"))
        assert len(r.intent.goals) == 3

    def test_goals_from_what_you_do_section(self):
        r = parse_agents_md(_fixture("langchain.md"))
        assert len(r.intent.goals) == 3

    def test_goals_from_objectives_section(self):
        r = parse_agents_md(_fixture("autogpt.md"))
        assert len(r.intent.goals) == 3

    def test_no_goals_section_yields_warning(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# Agent\n\ndesc\n\n## Constraints\n- MUST do X.\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert not r.intent.goals
        assert any("goals" in w.lower() for w in r.warnings)

    def test_goals_confidence(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        key = "intent.goals[0].description"
        assert r.confidences[key] == 0.80


# ---------------------------------------------------------------------------
# Constraints extraction
# ---------------------------------------------------------------------------

class TestConstraintsExtraction:
    def test_hard_constraint_keywords(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        hard = [c for c in r.intent.constraints if c.enforceable]
        soft = [c for c in r.intent.constraints if not c.enforceable]
        assert len(hard) >= 2
        assert len(soft) >= 1

    def test_never_is_enforceable_true(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# A\n\nd\n\n## Constraints\n- NEVER do X.\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert any(c.enforceable for c in r.intent.constraints)

    def test_must_not_is_enforceable_true(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# A\n\nd\n\n## Constraints\n- MUST NOT do X.\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert any(c.enforceable for c in r.intent.constraints)

    def test_do_not_is_enforceable_true(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# A\n\nd\n\n## Constraints\n- DO NOT do X.\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert any(c.enforceable for c in r.intent.constraints)

    def test_always_is_enforceable_true(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# A\n\nd\n\n## Constraints\n- ALWAYS do X.\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert any(c.enforceable for c in r.intent.constraints)

    def test_prefer_is_enforceable_false(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        soft = [c for c in r.intent.constraints if not c.enforceable]
        assert any("Prefer" in c.rule for c in soft)

    def test_should_is_enforceable_false(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        soft = [c for c in r.intent.constraints if not c.enforceable]
        assert any("Should" in c.rule for c in soft)

    def test_hard_confidence_0_85(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# A\n\nd\n\n## Constraints\n- MUST do X.\n", encoding="utf-8")
        r = parse_agents_md(md)
        key = "intent.constraints[0].rule"
        assert r.confidences[key] == 0.85

    def test_soft_confidence_0_55(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# A\n\nd\n\n## Constraints\n- Prefer X over Y.\n", encoding="utf-8")
        r = parse_agents_md(md)
        key = "intent.constraints[0].rule"
        assert r.confidences[key] == 0.55

    def test_duplicate_constraints_deduped(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "# A\n\nd\n\n## Constraints\n- NEVER push to main.\n\n## Non-negotiables\n- NEVER push to main.\n",
            encoding="utf-8",
        )
        r = parse_agents_md(md)
        all_rules = [c.rule.strip().lower() for c in r.intent.constraints]
        all_rules += [nn.rule.strip().lower() for nn in r.intent.non_negotiables]
        assert all_rules.count("never push to main.") == 1


# ---------------------------------------------------------------------------
# Non-negotiables extraction
# ---------------------------------------------------------------------------

class TestNonNegotiablesExtraction:
    def test_non_negotiables_section(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        assert len(r.intent.non_negotiables) == 4
        assert all(nn.severity == "hard" for nn in r.intent.non_negotiables)

    def test_hard_rules_section(self):
        r = parse_agents_md(_fixture("autogpt.md"))
        assert len(r.intent.non_negotiables) == 3

    def test_emphatic_patterns(self):
        r = parse_agents_md(_fixture("autogpt.md"))
        rules = [nn.rule for nn in r.intent.non_negotiables]
        assert any("Strictly forbidden" in r for r in rules)
        assert any("Absolutely never" in r for r in rules)

    def test_under_no_circumstances(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        rules = [nn.rule for nn in r.intent.non_negotiables]
        assert any("Under no circumstances" in r for r in rules)

    def test_non_negotiables_confidence(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        key = "intent.non_negotiables[0].rule"
        assert r.confidences[key] == 0.80

    def test_never_in_non_negotiables_section(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        nn_rules = [nn.rule for nn in r.intent.non_negotiables]
        assert any("NEVER push" in r for r in nn_rules)


# ---------------------------------------------------------------------------
# Tools extraction
# ---------------------------------------------------------------------------

class TestToolsExtraction:
    def test_table_extracts_tools_with_rationale(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        assert len(r.intent.tools_allowed) >= 4
        for t in r.intent.tools_allowed:
            assert t.name
            assert t.rationale

    def test_table_confidence_0_85(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        key = "intent.tools.allowed[0].name"
        assert r.confidences[key] == 0.85

    def test_intro_verb_code_span(self):
        r = parse_agents_md(_fixture("langchain.md"))
        tool_names = [t.name for t in r.intent.tools_allowed]
        assert "gh" in tool_names

    def test_tool_names_deduplicated(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "# A\n\nd\n\n## Tools\n\n| Tool | Why |\n|-----|-----|\n| pytest | testing |\n\nUse `pytest` for tests.\n",
            encoding="utf-8",
        )
        r = parse_agents_md(md)
        names = [t.name.lower() for t in r.intent.tools_allowed]
        assert names.count("pytest") == 1

    def test_empty_rationale_gets_default(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# A\n\nd\n\n## Tools\n\n| Tool | Why |\n|-----|-----|\n| foo | |\n", encoding="utf-8")
        r = parse_agents_md(md)
        assert r.intent.tools_allowed[0].rationale


# ---------------------------------------------------------------------------
# Boundaries extraction
# ---------------------------------------------------------------------------

class TestBoundariesExtraction:
    def test_boundaries_section(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        assert len(r.intent.boundaries) == 1
        assert r.intent.boundaries[0].scope
        assert r.intent.boundaries[0].out_of_scope

    def test_out_of_scope_section_title(self):
        r = parse_agents_md(_fixture("vercel-ai.md"))
        assert len(r.intent.boundaries) == 2
        for b in r.intent.boundaries:
            assert b.out_of_scope
            assert len(b.out_of_scope) >= 5

    def test_boundary_confidence(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        key = "intent.boundaries[0].scope"
        assert r.confidences[key] == 0.75

    def test_in_scope_prefix_stripped(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text(
            "# A\n\nAn agent that reviews code.\n\n## Constraints\n- MUST do X.\n\n## Boundaries\n- In scope: code review.\n- Out of scope: deployment.\n",
            encoding="utf-8",
        )
        r = parse_agents_md(md)
        assert r.intent.boundaries[0].scope == "code review."
        assert r.intent.boundaries[0].out_of_scope == "deployment."


# ---------------------------------------------------------------------------
# Recursive references
# ---------------------------------------------------------------------------

class TestRecursiveReferences:
    def test_recursive_reference_followed(self):
        r = parse_agents_md(_fixture("edge-recursive.md"))
        local_goals = 2
        total_goals = len(r.intent.goals)
        assert total_goals > local_goals

    def test_recursive_confidence_reduction(self):
        r = parse_agents_md(_fixture("edge-recursive.md"))
        local_confs = [v for k, v in r.confidences.items() if "goals" in k and "via" not in r.sources.get(k, type("", (), {})()).snippet]
        remote_confs = [v for k, v in r.confidences.items() if "goals" in k and "via" in r.sources.get(k, type("", (), {})()).snippet]
        if remote_confs:
            assert min(remote_confs) < max(local_confs)

    def test_recursive_depth_limited_to_2(self, tmp_path):
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        c = tmp_path / "c.md"
        d = tmp_path / "d.md"
        a.write_text("# A\n\nAgent that MUST coordinate.\n\nSee also: b.md\n", encoding="utf-8")
        b.write_text("# B\n\nAgent that MUST review.\n\n## Goals\n- Goal from B.\n\nSee also: c.md\n", encoding="utf-8")
        c.write_text("# C\n\nAgent that MUST test.\n\n## Goals\n- Goal from C.\n\nSee also: d.md\n", encoding="utf-8")
        d.write_text("# D\n\nAgent that MUST deploy.\n\n## Goals\n- Goal from D.\n", encoding="utf-8")
        r = parse_agents_md(a)
        goal_descs = [g.description for g in r.intent.goals]
        assert "Goal from B." in goal_descs
        assert "Goal from C." in goal_descs
        assert "Goal from D." not in goal_descs

    def test_no_self_reference_loop(self, tmp_path):
        a = tmp_path / "a.md"
        a.write_text("# A\n\ndesc\n\nSee also: a.md\n", encoding="utf-8")
        r = parse_agents_md(a)
        assert len(r.warnings) == 0 or not any("loop" in w for w in r.warnings)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_edge_empty_file(self):
        r = parse_agents_md(_fixture("edge-empty.md"))
        assert r.intent.agent_name == "edge-empty"
        assert r.intent.agent_description == "<empty source>"
        assert "empty" in " ".join(r.warnings).lower()
        assert r.confidences["agent.name"] == 0.50

    def test_edge_bom_no_corruption(self):
        r = parse_agents_md(_fixture("edge-bom.md"))
        assert "\ufeff" not in r.intent.agent_name
        assert "bom" in r.intent.agent_name.lower()

    def test_edge_non_english_warning(self):
        r = parse_agents_md(_fixture("edge-non-english.md"))
        assert any("no extractable" in w.lower() for w in r.warnings)

    def test_edge_non_english_name_preserved(self):
        r = parse_agents_md(_fixture("edge-non-english.md"))
        assert "asistente" in r.intent.agent_name

    def test_edge_malformed_no_traceback(self):
        r = parse_agents_md(_fixture("edge-malformed.md"))
        assert r.intent.agent_name
        assert len(r.intent.goals) >= 2
        assert len(r.intent.constraints) >= 1

    def test_edge_malformed_validate(self):
        tmp = tempfile.mkdtemp()
        out = Path(tmp) / "out.yaml"
        proc = _run_cli("init", str(_fixture("edge-malformed.md")), "--yes", "-o", str(out))
        assert proc.returncode == 0
        assert "Traceback" not in proc.stderr

    def test_edge_bom_validates(self):
        tmp = tempfile.mkdtemp()
        out = Path(tmp) / "out.yaml"
        proc = _run_cli("init", str(_fixture("edge-bom.md")), "--yes", "-o", str(out))
        assert proc.returncode == 0
        vproc = _run_cli("validate", str(out))
        assert vproc.returncode == 0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_determinism_two_runs_identical_sha256(self, tmp_path):
        out1 = tmp_path / "a.yaml"
        out2 = tmp_path / "b.yaml"
        _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", str(out1))
        _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", str(out2))
        h1 = __import__("hashlib").sha256(out1.read_bytes()).hexdigest()
        h2 = __import__("hashlib").sha256(out2.read_bytes()).hexdigest()
        assert h1 == h2

    def test_determinism_empty_fixture(self, tmp_path):
        out1 = tmp_path / "a.yaml"
        out2 = tmp_path / "b.yaml"
        _run_cli("init", str(_fixture("edge-empty.md")), "--yes", "-o", str(out1))
        _run_cli("init", str(_fixture("edge-empty.md")), "--yes", "-o", str(out2))
        h1 = __import__("hashlib").sha256(out1.read_bytes()).hexdigest()
        h2 = __import__("hashlib").sha256(out2.read_bytes()).hexdigest()
        assert h1 == h2


# ---------------------------------------------------------------------------
# Provenance and confidence
# ---------------------------------------------------------------------------

class TestProvenance:
    def test_provenance_header_in_output(self, tmp_path):
        out = tmp_path / "out.yaml"
        _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", str(out))
        text = out.read_text()
        assert "# Source:" in text
        assert "# Format: agents_md" in text
        assert "# Confidence:" in text

    def test_per_field_confidence_comments(self, tmp_path):
        out = tmp_path / "out.yaml"
        _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", str(out))
        text = out.read_text()
        assert "confidence: 0.85" in text
        assert "source:" in text

    def test_line_numbers_within_range(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        src = _fixture("kubernetes.md").read_bytes().decode("utf-8-sig")
        line_count = src.count("\n") + 1
        for key, src_info in r.sources.items():
            if src_info.line is not None:
                assert 1 <= src_info.line <= line_count, f"{key} line {src_info.line} out of range"

    def test_average_confidence(self):
        r = parse_agents_md(_fixture("kubernetes.md"))
        avg = r.average_confidence()
        assert 0.0 <= avg <= 1.0

    def test_low_confidence_keys(self):
        r = parse_agents_md(_fixture("edge-empty.md"))
        low = r.low_confidence_keys()
        assert "agent.type" in low


# ---------------------------------------------------------------------------
# CLI integration tests (subprocess)
# ---------------------------------------------------------------------------

class TestCLIIntegration:
    def test_init_kubernetes_validates(self):
        tmp = tempfile.mkdtemp()
        out = Path(tmp) / "intent.yaml"
        proc = _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", str(out))
        assert proc.returncode == 0
        vproc = _run_cli("validate", str(out))
        assert vproc.returncode == 0

    def test_init_all_non_edge_fixtures_validate(self):
        for name in ["kubernetes", "vercel-ai", "promptfoo", "autogpt", "langchain", "workspace-agents"]:
            tmp = tempfile.mkdtemp()
            out = Path(tmp) / "intent.yaml"
            proc = _run_cli("init", str(_fixture(f"{name}.md")), "--yes", "-o", str(out))
            assert proc.returncode == 0, f"{name}: init failed"
            vproc = _run_cli("validate", str(out))
            assert vproc.returncode == 0, f"{name}: validate failed"

    def test_init_output_stdout_yaml(self):
        proc = _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", "-", "--format", "yaml")
        assert proc.returncode == 0
        data = yaml.safe_load(proc.stdout)
        assert "intent" in data or "agent" in data

    def test_init_output_stdout_json(self):
        proc = _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", "-", "--format", "json")
        assert proc.returncode == 0
        import json
        data = json.loads(proc.stdout)
        assert "intent" in data

    def test_init_missing_file_exits_1(self):
        proc = _run_cli("init", "/tmp/does-not-exist-xyz.md", "--yes")
        assert proc.returncode == 1

    def test_init_force_format(self, tmp_path):
        weird = tmp_path / "weird.txt"
        weird.write_text("# Agent\n\ndesc\n\n## Goals\n- g1.\n", encoding="utf-8")
        out = tmp_path / "out.yaml"
        proc = _run_cli("init", str(weird), "--from", "agents_md", "--yes", "-o", str(out))
        assert proc.returncode == 0

    def test_init_existing_output_no_force_fails(self, tmp_path):
        out = tmp_path / "intent.yaml"
        out.write_text("exists\n", encoding="utf-8")
        proc = _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", str(out))
        assert proc.returncode == 1

    def test_init_existing_output_with_force_succeeds(self, tmp_path):
        out = tmp_path / "intent.yaml"
        out.write_text("exists\n", encoding="utf-8")
        proc = _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "--force", "-o", str(out))
        assert proc.returncode == 0

    def test_init_utf8_output_no_bom(self, tmp_path):
        out = tmp_path / "out.yaml"
        _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", str(out))
        raw = out.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")

    def test_init_lf_line_endings(self, tmp_path):
        out = tmp_path / "out.yaml"
        _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "-o", str(out))
        raw = out.read_bytes()
        assert b"\r\n" not in raw

    def test_no_network_calls_without_use_llm(self, monkeypatch):
        import urllib.request
        calls = []
        orig = urllib.request.urlopen

        def _spy(*a, **kw):
            calls.append(a)
            return orig(*a, **kw)

        monkeypatch.setattr(urllib.request, "urlopen", _spy)
        parse_agents_md(_fixture("kubernetes.md"))
        assert len(calls) == 0

    def test_format_detected_as_agents_md(self):
        proc = _run_cli("init", str(_fixture("kubernetes.md")), "--yes", "--format", "json", "-o", "-")
        assert proc.returncode == 0
        import json
        data = json.loads(proc.stdout)
        assert data.get("format") == "agents_md"

    def test_parse_does_not_mutate_filesystem(self, tmp_path):
        fixture = tmp_path / "AGENTS.md"
        fixture.write_text("# X\n\nd\n", encoding="utf-8")
        before = sorted(p.name for p in tmp_path.iterdir())
        parse(fixture)
        after = sorted(p.name for p in tmp_path.iterdir())
        assert before == after


# ---------------------------------------------------------------------------
# YAML safety check
# ---------------------------------------------------------------------------

class TestYAMLSafety:
    def test_no_unsafe_yaml_load(self):
        import subprocess
        proc = subprocess.run(
            ["rg", "-n", r"yaml\.load\(", "src/intentspec", "--glob", "*.py"],
            capture_output=True,
            text=True,
        )
        lines = proc.stdout.strip().split("\n") if proc.stdout.strip() else []
        unsafe = [line for line in lines if "safe_load" not in line]
        assert not unsafe, f"Unsafe yaml.load calls found: {unsafe}"
