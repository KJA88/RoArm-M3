"""Offline checks for the upstream IK comparison. No hardware."""

from __future__ import annotations

import unittest

from offline_waveshare_ik import all_comparisons, earlier_center_elbow_delta


class UpstreamIkComparisonTest(unittest.TestCase):
    def test_header_exposes_one_branch_and_reaches_the_target(self):
        for item in all_comparisons():
            exposed = [row for row in item["branches"] if row["exposed"]]
            hidden = [row for row in item["branches"] if not row["exposed"]]
            self.assertEqual(len(exposed), 1)
            self.assertFalse(exposed[0]["nan_ik"])
            self.assertGreater(exposed[0]["fk_to_target_mm"], 0.001)
            self.assertLess(exposed[0]["fk_to_target_mm"], 0.002)
            self.assertGreater(abs(hidden[0]["de"]), 2.0)
            self.assertEqual(item["nearer_ready"], "header_acos")

    def test_exposed_branch_elbow_residual_against_settled_readback(self):
        by_name = {item["name"]: item for item in all_comparisons()}
        expected = {
            "CENTER": -0.040070,
            "Z200": -0.005047,
            "Z300": -0.039402,
            "X300": -0.038276,
        }
        for name, elbow in expected.items():
            exposed = next(row for row in by_name[name]["branches"] if row["exposed"])
            self.assertAlmostEqual(exposed["de"], elbow, places=5)
            self.assertLess(abs(exposed["ds"]), 0.01)

    def test_cartesian_gap_matches_the_joint_gap_through_fk(self):
        by_name = {item["name"]: item for item in all_comparisons()}
        expected_norm = {"CENTER": 11.623, "Z200": 5.811, "Z300": 11.524, "X300": 15.109}
        for name, norm in expected_norm.items():
            exposed = next(row for row in by_name[name]["branches"] if row["exposed"])
            self.assertAlmostEqual(exposed["fk_ik_minus_fk_settled_mm"][3], norm, places=3)

    def test_documented_pre_poses_also_prefer_the_exposed_branch(self):
        by_name = {item["name"]: item for item in all_comparisons()}
        self.assertEqual(by_name["CENTER"]["nearer_pre_pose"], "header_acos")
        self.assertEqual(by_name["X300"]["nearer_pre_pose"], "header_acos")
        self.assertIsNone(by_name["Z200"]["pre_pose"])
        self.assertIsNone(by_name["Z300"]["pre_pose"])

    def test_earlier_center_readback_is_the_same_branch(self):
        self.assertAlmostEqual(earlier_center_elbow_delta(), -0.038536, places=5)


if __name__ == "__main__":
    unittest.main()
