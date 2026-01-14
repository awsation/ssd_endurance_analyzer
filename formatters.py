#!/usr/bin/env python3
"""
Output Formatting Module

Formats analysis results into ASCII tables and detailed reports.
"""

from typing import List, Dict, Any
from datetime import datetime
from smart_parser import SmartData
from endurance_calculator import EnduranceMetrics


def format_bytes(bytes_value: float, precision: int = 2) -> str:
    """Format bytes into human-readable format."""
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    value = float(bytes_value)
    unit_idx = 0
    
    while value >= 1024 and unit_idx < len(units) - 1:
        value /= 1024
        unit_idx += 1
    
    return f"{value:.{precision}f} {units[unit_idx]}"


def create_ascii_table(headers: List[str], rows: List[List[str]]) -> str:
    """
    Create a simple ASCII table.
    
    Args:
        headers: Column headers
        rows: List of rows (each row is a list of strings)
        
    Returns:
        Formatted ASCII table as string
    """
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Create separator
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    
    # Format header
    header_row = "|" + "|".join(f" {h:<{col_widths[i]}} " 
                                  for i, h in enumerate(headers)) + "|"
    
    # Format data rows
    data_rows = []
    for row in rows:
        data_row = "|" + "|".join(f" {str(cell):<{col_widths[i]}} " 
                                    for i, cell in enumerate(row)) + "|"
        data_rows.append(data_row)
    
    # Assemble table
    table = [separator, header_row, separator]
    table.extend(data_rows)
    table.append(separator)
    
    return "\n".join(table)


