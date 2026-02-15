#!/usr/bin/env python3
"""Tests for the ssd_analyzer CLI module."""

import os
import sys
import tempfile

import pytest

from smart_parser import SmartData
from ssd_analyzer import parse_arguments, _determine_capacity, main


# ===========================================================================
# parse_arguments tests
# ===========================================================================

class TestParseArguments:
    """Tests for parse_arguments()."""

    def test_all_required_args(self, monkeypatch):
        """All required args parse correctly."""
        monkeypatch.setattr(sys, 'argv', [
            'ssd_analyzer.py',
            '--snapshot1', 'file1.txt',
            '--snapshot2', 'file2.txt',
            '--host-lba-size', '0.5',
            '--flash-lba-size', '32',
            '--rated-pe-cycles', '3000',
        ])
        args = parse_arguments()
        assert str(args.snapshot1) == "file1.txt"
        assert str(args.snapshot2) == "file2.txt"
        assert args.host_lba_size == 0.5
        assert args.flash_lba_size == 32.0
        assert args.rated_pe_cycles == 3000
        assert args.capacity is None
        assert args.output is None

    def test_optional_capacity(self, monkeypatch):
        """--capacity flag parsed."""
        monkeypatch.setattr(sys, 'argv', [
            'ssd_analyzer.py',
            '--snapshot1', 'f1.txt',
            '--snapshot2', 'f2.txt',
            '--host-lba-size', '0.5',
            '--flash-lba-size', '32',
            '--rated-pe-cycles', '3000',
            '--capacity', '512',
        ])
        args = parse_arguments()
        assert args.capacity == 512.0

    def test_optional_output(self, monkeypatch):
        """--output flag parsed."""
        monkeypatch.setattr(sys, 'argv', [
            'ssd_analyzer.py',
            '--snapshot1', 'f1.txt',
            '--snapshot2', 'f2.txt',
            '--host-lba-size', '0.5',
            '--flash-lba-size', '32',
            '--rated-pe-cycles', '3000',
            '--output', 'report.txt',
        ])
        args = parse_arguments()
        assert str(args.output) == "report.txt"

    def test_missing_required_args(self, monkeypatch):
        """Missing required args causes SystemExit."""
        monkeypatch.setattr(sys, 'argv', [
            'ssd_analyzer.py',
            '--snapshot1', 'f1.txt',
            # missing --snapshot2 and others
        ])
        with pytest.raises(SystemExit):
            parse_arguments()


# ===========================================================================
# _determine_capacity tests
# ===========================================================================

class TestDetermineCapacity:
    """Tests for _determine_capacity()."""

    def test_from_args(self):
        """Capacity from command line args."""

        class FakeArgs:  # pylint: disable=too-few-public-methods
            """Fake args with capacity set."""
            capacity = 512.0

        snap = SmartData(capacity_bytes=500_107_862_016)
        result = _determine_capacity(FakeArgs(), snap)
        assert result == 512.0

    def test_from_snapshot(self):
        """Capacity auto-detected from snapshot."""

        class FakeArgs:  # pylint: disable=too-few-public-methods
            """Fake args without capacity."""
            capacity = None

        snap = SmartData(capacity_bytes=500_107_862_016)
        result = _determine_capacity(FakeArgs(), snap)
        expected = 500_107_862_016 / (1024 ** 3)
        assert result == pytest.approx(expected, rel=0.001)

    def test_neither_exits(self):
        """No capacity info causes SystemExit."""

        class FakeArgs:  # pylint: disable=too-few-public-methods
            """Fake args without capacity."""
            capacity = None

        snap = SmartData(capacity_bytes=None)
        with pytest.raises(SystemExit):
            _determine_capacity(FakeArgs(), snap)


# ===========================================================================
# main() integration tests
# ===========================================================================

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "samples")


class TestMainIntegration:
    """Integration tests for the main() function."""

    @pytest.fixture()
    def sample_files_exist(self):
        """Skip if sample files don't exist."""
        f1 = os.path.join(SAMPLE_DIR, "smartctl_day1.txt")
        f2 = os.path.join(SAMPLE_DIR, "smartctl_day30.txt")
        if not (os.path.exists(f1) and os.path.exists(f2)):
            pytest.skip("Sample files not present")
        return f1, f2

    def test_main_success(self, monkeypatch, capsys,
                          sample_files_exist):
        """main() runs successfully with sample data."""
        f1, f2 = sample_files_exist
        monkeypatch.setattr(sys, 'argv', [
            'ssd_analyzer.py',
            '--snapshot1', f1,
            '--snapshot2', f2,
            '--host-lba-size', '0.5',
            '--flash-lba-size', '32',
            '--rated-pe-cycles', '3000',
            '--capacity', '500',
        ])
        main()
        captured = capsys.readouterr()
        assert "SSD ENDURANCE ANALYSIS REPORT" in captured.out

    def test_main_output_file(self, monkeypatch,
                              sample_files_exist):
        """main() writes report to --output file."""
        f1, f2 = sample_files_exist
        fd, output_path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        try:
            monkeypatch.setattr(sys, 'argv', [
                'ssd_analyzer.py',
                '--snapshot1', f1,
                '--snapshot2', f2,
                '--host-lba-size', '0.5',
                '--flash-lba-size', '32',
                '--rated-pe-cycles', '3000',
                '--capacity', '500',
                '--output', output_path,
            ])
            main()
            with open(output_path, 'r', encoding='utf-8') as fh:
                content = fh.read()
            assert "SSD ENDURANCE ANALYSIS REPORT" in content
        finally:
            os.unlink(output_path)

    def test_main_file_not_found(self, monkeypatch):
        """main() exits 1 for missing snapshot file."""
        monkeypatch.setattr(sys, 'argv', [
            'ssd_analyzer.py',
            '--snapshot1', '/nonexistent/file1.txt',
            '--snapshot2', '/nonexistent/file2.txt',
            '--host-lba-size', '0.5',
            '--flash-lba-size', '32',
            '--rated-pe-cycles', '3000',
            '--capacity', '500',
        ])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_auto_detect_capacity(self, monkeypatch, capsys,
                                       sample_files_exist):
        """main() auto-detects capacity when --capacity omitted."""
        f1, f2 = sample_files_exist
        monkeypatch.setattr(sys, 'argv', [
            'ssd_analyzer.py',
            '--snapshot1', f1,
            '--snapshot2', f2,
            '--host-lba-size', '0.5',
            '--flash-lba-size', '32',
            '--rated-pe-cycles', '3000',
        ])
        main()
        captured = capsys.readouterr()
        assert "SSD ENDURANCE ANALYSIS REPORT" in captured.out
