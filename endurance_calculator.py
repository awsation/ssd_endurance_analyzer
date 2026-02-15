#!/usr/bin/env python3
"""
Endurance Calculator Module

Calculates SSD endurance metrics including WAF, TBW, DWPD, and life expectancy.
"""

from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class EnduranceMetrics:  # pylint: disable=too-many-instance-attributes
    """Container for calculated endurance metrics."""

    # Raw data
    time_delta_days: float = 0.0
    host_writes_delta: float = 0.0  # In bytes
    flash_writes_delta: float = 0.0  # In bytes

    # Calculated metrics
    waf: float = 0.0  # Write Amplification Factor
    total_host_writes_tb: float = 0.0  # Total TBW from host
    total_flash_writes_tb: float = 0.0  # Total flash writes in TB
    dwpd: float = 0.0  # Drive Writes Per Day
    daily_write_rate_gb: float = 0.0  # GB/day
    pe_cycles_consumed: float = 0.0  # P/E cycles used
    estimated_remaining_days: float = 0.0
    estimated_remaining_years: float = 0.0
    wear_percentage: float = 0.0

    def to_dict(self) -> dict:
        """Convert metrics to dictionary for display."""
        return {
            'Time Period (days)': f"{self.time_delta_days:.2f}",
            'Host Writes (TB)': f"{self.total_host_writes_tb:.2f}",
            'Flash Writes (TB)': f"{self.total_flash_writes_tb:.2f}",
            'WAF': f"{self.waf:.2f}",
            'Daily Write Rate (GB/day)': f"{self.daily_write_rate_gb:.2f}",
            'DWPD': f"{self.dwpd:.4f}",
            'P/E Cycles Consumed': f"{self.pe_cycles_consumed:.2f}",
            'Wear %': f"{self.wear_percentage:.2f}%",
            'Est. Remaining (days)': (
                f"{self.estimated_remaining_days:.0f}"
            ),
            'Est. Remaining (years)': (
                f"{self.estimated_remaining_years:.2f}"
            ),
        }


@dataclass
class _DriveParams:  # pylint: disable=too-few-public-methods
    """Internal container for drive parameters."""
    host_lba_size_kb: float
    flash_lba_size_kb: float
    rated_pe_cycles: int
    capacity_gb: float
    capacity_bytes: float = field(init=False)

    def __post_init__(self):
        self.capacity_bytes = self.capacity_gb * (1024 ** 3)


