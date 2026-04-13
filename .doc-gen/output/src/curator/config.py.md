# config.py

**Path:** src/curator/config.py
**Syntax:** python
**Generated:** 2026-04-13 04:51:40

```python
"""
curator.config - Configuration management for the Curator.

Loads curator.yaml from shipped defaults in curator/data/, with optional
user overrides from ~/.config/curator/curator.yaml. User config is merged
over defaults — only keys present in the user file are overridden.

Database connection configuration is handled separately by dbkit, which
reads ~/.config/dev-utils/config.yaml. The Curator does not manage
database credentials.

Usage:
    from curator.config import ConfigManager

    config = ConfigManager()
    page_size = config.get("ui", "page_size")
    host = config.get("server", "host")
"""

from pathlib import Path
from typing import Any, Optional

import yaml

from curator.exceptions import ConfigError


# Shipped defaults live alongside this file in curator/data/
_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_CONFIG = _DATA_DIR / "curator.yaml"
_DEFAULT_VIEWS = _DATA_DIR / "views.yaml"

# User config lives in ~/.config/curator/
_USER_CONFIG_DIR = Path.home() / ".config" / "curator"
_USER_CONFIG = _USER_CONFIG_DIR / "curator.yaml"
_USER_VIEWS = _USER_CONFIG_DIR / "views.yaml"


class ConfigManager:
    """
    Loads and merges Curator configuration.

    Shipped defaults in curator/data/curator.yaml are the baseline.
    User overrides in ~/.config/curator/curator.yaml are merged on top.
    Only keys present in the user file override defaults — the full
    default config does not need to be repeated.

    The path to views.yaml is resolved here and passed to ViewBuilder
    by the caller. ConfigManager does not import viewkit.

    Usage:
        config = ConfigManager()
        host = config.get("server", "host")
        views_path = config.views_path
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialise ConfigManager.

        Args:
            config_path: Override path to curator.yaml. Defaults to
                         ~/.config/curator/curator.yaml with fallback
                         to shipped defaults. Useful for testing.
        """
        self._config = self._load(config_path)
        self.views_path = self._resolve_views_path()

    # -- Public interface -----------------------------------------------------

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Return a config value by section and key.

        Args:
            section: Top-level section name (e.g. "server", "ui").
            key:     Key within the section.
            default: Value to return if section or key is absent.

        Returns:
            The config value, or default if not found.
        """
        return self._config.get(section, {}).get(key, default)

    def get_section(self, section: str) -> dict:
        """
        Return an entire config section as a dict.

        Args:
            section: Top-level section name.

        Returns:
            Dict of key/value pairs, or empty dict if section absent.
        """
        return self._config.get(section, {})

    @property
    def plugin_manifest(self) -> dict:
        """
        Return the plugin registration manifest.

        Used by Project Crew to discover and identify this crew member.

        Returns:
            Dict with name, version, description, type, crew_member keys.
        """
        return self.get_section("plugin")

    # -- Internal -------------------------------------------------------------

    def _resolve_views_path(self) -> Path:
        """
        Return the path to views.yaml, preferring user override.

        Returns:
            Path to the views.yaml file to load.
        """
        if _USER_VIEWS.exists():
            return _USER_VIEWS
        return _DEFAULT_VIEWS

    @staticmethod
    def _load(config_path: Optional[Path]) -> dict:
        """
        Load and merge default and user curator.yaml files.

        Args:
            config_path: Explicit path override, or None to use defaults.

        Returns:
            Merged config dict.

        Raises:
            ConfigError: If a config file exists but cannot be read or parsed.
        """
        defaults = ConfigManager._load_yaml(_DEFAULT_CONFIG)

        # Explicit override path (testing or advanced use)
        if config_path is not None:
            user = ConfigManager._load_yaml(config_path)
            return ConfigManager._merge(defaults, user)

        # Normal user config path
        if _USER_CONFIG.exists():
            user = ConfigManager._load_yaml(_USER_CONFIG)
            return ConfigManager._merge(defaults, user)

        return defaults

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        """
        Load a single YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed dict, or empty dict if file is empty.

        Raises:
            ConfigError: If the file cannot be read or parsed.
        """
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            raise ConfigError(
                f"Could not read config file {path}: {exc}"
            ) from exc

        return data or {}

    @staticmethod
    def _merge(base: dict, override: dict) -> dict:
        """
        Recursively merge override into base.

        Keys present in override replace or extend those in base.
        Keys absent from override are left unchanged.

        Args:
            base:     Default config dict.
            override: User config dict.

        Returns:
            Merged dict.
        """
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigManager._merge(result[key], value)
            else:
                result[key] = value
        return result
```
