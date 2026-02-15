#!/usr/bin/env python3
"""Tests for the formatters module."""

from datetime import datetime

from smart_parser import SmartData
from endurance_calculator import EnduranceMetrics
from formatters import format_bytes, create_ascii_table, format_analysis_report


# ===========================================================================
# format_bytes tests
# ===========================================================================

class TestFormatBytes:
    """Tests for format_bytes()."""

    def test_zero_bytes(self):
        """0 bytes formatted correctly."""
        assert format_bytes(0) == "0.00 B"

    def test_bytes_below_1kb(self):
        """Values below 1 KB stay in bytes."""
        assert format_bytes(512) == "512.00 B"
        assert format_bytes(1023) == "1023.00 B"

    def test_exactly_1kb(self):
        """1024 bytes = 1.00 KB."""
        assert format_bytes(1024) == "1.00 KB"

    def test_megabytes(self):
        """MB range."""
        assert format_bytes(1024 ** 2) == "1.00 MB"

    def test_gigabytes(self):
        """GB range."""
        assert format_bytes(1024 ** 3) == "1.00 GB"

    def test_terabytes(self):
        """TB range."""
        assert format_bytes(1024 ** 4) == "1.00 TB"

    def test_petabytes(self):
        """PB range."""
        assert format_bytes(1024 ** 5) == "1.00 PB"

    def test_beyond_petabytes(self):
        """Values beyond PB stay in PB."""
        result = format_bytes(2 * (1024 ** 5))
        assert result == "2.00 PB"

    def test_fractional_values(self):
        """Fractional values formatted correctly."""
        result = format_bytes(1536)  # 1.5 KB
        assert result == "1.50 KB"

    def test_custom_precision(self):
        """Custom precision parameter works."""
        result = format_bytes(1536, precision=0)
        assert result == "2 KB"  # rounds up
        result = format_bytes(1536, precision=4)
        assert result == "1.5000 KB"


# ===========================================================================
# create_ascii_table tests
# ===========================================================================

class TestCreateAsciiTable:
    """Tests for create_ascii_table()."""

    def test_single_row(self):
        """Table with one data row."""
        headers = ["Name", "Value"]
        rows = [["Foo", "123"]]
        table = create_ascii_table(headers, rows)
        assert "Name" in table
        assert "Value" in table
        assert "Foo" in table
        assert "123" in table

    def test_multiple_rows(self):
        """Table with multiple data rows."""
        headers = ["A", "B"]
        rows = [["1", "2"], ["3", "4"]]
        table = create_ascii_table(headers, rows)
        lines = table.split("\n")
        # separator + header + separator + 2 data + separator = 6 lines
        assert len(lines) == 6

    def test_column_width_adjustment(self):
        """Columns expand for long values."""
        headers = ["H"]
        rows = [["VeryLongValue"]]
        table = create_ascii_table(headers, rows)
        assert "VeryLongValue" in table

    def test_separators(self):
        """Table has + separators at row boundaries."""
        headers = ["X"]
        rows = [["Y"]]
        table = create_ascii_table(headers, rows)
        lines = table.split("\n")
        assert lines[0].startswith("+")
        assert lines[0].endswith("+")

    def test_empty_rows(self):
        """Table with no data rows still has header."""
        headers = ["A", "B"]
        table = create_ascii_table(headers, [])
        assert "A" in table
        assert "B" in table


# ===========================================================================
# format_analysis_report tests
# ===========================================================================

