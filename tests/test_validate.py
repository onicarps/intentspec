"""Tests for validate command + schema + config."""

import json
from pathlib import Path

import pytest

from intentspec.models.intent import Intent, IntentValidationError
from intentspec.spec.schema import INTENT_SCHEMA_V1
from intentspec.spec.validate import validate_schema, validate_semantic, validate_file


FIXTURES = Path(__file__).parent / "fixtures"


class TestSchemaValidation:
    """Test JSON Schema validation."""

    def test_valid_intent(self):
        path = FIXTURES / "valid_intent.yaml"
        intent = Intent.from_file(path)
        raw = self._load_raw(path)
        errors = validate_schema(raw)
        assert len(errors) == 0

    def test_invalid_missing_required_fields(self):
        data = {"version": "1.0"}
        errors = validate_schema(data)
        assert any("required" in e.lower() for e in errors)

    def test_invalid_wrong_type(self):
        data = {
            "version": "1.0",
            "agent": {"name": "test", "type": "invalid", "description": "A test"},
            "intent": {},
        }
        errors = validate_schema(data)
        assert len(errors) > 0

    def test_invalid_additional_properties(self):
        data = {
            "version": "1.0",
            "agent": {"name": "test", "type": "custom", "description": "A test"},
            "intent": {},
            "unknown_field": "value",
        }
        errors = validate_schema(data)
        assert any("additional" in e.lower() for e in errors)

    def test_invalid_version(self):
        data = {
            "version": "2.0",
            "agent": {"name": "test", "type": "custom", "description": "A test"},
            "intent": {},
        }
        errors = validate_schema(data)
        assert len(errors) > 0

    def test_invalid_agent_name_format(self):
        data = {
            "version": "1.0",
            "agent": {"name": "Test Agent!", "type": "custom", "description": "A test"},
            "intent": {},
        }
        errors = validate_schema(data)
        assert len(errors) > 0

    def test_invalid_negative_priority(self):
        data = {
            "version": "1.0",
            "agent": {"name": "test", "type": "custom", "description": "A test"},
            "intent": {"goals": [{"description": "A valid goal description", "priority": "critical"}]},
        }
        errors = validate_schema(data)
        assert any("priority" in e.lower() or "enum" in e.lower() for e in errors)

    @staticmethod
    def _load_raw(path: Path) -> dict:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)


class TestIntentModel:
    """Test Intent dataclass parsing."""

    def test_from_file_valid(self):
        path = FIXTURES / "valid_intent.yaml"
        intent = Intent.from_file(path)
        assert intent.version == "1.0"
        assert intent.agent_name == "code-reviewer"
        assert intent.agent_type == "coding"
        assert len(intent.goals) == 3
        assert len(intent.constraints) == 3
        assert len(intent.non_negotiables) == 3
        assert len(intent.tools_allowed) == 3
        assert len(intent.tools_denied) == 2
        assert len(intent.boundaries) == 1
        assert intent.escalation is not None
        assert len(intent.failure_modes) == 2
        assert intent.metadata.status == "active"
        assert intent.metadata.owner == "backend-team@acme.com"

    def test_from_dict_minimal(self):
        data = {
            "version": "1.0",
            "agent": {"name": "minimal", "type": "custom", "description": "Minimal agent"},
            "intent": {},
        }
        intent = Intent.from_dict(data)
        assert intent.agent_name == "minimal"
        assert intent.goals == []
        assert intent.constraints == []

    def test_to_dict_roundtrip(self):
        path = FIXTURES / "valid_intent.yaml"
        intent = Intent.from_file(path)
        result = intent.to_dict()
        assert result["version"] == "1.0"
        assert result["agent"]["name"] == "code-reviewer"
        assert len(result["intent"]["goals"]) == 3

    def test_to_yaml(self):
        path = FIXTURES / "valid_intent.yaml"
        intent = Intent.from_file(path)
        yaml_str = intent.to_yaml()
        assert "version: '1.0'" in yaml_str
        assert "code-reviewer" in yaml_str

    def test_tool_names_allowed(self):
        path = FIXTURES / "valid_intent.yaml"
        intent = Intent.from_file(path)
        names = intent.tool_names_allowed
        assert "github_api" in names
        assert "code_analysis_tools" in names

    def test_tool_names_denied(self):
        path = FIXTURES / "valid_intent.yaml"
        intent = Intent.from_file(path)
        names = intent.tool_names_denied
        assert "production_deployer" in names

    def test_enforceable_constraints(self):
        path = FIXTURES / "valid_intent.yaml"
        intent = Intent.from_file(path)
        enforceable = intent.enforceable_constraints
        assert len(enforceable) == 2  # 2 of 3 are enforceable

    def test_hard_non_negotiables(self):
        path = FIXTURES / "valid_intent.yaml"
        intent = Intent.from_file(path)
        hard = intent.hard_non_negotiables
        assert len(hard) == 3  # all are hard

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Intent.from_file("/nonexistent/path/intent.yaml")

    def test_empty_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            with pytest.raises(IntentValidationError):
                Intent.from_file(f.name)


