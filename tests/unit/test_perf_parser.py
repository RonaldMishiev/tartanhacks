"""
Extended edge case tests for the perf_parser (llvm-mca output parsing).
Ensures both legacy and table formats work, and edge cases don't crash.
"""
import pytest
from localbolt.parsing.perf_parser import parse_mca_output, InstructionStats


class TestParseMcaLegacyFormat:
    """Test the [idx]: {latency, uops, throughput} format."""

    def test_basic_legacy_parsing(self):
        mca = """
Instruction Info:
[0]: {1, 0.50, 0.50, 0.00,  - }     pushq  %rbp
[1]: {3, 1.00, 1.00, 0.00,  - }     imul   eax, edi
"""
        stats = parse_mca_output(mca)
        assert len(stats) == 2
        assert stats[0].latency == 1
        assert stats[1].latency == 3
        assert stats[1].throughput == 1.0

    def test_single_instruction(self):
        mca = """
Instruction Info:
[0]: {1, 0.50, 0.50, 0.00,  - }     ret
"""
        stats = parse_mca_output(mca)
        assert len(stats) == 1
        assert stats[0].latency == 1


class TestParseMcaTableFormat:
    """Test the uOps Latency RThroughput table format."""

    def test_table_format_parsing(self):
        mca = """
Instruction Info:
[1]    [2]    [3]    [4]
 1      1     0.50          pushq  %rbp
 1      3     1.00          imul   eax, edi
"""
        stats = parse_mca_output(mca)
        assert len(stats) == 2
        assert stats[0].latency == 1
        assert stats[1].latency == 3


class TestParseMcaEdgeCases:
    """Edge cases for parse_mca_output."""

    def test_empty_input(self):
        stats = parse_mca_output("")
        assert stats == {}

    def test_no_instruction_info_section(self):
        stats = parse_mca_output("Timeline view:\nsome other stuff")
        assert stats == {}

    def test_only_header_no_instructions(self):
        mca = """
Instruction Info:

Timeline view:
"""
        stats = parse_mca_output(mca)
        assert stats == {}

    def test_garbage_input(self):
        stats = parse_mca_output("hello world\nfoo bar\n12345")
        assert stats == {}

    def test_multiline_with_other_sections(self):
        """Real llvm-mca output has multiple sections — only Instruction Info matters."""
        mca = """
Iterations:        100
Instructions:      400
Total Cycles:      103

Instruction Info:
[0]: {1, 0.50, 0.50, 0.00,  - }     pushq  %rbp
[1]: {1, 0.25, 0.25, 0.00,  - }     ret

Resources:
[0] - some resource info
"""
        stats = parse_mca_output(mca)
        assert len(stats) == 2
        assert stats[0].latency == 1
        assert stats[1].latency == 1


class TestInstructionStats:
    """Test InstructionStats NamedTuple."""

    def test_fields(self):
        s = InstructionStats(latency=2, uops=1.0, throughput=0.5)
        assert s.latency == 2
        assert s.uops == 1.0
        assert s.throughput == 0.5

    def test_named_access(self):
        s = InstructionStats(latency=1, uops=0.5, throughput=0.25)
        assert s[0] == 1  # positional access
        assert s[1] == 0.5
        assert s[2] == 0.25

    def test_equality(self):
        s1 = InstructionStats(1, 0.5, 0.5)
        s2 = InstructionStats(1, 0.5, 0.5)
        assert s1 == s2

    def test_inequality(self):
        s1 = InstructionStats(1, 0.5, 0.5)
        s2 = InstructionStats(2, 0.5, 0.5)
        assert s1 != s2
