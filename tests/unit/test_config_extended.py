"""
Extended tests for ConfigManager — ensures Rust config additions
don't break existing C++ config behavior.
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from localbolt.utils.config import ConfigManager, DEFAULT_CONFIG


class TestConfigDefaults:
    """Test that default configuration values are correct."""

    def test_default_compiler(self):
        assert DEFAULT_CONFIG["compiler"] == "g++"

    def test_default_opt_level(self):
        assert DEFAULT_CONFIG["opt_level"] == "-O0"

    def test_default_flags_empty(self):
        assert DEFAULT_CONFIG["flags"] == []


class TestConfigManagerLoadSave:
    """Test config loading and saving."""

    def test_creates_config_dir(self, tmp_path):
        """ConfigManager should create ~/.localbolt/ if it doesn't exist."""
        config_dir = tmp_path / ".localbolt"
        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_dir / "config.json"
            mgr.config = mgr.load_config()
            # Directory should now exist
            assert config_dir.exists()

    def test_load_returns_defaults_when_no_file(self, tmp_path):
        config_dir = tmp_path / ".localbolt"
        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_dir / "config.json"
            config = mgr.load_config()
            assert config["compiler"] == "g++"
            assert config["opt_level"] == "-O0"

    def test_load_merges_user_config(self, tmp_path):
        config_dir = tmp_path / ".localbolt"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"compiler": "clang++"}))

        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_file
            config = mgr.load_config()
            # User override
            assert config["compiler"] == "clang++"
            # Default preserved
            assert config["opt_level"] == "-O0"

    def test_load_handles_corrupt_config(self, tmp_path):
        """Corrupt JSON should fall back to defaults."""
        config_dir = tmp_path / ".localbolt"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text("NOT VALID JSON {{{")

        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_file
            config = mgr.load_config()
            assert config["compiler"] == "g++"

    def test_save_and_reload(self, tmp_path):
        config_dir = tmp_path / ".localbolt"
        config_dir.mkdir()
        config_file = config_dir / "config.json"

        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_file
            mgr.config = DEFAULT_CONFIG.copy()

            mgr.set("compiler", "clang++")
            assert mgr.get("compiler") == "clang++"

            # Reload from disk
            mgr2 = ConfigManager()
            mgr2.config_dir = config_dir
            mgr2.config_file = config_file
            mgr2.config = mgr2.load_config()
            assert mgr2.get("compiler") == "clang++"


class TestConfigManagerGetSet:
    """Test get/set methods."""

    def test_get_existing_key(self, tmp_path):
        config_dir = tmp_path / ".localbolt"
        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_dir / "config.json"
            mgr.config = DEFAULT_CONFIG.copy()
            assert mgr.get("compiler") == "g++"

    def test_get_missing_key_returns_default(self, tmp_path):
        config_dir = tmp_path / ".localbolt"
        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_dir / "config.json"
            mgr.config = DEFAULT_CONFIG.copy()
            assert mgr.get("nonexistent", "fallback") == "fallback"

    def test_get_missing_key_returns_none(self, tmp_path):
        config_dir = tmp_path / ".localbolt"
        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_dir / "config.json"
            mgr.config = DEFAULT_CONFIG.copy()
            assert mgr.get("nonexistent") is None

    def test_set_new_key(self, tmp_path):
        config_dir = tmp_path / ".localbolt"
        config_dir.mkdir()
        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_dir / "config.json"
            mgr.config = DEFAULT_CONFIG.copy()
            mgr.set("rust_compiler", "rustc")
            assert mgr.get("rust_compiler") == "rustc"

    def test_set_overwrites_existing(self, tmp_path):
        config_dir = tmp_path / ".localbolt"
        config_dir.mkdir()
        with patch.object(ConfigManager, "__init__", lambda self: None):
            mgr = ConfigManager()
            mgr.config_dir = config_dir
            mgr.config_file = config_dir / "config.json"
            mgr.config = DEFAULT_CONFIG.copy()
            mgr.set("compiler", "clang++")
            assert mgr.get("compiler") == "clang++"
