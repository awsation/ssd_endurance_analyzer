"""
Unit tests for ssd_analyzer_daemon.py
"""
import os
import subprocess
import time
from unittest.mock import patch, MagicMock

import pytest
from ssd_analyzer_daemon import rotate_reports, run_smartctl, main

def test_rotate_reports_less_than_keep(tmp_path):
    report1 = tmp_path / "report-1.txt"
    report1.write_text("1")
    rotate_reports(tmp_path, keep_count=2)
    assert len(list(tmp_path.glob("report-*.txt"))) == 1

def test_rotate_reports_more_than_keep(tmp_path):
    reports = []
    # Create 4 files with distinct mtimes
    now = time.time()
    for i in range(4):
        f = tmp_path / f"report-{i}.txt"
        f.write_text(str(i))
        # i=0 is newest, i=3 is oldest
        os.utime(f, (now - i * 10, now - i * 10))
        reports.append(f)

    rotate_reports(tmp_path, keep_count=2)
    remaining = list(tmp_path.glob("report-*.txt"))
    assert len(remaining) == 2
    # Should keep the newest two: 0 and 1
    names = set(p.name for p in remaining)
    assert "report-0.txt" in names
    assert "report-1.txt" in names

@patch("subprocess.run")
def test_run_smartctl_success(mock_run):
    mock_run.return_value = MagicMock(stdout="output", stderr="")
    assert run_smartctl("/dev/test") == "output"
    mock_run.assert_called_once()

@patch("subprocess.run")
def test_run_smartctl_called_process_error(mock_run, capsys):
    mock_run.side_effect = subprocess.CalledProcessError(1, ['smartctl'], output="out", stderr="err")
    with pytest.raises(SystemExit):
        run_smartctl("/dev/test")
    captured = capsys.readouterr()
    assert "Error running smartctl" in captured.err

@patch("subprocess.run")
def test_run_smartctl_file_not_found(mock_run, capsys):
    mock_run.side_effect = FileNotFoundError()
    with pytest.raises(SystemExit):
        run_smartctl("/dev/test")
    captured = capsys.readouterr()
    assert "smartctl not found" in captured.err

@patch("sys.argv", ["ssd_analyzer_daemon.py", "--device", "/dev/nvme0n1", 
                    "--host-lba-size", "0.5", "--flash-lba-size", "32", 
                    "--rated-pe-cycles", "3000", "--capacity", "512"])
@patch("ssd_analyzer_daemon.run_smartctl")
@patch("ssd_analyzer_daemon.SmartParser")
@patch("ssd_analyzer_daemon.EnduranceCalculator")
@patch("ssd_analyzer_daemon.format_analysis_report")
def test_main_first_run(mock_format, mock_calc, mock_parser, mock_run_smartctl, tmp_path):
    with patch("ssd_analyzer_daemon.argparse.ArgumentParser.parse_args") as mock_args:
        args = MagicMock()
        args.device = "/dev/nvme0n1"
        args.host_lba_size = 0.5
        args.flash_lba_size = 32
        args.rated_pe_cycles = 3000
        args.capacity = 512
        args.state_dir = tmp_path / "state"
        args.log_dir = tmp_path / "log"
        mock_args.return_value = args

        mock_run_smartctl.return_value = "fake smart data"

        # When state_file is missing, it exits 0
        with pytest.raises(SystemExit) as exc:
            main()
        
        assert exc.value.code == 0
        state_file = args.state_dir / "last_smart_snapshot.txt"
        assert state_file.exists()
        assert state_file.read_text() == "fake smart data"

@patch("sys.argv", ["ssd_analyzer_daemon.py", "--device", "/dev/nvme0n1", 
                    "--host-lba-size", "0.5", "--flash-lba-size", "32", 
                    "--rated-pe-cycles", "3000", "--capacity", "512"])
@patch("ssd_analyzer_daemon.run_smartctl")
@patch("ssd_analyzer_daemon.SmartParser")
@patch("ssd_analyzer_daemon.EnduranceCalculator")
@patch("ssd_analyzer_daemon.format_analysis_report")
def test_main_second_run(mock_format, mock_calc, mock_parser, mock_run_smartctl, tmp_path):
    with patch("ssd_analyzer_daemon.argparse.ArgumentParser.parse_args") as mock_args:
        args = MagicMock()
        args.device = "/dev/nvme0n1"
        args.host_lba_size = 0.5
        args.flash_lba_size = 32
        args.rated_pe_cycles = 3000
        args.capacity = 512
        args.state_dir = tmp_path / "state"
        args.log_dir = tmp_path / "log"
        mock_args.return_value = args

        args.state_dir.mkdir()
        args.log_dir.mkdir()
        state_file = args.state_dir / "last_smart_snapshot.txt"
        state_file.write_text("old smart data")

        mock_run_smartctl.return_value = "new smart data"

        parser_inst = mock_parser.return_value
        snap1 = MagicMock()
        snap1.data_units_written = 100
        snap1.timestamp = None
        snap2 = MagicMock()
        snap2.data_units_written = 200
        snap2.timestamp = None
        snap2.capacity_bytes = 512 * 1024**3
        parser_inst.parse_file.side_effect = [snap1, snap2]

        calc_inst = mock_calc.return_value
        calc_inst.calculate.return_value = MagicMock()
        mock_format.return_value = "fake report"

        main()
        
        reports = list(args.log_dir.glob("report-*.txt"))
        assert len(reports) == 1
        assert reports[0].read_text() == "fake report"
        
        assert state_file.read_text() == "new smart data"
