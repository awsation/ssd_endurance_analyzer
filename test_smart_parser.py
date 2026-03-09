#!/usr/bin/env python3
"""Tests for the smart_parser module."""
# pylint: disable=too-many-public-methods

import os
import tempfile
from datetime import datetime

import pytest

from smart_parser import SmartData, SmartParser


# ---------------------------------------------------------------------------
# Sample smartctl content builders
# ---------------------------------------------------------------------------

NVME_TEMPLATE = """\
smartctl 7.2 2020-12-30 r5155

=== START OF INFORMATION SECTION ===
Model Number:                       Samsung SSD 970 EVO Plus 500GB
Serial Number:                      S4EWNF0M123456X
Namespace 1 Size/Capacity:          500,107,862,016 [500 GB]
Local Time is:                      {timestamp}
NVMe Version:                       1.3

=== START OF SMART DATA SECTION ===
SMART/Health Information (NVMe Log 0x02)
Available Spare:                    {spare}%
Percentage Used:                    {pct_used}%
Data Units Read:                    {units_read} [23.1 TB]
Data Units Written:                 {units_written} [25.6 TB]
Power On Hours:                     {power_on_hours}
"""

SATA_TEMPLATE = """\
smartctl 7.2 2020-12-30 r5155

=== START OF INFORMATION SECTION ===
Device Model:     Samsung SSD 860 EVO 500GB
Serial Number:                      S3YANB0K123456X
User Capacity:    500,107,862,016 bytes [500 GB]
Local Time is:                      {timestamp}

=== START OF SMART DATA SECTION ===
SMART Attributes Data Structure revision number: 1
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED WHEN_FAILED RAW_VALUE
  9 Power_On_Hours          0x0032   099   099   000    Old_age   Always       -       {power_on_hours}
241 Total_LBAs_Written      0x0032   099   099   000    Old_age   Always       -       {lba_written}
"""


def _write_temp_file(content: str) -> str:
    """Write content to a temp file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        fh.write(content)
    return path


def _make_nvme(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    timestamp="Mon Jan 01 10:00:00 2026 EST",
    units_written="50,000,000",
    units_read="45,232,156",
    power_on_hours="1,200",
    pct_used="4",
    spare="100",
) -> str:
    """Build NVMe smartctl content."""
    return NVME_TEMPLATE.format(
        timestamp=timestamp,
        units_written=units_written,
        units_read=units_read,
        power_on_hours=power_on_hours,
        pct_used=pct_used,
        spare=spare,
    )


def _make_sata(
    timestamp="Mon Jan 01 10:00:00 2026 EST",
    lba_written="97656250",
    power_on_hours="1200",
) -> str:
    """Build SATA smartctl content."""
    return SATA_TEMPLATE.format(
        timestamp=timestamp,
        lba_written=lba_written,
        power_on_hours=power_on_hours,
    )


# ===========================================================================
# SmartData tests
# ===========================================================================

class TestSmartData:
    """Tests for the SmartData dataclass."""

    def test_default_values(self):
        """All fields default to None/False."""
        data = SmartData()
        assert data.timestamp is None
        assert data.model is None
        assert data.serial is None
        assert data.capacity_bytes is None
        assert data.data_units_written is None
        assert data.data_units_read is None
        assert data.power_on_hours is None
        assert data.percentage_used is None
        assert data.available_spare is None
        assert data.is_nvme is False

    def test_repr(self):
        """__repr__ includes key fields."""
        data = SmartData(model="Test", serial="SN1",
                         data_units_written=100)
        r = repr(data)
        assert "Test" in r
        assert "SN1" in r
        assert "100" in r


# ===========================================================================
# NVMe parsing tests
# ===========================================================================

class TestSmartParserNVMe:
    """Tests for parsing NVMe smartctl output."""

    def test_parse_nvme_model(self):
        """Model is correctly extracted."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.model == "Samsung SSD 970 EVO Plus 500GB"
        finally:
            os.unlink(path)

    def test_parse_nvme_serial(self):
        """Serial number is correctly extracted."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.serial == "S4EWNF0M123456X"
        finally:
            os.unlink(path)

    def test_parse_nvme_is_nvme(self):
        """is_nvme flag set for NVMe content."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.is_nvme is True
        finally:
            os.unlink(path)

    def test_parse_nvme_capacity(self):
        """Capacity parsed from Namespace line."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.capacity_bytes == 500_107_862_016
        finally:
            os.unlink(path)

    def test_parse_nvme_data_units_written(self):
        """Data Units Written parsed correctly."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.data_units_written == 50_000_000
        finally:
            os.unlink(path)

    def test_parse_nvme_data_units_read(self):
        """Data Units Read parsed correctly."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.data_units_read == 45_232_156
        finally:
            os.unlink(path)

    def test_parse_nvme_power_on_hours(self):
        """Power On Hours parsed correctly."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.power_on_hours == 1200
        finally:
            os.unlink(path)

    def test_parse_nvme_percentage_used(self):
        """Percentage Used parsed correctly."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.percentage_used == 4
        finally:
            os.unlink(path)

    def test_parse_nvme_available_spare(self):
        """Available Spare parsed correctly."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.available_spare == 100
        finally:
            os.unlink(path)

    def test_parse_nvme_timestamp(self):
        """Timestamp parsed from Local Time line."""
        path = _write_temp_file(_make_nvme())
        try:
            data = SmartParser.parse_file(path)
            assert data.timestamp is not None
            assert data.timestamp.year == 2026
            assert data.timestamp.month == 1
            assert data.timestamp.day == 1
        finally:
            os.unlink(path)