def _build_test_data():
    """Create consistent test data for report tests."""
    snap1 = SmartData(
        timestamp=datetime(2026, 1, 1, 10, 0, 0),
        model="Samsung SSD 970 EVO Plus 500GB",
        serial="S4EWNF0M123456X",
        capacity_bytes=500_107_862_016,
        data_units_written=50_000_000,
        data_units_read=45_000_000,
        power_on_hours=1200,
        percentage_used=4,
        available_spare=100,
        is_nvme=True,
    )
    snap2 = SmartData(
        timestamp=datetime(2026, 1, 30, 10, 0, 0),
        model="Samsung SSD 970 EVO Plus 500GB",
        serial="S4EWNF0M123456X",
        capacity_bytes=500_107_862_016,
        data_units_written=52_500_000,
        data_units_read=48_000_000,
        power_on_hours=1896,
        percentage_used=5,
        available_spare=100,
        is_nvme=True,
    )
    metrics = EnduranceMetrics(
        time_delta_days=29.0,
        host_writes_delta=1_280_000_000.0,
        flash_writes_delta=1_280_000_000.0,
        waf=1.0,
        total_host_writes_tb=25.0,
        total_flash_writes_tb=25.0,
        dwpd=0.0834,
        daily_write_rate_gb=41.72,
        pe_cycles_consumed=50.0,
        estimated_remaining_days=52_000.0,
        estimated_remaining_years=142.35,
        wear_percentage=1.67,
    )
    return snap1, snap2, metrics


class TestFormatAnalysisReport:
    """Tests for format_analysis_report()."""

    def test_report_has_header(self):
        """Report contains the main header."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "SSD ENDURANCE ANALYSIS REPORT" in report

    def test_report_has_drive_info(self):
        """Report contains drive information section."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "DRIVE INFORMATION" in report
        assert "Samsung SSD 970 EVO Plus 500GB" in report
        assert "S4EWNF0M123456X" in report
        assert "NVMe" in report

    def test_report_has_parameters(self):
        """Report contains analysis parameters."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "ANALYSIS PARAMETERS" in report
        assert "0.5 KB per count" in report
        assert "32.0 KB per count" in report
        assert "3000" in report

    def test_report_has_snapshot_comparison(self):
        """Report contains snapshot comparison table."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "SNAPSHOT COMPARISON" in report
        assert "Data Units Written" in report
        assert "Power On Hours" in report

    def test_report_has_endurance_metrics(self):
        """Report contains endurance metrics table."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "CALCULATED ENDURANCE METRICS" in report
        assert "WAF" in report
        assert "TBW" in report
        assert "DWPD" in report

    def test_report_has_wear_analysis(self):
        """Report contains wear and lifetime section."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "WEAR AND LIFETIME ANALYSIS" in report
        assert "P/E Cycles Consumed" in report

    def test_report_has_methodology(self):
        """Report contains calculation methodology."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "CALCULATION METHODOLOGY" in report

    def test_report_has_footer(self):
        """Report contains footer with timestamp."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "Report generated:" in report

    def test_percentage_used_shown(self):
        """Percentage Used row appears when data is present."""
        s1, s2, m = _build_test_data()
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "Percentage Used" in report

    def test_percentage_used_hidden_when_none(self):
        """Percentage Used row omitted when snap2 has None."""
        s1, s2, m = _build_test_data()
        s2.percentage_used = None
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "Percentage Used" not in report

    def test_sata_drive_type(self):
        """SATA drive shows 'SATA' in drive type."""
        s1, s2, m = _build_test_data()
        s2.is_nvme = False
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "SATA" in report

    def test_capacity_fallback_to_gb(self):
        """When capacity_bytes is None, uses capacity_gb."""
        s1, s2, m = _build_test_data()
        s2.capacity_bytes = None
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "500.0 GB" in report

    def test_wear_status_good(self):
        """Wear below 50% shows 'Good'."""
        s1, s2, m = _build_test_data()
        m.wear_percentage = 10.0
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "Good" in report

    def test_wear_status_critical(self):
        """Wear >= 95% shows 'Critical'."""
        s1, s2, m = _build_test_data()
        m.wear_percentage = 98.0
        m.estimated_remaining_years = 0.1
        report = format_analysis_report(
            s1, s2, m,
            host_lba_size_kb=0.5,
            flash_lba_size_kb=32.0,
            rated_pe_cycles=3000,
            capacity_gb=500.0,
        )
        assert "Critical" in report
        assert "Replace Soon" in report
