#!/usr/bin/env python3
"""Tests for Poly Haven asset ranking."""

from __future__ import annotations

import unittest

import polyhaven_search


class PolyHavenSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = {
            "dark_wood": {
                "name": "Dark Wood",
                "tags": ["wood", "dark", "oak", "grain"],
                "categories": ["wood", "indoor"],
                "description": "Dark oak wood with a satin finish.",
                "download_count": 60000,
                "max_resolution": [8192, 8192],
            },
            "bright_plaster": {
                "name": "Bright Plaster",
                "tags": ["plaster", "wall", "white"],
                "categories": ["plaster-concrete", "wall"],
                "description": "Clean white plaster wall.",
                "download_count": 5000,
            },
            "stone_floor": {
                "name": "Stone Floor",
                "tags": ["stone", "floor"],
                "categories": ["rock", "floor"],
                "description": "Weathered stone floor.",
                "download_count": 1000,
            },
        }

    def test_dark_wood_ranks_first(self) -> None:
        result = polyhaven_search.rank_assets(
            "dark oak wood",
            "textures",
            self.catalog,
            3,
        )
        self.assertEqual(result[0]["slug"], "dark_wood")
        self.assertEqual(result[0]["page_url"], "https://polyhaven.com/a/dark_wood")

    def test_unmatched_assets_are_filtered(self) -> None:
        result = polyhaven_search.rank_assets(
            "mossy slate",
            "textures",
            self.catalog,
            3,
        )
        self.assertEqual(result, [])

    def test_exact_phrase_gets_priority(self) -> None:
        catalog = {
            "wood_dark": {
                "name": "Wood Dark",
                "tags": ["wood", "dark"],
                "categories": ["wood"],
                "description": "",
            },
            "dark_wood": {
                "name": "Dark Wood",
                "tags": ["wood"],
                "categories": ["wood"],
                "description": "",
            },
        }
        result = polyhaven_search.rank_assets(
            "dark wood",
            "textures",
            catalog,
            2,
        )
        self.assertEqual(result[0]["slug"], "dark_wood")


if __name__ == "__main__":
    unittest.main(verbosity=2)