# ===========================================================================
# Timestamp format tests
# ===========================================================================

class TestTimestampParsing:
    """Test various timestamp formats."""

    def test_format_without_timezone(self):
        """Parses '%a %b %d %H:%M:%S %Y' format."""
        content = _make_nvme(timestamp="Mon Jan 01 10:00:00 2026")
        path = _write_temp_file(content)
        try:
            data = SmartParser.parse_file(path)
            assert data.timestamp is not None
            assert data.timestamp.year == 2026
        finally:
            os.unlink(path)

    def test_iso_format(self):
        """Parses '%Y-%m-%d %H:%M:%S' format."""
        content = _make_nvme(timestamp="2026-01-15 14:30:00")
        path = _write_temp_file(content)
        try:
            data = SmartParser.parse_file(path)
            assert data.timestamp is not None
            assert data.timestamp.day == 15
            assert data.timestamp.hour == 14
        finally:
            os.unlink(path)


# ===========================================================================
# SATA parsing tests
# ===========================================================================

class TestSmartParserSATA:
    """Tests for parsing SATA smartctl output."""

    def test_sata_not_nvme(self):
        """is_nvme is False for SATA output."""
        path = _write_temp_file(_make_sata())
        try:
            data = SmartParser.parse_file(path)
            assert data.is_nvme is False
        finally:
            os.unlink(path)

    def test_sata_model(self):
        """Device Model parsed from SATA."""
        path = _write_temp_file(_make_sata())
        try:
            data = SmartParser.parse_file(path)
            assert data.model == "Samsung SSD 860 EVO 500GB"
        finally:
            os.unlink(path)

    def test_sata_capacity_user_capacity(self):
        """User Capacity parsed from SATA."""
        path = _write_temp_file(_make_sata())
        try:
            data = SmartParser.parse_file(path)
            assert data.capacity_bytes == 500_107_862_016
        finally:
            os.unlink(path)

    def test_sata_lba_written(self):
        """Total_LBAs_Written attribute parsed."""
        path = _write_temp_file(_make_sata())
        try:
            data = SmartParser.parse_file(path)
            assert data.data_units_written == 97656250
        finally:
            os.unlink(path)

    def test_sata_power_on_hours(self):
        """Power_On_Hours attribute parsed."""
        path = _write_temp_file(_make_sata())
        try:
            data = SmartParser.parse_file(path)
            assert data.power_on_hours == 1200
        finally:
            os.unlink(path)


# ===========================================================================
# Error / edge case tests
# ===========================================================================

class TestSmartParserErrors:
    """Tests for error conditions and edge cases."""

    def test_file_not_found(self):
        """Non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            SmartParser.parse_file("/nonexistent/path/smartctl.txt")

    def test_missing_data_units_written(self):
        """File without Data Units Written raises ValueError."""
        content = """\
