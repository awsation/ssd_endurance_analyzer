#!/usr/bin/env python3
"""Tests for the endurance_calculator module."""

import math
from datetime import datetime

import pytest

from endurance_calculator import EnduranceMetrics, EnduranceCalculator


# ===========================================================================
# EnduranceMetrics tests
# ===========================================================================

class TestEnduranceMetrics:
    """Tests for the EnduranceMetrics dataclass."""

    def test_default_values(self):
        """All fields initialize to 0.0."""
        m = EnduranceMetrics()
        assert m.time_delta_days == 0.0
        assert m.waf == 0.0
        assert m.dwpd == 0.0
        assert m.wear_percentage == 0.0
        assert m.estimated_remaining_days == 0.0

    def test_to_dict_keys(self):
        """to_dict returns all expected keys."""
        m = EnduranceMetrics()
        d = m.to_dict()
        expected_keys = {
            'Time Period (days)', 'Host Writes (TB)',
            'Flash Writes (TB)', 'WAF',
            'Daily Write Rate (GB/day)', 'DWPD',
            'P/E Cycles Consumed', 'Wear %',
            'Est. Remaining (days)', 'Est. Remaining (years)',
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_formatting(self):
        """to_dict returns correctly formatted strings."""
        m = EnduranceMetrics(
            time_delta_days=29.5,
            waf=1.23,
            dwpd=0.1234,
            wear_percentage=5.67,
        )
        d = m.to_dict()
        assert d['Time Period (days)'] == "29.50"
        assert d['WAF'] == "1.23"
        assert d['DWPD'] == "0.1234"
        assert d['Wear %'] == "5.67%"


# ===========================================================================
# EnduranceCalculator tests
# ===========================================================================

def _make_calculator(
    host_lba_size_kb=0.5,
    flash_lba_size_kb=32.0,
    rated_pe_cycles=3000,
    capacity_gb=500.0,
):
    """Create a calculator with typical defaults."""
    return EnduranceCalculator(
        host_lba_size_kb=host_lba_size_kb,
        flash_lba_size_kb=flash_lba_size_kb,
        rated_pe_cycles=rated_pe_cycles,
        capacity_gb=capacity_gb,
    )


class TestEnduranceCalculatorBasic:
    """Basic calculation tests."""

    def test_time_delta(self):
        """Time delta calculated correctly."""
        calc = _make_calculator()
        ts1 = datetime(2026, 1, 1, 10, 0, 0)
        ts2 = datetime(2026, 1, 31, 10, 0, 0)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        assert m.time_delta_days == pytest.approx(30.0, abs=0.01)

    def test_host_writes_delta(self):
        """Host writes delta computed from unit counts and LBA size."""
        calc = _make_calculator(host_lba_size_kb=0.5)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        # delta = 2,500,000 units * 0.5 KB * 1024 bytes = 1,280,000,000
        expected_delta = 2_500_000 * 0.5 * 1024
        assert m.host_writes_delta == pytest.approx(expected_delta)

    def test_daily_write_rate(self):
        """Daily write rate computed correctly."""
        calc = _make_calculator(host_lba_size_kb=0.5)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        delta_bytes = 2_500_000 * 0.5 * 1024
        expected_gb_per_day = (delta_bytes / (1024**3)) / 30.0
        assert m.daily_write_rate_gb == pytest.approx(
            expected_gb_per_day, rel=0.01
        )

    def test_dwpd(self):
        """DWPD = daily_write_rate_gb / capacity_gb."""
        calc = _make_calculator(capacity_gb=500.0)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        assert m.dwpd == pytest.approx(
            m.daily_write_rate_gb / 500.0, rel=0.001
        )

    def test_total_host_writes_tb(self):
        """Total host writes in TB based on snapshot2 units."""
        calc = _make_calculator(host_lba_size_kb=0.5)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        expected_tb = (52_500_000 * 0.5 * 1024) / (1024**4)
        assert m.total_host_writes_tb == pytest.approx(
            expected_tb, rel=0.001
        )


class TestEnduranceCalculatorWAF:
    """WAF-specific calculation tests."""

    def test_waf_without_nand_default_1(self):
        """WAF defaults to 1.0 when no NAND data provided."""
        calc = _make_calculator()
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        assert m.waf == 1.0

    def test_waf_with_nand_writes(self):
        """WAF computed from actual flash/host delta."""
        calc = _make_calculator(host_lba_size_kb=0.5,
                                flash_lba_size_kb=32.0)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=1_000_000,
            snapshot2_data_units_written=2_000_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
            snapshot1_nand_writes=100_000,
            snapshot2_nand_writes=200_000,
        )
        # host delta = 1,000,000 * 0.5 KB * 1024 = 512,000,000 bytes
        # flash delta = 100,000 * 32 KB * 1024 = 3,276,800,000 bytes
        # WAF = 3,276,800,000 / 512,000,000 = 6.4
        assert m.waf == pytest.approx(6.4, rel=0.01)

    def test_waf_zero_host_writes(self):
        """WAF defaults to 1.0 when host writes delta is zero."""
        calc = _make_calculator()
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=1_000_000,
            snapshot2_data_units_written=1_000_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
            snapshot1_nand_writes=100,
            snapshot2_nand_writes=100,
        )
        assert m.waf == 1.0


