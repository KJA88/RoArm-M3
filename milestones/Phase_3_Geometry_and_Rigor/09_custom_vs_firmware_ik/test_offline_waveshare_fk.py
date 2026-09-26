"""Offline checks for the upstream Waveshare FK comparison. No hardware."""

from __future__ import annotations

import unittest

from offline_waveshare_fk import (
    HISTORICAL_FITTED_PLANAR,
    base_height_trials,
    pitch_conventions,
    raw_rows,
    ready_low_wrist_shift_mm,
    sign_trials,
)
from waveshare_m3_fk import ARM_L2_LENGTH_MM_A, ARM_L3_LENGTH_MM_A, ARM_L4_LENGTH_MM_A


class UpstreamFkComparisonTest(unittest.TestCase):
    def test_lengths_are_the_published_values(self):
        self.assertEqual(ARM_L2_LENGTH_MM_A, 236.82)
        self.assertEqual(ARM_L3_LENGTH_MM_A, 144.49)
        self.assertEqual(ARM_L4_LENGTH_MM_A, 171.67)
        self.assertEqual(HISTORICAL_FITTED_PLANAR["L1"], 238.839)
        self.assertNotEqual(HISTORICAL_FITTED_PLANAR["L2"], 145.0)

    def test_full_precision_records_match_upstream_fk(self):
        by_name = {row["name"]: row for row in raw_rows()}
        for name in ("READY", "CENTER", "Z200", "Z300", "X300"):
            self.assertLess(by_name[name]["norm"], 1e-6)
            self.assertLess(abs(by_name[name]["pitch_error"]), 1e-8)

    def test_candle_residual_is_at_the_supplied_rounding(self):
        candle = next(row for row in raw_rows() if row["name"] == "CANDLE")
        self.assertLess(candle["norm"], 5e-5)
        self.assertLess(abs(candle["pitch_error"]), 1e-5)

    def test_explicit_sign_and_height_trials_are_worse(self):
        signs = sign_trials()
        self.assertLess(signs["as_published"], 1e-4)
        self.assertGreater(signs["flip_shoulder"], 300.0)
        self.assertGreater(signs["flip_elbow"], 600.0)
        self.assertGreater(signs["flip_wrist"], 150.0)
        heights = base_height_trials()
        self.assertGreater(heights["add_unused_solver_L1_126_06"], 120.0)
        self.assertGreater(heights["add_urdf_base_stack_123_559"], 120.0)

    def test_upstream_pitch_formula_matches_tit(self):
        pitches = pitch_conventions()
        self.assertLess(pitches["s_plus_e_plus_t_minus_pi_over_2"], 1e-5)
        self.assertGreater(pitches["s_plus_e_plus_t"], 1.0)
        self.assertGreater(pitches["negated_upstream_pitch"], 0.03)

    def test_ready_wrist_range_is_not_interchangeable(self):
        self.assertGreater(ready_low_wrist_shift_mm(), 1.0)


if __name__ == "__main__":
    unittest.main()
