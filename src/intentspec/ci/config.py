"""Configuration loading and precedence resolution for the ``ci`` command.

Two responsibilities live here:

* :func:`load_ci_config` reads ``.intentspec.yaml`` (auto-discovered in the
  working directory, or an explicit ``--config PATH``) and returns the recognized
  keys as a plain dict.
* :func:`resolve_ci_settings` combines that config with environment variables and
  explicitly-passed CLI flags, applying the precedence rule
  ``CLI flag > environment variable > config file > built-in default`` for each of
  ``min_coverage``, ``strict``, and ``format``.

All invalid input (malformed YAML, a missing/directory ``--config`` path, or an
out-of-range/non-coercible value from any source) raises :class:`CiConfigError`
with a clear, human-readable message so the CLI can surface it as exit code 3
without leaking a traceback.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILENAME = ".intentspec.yaml"

ENV_MIN_COVERAGE = "INTENTSPEC_MIN_COVERAGE"
ENV_STRICT = "INTENTSPEC_STRICT"
ENV_FORMAT = "INTENTSPEC_FORMAT"

DEFAULT_MIN_COVERAGE = 0
DEFAULT_STRICT = False
DEFAULT_FORMAT = "text"

_RECOGNIZED_KEYS = ("min_coverage", "strict", "format")
_VALID_FORMATS = ("text", "json", "yaml")
_TRUE_STRINGS = frozenset({"true", "1", "yes", "on"})
_FALSE_STRINGS = frozenset({"false", "0", "no", "off"})


class CiConfigError(Exception):
    """Raised for an unreadable, malformed, or invalid CI configuration value."""


@dataclass
class ResolvedSettings:
    """Effective CI settings after applying the precedence rule.

    Attributes:
        min_coverage: Minimum coverage percentage (0-100); 0 disables the check.
        strict: Whether warnings are promoted to errors.
        output_format: Output format, one of ``text``, ``json``, or ``yaml``.
    """

    min_coverage: int
    strict: bool
    output_format: str


def load_ci_config(config_path: str | None = None) -> dict[str, Any]:
    """Load CI configuration from a file.

    When ``config_path`` is given it is read directly; otherwise
    ``./.intentspec.yaml`` is auto-discovered in the current working directory.
    Only the recognized keys (``min_coverage``, ``strict``, ``format``) are
    returned; unknown keys are ignored. An absent or empty file yields an empty
    dict.

    Args:
        config_path: Explicit path to a config file, or None to auto-discover
            ``./.intentspec.yaml``.

    Returns:
        A dict containing only the recognized keys present in the file (raw,
        un-coerced values).

    Raises:
        CiConfigError: If an explicit ``config_path`` is missing or a directory,
            the file cannot be read, the YAML is malformed, or the top-level
            document is not a mapping.
    """
    if config_path is not None:
        path = Path(config_path)
        if path.is_dir():
            raise CiConfigError(
                f"config path is a directory, not a file: {config_path}"
            )
        if not path.exists():
            raise CiConfigError(f"config file not found: {config_path}")
    else:
        path = Path(CONFIG_FILENAME)
        if not path.is_file():
            return {}

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CiConfigError(f"could not read config file {path}: {exc}") from exc

    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise CiConfigError(
            f"could not parse config file {path}: malformed YAML"
        ) from exc

    if loaded is None:
        return {}
    if not isinstance(loaded, Mapping):
        raise CiConfigError(
            f"config file {path} must contain a mapping at the top level"
        )
    return {key: loaded[key] for key in _RECOGNIZED_KEYS if key in loaded}


def resolve_ci_settings(
    config: Mapping[str, Any],
    *,
    cli_min_coverage: int | None = None,
    cli_strict: bool | None = None,
    cli_format: str | None = None,
    env: Mapping[str, str] | None = None,
) -> ResolvedSettings:
    """Resolve effective settings using CLI > env > config > default precedence.

    A CLI argument counts as "explicitly set" only when it is not ``None``. The
    CLI layer is expected to pass ``None`` for any flag the user did not actually
    provide (detected via Click's ``ctx.get_parameter_source``), so an unpassed
    flag's default never clobbers a config or environment value.

    Args:
        config: Recognized config keys (typically from :func:`load_ci_config`).
        cli_min_coverage: Explicit ``--min-coverage`` value, or None if unset.
        cli_strict: Explicit ``--strict`` value, or None if unset.
        cli_format: Explicit ``--format`` value, or None if unset.
        env: Environment mapping to read; defaults to ``os.environ``.

    Returns:
        The resolved :class:`ResolvedSettings`.

    Raises:
        CiConfigError: If an environment or config value cannot be coerced or is
            out of range.
    """
    environ: Mapping[str, str] = os.environ if env is None else env

    return ResolvedSettings(
        min_coverage=_resolve_min_coverage(config, cli_min_coverage, environ),
        strict=_resolve_strict(config, cli_strict, environ),
        output_format=_resolve_format(config, cli_format, environ),
    )


def _env_value(environ: Mapping[str, str], name: str) -> str | None:
    """Return a non-empty environment value, or None if unset/blank."""
    raw = environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw


def _resolve_min_coverage(
    config: Mapping[str, Any], cli_value: int | None, environ: Mapping[str, str]
) -> int:
    if cli_value is not None:
        return _coerce_min_coverage(cli_value, "--min-coverage")
    env_raw = _env_value(environ, ENV_MIN_COVERAGE)
    if env_raw is not None:
        return _coerce_min_coverage(env_raw, f"environment variable {ENV_MIN_COVERAGE}")
    if "min_coverage" in config:
        return _coerce_min_coverage(config["min_coverage"], "config key 'min_coverage'")
    return DEFAULT_MIN_COVERAGE


def _resolve_strict(
    config: Mapping[str, Any], cli_value: bool | None, environ: Mapping[str, str]
) -> bool:
    if cli_value is not None:
        return _coerce_strict(cli_value, "--strict")
    env_raw = _env_value(environ, ENV_STRICT)
    if env_raw is not None:
        return _coerce_strict(env_raw, f"environment variable {ENV_STRICT}")
    if "strict" in config:
        return _coerce_strict(config["strict"], "config key 'strict'")
    return DEFAULT_STRICT


def _resolve_format(
    config: Mapping[str, Any], cli_value: str | None, environ: Mapping[str, str]
) -> str:
    if cli_value is not None:
        return _coerce_format(cli_value, "--format")
    env_raw = _env_value(environ, ENV_FORMAT)
    if env_raw is not None:
        return _coerce_format(env_raw, f"environment variable {ENV_FORMAT}")
    if "format" in config:
        return _coerce_format(config["format"], "config key 'format'")
    return DEFAULT_FORMAT


def _coerce_min_coverage(value: Any, source: str) -> int:
    """Coerce a value to an int percentage in 0-100, or raise CiConfigError."""
    if isinstance(value, bool):
        raise CiConfigError(
            f"{source} must be an integer between 0 and 100, got boolean {value!r}"
        )
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        raise CiConfigError(
            f"{source} must be an integer between 0 and 100, got {value!r}"
        ) from None
    if not 0 <= coerced <= 100:
        raise CiConfigError(
            f"{source} must be between 0 and 100, got {coerced}"
        )
    return coerced


def _coerce_strict(value: Any, source: str) -> bool:
    """Coerce a value to a bool, or raise CiConfigError."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return True
        if normalized in _FALSE_STRINGS:
            return False
    raise CiConfigError(
        f"{source} must be a boolean (true/false), got {value!r}"
    )


def _coerce_format(value: Any, source: str) -> str:
    """Validate a value is a supported format string, or raise CiConfigError."""
    if not isinstance(value, str) or value not in _VALID_FORMATS:
        raise CiConfigError(
            f"{source} must be one of {', '.join(_VALID_FORMATS)}, got {value!r}"
        )
    return value
