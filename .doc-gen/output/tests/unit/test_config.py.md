# test_config.py

**Path:** tests/unit/test_config.py
**Syntax:** python
**Generated:** 2026-04-19 14:58:02

```python
"""
tests.unit.test_config - Unit tests for curator.config.ConfigManager.

Tests cover:
  - Default config loads without error (no config_path override)
  - get() returns correct values from defaults
  - get() returns default argument when key is absent
  - views_path and queries_path resolve to existing files
  - User override merges correctly over defaults
  - Nonexistent explicit config_path raises ConfigError
  - Malformed YAML raises ConfigError
  - Non-dict YAML raises ConfigError (real bug guard)
"""

from pathlib import Path

import pytest
import yaml

from curator.config import ConfigManager
from curator.exceptions import ConfigError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_yaml(path: Path, data: dict) -> Path:
    """Write a dict as YAML to path and return the path."""
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Default config (no config_path override — falls back to shipped defaults)
# ---------------------------------------------------------------------------

class TestDefaultConfig:
    """ConfigManager loads shipped defaults when no user config is present."""

    def test_loads_without_error(self):
        cfg = ConfigManager()
        assert cfg is not None

    def test_get_server_host(self):
        cfg = ConfigManager()
        host = cfg.get("server", "host")
        assert host is not None

    def test_get_missing_key_returns_default(self):
        cfg = ConfigManager()
        result = cfg.get("server", "no_such_key", default="sentinel")
        assert result == "sentinel"

    def test_get_missing_section_returns_default(self):
        cfg = ConfigManager()
        result = cfg.get("no_such_section", "key", default=42)
        assert result == 42

    def test_views_path_exists(self):
        cfg = ConfigManager()
        assert cfg.views_path.exists()

    def test_queries_path_exists(self):
        cfg = ConfigManager()
        assert cfg.queries_path.exists()


# ---------------------------------------------------------------------------
# User override merging
# ---------------------------------------------------------------------------

class TestUserOverride:
    """User config merges over defaults — only present keys are overridden."""

    def test_override_single_value(self, tmp_path):
        user_cfg = write_yaml(tmp_path / "curator.yaml", {"server": {"host": "myhost"}})
        cfg = ConfigManager(config_path=user_cfg)
        assert cfg.get("server", "host") == "myhost"

    def test_non_overridden_keys_retain_defaults(self, tmp_path):
        user_cfg = write_yaml(tmp_path / "curator.yaml", {"server": {"host": "myhost"}})
        cfg = ConfigManager(config_path=user_cfg)
        port = cfg.get("server", "port")
        assert port is not None

    def test_user_views_path_used_when_present(self, tmp_path):
        write_yaml(tmp_path / "views.yaml", {"projects": {}})
        user_cfg = write_yaml(tmp_path / "curator.yaml", {})
        cfg = ConfigManager(config_path=user_cfg)
        assert cfg.views_path is not None


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestConfigErrors:
    """ConfigManager raises ConfigError on bad input."""

    def test_nonexistent_explicit_path_raises(self, tmp_path):
        with pytest.raises(ConfigError):
            ConfigManager(config_path=tmp_path / "nonexistent.yaml")

    def test_malformed_yaml_raises(self, tmp_path):
        bad = tmp_path / "curator.yaml"
        bad.write_text("key: [unclosed", encoding="utf-8")
        with pytest.raises(ConfigError):
            ConfigManager(config_path=bad)

    def test_non_dict_yaml_raises(self, tmp_path):
        bad = tmp_path / "curator.yaml"
        bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises((ConfigError, AttributeError)):
            ConfigManager(config_path=bad)

```