class TestEnduranceCalculatorLifetime:
    """Lifetime and wear calculation tests."""

    def test_wear_percentage(self):
        """Wear percentage = (pe_consumed / rated) * 100."""
        calc = _make_calculator(rated_pe_cycles=3000)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        expected_wear = (m.pe_cycles_consumed / 3000) * 100
        assert m.wear_percentage == pytest.approx(expected_wear)

    def test_remaining_positive(self):
        """Remaining days/years positive for healthy drive."""
        calc = _make_calculator(rated_pe_cycles=3000, capacity_gb=500)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        assert m.estimated_remaining_days > 0
        assert m.estimated_remaining_years > 0

    def test_exhausted_drive(self):
        """Exhausted drive (pe > rated) returns 0 remaining."""
        # Use tiny rated cycles so they're exceeded
        calc = _make_calculator(
            rated_pe_cycles=1,
            capacity_gb=0.001,  # very small capacity
            host_lba_size_kb=1024.0,  # 1 MB per unit
        )
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=1_000,
            snapshot2_data_units_written=1_000_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        assert m.estimated_remaining_days == 0
        assert m.estimated_remaining_years == 0


class TestEnduranceCalculatorErrors:
    """Error condition tests."""

    def test_zero_time_delta(self):
        """Same timestamp raises ValueError."""
        calc = _make_calculator()
        ts = datetime(2026, 1, 1)
        with pytest.raises(ValueError, match="positive"):
            calc.calculate(
                snapshot1_data_units_written=100,
                snapshot2_data_units_written=200,
                snapshot1_timestamp=ts,
                snapshot2_timestamp=ts,
            )

    def test_negative_time_delta(self):
        """Reversed timestamps raise ValueError."""
        calc = _make_calculator()
        ts1 = datetime(2026, 2, 1)
        ts2 = datetime(2026, 1, 1)
        with pytest.raises(ValueError, match="positive"):
            calc.calculate(
                snapshot1_data_units_written=100,
                snapshot2_data_units_written=200,
                snapshot1_timestamp=ts1,
                snapshot2_timestamp=ts2,
            )

    def test_zero_daily_writes_no_crash(self):
        """Zero host write delta doesn't crash."""
        calc = _make_calculator()
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=100,
            snapshot2_data_units_written=100,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        assert m.daily_write_rate_gb == 0.0
        # With zero writes: remaining should be inf or 0
        assert (m.estimated_remaining_days == 0
                or math.isinf(m.estimated_remaining_days))


class TestEnduranceCalculatorParams:
    """Test different drive parameter configurations."""

    def test_large_capacity(self):
        """Large capacity drive produces valid metrics."""
        calc = _make_calculator(capacity_gb=8000.0)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        m = calc.calculate(
            snapshot1_data_units_written=50_000_000,
            snapshot2_data_units_written=52_500_000,
            snapshot1_timestamp=ts1,
            snapshot2_timestamp=ts2,
        )
        assert m.dwpd < 1.0  # DWPD should be small for 8TB drive
        assert m.estimated_remaining_days > 0

    def test_slc_high_pe_cycles(self):
        """SLC drive with high P/E cycles has more remaining life."""
        calc_tlc = _make_calculator(rated_pe_cycles=3000)
        calc_slc = _make_calculator(rated_pe_cycles=100_000)
        ts1 = datetime(2026, 1, 1)
        ts2 = datetime(2026, 1, 31)
        kwargs = {
            "snapshot1_data_units_written": 50_000_000,
            "snapshot2_data_units_written": 52_500_000,
            "snapshot1_timestamp": ts1,
            "snapshot2_timestamp": ts2,
        }
        m_tlc = calc_tlc.calculate(**kwargs)
        m_slc = calc_slc.calculate(**kwargs)
        assert m_slc.estimated_remaining_years > (
            m_tlc.estimated_remaining_years
        )
