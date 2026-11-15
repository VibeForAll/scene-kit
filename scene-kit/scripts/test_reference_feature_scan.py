#!/usr/bin/env python3

from __future__ import annotations

import unittest

import reference_feature_scan


class ReferenceFeatureScanTests(unittest.TestCase):
    def test_scan_returns_diagnostic_candidate_pools(self) -> None:
        report = {
            "object": "REF",
            "mesh_islands": [
                {
                    "island_id": 1,
                    "vertices": 100,
                    "min": [0.0, -0.1, 1.0],
                    "max": [1.0, 0.1, 2.2],
                    "dimensions": [1.0, 0.2, 1.2],
                    "center": [0.5, 0.0, 1.6],
                },
                {
                    "island_id": 2,
                    "vertices": 300,
                    "min": [-4.0, -2.0, 0.0],
                    "max": [4.0, 2.0, 5.0],
                    "dimensions": [8.0, 4.0, 5.0],
                    "center": [0.0, 0.0, 2.5],
                },
            ],
        }
        result = reference_feature_scan.scan(report)
        self.assertEqual(result["status"], "diagnostic_only")
        self.assertIn(1, result["candidate_island_ids"]["window_candidates"])
        self.assertIn(2, result["candidate_island_ids"]["wall_candidates"])
        self.assertIn("candidate_clusters", result)

    def test_cluster_islands_merges_adjacent_window_fragments(self) -> None:
        islands = [
            {
                "island_id": 1,
                "min": [0.0, 0.0, 0.5],
                "max": [0.4, 0.1, 1.0],
            },
            {
                "island_id": 2,
                "min": [0.42, 0.0, 0.5],
                "max": [0.8, 0.1, 1.0],
            },
            {
                "island_id": 3,
                "min": [2.0, 0.0, 0.5],
                "max": [2.8, 0.1, 1.0],
            },
        ]
        clusters = reference_feature_scan.cluster_islands(
            islands,
            [1, 2, 3],
            max_gap=0.05,
        )
        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0]["island_ids"], [1, 2])
        self.assertEqual(clusters[1]["island_ids"], [3])

    def test_cluster_islands_rejects_negative_gap(self) -> None:
        self.assertEqual(
            reference_feature_scan.cluster_islands([], [1], -0.1),
            [],
        )


if __name__ == "__main__":
    unittest.main()