def format_analysis_report(
    snapshot1: SmartData,
    snapshot2: SmartData,
    metrics: EnduranceMetrics,
    host_lba_size_kb: float,
    flash_lba_size_kb: float,
    rated_pe_cycles: int,
    capacity_gb: float
) -> str:
    """
    Format complete analysis report.
    
    Args:
        snapshot1: First SMART snapshot
        snapshot2: Second SMART snapshot
        metrics: Calculated endurance metrics
        host_lba_size_kb: Host LBA size parameter
        flash_lba_size_kb: Flash LBA size parameter
        rated_pe_cycles: Rated P/E cycles
        capacity_gb: Drive capacity in GB
        
    Returns:
        Formatted report as string
    """
    lines = []
    
    # Header
    lines.append("=" * 80)
    lines.append("SSD ENDURANCE ANALYSIS REPORT".center(80))
    lines.append("=" * 80)
    lines.append("")
    
    # Drive Information
    lines.append("DRIVE INFORMATION")
    lines.append("-" * 80)
    drive_info = [
        ["Model", snapshot2.model or "Unknown"],
        ["Serial Number", snapshot2.serial or "Unknown"],
        ["Capacity", format_bytes(snapshot2.capacity_bytes) if snapshot2.capacity_bytes else f"{capacity_gb} GB"],
        ["Drive Type", "NVMe" if snapshot2.is_nvme else "SATA"],
    ]
    for label, value in drive_info:
        lines.append(f"{label:<25}: {value}")
    lines.append("")
    
    # Analysis Parameters
    lines.append("ANALYSIS PARAMETERS")
    lines.append("-" * 80)
    params = [
        ["Host LBA Size", f"{host_lba_size_kb} KB per count"],
        ["Flash LBA Size", f"{flash_lba_size_kb} KB per count"],
        ["Rated P/E Cycles", str(rated_pe_cycles)],
        ["Drive Capacity", f"{capacity_gb} GB"],
    ]
    for label, value in params:
        lines.append(f"{label:<25}: {value}")
    lines.append("")
    
    # Snapshot Information Table
    lines.append("SNAPSHOT COMPARISON")
    lines.append("-" * 80)
    
    snapshot_headers = ["Metric", "Snapshot 1", "Snapshot 2", "Delta"]
    snapshot_rows = [
        [
            "Timestamp",
            snapshot1.timestamp.strftime("%Y-%m-%d %H:%M:%S") if snapshot1.timestamp else "Unknown",
            snapshot2.timestamp.strftime("%Y-%m-%d %H:%M:%S") if snapshot2.timestamp else "Unknown",
            f"{metrics.time_delta_days:.2f} days"
        ],
        [
            "Data Units Written",
            f"{snapshot1.data_units_written:,}",
            f"{snapshot2.data_units_written:,}",
            f"{snapshot2.data_units_written - snapshot1.data_units_written:,}"
        ],
        [
            "Power On Hours",
            f"{snapshot1.power_on_hours:,}" if snapshot1.power_on_hours else "N/A",
            f"{snapshot2.power_on_hours:,}" if snapshot2.power_on_hours else "N/A",
            f"{(snapshot2.power_on_hours or 0) - (snapshot1.power_on_hours or 0):,}" if snapshot1.power_on_hours and snapshot2.power_on_hours else "N/A"
        ],
    ]
    
    if snapshot2.percentage_used is not None:
        snapshot_rows.append([
            "Percentage Used",
            f"{snapshot1.percentage_used}%" if snapshot1.percentage_used is not None else "N/A",
            f"{snapshot2.percentage_used}%",
            f"{(snapshot2.percentage_used or 0) - (snapshot1.percentage_used or 0)}%" if snapshot1.percentage_used is not None else "N/A"
        ])
    
    lines.append(create_ascii_table(snapshot_headers, snapshot_rows))
    lines.append("")
    
    # Endurance Metrics
    lines.append("CALCULATED ENDURANCE METRICS")
    lines.append("-" * 80)
    
    metrics_headers = ["Metric", "Value", "Description"]
    metrics_rows = [
        ["WAF", f"{metrics.waf:.2f}", "Write Amplification Factor"],
        ["TBW (Host)", f"{metrics.total_host_writes_tb:.2f} TB", "Total Bytes Written (Host)"],
        ["TBW (Flash)", f"{metrics.total_flash_writes_tb:.2f} TB", "Total Bytes Written (Flash)"],
        ["DWPD", f"{metrics.dwpd:.4f}", "Drive Writes Per Day"],
        ["Daily Write Rate", f"{metrics.daily_write_rate_gb:.2f} GB/day", "Average daily host writes"],
    ]
    lines.append(create_ascii_table(metrics_headers, metrics_rows))
    lines.append("")
    
    # Wear and Lifetime Analysis
    lines.append("WEAR AND LIFETIME ANALYSIS")
    lines.append("-" * 80)
    
    lifetime_headers = ["Metric", "Value", "Status"]
    
    # Determine status based on wear percentage
    if metrics.wear_percentage < 50:
        wear_status = "Good"
    elif metrics.wear_percentage < 80:
        wear_status = "Fair"
    elif metrics.wear_percentage < 95:
        wear_status = "Warning"
    else:
        wear_status = "Critical"
    
    # Determine remaining life status
    if metrics.estimated_remaining_years > 3:
        life_status = "Excellent"
    elif metrics.estimated_remaining_years > 1:
        life_status = "Good"
    elif metrics.estimated_remaining_years > 0.5:
        life_status = "Fair"
    else:
        life_status = "Replace Soon"
    
    lifetime_rows = [
        ["P/E Cycles Consumed", f"{metrics.pe_cycles_consumed:.2f}", f"of {rated_pe_cycles}"],
        ["Wear Percentage", f"{metrics.wear_percentage:.2f}%", wear_status],
        ["Estimated Remaining", f"{metrics.estimated_remaining_days:.0f} days", f"~{metrics.estimated_remaining_years:.2f} years"],
        ["Overall Health", "", life_status],
    ]
    lines.append(create_ascii_table(lifetime_headers, lifetime_rows))
    lines.append("")
    
    # Calculation Details
    lines.append("CALCULATION METHODOLOGY")
    lines.append("-" * 80)
    lines.append(f"• WAF = Flash Writes / Host Writes")
    lines.append(f"  = {metrics.flash_writes_delta / (1024**4):.4f} TB / {metrics.host_writes_delta / (1024**4):.4f} TB")
    lines.append(f"  = {metrics.waf:.2f}")
    lines.append("")
    lines.append(f"• DWPD = Daily Write Rate / Drive Capacity")
    lines.append(f"  = {metrics.daily_write_rate_gb:.2f} GB/day / {capacity_gb} GB")
    lines.append(f"  = {metrics.dwpd:.4f}")
    lines.append("")
    lines.append(f"• P/E Cycles = Total Flash Writes / Drive Capacity")
    lines.append(f"  = {metrics.total_flash_writes_tb * 1024:.2f} GB / {capacity_gb} GB")
    lines.append(f"  = {metrics.pe_cycles_consumed:.2f}")
    lines.append("")
    lines.append(f"• Remaining Lifetime = (Rated P/E - Used P/E) × Capacity / Daily Flash Writes")
    lines.append(f"  = ({rated_pe_cycles} - {metrics.pe_cycles_consumed:.2f}) × {capacity_gb} GB / {metrics.daily_write_rate_gb * metrics.waf:.2f} GB/day")
    lines.append(f"  = {metrics.estimated_remaining_days:.0f} days")
    lines.append("")
    
    # Footer
    lines.append("=" * 80)
    lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    
    return "\n".join(lines)
