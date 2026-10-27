"""
setupkit.plugin - Plugin configuration loader and validator.

Loads a plugin.yaml file and validates its contents against the
expected schema. Returns a typed PluginConfig dataclass for use
by the rest of setupkit.

Expected plugin.yaml format:

    name: dbkit
    version: 0.1.0
    manifest_url: https://raw.githubusercontent.com/carolynboyle/dev-utils/master/.doc-gen/manifest.fletch
    pyproject: python/dbkit/pyproject.toml
    path_prefix: python/dbkit/dbkit/
    install:
      method: pip
      url: git+https://github.com/carolynboyle/dev-utils.git#subdirectory=python/dbkit

Public API:
    PluginConfig   — dataclass representing a validated plugin.yaml
    load_plugin    — load and validate a plugin.yaml file
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from setupkit.exceptions import PluginConfigError


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------

_REQUIRED_TOP = {"name", "version", "manifest_url", "pyproject", "path_prefix", "install"}
_REQUIRED_INSTALL = {"method", "url"}
_SUPPORTED_METHODS = {"pip"}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class InstallConfig:
    """
    Installation configuration for a plugin.

    Attributes:
        method: Installation method. Currently only 'pip' is supported.
        url:    URL passed to the install method (e.g. a git+ URL for pip).
    """

    method: str
    url: str


@dataclass
class PluginConfig:
    """
    Validated configuration for a single plugin, loaded from plugin.yaml.

    Attributes:
        name:         Plugin package name (e.g. 'dbkit').
        version:      Currently installed version string (e.g. '0.1.0').
        manifest_url: Raw URL to the plugin's manifest.fletch file.
        pyproject:    Path within the manifest to the plugin's pyproject.toml,
                      relative to the repo root.
        path_prefix:  Path prefix used to filter manifest.fletch entries to
                      only this plugin's source files.
        install:      Installation configuration.
    """

    name: str
    version: str
    manifest_url: str
    pyproject: str
    path_prefix: str
    install: InstallConfig


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_plugin(path: Path) -> PluginConfig:
    """
    Load and validate a plugin.yaml file.

    Args:
        path: Path to the plugin.yaml file.

    Returns:
        A validated PluginConfig instance.

    Raises:
        PluginConfigError: If the file is missing, unreadable, not valid YAML,
                           or missing required fields.
    """
    if not path.exists():
        raise PluginConfigError(f"Plugin config not found: {path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        raise PluginConfigError(f"Could not read plugin config {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise PluginConfigError(f"Plugin config {path} is empty or not a mapping")

    _validate_required(data, _REQUIRED_TOP, path)

    install_data = data["install"]
    if not isinstance(install_data, dict):
        raise PluginConfigError(
            f"Plugin config {path}: 'install' must be a mapping"
        )
    _validate_required(install_data, _REQUIRED_INSTALL, path, section="install")

    method = install_data["method"]
    if method not in _SUPPORTED_METHODS:
        raise PluginConfigError(
            f"Plugin config {path}: unsupported install method {method!r}. "
            f"Supported: {sorted(_SUPPORTED_METHODS)}"
        )

    return PluginConfig(
        name=data["name"],
        version=data["version"],
        manifest_url=data["manifest_url"],
        pyproject=data["pyproject"],
        path_prefix=data["path_prefix"],
        install=InstallConfig(
            method=method,
            url=install_data["url"],
        ),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_required(
    data: dict,
    required: set,
    path: Path,
    section: str | None = None,
) -> None:
    """
    Check that all required keys are present in a config dict.

    Args:
        data:     The dict to validate.
        required: Set of required key names.
        path:     Path to the config file, used in error messages.
        section:  Optional section name for nested dicts, used in error messages.

    Raises:
        PluginConfigError: If any required keys are missing.
    """
    missing = required - data.keys()
    if missing:
        location = f"{path} [{section}]" if section else str(path)
        raise PluginConfigError(
            f"Plugin config {location} missing required fields: {sorted(missing)}"
        )
