"""Schema migration utilities for IntentSpec — v1.0 to v1.1 (additive only)."""

from __future__ import annotations

import re
from typing import Any

import yaml


def detect_version(content: str) -> str:
    """Detect the version of an intent.yaml document from its raw content.

    Returns:
        "1.0" if version field is "1.0" or absent (assumed legacy).
        "1.1" if version field is "1.1" or document has v1.1 header annotation.
        Other version strings as-is.
    """
    # Check for v1.1 header annotation first
    if re.search(r"^#.*v1\.1", content, re.MULTILINE):
        return "1.1"

    # Parse YAML and look for version field
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return "1.0"

    if not isinstance(data, dict):
        return "1.0"

    version = data.get("version", "1.0")
    if isinstance(version, (int, float)):
        version = str(version)
    return str(version)


def migrate_v1_0_to_v1_1(content: str) -> str:
    """Migrate a v1.0 intent document to v1.1 annotation.

    The migration is additive and non-breaking:
    - Adds a header comment marking the document as v1.1
    - Keeps version field as "1.0" (schema-valid)
    - Preserves all semantic content

    Args:
        content: Raw YAML text of an intent.yaml document.

    Returns:
        Migrated YAML text with v1.1 header annotation.

    Raises:
        ValueError: If content is malformed YAML.
    """
    # Validate parseability
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Malformed YAML: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("Expected a YAML mapping at the top level")

    # Check if already migrated
    if "migrated by intentspec" in content:
        return content  # Idempotent

    # Build v1.1 header comment
    line1 = "# intent.yaml - migrated by intentspec"
    line2 = "# version annotation: v1.1 (additive, schema-valid as v1.0)"
    header = line1 + chr(10) + line2 + chr(10)
    return header + content


def migrate(content: str) -> str:
    """Migrate an intent.yaml document to the latest version.

    Detects current version and applies appropriate migrations.

    Args:
        content: Raw YAML text.

    Returns:
        Migrated YAML text.

    Raises:
        ValueError: If content is malformed.
    """
    version = detect_version(content)

    if version == "1.1":
        return content  # Already current

    # Apply migration chain
    result = migrate_v1_0_to_v1_1(content)
    return result


class Migrator:
    """Encapsulates migration logic for intent.yaml documents."""

    def detect_version(self, content: str) -> str:
        """Detect version from raw content."""
        return detect_version(content)

    def migrate(self, content: str) -> str:
        """Migrate content to latest version."""
        return migrate(content)
