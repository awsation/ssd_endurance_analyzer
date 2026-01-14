#!/usr/bin/env python3
"""
Endurance Calculator Module

Calculates SSD endurance metrics including WAF, TBW, DWPD, and life expectancy.
"""

from typing import Dict, Optional
from datetime import datetime


class EnduranceMetrics:
    """Container for calculated endurance metrics."""
    
    def __init__(self):
        # Raw data
        self.time_delta_days: float = 0.0
        self.host_writes_delta: float = 0.0  # In bytes
        self.flash_writes_delta: float = 0.0  # In bytes
        
        # Calculated metrics
        self.waf: float = 0.0  # Write Amplification Factor
        self.total_host_writes_tb: float = 0.0  # Total TBW from host
        self.total_flash_writes_tb: float = 0.0  # Total flash writes in TB
        self.dwpd: float = 0.0  # Drive Writes Per Day
        self.daily_write_rate_gb: float = 0.0  # GB/day
        self.pe_cycles_consumed: float = 0.0  # P/E cycles used
        self.estimated_remaining_days: float = 0.0
        self.estimated_remaining_years: float = 0.0
        self.wear_percentage: float = 0.0
        
    def to_dict(self) -> Dict:
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
            'Est. Remaining (days)': f"{self.estimated_remaining_days:.0f}",
            'Est. Remaining (years)': f"{self.estimated_remaining_years:.2f}",
        }


class EnduranceCalculator:
    """Calculator for SSD endurance metrics."""
    
    def __init__(self,
                 host_lba_size_kb: float,
                 flash_lba_size_kb: float,
                 rated_pe_cycles: int,
                 capacity_gb: float):
        """
        Initialize the calculator with drive parameters.
        
        Args:
            host_lba_size_kb: Size in KB per host data unit count (e.g., 0.5)
            flash_lba_size_kb: Size in KB per flash data unit count (e.g., 32)
            rated_pe_cycles: Manufacturer rated P/E cycles (e.g., 3000)
            capacity_gb: Drive capacity in GB
        """
        self.host_lba_size_kb = host_lba_size_kb
        self.flash_lba_size_kb = flash_lba_size_kb
        self.rated_pe_cycles = rated_pe_cycles
        self.capacity_gb = capacity_gb
        self.capacity_bytes = capacity_gb * (1024 ** 3)
        
    def calculate(self,
                  snapshot1_data_units_written: int,
                  snapshot2_data_units_written: int,
                  snapshot1_timestamp: datetime,
                  snapshot2_timestamp: datetime,
                  snapshot1_nand_writes: Optional[int] = None,
                  snapshot2_nand_writes: Optional[int] = None) -> EnduranceMetrics:
        """
        Calculate endurance metrics from two snapshots.
        
        Args:
            snapshot1_data_units_written: Host data units written (snapshot 1)
            snapshot2_data_units_written: Host data units written (snapshot 2)
            snapshot1_timestamp: Timestamp of snapshot 1
            snapshot2_timestamp: Timestamp of snapshot 2
            snapshot1_nand_writes: NAND/flash writes if available (snapshot 1)
            snapshot2_nand_writes: NAND/flash writes if available (snapshot 2)
            
        Returns:
            EnduranceMetrics object with calculated values
        """
        metrics = EnduranceMetrics()
        
        # Calculate time delta
        time_delta = snapshot2_timestamp - snapshot1_timestamp
        metrics.time_delta_days = time_delta.total_seconds() / 86400.0
        
        if metrics.time_delta_days <= 0:
            raise ValueError("Time delta must be positive")
        
        # Calculate host writes delta
        host_units_delta = snapshot2_data_units_written - snapshot1_data_units_written
        metrics.host_writes_delta = host_units_delta * self.host_lba_size_kb * 1024  # bytes
        
        # Calculate total host writes
        total_host_bytes = snapshot2_data_units_written * self.host_lba_size_kb * 1024
        metrics.total_host_writes_tb = total_host_bytes / (1024 ** 4)
        
        # Calculate daily write rate
        metrics.daily_write_rate_gb = (metrics.host_writes_delta / (1024 ** 3)) / metrics.time_delta_days
        
        # Calculate DWPD (Drive Writes Per Day)
        metrics.dwpd = metrics.daily_write_rate_gb / self.capacity_gb
        
        # Calculate WAF if flash write data is available
        if snapshot1_nand_writes is not None and snapshot2_nand_writes is not None:
            flash_units_delta = snapshot2_nand_writes - snapshot1_nand_writes
            metrics.flash_writes_delta = flash_units_delta * self.flash_lba_size_kb * 1024  # bytes
            metrics.total_flash_writes_tb = (snapshot2_nand_writes * self.flash_lba_size_kb * 1024) / (1024 ** 4)
            
            if metrics.host_writes_delta > 0:
                metrics.waf = metrics.flash_writes_delta / metrics.host_writes_delta
            else:
                metrics.waf = 1.0  # No writes occurred
        else:
            # Assume typical WAF if not provided
            metrics.waf = 1.0  # Conservative estimate
            metrics.flash_writes_delta = metrics.host_writes_delta * metrics.waf
            metrics.total_flash_writes_tb = metrics.total_host_writes_tb * metrics.waf
        
        # Calculate P/E cycles consumed
        # Total data written to NAND / Drive capacity = P/E cycles used
        total_flash_bytes = snapshot2_data_units_written * self.host_lba_size_kb * 1024 * metrics.waf
        metrics.pe_cycles_consumed = total_flash_bytes / self.capacity_bytes
        
        # Calculate wear percentage
        metrics.wear_percentage = (metrics.pe_cycles_consumed / self.rated_pe_cycles) * 100
        
        # Calculate remaining lifetime
        remaining_pe_cycles = self.rated_pe_cycles - metrics.pe_cycles_consumed
        
        if remaining_pe_cycles > 0 and metrics.daily_write_rate_gb > 0:
            # Remaining capacity = remaining P/E * drive capacity
            remaining_write_capacity_bytes = remaining_pe_cycles * self.capacity_bytes
            
            # Daily flash writes (accounting for WAF)
            daily_flash_writes_bytes = metrics.daily_write_rate_gb * (1024 ** 3) * metrics.waf
            
            if daily_flash_writes_bytes > 0:
                metrics.estimated_remaining_days = remaining_write_capacity_bytes / daily_flash_writes_bytes
                metrics.estimated_remaining_years = metrics.estimated_remaining_days / 365.25
            else:
                metrics.estimated_remaining_days = float('inf')
                metrics.estimated_remaining_years = float('inf')
        else:
            metrics.estimated_remaining_days = 0
            metrics.estimated_remaining_years = 0
        
        return metrics