class TestSemanticValidation:
    """Test semantic validation beyond schema."""

    def test_empty_goals_warning(self):
        intent = Intent.from_dict({
            "version": "1.0",
            "agent": {"name": "test", "type": "custom", "description": "A test"},
            "intent": {},
        })
        warnings = validate_semantic(intent)
        assert any("empty" in w.lower() for w in warnings)

    def test_duplicate_tool_allowed(self):
        intent = Intent.from_dict({
            "version": "1.0",
            "agent": {"name": "test", "type": "custom", "description": "A test"},
            "intent": {
                "tools": {
                    "allowed": [
                        {"name": "same-tool", "rationale": "reason 1"},
                        {"name": "same-tool", "rationale": "reason 2"},
                    ],
                },
            },
        })
        warnings = validate_semantic(intent)
        assert any("duplicate" in w.lower() for w in warnings)

    def test_tool_overlap(self):
        intent = Intent.from_dict({
            "version": "1.0",
            "agent": {"name": "test", "type": "custom", "description": "A test"},
            "intent": {
                "tools": {
                    "allowed": [{"name": "overlap-tool", "rationale": "allowed"}],
                    "denied": [{"name": "overlap-tool", "rationale": "denied"}],
                },
            },
        })
        warnings = validate_semantic(intent)
        assert any("overlap" in w.lower() for w in warnings)

    def test_missing_rationale(self):
        intent = Intent.from_dict({
            "version": "1.0",
            "agent": {"name": "test", "type": "custom", "description": "A test"},
            "intent": {
                "tools": {
                    "allowed": [{"name": "tool-without-rationale"}],
                },
            },
        })
        warnings = validate_semantic(intent)
        assert any("rationale" in w.lower() for w in warnings)

    def test_short_description(self):
        intent = Intent.from_dict({
            "version": "1.0",
            "agent": {"name": "test", "type": "custom", "description": "Hi"},
            "intent": {},
        })
        warnings = validate_semantic(intent)
        assert any("short" in w.lower() for w in warnings)


class TestValidateFile:
    """Test full file validation."""

    def test_valid_file(self):
        path = FIXTURES / "valid_intent.yaml"
        intent, errors, warnings = validate_file(path)
        assert len(errors) == 0
        assert intent.agent_name == "code-reviewer"

    def test_invalid_file(self):
        path = FIXTURES / "invalid_intent.yaml"
        intent, errors, warnings = validate_file(path)
        assert len(errors) > 0


class TestFormatter:
    """Test output formatting."""

    def test_error_format(self):
        from intentspec.spec.formatter import Formatter
        fmt = Formatter(use_color=False)
        result = fmt.error("test error")
        assert "test error" in result
        assert "✗" in result

    def test_success_format(self):
        from intentspec.spec.formatter import Formatter
        fmt = Formatter(use_color=False)
        result = fmt.success("test success")
        assert "test success" in result
        assert "✓" in result

    def test_validation_output_valid(self):
        from intentspec.spec.formatter import Formatter
        fmt = Formatter(use_color=False)
        result = fmt.format_validation_errors(Path("test.yaml"), [], [])
        assert "valid" in result

    def test_validation_output_errors(self):
        from intentspec.spec.formatter import Formatter
        fmt = Formatter(use_color=False)
        result = fmt.format_validation_errors(
            Path("test.yaml"),
            ["error 1", "error 2"],
            ["warning 1"],
        )
        assert "error 1" in result
        assert "warning 1" in result
