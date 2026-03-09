#!/usr/bin/env python3
"""
Output Formatting Module

Formats analysis results into ASCII tables and detailed reports.
"""

from typing import List
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


def create_ascii_table(headers: List[str],
                       rows: List[List[str]]) -> str:
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
    separator = (
        "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    )

    # Format header
    header_row = (
        "|"
        + "|".join(
            f" {h:<{col_widths[i]}} "
            for i, h in enumerate(headers)
        )
        + "|"
    )

    # Format data rows
    data_rows = []
    for row in rows:
        data_row = (
            "|"
            + "|".join(
                f" {str(cell):<{col_widths[i]}} "
                for i, cell in enumerate(row)
            )
            + "|"
        )
        data_rows.append(data_row)

    # Assemble table
    table = [separator, header_row, separator]
    table.extend(data_rows)
    table.append(separator)

    return "\n".join(table)


def format_analysis_report(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
    lines: List[str] = []

    _add_header(lines)
    _add_drive_info(lines, snapshot2, capacity_gb)
    _add_analysis_params(
        lines, host_lba_size_kb, flash_lba_size_kb,
        rated_pe_cycles, capacity_gb
    )
    _add_snapshot_comparison(lines, snapshot1, snapshot2, metrics)
    _add_endurance_metrics(lines, metrics)
    _add_wear_analysis(lines, metrics, rated_pe_cycles)
    _add_methodology(
        lines, metrics, capacity_gb, rated_pe_cycles
    )
    _add_footer(lines)

    return "\n".join(lines)


def _add_header(lines: List[str]) -> None:
    """Add report header."""
    lines.append("=" * 80)
    lines.append("SSD ENDURANCE ANALYSIS REPORT".center(80))
    lines.append("=" * 80)
    lines.append("")


def _add_drive_info(lines: List[str],
                    snapshot: SmartData,
                    capacity_gb: float) -> None:
    """Add drive information section."""
    lines.append("DRIVE INFORMATION")
    lines.append("-" * 80)
    cap_str = (
        format_bytes(snapshot.capacity_bytes)
        if snapshot.capacity_bytes
        else f"{capacity_gb} GB"
    )
    drive_info = [
        ["Model", snapshot.model or "Unknown"],
        ["Serial Number", snapshot.serial or "Unknown"],
        ["Capacity", cap_str],
        ["Drive Type", "NVMe" if snapshot.is_nvme else "SATA"],
    ]
    for label, value in drive_info:
        lines.append(f"{label:<25}: {value}")
    lines.append("")


def _add_analysis_params(lines: List[str],
                         host_lba_size_kb: float,
                         flash_lba_size_kb: float,
                         rated_pe_cycles: int,
                         capacity_gb: float) -> None:
    """Add analysis parameters section."""
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


def _add_snapshot_comparison(lines: List[str],
                             snap1: SmartData,
                             snap2: SmartData,
                             metrics: EnduranceMetrics) -> None:
    """Add snapshot comparison table."""
    lines.append("SNAPSHOT COMPARISON")
    lines.append("-" * 80)

    headers = ["Metric", "Snapshot 1", "Snapshot 2", "Delta"]
    rows = _build_snapshot_rows(snap1, snap2, metrics)

    lines.append(create_ascii_table(headers, rows))
    lines.append("")


def _build_snapshot_rows(snap1: SmartData,
                         snap2: SmartData,
                         metrics: EnduranceMetrics
                         ) -> List[List[str]]:
    """Build rows for the snapshot comparison table."""
    ts1 = (snap1.timestamp.strftime("%Y-%m-%d %H:%M:%S")
           if snap1.timestamp else "Unknown")
    ts2 = (snap2.timestamp.strftime("%Y-%m-%d %H:%M:%S")
           if snap2.timestamp else "Unknown")

    delta_units = (
        snap2.data_units_written - snap1.data_units_written
    )

    rows = [
        ["Timestamp", ts1, ts2, f"{metrics.time_delta_days:.2f} days"],
        [
            "Data Units Written",
            f"{snap1.data_units_written:,}",
            f"{snap2.data_units_written:,}",
            f"{delta_units:,}",
        ],
    ]

    # Power on hours row
    poh1 = (f"{snap1.power_on_hours:,}"
            if snap1.power_on_hours else "N/A")
    poh2 = (f"{snap2.power_on_hours:,}"
            if snap2.power_on_hours else "N/A")
    if snap1.power_on_hours and snap2.power_on_hours:
        poh_delta = (
            f"{snap2.power_on_hours - snap1.power_on_hours:,}"
        )
    else:
        poh_delta = "N/A"
    rows.append(["Power On Hours", poh1, poh2, poh_delta])

    # Percentage used row (if available)
    if snap2.percentage_used is not None:
        pct1 = (f"{snap1.percentage_used}%"
                if snap1.percentage_used is not None else "N/A")
        pct2 = f"{snap2.percentage_used}%"
        if snap1.percentage_used is not None:
            pct_diff = snap2.percentage_used - snap1.percentage_used
            pct_delta = f"{pct_diff}%"
        else:
            pct_delta = "N/A"
        rows.append(["Percentage Used", pct1, pct2, pct_delta])

    return rows


def _add_endurance_metrics(lines: List[str],
                           metrics: EnduranceMetrics) -> None:
    """Add endurance metrics table."""
    lines.append("CALCULATED ENDURANCE METRICS")
    lines.append("-" * 80)

    headers = ["Metric", "Value", "Description"]
    rows = [
        ["WAF", f"{metrics.waf:.2f}",
         "Write Amplification Factor"],
        ["TBW (Host)", f"{metrics.total_host_writes_tb:.2f} TB",
         "Total Bytes Written (Host)"],
        ["TBW (Flash)", f"{metrics.total_flash_writes_tb:.2f} TB",
         "Total Bytes Written (Flash)"],
        ["DWPD", f"{metrics.dwpd:.4f}",
         "Drive Writes Per Day"],
        ["Daily Write Rate",
         f"{metrics.daily_write_rate_gb:.2f} GB/day",
         "Average daily host writes"],
    ]
    lines.append(create_ascii_table(headers, rows))
    lines.append("")


def _add_wear_analysis(lines: List[str],
                       metrics: EnduranceMetrics,
                       rated_pe_cycles: int) -> None:
    """Add wear and lifetime analysis table."""
    lines.append("WEAR AND LIFETIME ANALYSIS")
    lines.append("-" * 80)

    wear_status = _get_wear_status(metrics.wear_percentage)
    life_status = _get_life_status(metrics.estimated_remaining_years)

    remaining_str = f"{metrics.estimated_remaining_days:.0f} days"
    years_str = f"~{metrics.estimated_remaining_years:.2f} years"

    headers = ["Metric", "Value", "Status"]
    rows = [
        ["P/E Cycles Consumed",
         f"{metrics.pe_cycles_consumed:.2f}",
         f"of {rated_pe_cycles}"],
        ["Wear Percentage",
         f"{metrics.wear_percentage:.2f}%",
         wear_status],
        ["Estimated Remaining", remaining_str, years_str],
        ["Overall Health", "", life_status],
    ]
    lines.append(create_ascii_table(headers, rows))
    lines.append("")


def _get_wear_status(wear_pct: float) -> str:
    """Return status label based on wear percentage."""
    if wear_pct < 50:
        return "Good"
    if wear_pct < 80:
        return "Fair"
    if wear_pct < 95:
        return "Warning"
    return "Critical"


def _get_life_status(remaining_years: float) -> str:
    """Return status label based on remaining years."""
    if remaining_years > 3:
        return "Excellent"
    if remaining_years > 1:
        return "Good"
    if remaining_years > 0.5:
        return "Fair"
    return "Replace Soon"


def _add_methodology(lines: List[str],
                     metrics: EnduranceMetrics,
                     capacity_gb: float,
                     rated_pe_cycles: int) -> None:
    """Add calculation methodology section."""
    lines.append("CALCULATION METHODOLOGY")
    lines.append("-" * 80)

    flash_tb = metrics.flash_writes_delta / (1024**4)
    host_tb = metrics.host_writes_delta / (1024**4)
    flash_gb = metrics.total_flash_writes_tb * 1024
    daily_flash = metrics.daily_write_rate_gb * metrics.waf

    lines.append("• WAF = Flash Writes / Host Writes")
    lines.append(f"  = {flash_tb:.4f} TB / {host_tb:.4f} TB")
    lines.append(f"  = {metrics.waf:.2f}")
    lines.append("")
    lines.append("• DWPD = Daily Write Rate / Drive Capacity")
    lines.append(
        f"  = {metrics.daily_write_rate_gb:.2f} GB/day"
        f" / {capacity_gb} GB"
    )
    lines.append(f"  = {metrics.dwpd:.4f}")
    lines.append("")
    lines.append(
        "• P/E Cycles = Total Flash Writes / Drive Capacity"
    )
    lines.append(f"  = {flash_gb:.2f} GB / {capacity_gb} GB")
    lines.append(f"  = {metrics.pe_cycles_consumed:.2f}")
    lines.append("")
    lines.append(
        "• Remaining Lifetime = "
        "(Rated P/E - Used P/E) × Capacity / Daily Flash Writes"
    )
    lines.append(
        f"  = ({rated_pe_cycles} - {metrics.pe_cycles_consumed:.2f})"
        f" × {capacity_gb} GB / {daily_flash:.2f} GB/day"
    )
    lines.append(
        f"  = {metrics.estimated_remaining_days:.0f} days"
    )
    lines.append("")


def _add_footer(lines: List[str]) -> None:
    """Add report footer."""
    lines.append("=" * 80)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines.append(f"Report generated: {now_str}")
    lines.append("=" * 80)
