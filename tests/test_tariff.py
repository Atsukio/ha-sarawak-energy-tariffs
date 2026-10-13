"""Tests for the pure tariff maths. Run with: python -m unittest discover tests"""

import importlib.util
import math
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Load tariff.py directly so Home Assistant isn't needed to run these tests.
_PATH = (
    Path(__file__).parents[1] / "custom_components" / "sarawak_energy_tariffs" / "tariff.py"
)
_spec = importlib.util.spec_from_file_location("tariff", _PATH)
tariff = importlib.util.module_from_spec(_spec)
sys.modules["tariff"] = tariff
_spec.loader.exec_module(tariff)

TIERS = tariff.parse_tiers(tariff.DEFAULT_TIERS)


class ParseTiersTest(unittest.TestCase):
    def test_default_tiers(self):
        self.assertEqual(len(TIERS), 9)
        self.assertEqual(TIERS[0], tariff.Tier(0, 150, 0.18))
        self.assertTrue(math.isinf(TIERS[-1].upper))

    def test_comma_separated(self):
        tiers = tariff.parse_tiers("100:0.2, inf:0.3")
        self.assertEqual([t.rate for t in tiers], [0.2, 0.3])

    def test_rejects_bad_input(self):
        for text in ("", "100:0.2", "200:0.2\n100:0.3\ninf:0.4", "abc", "100:-1\ninf:1",
                     "inf:0.2\n500:0.3", "nan:0.1\ninf:0.2"):
            with self.subTest(text=text), self.assertRaises(tariff.TariffError):
                tariff.parse_tiers(text)


class ChargeTest(unittest.TestCase):
    def test_find_tier_boundaries(self):
        self.assertEqual(tariff.find_tier(TIERS, 0).rate, 0.18)
        self.assertEqual(tariff.find_tier(TIERS, 150).rate, 0.18)
        self.assertEqual(tariff.find_tier(TIERS, 150.01).rate, 0.22)
        self.assertEqual(tariff.find_tier(TIERS, 5000).rate, 0.315)

    def test_flat_mode(self):
        self.assertAlmostEqual(tariff.energy_charge(TIERS, 250, tariff.MODE_FLAT), 62.5)
        self.assertAlmostEqual(tariff.energy_charge(TIERS, 1500, tariff.MODE_FLAT), 472.5)

    def test_block_mode(self):
        # 150 * 0.18 + 50 * 0.22 + 50 * 0.25
        self.assertAlmostEqual(tariff.energy_charge(TIERS, 250, tariff.MODE_BLOCK), 50.5)

    def test_minimum_charge(self):
        self.assertEqual(tariff.bill_amount(TIERS, 10, tariff.MODE_FLAT, 5.0), 5.0)
        self.assertAlmostEqual(tariff.bill_amount(TIERS, 100, tariff.MODE_FLAT, 5.0), 18.0)

    def test_negative_usage_is_zero(self):
        self.assertEqual(tariff.energy_charge(TIERS, -5, tariff.MODE_BLOCK), 0)


class PeriodStartTest(unittest.TestCase):
    def test_same_month(self):
        now = datetime(2026, 10, 14, 9, 30, tzinfo=timezone.utc)
        self.assertEqual(tariff.period_start(now, 1), datetime(2026, 10, 1, tzinfo=timezone.utc))

    def test_previous_month(self):
        now = datetime(2026, 10, 14, tzinfo=timezone.utc)
        self.assertEqual(tariff.period_start(now, 20), datetime(2026, 9, 20, tzinfo=timezone.utc))

    def test_previous_year(self):
        now = datetime(2026, 1, 3, tzinfo=timezone.utc)
        self.assertEqual(tariff.period_start(now, 15), datetime(2025, 12, 15, tzinfo=timezone.utc))

    def test_on_billing_day(self):
        now = datetime(2026, 10, 15, 0, 0, 1, tzinfo=timezone.utc)
        self.assertEqual(tariff.period_start(now, 15), datetime(2026, 10, 15, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
