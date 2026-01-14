# SSD Endurance Analyzer

A Python CLI tool that analyzes SSD endurance and estimates lifetime using S.M.A.R.T data from `smartctl` output.

## Features

- 📊 **Comprehensive Metrics**: Calculates WAF, TBW, DWPD, and life expectancy
- 🔍 **Dual Snapshot Analysis**: Compares two smartctl snapshots to track wear over time
- 📈 **P/E Cycle Tracking**: Factors in program/erase cycle wear
- 📋 **ASCII Table Output**: Organized, easy-to-read results
- 🔧 **Flexible Parameters**: Configurable LBA sizes and P/E ratings
- 🖥️ **Multi-Format Support**: Works with both NVMe and SATA drives

## Installation

No external dependencies required - uses Python 3.6+ standard library only.

```bash
# Clone or download the repository
cd ssd-endurance-analyzer

# Make the script executable (optional)
chmod +x ssd_analyzer.py
```

## Usage

### Basic Usage

```bash
python3 ssd_analyzer.py \
  --snapshot1 smartctl_day1.txt \
  --snapshot2 smartctl_day30.txt \
  --host-lba-size 0.5 \
  --flash-lba-size 32 \
  --rated-pe-cycles 3000 \
  --capacity 512
```

### Capturing smartctl Output

To create snapshot files:

```bash
# First snapshot
sudo smartctl -a /dev/nvme0 > smartctl_$(date +%Y%m%d).txt

# Wait some time (days/weeks), then capture second snapshot
sudo smartctl -a /dev/nvme0 > smartctl_$(date +%Y%m%d).txt
```

### Parameters Explained

#### Required Parameters

- `--snapshot1`: First smartctl output file (earlier timestamp)
- `--snapshot2`: Second smartctl output file (later timestamp)
- `--host-lba-size`: **Host LBA size in KB per data unit count**
  - Example: `0.5` means each "Data Units Written" count = 0.5 KB
  - Find this in your SSD specifications or calculate from smartctl output
- `--flash-lba-size`: **Flash LBA size in KB per write unit count**
  - Example: `32` means each flash write unit = 32 KB
  - Typically larger than host LBA size due to write amplification
- `--rated-pe-cycles`: Manufacturer rated P/E cycles
  - TLC NAND: typically 3000
  - MLC NAND: typically 10000
  - SLC NAND: typically 100000

#### Optional Parameters

- `--capacity`: Drive capacity in GB (auto-detected from smartctl if not specified)
- `--output`: Save report to file instead of printing to stdout

### Example Output

```
================================================================================
                      SSD ENDURANCE ANALYSIS REPORT
================================================================================

DRIVE INFORMATION
--------------------------------------------------------------------------------
Model                    : Samsung SSD 970 EVO Plus 500GB
Serial Number            : S4EWNF0M123456X
Capacity                 : 500 GB
Drive Type               : NVMe

ANALYSIS PARAMETERS
--------------------------------------------------------------------------------
Host LBA Size            : 0.5 KB per count
Flash LBA Size           : 32 KB per count
Rated P/E Cycles         : 3000
Drive Capacity           : 512 GB

SNAPSHOT COMPARISON
--------------------------------------------------------------------------------
+--------------------+-----------------------+-----------------------+-------------+
| Metric             | Snapshot 1            | Snapshot 2            | Delta       |
+--------------------+-----------------------+-----------------------+-------------+
| Timestamp          | 2026-01-01 10:00:00   | 2026-01-30 10:00:00   | 29.00 days  |
| Data Units Written | 50,000,000            | 52,500,000            | 2,500,000   |
| Power On Hours     | 1,200                 | 1,896                 | 696         |
+--------------------+-----------------------+-----------------------+-------------+

CALCULATED ENDURANCE METRICS
--------------------------------------------------------------------------------
+-------------------+----------------------+------------------------------------+
| Metric            | Value                | Description                        |
+-------------------+----------------------+------------------------------------+
| WAF               | 1.50                 | Write Amplification Factor         |
| TBW (Host)        | 25.00 TB             | Total Bytes Written (Host)         |
| TBW (Flash)       | 37.50 TB             | Total Bytes Written (Flash)        |
| DWPD              | 0.0845               | Drive Writes Per Day               |
| Daily Write Rate  | 43.10 GB/day         | Average daily host writes          |
+-------------------+----------------------+------------------------------------+

WEAR AND LIFETIME ANALYSIS
--------------------------------------------------------------------------------
+---------------------+-----------------------+----------------+
| Metric              | Value                 | Status         |
+---------------------+-----------------------+----------------+
| P/E Cycles Consumed | 146.48                | of 3000        |
| Wear Percentage     | 4.88%                 | Good           |
| Estimated Remaining | 13191 days            | ~36.12 years   |
| Overall Health      |                       | Excellent      |
+---------------------+-----------------------+----------------+
```

## Metrics Explained

### WAF (Write Amplification Factor)
Ratio of actual NAND writes to host writes. Higher values indicate more internal drive operations (garbage collection, wear leveling).

### TBW (Total Bytes Written)
Cumulative data written to the drive. Tracked separately for host and flash.

### DWPD (Drive Writes Per Day)
How many times the entire drive capacity is written per day on average.

### P/E Cycles
Program/Erase cycles - the number of times flash cells have been written and erased.

### Life Expectancy
Estimated remaining lifetime based on current write rate and remaining P/E budget.

## Determining LBA Sizes

### For NVMe Drives

Check your SSD datasheet or smartctl output. Common values:
- Host LBA: 0.5 KB (512 bytes) or 1 KB (1024 bytes)
- Flash LBA: 16-64 KB depending on NAND architecture

### For SATA Drives

Most SATA drives use:
- Host LBA: 0.512 KB (512 bytes)
- Flash LBA: Varies by controller (check manufacturer specs)

## Troubleshooting

### "Could not parse data units written"
- Ensure smartctl output is complete (`smartctl -a /dev/devicename`)
- Check that the drive supports SMART monitoring
- Verify the output contains "Data Units Written" (NVMe) or LBA write statistics (SATA)

### "Snapshots are from different drives"
- Verify both snapshots are from the same physical drive
- Check serial numbers match

### "Snapshot 1 must be earlier than snapshot 2"
- Ensure files are specified in chronological order
- Check timestamps in smartctl output

## License

MIT License - feel free to use and modify as needed.

## Contributing

Contributions welcome! Please feel free to submit issues or pull requests.
