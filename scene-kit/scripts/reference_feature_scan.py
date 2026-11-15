#!/usr/bin/env python3
"""Scan and spatially cluster connected mesh islands.

This produces model-based candidate pools only. It does not assign final
semantic component IDs or approve a decomposition.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _expanded_intersects(
    first: dict[str, Any],
    second: dict[str, Any],
    gap: float,
) -> bool:
    return all(
        first["min"][axis] - gap <= second["max"][axis]
        and second["min"][axis] - gap <= first["max"][axis]
        for axis in range(3)
    )


def cluster_islands(
    islands: list[dict[str, Any]],
    island_ids: list[int],
    max_gap: float,
) -> list[dict[str, Any]]:
    """Group spatially adjacent candidates without assigning semantics."""
    if not island_ids or max_gap < 0:
        return []
    by_id = {item["island_id"]: item for item in islands}
    selected = [by_id[value] for value in island_ids if value in by_id]
    if not selected:
        return []

    parents = list(range(len(selected)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(first: int, second: int) -> None:
        first_root = find(first)
        second_root = find(second)
        if first_root != second_root:
            parents[second_root] = first_root

    for first in range(len(selected)):
        for second in range(first + 1, len(selected)):
            if _expanded_intersects(
                selected[first],
                selected[second],
                max_gap,
            ):
                union(first, second)

    groups: dict[int, list[dict[str, Any]]] = {}
    for index, item in enumerate(selected):
        groups.setdefault(find(index), []).append(item)

    clusters: list[dict[str, Any]] = []
    for members in groups.values():
        minimum = [
            min(item["min"][axis] for item in members)
            for axis in range(3)
        ]
        maximum = [
            max(item["max"][axis] for item in members)
            for axis in range(3)
        ]
        dimensions = [
            maximum[axis] - minimum[axis] for axis in range(3)
        ]
        clusters.append(
            {
                "island_ids": sorted(
                    item["island_id"] for item in members
                ),
                "island_count": len(members),
                "min": [round(value, 4) for value in minimum],
                "max": [round(value, 4) for value in maximum],
                "center": [
                    round((minimum[axis] + maximum[axis]) / 2, 4)
                    for axis in range(3)
                ],
                "dimensions": [
                    round(value, 4) for value in dimensions
                ],
                "role": "spatial_candidate_only",
            }
        )
    clusters.sort(
        key=lambda item: (
            item["center"][2],
            item["center"][0],
            item["center"][1],
        )
    )
    return clusters


def is_window_candidate(item: dict[str, Any]) -> bool:
    dx, dy, dz = item["dimensions"]
    minimum_z = item["min"][2]
    maximum_z = item["max"][2]
    return (
        item["vertices"] >= 15
        and 0.7 <= dz <= 2.8
        and min(dx, dy) <= 1.1
        and max(dx, dy) <= 2.5
        and minimum_z > 0.15
        and maximum_z < 4.8
    )


def is_door_candidate(item: dict[str, Any]) -> bool:
    dx, dy, dz = item["dimensions"]
    return (
        item["vertices"] >= 20
        and item["min"][2] < 0.45
        and 1.1 <= dz <= 3.0
        and min(dx, dy) <= 1.2
        and max(dx, dy) <= 2.4
    )


def is_chimney_candidate(item: dict[str, Any]) -> bool:
    dx, dy, dz = item["dimensions"]
    return (
        item["vertices"] >= 20
        and item["min"][2] > 3.7
        and dz > 0.6
        and max(dx, dy) < 3.0
    )


def is_roof_candidate(item: dict[str, Any]) -> bool:
    dx, dy, _ = item["dimensions"]
    return (
        item["vertices"] >= 80
        and item["max"][2] > 4.4
        and max(dx, dy) > 1.6
    )


def is_wall_candidate(item: dict[str, Any]) -> bool:
    return (
        item["vertices"] >= 200
        and item["min"][2] < 0.8
        and item["dimensions"][2] > 2.3
    )


def scan(
    report: dict[str, Any],
    max_gap: float = 0.12,
) -> dict[str, Any]:
    islands = report.get("mesh_islands") or []
    categories = {
        "window_candidates": [],
        "door_candidates": [],
        "chimney_candidates": [],
        "roof_candidates": [],
        "wall_candidates": [],
    }
    predicates = {
        "window_candidates": is_window_candidate,
        "door_candidates": is_door_candidate,
        "chimney_candidates": is_chimney_candidate,
        "roof_candidates": is_roof_candidate,
        "wall_candidates": is_wall_candidate,
    }
    for item in islands:
        for category, predicate in predicates.items():
            if predicate(item):
                categories[category].append(item["island_id"])
    clusters = {
        category: cluster_islands(islands, island_ids, max_gap)
        for category, island_ids in categories.items()
    }
    return {
        "status": "diagnostic_only",
        "source_object": report.get("object"),
        "island_count": len(islands),
        "cluster_max_gap_m": max_gap,
        "candidate_counts": {
            key: len(value) for key, value in categories.items()
        },
        "candidate_island_ids": categories,
        "candidate_cluster_counts": {
            key: len(value) for key, value in clusters.items()
        },
        "candidate_clusters": clusters,
        "note": (
            "连通岛和空间聚类只用于三维组件定位。碎片、融合面和语义"
            "归属仍需通过模型派生多视图和原始图校验，不能自动作为"
            "最终拆件。"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-gap", type=float, default=0.12)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = scan(report, max_gap=args.max_gap)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