NVMe Version: 1.3
Local Time is: Mon Jan 01 10:00:00 2026
Model Number: TestDrive
"""
        path = _write_temp_file(content)
        try:
            with pytest.raises(ValueError, match="data units written"):
                SmartParser.parse_file(path)
        finally:
            os.unlink(path)

    def test_empty_file_raises(self):
        """Empty file raises ValueError (no data units)."""
        path = _write_temp_file("")
        try:
            with pytest.raises(ValueError):
                SmartParser.parse_file(path)
        finally:
            os.unlink(path)

    def test_numbers_with_commas(self):
        """Numbers with commas are parsed correctly."""
        content = _make_nvme(units_written="1,234,567,890")
        path = _write_temp_file(content)
        try:
            data = SmartParser.parse_file(path)
            assert data.data_units_written == 1_234_567_890
        finally:
            os.unlink(path)

    def test_parse_real_sample_day1(self):
        """Parse the bundled sample file (day 1)."""
        sample = os.path.join(
            os.path.dirname(__file__), "samples", "smartctl_day1.txt"
        )
        if not os.path.exists(sample):
            pytest.skip("Sample file not present")
        data = SmartParser.parse_file(sample)
        assert data.data_units_written == 50_000_000
        assert data.is_nvme is True

    def test_parse_real_sample_day30(self):
        """Parse the bundled sample file (day 30)."""
        sample = os.path.join(
            os.path.dirname(__file__), "samples", "smartctl_day30.txt"
        )
        if not os.path.exists(sample):
            pytest.skip("Sample file not present")
        data = SmartParser.parse_file(sample)
        assert data.data_units_written == 52_500_000


# ===========================================================================
# validate_snapshots tests
# ===========================================================================

class TestValidateSnapshots:
    """Tests for SmartParser.validate_snapshots()."""

    @staticmethod
    def _snap(serial="SN1", ts=None, units=100):
        """Create a minimal SmartData for validation tests."""
        return SmartData(
            serial=serial,
            timestamp=ts,
            data_units_written=units,
        )

    def test_valid_snapshots(self):
        """Valid snapshot pair passes without error."""
        s1 = self._snap(ts=datetime(2026, 1, 1), units=100)
        s2 = self._snap(ts=datetime(2026, 1, 30), units=200)
        SmartParser.validate_snapshots(s1, s2)  # no exception

    def test_mismatched_serials(self):
        """Different serial numbers raises ValueError."""
        s1 = self._snap(serial="SN1", ts=datetime(2026, 1, 1))
        s2 = self._snap(serial="SN2", ts=datetime(2026, 1, 30))
        with pytest.raises(ValueError, match="different drives"):
            SmartParser.validate_snapshots(s1, s2)

    def test_wrong_timestamp_order(self):
        """Snapshot 1 later than snapshot 2 raises ValueError."""
        s1 = self._snap(ts=datetime(2026, 2, 1), units=100)
        s2 = self._snap(ts=datetime(2026, 1, 1), units=200)
        with pytest.raises(ValueError, match="earlier"):
            SmartParser.validate_snapshots(s1, s2)

    def test_same_timestamp(self):
        """Same timestamps raises ValueError."""
        ts = datetime(2026, 1, 1)
        s1 = self._snap(ts=ts, units=100)
        s2 = self._snap(ts=ts, units=200)
        with pytest.raises(ValueError, match="earlier"):
            SmartParser.validate_snapshots(s1, s2)

    def test_decreasing_data_units(self):
        """Decreasing data units raises ValueError."""
        s1 = self._snap(ts=datetime(2026, 1, 1), units=500)
        s2 = self._snap(ts=datetime(2026, 1, 30), units=100)
        with pytest.raises(ValueError, match="decreased"):
            SmartParser.validate_snapshots(s1, s2)

    def test_none_serial_allowed(self):
        """None serial numbers skip serial check."""
        s1 = self._snap(serial=None, ts=datetime(2026, 1, 1),
                        units=100)
        s2 = self._snap(serial=None, ts=datetime(2026, 1, 30),
                        units=200)
        SmartParser.validate_snapshots(s1, s2)  # no exception

    def test_none_timestamp_allowed(self):
        """None timestamps skip timestamp check."""
        s1 = self._snap(ts=None, units=100)
        s2 = self._snap(ts=None, units=200)
        SmartParser.validate_snapshots(s1, s2)  # no exception
