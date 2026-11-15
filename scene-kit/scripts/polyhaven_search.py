#!/usr/bin/env python3
"""Search free Poly Haven assets before generating local textures.

This helper uses Poly Haven's public API and does not require the paid Blender
asset-browser add-on. Results are candidates only; the user or agent must still
compare color, scale, roughness and style to the selected architecture.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


API_ROOT = "https://api.polyhaven.com"
ASSET_TYPES = ("textures", "models", "hdris")


def tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1
    }


def score_asset(query: str, slug: str, asset: dict[str, Any]) -> int:
    query_lower = query.lower().strip()
    query_tokens = tokens(query)
    name = str(asset.get("name", "")).lower()
    tags = [str(value).lower() for value in asset.get("tags", [])]
    categories = [str(value).lower() for value in asset.get("categories", [])]
    description = str(asset.get("description", "")).lower()
    segments = [
        slug.replace("_", " "),
        name,
        description,
        *tags,
        *categories,
    ]
    searchable = " ".join(
        segments
    )
    score = (
        10
        if query_lower and any(query_lower in segment for segment in segments)
        else 0
    )
    score += sum(4 for token in query_tokens if token in name)
    score += sum(3 for token in query_tokens if token in " ".join(tags))
    score += sum(2 for token in query_tokens if token in " ".join(categories))
    score += sum(1 for token in query_tokens if token in description)
    if score > 0:
        score += min(int(asset.get("download_count", 0)) // 5000, 3)
    return score


def rank_assets(
    query: str,
    asset_type: str,
    catalog: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    ranked = []
    for slug, asset in catalog.items():
        if not isinstance(asset, dict):
            continue
        score = score_asset(query, slug, asset)
        if score <= 0:
            continue
        ranked.append(
            {
                "slug": slug,
                "name": asset.get("name", slug.replace("_", " ").title()),
                "type": asset_type,
                "score": score,
                "categories": asset.get("categories", []),
                "tags": asset.get("tags", []),
                "max_resolution": asset.get("max_resolution"),
                "thumbnail_url": asset.get("thumbnail_url"),
                "description": asset.get("description", ""),
                "page_url": f"https://polyhaven.com/a/{slug}",
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["slug"]))
    return ranked[: max(1, limit)]


def fetch_catalog(asset_type: str, timeout: int) -> dict[str, Any]:
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    request = urllib.request.Request(
        f"{API_ROOT}/assets?t={asset_type}",
        headers={"User-Agent": "scene-kit-polyhaven-search"},
    )
    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=context,
    ) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Poly Haven API 返回格式异常")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Search Poly Haven's free CC0 assets by keywords."
    )
    parser.add_argument("query")
    parser.add_argument(
        "--type",
        choices=(*ASSET_TYPES, "all"),
        default="textures",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    selected_types = ASSET_TYPES if args.type == "all" else (args.type,)
    results: list[dict[str, Any]] = []
    raw_counts: dict[str, int] = {}
    for asset_type in selected_types:
        catalog = fetch_catalog(asset_type, args.timeout)
        raw_counts[asset_type] = len(catalog)
        results.extend(
            rank_assets(
                args.query,
                asset_type,
                catalog,
                args.limit,
            )
        )
    results.sort(key=lambda item: (-item["score"], item["slug"]))
    results = results[: max(1, args.limit)]
    report = {
        "schema_version": 1,
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "query": args.query,
        "asset_type": args.type,
        "catalog_counts": raw_counts,
        "license_note": "Poly Haven assets are free CC0 assets; verify the asset page before use.",
        "results": results,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
