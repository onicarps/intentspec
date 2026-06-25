"""Tests for schema migration (v1.0 → v1.1)."""

from __future__ import annotations

import pytest

from intentspec.migrate import Migrator, detect_version, migrate, migrate_v1_0_to_v1_1


V10_CONTENT = """version: "1.0"
agent:
  name: test-agent
  type: coding
  description: A test agent for validation
intent:
  goals:
    - description: "Write code"
      priority: high
"""

V10_NO_VERSION = """agent:
  name: test-agent
  type: coding
  description: A test agent for validation
intent: {}
"""

V11_CONTENT = """# intent.yaml — migrated by intentspec
# version annotation: v1.1 (additive, schema-valid as v1.0)
version: "1.0"
agent:
  name: test-agent
  type: coding
  description: A test agent
intent: {}
"""

MALFORMED_YAML = """version: "1.0"
agent:
  name: [invalid
"""


class TestDetectVersion:
    def test_v10_explicit(self):
        assert detect_version(V10_CONTENT) == "1.0"

    def test_v10_implicit(self):
        assert detect_version(V10_NO_VERSION) == "1.0"

    def test_v11_annotation(self):
        assert detect_version(V11_CONTENT) == "1.1"

    def test_malformed(self):
        assert detect_version(MALFORMED_YAML) == "1.0"


class TestMigrateV10ToV11:
    def test_adds_header(self):
        result = migrate_v1_0_to_v1_1(V10_CONTENT)
        assert "migrated by intentspec" in result
        assert "v1.1" in result

    def test_preserves_content(self):
        result = migrate_v1_0_to_v1_1(V10_CONTENT)
        assert 'version: "1.0"' in result
        assert "test-agent" in result
        assert "Write code" in result

    def test_idempotent(self):
        first = migrate_v1_0_to_v1_1(V10_CONTENT)
        second = migrate_v1_0_to_v1_1(first)
        assert first == second

    def test_malformed_raises(self):
        with pytest.raises(ValueError, match="Malformed YAML"):
            migrate_v1_0_to_v1_1(MALFORMED_YAML)

    def test_non_mapping_raises(self):
        with pytest.raises(ValueError, match="mapping"):
            migrate_v1_0_to_v1_1("- just a list")


class TestMigrate:
    def test_v10_migrates(self):
        result = migrate(V10_CONTENT)
        assert "v1.1" in result

    def test_v11_noop(self):
        result = migrate(V11_CONTENT)
        assert result == V11_CONTENT

    def test_implicit_v10_migrates(self):
        result = migrate(V10_NO_VERSION)
        assert "v1.1" in result


class TestMigrator:
    def test_detect_version(self):
        m = Migrator()
        assert m.detect_version(V10_CONTENT) == "1.0"
        assert m.detect_version(V11_CONTENT) == "1.1"

    def test_migrate(self):
        m = Migrator()
        result = m.migrate(V10_CONTENT)
        assert "migrated by intentspec" in result
