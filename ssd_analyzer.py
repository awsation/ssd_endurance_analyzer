#!/usr/bin/env python3
"""
SSD Endurance Analyzer

A CLI tool for analyzing SSD endurance and estimating lifetime based on
S.M.A.R.T data from smartctl output files.
"""

import argparse
import sys
from pathlib import Path

from smart_parser import SmartParser
from endurance_calculator import EnduranceCalculator
from formatters import format_analysis_report


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            'Analyze SSD endurance and estimate lifetime '
            'from smartctl data'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Example usage:
  %(prog)s \\
    --snapshot1 smartctl_day1.txt \\
    --snapshot2 smartctl_day30.txt \\
    --host-lba-size 0.5 \\
    --flash-lba-size 32 \\
    --rated-pe-cycles 3000 \\
    --capacity 512

Notes:
  - Host LBA size: KB per data unit count from SMART (e.g., 0.5 KB)
  - Flash LBA size: KB per flash write count from SMART (e.g., 32 KB)
  - Capacity: Drive capacity in GB
  - If capacity is not specified, it will be auto-detected from \
smartctl output
        """
    )

    # Required arguments
    parser.add_argument(
        '--snapshot1',
        required=True,
        type=Path,
        help='Path to first smartctl output file (earlier timestamp)'
    )

    parser.add_argument(
        '--snapshot2',
        required=True,
        type=Path,
        help='Path to second smartctl output file (later timestamp)'
    )

    parser.add_argument(
        '--host-lba-size',
        required=True,
        type=float,
        help='Host LBA size in KB per data unit count (e.g., 0.5)'
    )

    parser.add_argument(
        '--flash-lba-size',
        required=True,
        type=float,
        help='Flash LBA size in KB per write unit count (e.g., 32)'
    )

    parser.add_argument(
        '--rated-pe-cycles',
        required=True,
        type=int,
        help=(
            'Manufacturer rated P/E cycles '
            '(e.g., 3000 for TLC, 100000 for SLC)'
        )
    )

    # Optional arguments
    parser.add_argument(
        '--capacity',
        type=float,
        help='Drive capacity in GB (auto-detected if not specified)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output file path (prints to stdout if not specified)'
    )

    return parser.parse_args()


def _determine_capacity(args, snapshot2):
    """Determine drive capacity from args or auto-detect."""
    if args.capacity:
        return args.capacity
    if snapshot2.capacity_bytes:
        return snapshot2.capacity_bytes / (1024 ** 3)

    print(
        "Error: Could not auto-detect capacity. "
        "Please specify --capacity",
        file=sys.stderr
    )
    sys.exit(1)


def main():
    """Main entry point."""
    args = parse_arguments()

    try:
        # Parse smartctl outputs
        print("Parsing smartctl outputs...", file=sys.stderr)
        parser = SmartParser()

        snapshot1 = parser.parse_file(str(args.snapshot1))
        snapshot2 = parser.parse_file(str(args.snapshot2))

        # Validate snapshots
        parser.validate_snapshots(snapshot1, snapshot2)

        # Determine capacity
        capacity_gb = _determine_capacity(args, snapshot2)
        print(
            f"Drive capacity: {capacity_gb:.2f} GB",
            file=sys.stderr
        )

        # Create calculator
        calculator = EnduranceCalculator(
            host_lba_size_kb=args.host_lba_size,
            flash_lba_size_kb=args.flash_lba_size,
            rated_pe_cycles=args.rated_pe_cycles,
            capacity_gb=capacity_gb
        )

        # Calculate metrics
        print(
            "Calculating endurance metrics...", file=sys.stderr
        )
        metrics = calculator.calculate(
            snapshot1_data_units_written=snapshot1.data_units_written,
            snapshot2_data_units_written=snapshot2.data_units_written,
            snapshot1_timestamp=snapshot1.timestamp,
            snapshot2_timestamp=snapshot2.timestamp
        )

        # Generate report
        print("Generating report...", file=sys.stderr)
        report = format_analysis_report(
            snapshot1=snapshot1,
            snapshot2=snapshot2,
            metrics=metrics,
            host_lba_size_kb=args.host_lba_size,
            flash_lba_size_kb=args.flash_lba_size,
            rated_pe_cycles=args.rated_pe_cycles,
            capacity_gb=capacity_gb
        )

        # Output report
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(
                f"\nReport saved to: {args.output}",
                file=sys.stderr
            )
        else:
            print("\n" + report)

        print("\nAnalysis complete!", file=sys.stderr)

    except FileNotFoundError as exc:
        print(f"Error: File not found - {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
