"""Curator configuration management.

Loads curator.yaml from shipped defaults in curator/data/, with optional
user overrides from ~/.config/curator/curator.yaml.

Database connection is handled by dbkit — Curator does not manage credentials.
"""

from pathlib import Path
from typing import Any, Optional

import yaml

from curator.exceptions import ConfigError


# Shipped defaults live in curator/data/
_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_CONFIG = _DATA_DIR / "curator.yaml"

# User config lives in ~/.config/curator/
_USER_CONFIG_DIR = Path.home() / ".config" / "curator"
_USER_CONFIG = _USER_CONFIG_DIR / "curator.yaml"


class ConfigManager:
    """Load and merge Curator configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize ConfigManager.

        Args:
            config_path: Override path to curator.yaml for testing.
                        Defaults to ~/.config/curator/curator.yaml with
                        fallback to shipped defaults.
        """
        self._config = self._load(config_path)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a config value by section and key.

        Args:
            section: Top-level section (e.g., "server", "ui").
            key: Key within the section.
            default: Default if not found.

        Returns:
            Config value or default.
        """
        return self._config.get(section, {}).get(key, default)

    def get_section(self, section: str) -> dict:
        """Get an entire config section as a dict.

        Args:
            section: Top-level section name.

        Returns:
            Dict of key/value pairs, or empty dict if absent.
        """
        return self._config.get(section, {})

    @staticmethod
    def _load(config_path: Optional[Path]) -> dict:
        """Load and merge default and user curator.yaml files.

        Args:
            config_path: Explicit path override, or None for defaults.

        Returns:
            Merged config dict.

        Raises:
            ConfigError: If config file exists but cannot be read.
        """
        defaults = ConfigManager._load_yaml(_DEFAULT_CONFIG)

        if config_path is not None:
            user = ConfigManager._load_yaml(config_path)
            return ConfigManager._merge(defaults, user)

        if _USER_CONFIG.exists():
            user = ConfigManager._load_yaml(_USER_CONFIG)
            return ConfigManager._merge(defaults, user)

        return defaults

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        """Load a single YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed dict, or empty dict if file is empty.

        Raises:
            ConfigError: If file cannot be read or parsed.
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
        """Recursively merge override into base.

        Args:
            base: Default config dict.
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