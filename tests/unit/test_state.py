"""
Tests for the LocalBoltState dataclass.
Ensures state management works correctly for both C++ and Rust pipelines.
"""
import pytest
from localbolt.utils.state import LocalBoltState
from localbolt.parsing.perf_parser import InstructionStats
from localbolt.parsing.diagnostics import Diagnostic


class TestLocalBoltStateDefaults:
    """Test default values of LocalBoltState."""

    def test_default_fields(self):
        state = LocalBoltState()
        assert state.source_path == ""
        assert state.source_code == ""
        assert state.source_lines == []
        assert state.asm_content == ""
        assert state.asm_mapping == {}
        assert state.perf_stats == {}
        assert state.raw_mca_output == ""
        assert state.compiler_output == ""
        assert state.user_flags == []
        assert state.diagnostics == []

    def test_has_errors_false_by_default(self):
        state = LocalBoltState()
        assert state.has_errors is False


class TestLocalBoltStateErrors:
    """Test has_errors property."""

    def test_has_errors_with_error(self):
        state = LocalBoltState()
        state.diagnostics = [Diagnostic(line=1, column=1, severity="error", message="bad")]
        assert state.has_errors is True

    def test_has_errors_with_warning_only(self):
        state = LocalBoltState()
        state.diagnostics = [Diagnostic(line=1, column=1, severity="warning", message="warn")]
        assert state.has_errors is False

    def test_has_errors_mixed(self):
        state = LocalBoltState()
        state.diagnostics = [
            Diagnostic(line=1, column=1, severity="warning", message="warn"),
            Diagnostic(line=2, column=1, severity="error", message="err"),
        ]
        assert state.has_errors is True


class TestLocalBoltStateSourceMapping:
    """Test get_source_line_for_asm."""

    def test_valid_mapping(self):
        state = LocalBoltState()
        state.source_lines = ["line1", "line2", "line3"]
        state.asm_mapping = {0: 1, 1: 2, 2: 3}
        assert state.get_source_line_for_asm(0) == "line1"
        assert state.get_source_line_for_asm(1) == "line2"
        assert state.get_source_line_for_asm(2) == "line3"

    def test_unmapped_asm_line_returns_none(self):
        state = LocalBoltState()
        state.source_lines = ["line1"]
        state.asm_mapping = {0: 1}
        assert state.get_source_line_for_asm(99) is None

    def test_out_of_range_source_line_returns_none(self):
        state = LocalBoltState()
        state.source_lines = ["line1"]
        state.asm_mapping = {0: 100}  # Maps to line 100 but only 1 line exists
        assert state.get_source_line_for_asm(0) is None

    def test_zero_source_line_returns_none(self):
        state = LocalBoltState()
        state.source_lines = ["line1"]
        state.asm_mapping = {0: 0}  # Line 0 is out of range (1-indexed)
        assert state.get_source_line_for_asm(0) is None

    def test_empty_source_lines(self):
        state = LocalBoltState()
        state.source_lines = []
        state.asm_mapping = {0: 1}
        assert state.get_source_line_for_asm(0) is None


class TestLocalBoltStateUpdate:
    """Test update methods."""

    def test_update_asm(self):
        state = LocalBoltState()
        state.update_asm("push rbp\nret", {0: 1, 1: 2})
        assert state.asm_content == "push rbp\nret"
        assert state.asm_mapping == {0: 1, 1: 2}

    def test_update_perf(self):
        state = LocalBoltState()
        stats = {0: InstructionStats(latency=1, uops=0.5, throughput=0.5)}
        state.update_perf(stats, "raw mca output")
        assert state.perf_stats == stats
        assert state.raw_mca_output == "raw mca output"

    def test_update_asm_replaces_previous(self):
        state = LocalBoltState()
        state.update_asm("old asm", {0: 1})
        state.update_asm("new asm", {0: 2})
        assert state.asm_content == "new asm"
        assert state.asm_mapping == {0: 2}

    def test_update_perf_replaces_previous(self):
        state = LocalBoltState()
        state.update_perf({0: InstructionStats(1, 0.5, 0.5)}, "old")
        state.update_perf({}, "new")
        assert state.perf_stats == {}
        assert state.raw_mca_output == "new"


class TestLocalBoltStateWithSourcePath:
    """Test state initialized with source path (as engine does)."""

    def test_source_path_preserved(self):
        state = LocalBoltState(source_path="/home/user/main.cpp")
        assert state.source_path == "/home/user/main.cpp"

    def test_rust_source_path(self):
        state = LocalBoltState(source_path="/home/user/main.rs")
        assert state.source_path == "/home/user/main.rs"

    def test_user_flags_mutability(self):
        state = LocalBoltState()
        state.user_flags = ["-O2", "-g"]
        assert state.user_flags == ["-O2", "-g"]
