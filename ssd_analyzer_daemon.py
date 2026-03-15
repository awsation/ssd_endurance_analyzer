#!/usr/bin/env python3
"""
SSD Endurance Analyzer Daemon

A daemon script that executes smartctl, compares it against the last run,
and generates an endurance report, keeping only the last two reports.
"""

import argparse
import datetime
import os
import subprocess
import sys
import shutil
from pathlib import Path

from smart_parser import SmartParser, SmartData
from endurance_calculator import EnduranceCalculator
from formatters import format_analysis_report

def run_smartctl(device: str) -> str:
    """Run smartctl -a on the given device and return the output."""
    try:
        # Assuming we are running as root or have proper permissions
        result = subprocess.run(
            ['smartctl', '-a', device],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running smartctl: {e}", file=sys.stderr)
        if e.stdout:
            print(f"stdout: {e.stdout}", file=sys.stderr)
        if e.stderr:
            print(f"stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: smartctl not found. Please install smartmontools.", file=sys.stderr)
        sys.exit(1)

def rotate_reports(log_dir: Path, keep_count: int = 2):
    """Keep only the latest `keep_count` report files, delete the rest."""
    reports = list(log_dir.glob('report-*.txt'))
    # Sort by modification time, oldest first
    reports.sort(key=lambda p: p.stat().st_mtime)
    
    if len(reports) > keep_count:
        files_to_delete = reports[:-keep_count]
        for f in files_to_delete:
            try:
                f.unlink()
                print(f"Deleted old report: {f}")
            except OSError as e:
                print(f"Warning: Failed to delete {f}: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="SSD Endurance Analyzer Daemon")
    parser.add_argument('--device', required=True, help="Device to analyze (e.g., /dev/nvme0n1)")
    parser.add_argument('--host-lba-size', required=True, type=float, help='Host LBA size in KB')
    parser.add_argument('--flash-lba-size', required=True, type=float, help='Flash LBA size in KB')
    parser.add_argument('--rated-pe-cycles', required=True, type=int, help='Manufacturer rated P/E cycles')
    parser.add_argument('--capacity', type=float, help='Drive capacity in GB (optional)')
    
    parser.add_argument('--state-dir', type=Path, default=Path('/var/lib/ssd-analyzer'),
                        help='Directory to store state (default: /var/lib/ssd-analyzer)')
    parser.add_argument('--log-dir', type=Path, default=Path('/var/log/ssd-analyzer'),
                        help='Directory to store reports (default: /var/log/ssd-analyzer)')
    
    args = parser.parse_args()

    args.state_dir.mkdir(parents=True, exist_ok=True)
    args.log_dir.mkdir(parents=True, exist_ok=True)

    state_file = args.state_dir / 'last_smart_snapshot.txt'
    temp_snapshot_file = args.state_dir / 'current_snapshot.tmp'

    print(f"Running smartctl for device {args.device}...")
    current_snapshot_text = run_smartctl(args.device)

    # Save current output to temp file
    with open(temp_snapshot_file, 'w', encoding='utf-8') as f:
        f.write(current_snapshot_text)

    smart_parser = SmartParser()

    if not state_file.exists():
        print("No previous state found. Saving current SMART state as baseline.")
        shutil.move(temp_snapshot_file, state_file)
        sys.exit(0)

    print("Parsing SMART outputs...")
    
    try:
        snapshot1 = smart_parser.parse_file(str(state_file))
        snapshot2 = smart_parser.parse_file(str(temp_snapshot_file))
        smart_parser.validate_snapshots(snapshot1, snapshot2)
    except Exception as e:
        print(f"Error parsing/validating snapshots: {e}", file=sys.stderr)
        # If parsing current failed, we don't want to overwrite the old good state
        temp_snapshot_file.unlink(missing_ok=True)
        sys.exit(1)

    capacity_gb = args.capacity
    if not capacity_gb:
        if snapshot2.capacity_bytes:
            capacity_gb = snapshot2.capacity_bytes / (1024 ** 3)
        else:
            print("Error: Could not auto-detect capacity. Please specify --capacity", file=sys.stderr)
            temp_snapshot_file.unlink(missing_ok=True)
            sys.exit(1)

    print(f"Drive capacity: {capacity_gb:.2f} GB")

    calculator = EnduranceCalculator(
        host_lba_size_kb=args.host_lba_size,
        flash_lba_size_kb=args.flash_lba_size,
        rated_pe_cycles=args.rated_pe_cycles,
        capacity_gb=capacity_gb
    )

    print("Calculating endurance metrics...")
    metrics = calculator.calculate(
        snapshot1_data_units_written=snapshot1.data_units_written,
        snapshot2_data_units_written=snapshot2.data_units_written,
        snapshot1_timestamp=snapshot1.timestamp,
        snapshot2_timestamp=snapshot2.timestamp
    )

    print("Generating report...")
    report = format_analysis_report(
        snapshot1=snapshot1,
        snapshot2=snapshot2,
        metrics=metrics,
        host_lba_size_kb=args.host_lba_size,
        flash_lba_size_kb=args.flash_lba_size,
        rated_pe_cycles=args.rated_pe_cycles,
        capacity_gb=capacity_gb
    )

    # Use snapshot2 timestamp to name the report, fallback to current time
    timestamp_str = (snapshot2.timestamp or datetime.datetime.now()).strftime('%Y%m%d_%H%M%S')
    report_file = args.log_dir / f"report-{timestamp_str}.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to: {report_file}")

    print("Rotating reports...")
    rotate_reports(args.log_dir, keep_count=2)

    # Finally update state
    shutil.move(temp_snapshot_file, state_file)
    print("State updated. Daemon run complete.")

if __name__ == '__main__':
    main()
