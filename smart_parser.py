#!/usr/bin/env python3
"""
SMART Data Parser Module

Parses smartctl output files and extracts relevant SSD health metrics.
Supports both NVMe and SATA drive formats.
"""

import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SmartData:  # pylint: disable=too-many-instance-attributes
    """Container for parsed SMART data from a single snapshot."""

    timestamp: Optional[datetime] = None
    model: Optional[str] = None
    serial: Optional[str] = None
    capacity_bytes: Optional[int] = None
    data_units_written: Optional[int] = None  # Raw counter value
    data_units_read: Optional[int] = None     # Raw counter value
    power_on_hours: Optional[int] = None
    percentage_used: Optional[int] = None
    available_spare: Optional[int] = None
    is_nvme: bool = field(default=False)

    def __repr__(self):
        return (f"SmartData(model={self.model}, serial={self.serial}, "
                f"timestamp={self.timestamp}, "
                f"data_units_written={self.data_units_written})")


class SmartParser:
    """Parser for smartctl output files."""

    @staticmethod
    def parse_file(filepath: str) -> SmartData:
        """
        Parse a smartctl output file and extract relevant metrics.

        Args:
            filepath: Path to the smartctl output file

        Returns:
            SmartData object containing parsed metrics

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If critical data cannot be parsed
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        data = SmartData()

        # Detect if it's NVMe or SATA
        data.is_nvme = 'NVMe' in content or 'NVME' in content

        # Parse timestamp from local time line
        _parse_timestamp(content, data)

        # Parse model
        model_match = re.search(
            r'(?:Device Model|Model Number|Product):\s+(.+)', content)
        if model_match:
            data.model = model_match.group(1).strip()

        # Parse serial number
        serial_match = re.search(r'Serial Number:\s+(.+)', content)
        if serial_match:
            data.serial = serial_match.group(1).strip()

        # Parse capacity
        _parse_capacity(content, data)

        if data.is_nvme:
            _parse_nvme_fields(content, data)
        else:
            _parse_sata_fields(content, data)

        # Validate essential data
        if data.data_units_written is None:
            raise ValueError(
                f"Could not parse data units written from {filepath}")

        return data

    @staticmethod
    def validate_snapshots(snapshot1: SmartData,
                           snapshot2: SmartData) -> None:
        """
        Validate that two snapshots are from the same drive
        and in correct order.

        Args:
            snapshot1: First snapshot
            snapshot2: Second snapshot

        Raises:
            ValueError: If snapshots are invalid or incompatible
        """
        # Check same drive
        if snapshot1.serial and snapshot2.serial:
            if snapshot1.serial != snapshot2.serial:
                raise ValueError(
                    f"Snapshots are from different drives: "
                    f"{snapshot1.serial} vs {snapshot2.serial}")

        # Check timestamp order
        if snapshot1.timestamp and snapshot2.timestamp:
            if snapshot1.timestamp >= snapshot2.timestamp:
                raise ValueError(
                    "Snapshot 1 must be earlier than snapshot 2")

        # Check data units written - should be monotonically increasing
        if snapshot2.data_units_written < snapshot1.data_units_written:
            raise ValueError(
                "Data units written decreased between snapshots - "
                "check snapshot order")


def _parse_timestamp(content: str, data: SmartData) -> None:
    """Parse timestamp from smartctl local time line."""
    timestamp_match = re.search(
        r'Local Time is:\s+(.+?)(?:\n|$)', content)
    if timestamp_match:
        time_str = timestamp_match.group(1).strip()
        for fmt in ['%a %b %d %H:%M:%S %Y %Z',
                     '%a %b %d %H:%M:%S %Y',
                     '%Y-%m-%d %H:%M:%S',
                     '%c']:
            try:
                data.timestamp = datetime.strptime(
                    time_str.strip(), fmt)
                break
            except ValueError:
                continue


def _parse_capacity(content: str, data: SmartData) -> None:
    """Parse drive capacity from smartctl output."""
    capacity_match = re.search(
        r'User Capacity:\s+([0-9,]+)\s+bytes', content)
    if capacity_match:
        data.capacity_bytes = int(
            capacity_match.group(1).replace(',', ''))
    else:
        # Try alternate format for NVMe
        capacity_match = re.search(
            r'Namespace 1 Size/Capacity:\s+([0-9,]+)\s+', content)
        if capacity_match:
            data.capacity_bytes = int(
                capacity_match.group(1).replace(',', ''))


def _parse_nvme_fields(content: str, data: SmartData) -> None:
    """Parse NVMe-specific SMART fields."""
    written_match = re.search(
        r'Data Units Written:\s+([0-9,]+)', content)
    if written_match:
        data.data_units_written = int(
            written_match.group(1).replace(',', ''))

    read_match = re.search(
        r'Data Units Read:\s+([0-9,]+)', content)
    if read_match:
        data.data_units_read = int(
            read_match.group(1).replace(',', ''))

    power_on_match = re.search(
        r'Power On Hours:\s+([0-9,]+)', content)
    if power_on_match:
        data.power_on_hours = int(
            power_on_match.group(1).replace(',', ''))

    pct_used_match = re.search(
        r'Percentage Used:\s+([0-9]+)%', content)
    if pct_used_match:
        data.percentage_used = int(pct_used_match.group(1))

    spare_match = re.search(
        r'Available Spare:\s+([0-9]+)%', content)
    if spare_match:
        data.available_spare = int(spare_match.group(1))


def _parse_sata_fields(content: str, data: SmartData) -> None:
    """Parse SATA-specific SMART fields."""
    lba_pattern = (
        r'(?:241|Total_LBAs_Written)'
        r'\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)'
    )
    lba_written_match = re.search(lba_pattern, content)
    if lba_written_match:
        data.data_units_written = int(lba_written_match.group(1))

    poh_pattern = (
        r'(?:9|Power_On_Hours)'
        r'\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(\d+)'
    )
    power_on_match = re.search(poh_pattern, content)
    if power_on_match:
        data.power_on_hours = int(power_on_match.group(1))