class EnduranceCalculator:  # pylint: disable=too-few-public-methods
    """Calculator for SSD endurance metrics."""

    def __init__(self,
                 host_lba_size_kb: float,
                 flash_lba_size_kb: float,
                 rated_pe_cycles: int,
                 capacity_gb: float):
        """
        Initialize the calculator with drive parameters.

        Args:
            host_lba_size_kb: Size in KB per host data unit count
            flash_lba_size_kb: Size in KB per flash data unit count
            rated_pe_cycles: Manufacturer rated P/E cycles
            capacity_gb: Drive capacity in GB
        """
        self._params = _DriveParams(
            host_lba_size_kb=host_lba_size_kb,
            flash_lba_size_kb=flash_lba_size_kb,
            rated_pe_cycles=rated_pe_cycles,
            capacity_gb=capacity_gb,
        )

    def calculate(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        snapshot1_data_units_written: int,
        snapshot2_data_units_written: int,
        snapshot1_timestamp: datetime,
        snapshot2_timestamp: datetime,
        snapshot1_nand_writes: Optional[int] = None,
        snapshot2_nand_writes: Optional[int] = None,
    ) -> EnduranceMetrics:
        """
        Calculate endurance metrics from two snapshots.

        Args:
            snapshot1_data_units_written: Host data units (snap 1)
            snapshot2_data_units_written: Host data units (snap 2)
            snapshot1_timestamp: Timestamp of snapshot 1
            snapshot2_timestamp: Timestamp of snapshot 2
            snapshot1_nand_writes: NAND writes if available (snap 1)
            snapshot2_nand_writes: NAND writes if available (snap 2)

        Returns:
            EnduranceMetrics object with calculated values
        """
        metrics = EnduranceMetrics()
        p = self._params

        # Calculate time delta
        time_delta = snapshot2_timestamp - snapshot1_timestamp
        metrics.time_delta_days = time_delta.total_seconds() / 86400.0

        if metrics.time_delta_days <= 0:
            raise ValueError("Time delta must be positive")

        # Calculate host writes delta
        host_units_delta = (
            snapshot2_data_units_written - snapshot1_data_units_written
        )
        metrics.host_writes_delta = (
            host_units_delta * p.host_lba_size_kb * 1024
        )

        # Calculate total host writes
        total_host_bytes = (
            snapshot2_data_units_written * p.host_lba_size_kb * 1024
        )
        metrics.total_host_writes_tb = total_host_bytes / (1024 ** 4)

        # Calculate daily write rate
        daily_host_gb = (
            metrics.host_writes_delta / (1024 ** 3)
        )
        metrics.daily_write_rate_gb = (
            daily_host_gb / metrics.time_delta_days
        )

        # Calculate DWPD (Drive Writes Per Day)
        metrics.dwpd = metrics.daily_write_rate_gb / p.capacity_gb

        # Calculate WAF
        self._calculate_waf(
            metrics, snapshot1_nand_writes, snapshot2_nand_writes
        )

        # Calculate P/E cycles consumed
        total_flash_bytes = (
            snapshot2_data_units_written
            * p.host_lba_size_kb * 1024 * metrics.waf
        )
        metrics.pe_cycles_consumed = total_flash_bytes / p.capacity_bytes

        # Calculate wear percentage
        metrics.wear_percentage = (
            (metrics.pe_cycles_consumed / p.rated_pe_cycles) * 100
        )

        # Calculate remaining lifetime
        self._calculate_remaining_lifetime(metrics)

        return metrics

    def _calculate_waf(
        self,
        metrics: EnduranceMetrics,
        snap1_nand: Optional[int],
        snap2_nand: Optional[int],
    ) -> None:
        """Calculate Write Amplification Factor."""
        p = self._params
        if snap1_nand is not None and snap2_nand is not None:
            flash_delta = snap2_nand - snap1_nand
            metrics.flash_writes_delta = (
                flash_delta * p.flash_lba_size_kb * 1024
            )
            metrics.total_flash_writes_tb = (
                (snap2_nand * p.flash_lba_size_kb * 1024) / (1024 ** 4)
            )
            if metrics.host_writes_delta > 0:
                metrics.waf = (
                    metrics.flash_writes_delta / metrics.host_writes_delta
                )
            else:
                metrics.waf = 1.0  # No writes occurred
        else:
            # Assume typical WAF if not provided
            metrics.waf = 1.0  # Conservative estimate
            metrics.flash_writes_delta = (
                metrics.host_writes_delta * metrics.waf
            )
            metrics.total_flash_writes_tb = (
                metrics.total_host_writes_tb * metrics.waf
            )

    def _calculate_remaining_lifetime(
        self, metrics: EnduranceMetrics
    ) -> None:
        """Calculate estimated remaining lifetime."""
        p = self._params
        remaining_pe = p.rated_pe_cycles - metrics.pe_cycles_consumed

        if remaining_pe > 0 and metrics.daily_write_rate_gb > 0:
            remaining_bytes = remaining_pe * p.capacity_bytes
            daily_flash_bytes = (
                metrics.daily_write_rate_gb * (1024 ** 3) * metrics.waf
            )
            if daily_flash_bytes > 0:
                metrics.estimated_remaining_days = (
                    remaining_bytes / daily_flash_bytes
                )
                metrics.estimated_remaining_years = (
                    metrics.estimated_remaining_days / 365.25
                )
            else:
                metrics.estimated_remaining_days = float('inf')
                metrics.estimated_remaining_years = float('inf')
        else:
            metrics.estimated_remaining_days = 0
            metrics.estimated_remaining_years = 0
