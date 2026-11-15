#!/usr/bin/env python3
"""Check and optionally install Scene Kit's recommended Blender extensions.

Run inside Blender:

    blender --background --python scripts/ensure_modeling_extensions.py -- \
      --install --output <project>/internal/toolchain.json

The script uses the official extensions.blender.org metadata, selects the
current-platform package, verifies the published SHA-256, installs through
Blender's extension API, enables the add-on, and writes a machine-readable
report. It does not modify project stage state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import ssl
import sys
import tempfile
import tomllib
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


EXTENSION_API = "https://extensions.blender.org/api/v1/extensions/"
USER_REPO = "user_default"
RECOMMENDED_EXTENSIONS = (
    ("archimesh", "Archimesh"),
    ("measureit", "MeasureIt"),
    ("print3d_toolbox", "3D Print Toolbox"),
    ("looptools", "LoopTools"),
    ("edit_mesh_tools", "Edit Mesh Tools"),
    ("CAD_Sketcher", "CAD Sketcher"),
    ("surface_diagnostics", "Surface Diagnostics"),
    ("curiomesh", "CurioMesh"),
)
POLYHAVEN_MODULE_HINTS = (
    "polyhaven_assets",
    "polyhavenassets",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check or install Scene Kit's recommended Blender extensions."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install missing extensions from the official Blender catalog.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON report path.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Network timeout in seconds.",
    )
    return parser


def argument_argv(argv: list[str] | None) -> list[str]:
    if argv is not None:
        return argv
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return sys.argv[1:]


def current_platform_tag() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    if system == "windows":
        return f"windows-{arch}"
    if system == "darwin":
        return f"macos-{arch}"
    return f"linux-{arch}"


def version_key(value: Any) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", str(value)))


def choose_package(
    items: list[dict[str, Any]],
    package_id: str,
    platform_tag: str,
) -> dict[str, Any] | None:
    candidates = [item for item in items if item.get("id") == package_id]
    if not candidates:
        return None
    platform_matches = [
        item
        for item in candidates
        if not item.get("platforms") or platform_tag in item.get("platforms", [])
    ]
    pool = platform_matches or candidates
    return max(pool, key=lambda item: version_key(item.get("version", "0")))


def module_name(package_id: str) -> str:
    return f"bl_ext.{USER_REPO}.{package_id}"


def manifest_version(package_id: str) -> str | None:
    import bpy

    root = Path(
        bpy.utils.user_resource(
            "EXTENSIONS",
            path=USER_REPO,
            create=False,
        )
    )
    candidates = (
        root / package_id / "blender_manifest.toml",
        root / package_id.lower() / "blender_manifest.toml",
    )
    for manifest in candidates:
        if not manifest.is_file():
            continue
        with manifest.open("rb") as handle:
            data = tomllib.load(handle)
        version = data.get("version")
        if version:
            return str(version)
    return None


def polyhaven_addon_status(bpy_module: Any) -> dict[str, Any]:
    enabled_modules = sorted(
        key
        for key in bpy_module.context.preferences.addons.keys()
        if any(hint in key.lower() for hint in POLYHAVEN_MODULE_HINTS)
    )
    installed_dirs: list[str] = []
    roots = []
    try:
        roots.append(
            Path(
                bpy_module.utils.user_resource(
                    "SCRIPTS",
                    path="addons",
                    create=False,
                )
            )
        )
    except Exception:
        pass
    try:
        roots.append(
            Path(
                bpy_module.utils.user_resource(
                    "EXTENSIONS",
                    path=USER_REPO,
                    create=False,
                )
            )
        )
    except Exception:
        pass
    for root in roots:
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if child.is_dir() and any(
                hint in child.name.lower() for hint in POLYHAVEN_MODULE_HINTS
            ):
                installed_dirs.append(child.name)
    return {
        "optional": True,
        "auto_install": False,
        "install_policy": "licensed_external",
        "installed": bool(enabled_modules or installed_dirs),
        "enabled": bool(enabled_modules),
        "modules": enabled_modules,
        "directories": installed_dirs,
        "documentation": "references/polyhaven-assets.md",
    }


def fetch_catalog(timeout: int) -> list[dict[str, Any]]:
    import certifi

    context = ssl.create_default_context(cafile=certifi.where())
    request = urllib.request.Request(
        EXTENSION_API,
        headers={"User-Agent": "scene-kit-modeling-extension-check"},
    )
    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=context,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("官方扩展目录返回格式异常")
    return data


def download_archive(
    package: dict[str, Any],
    destination: Path,
    timeout: int,
) -> None:
    import certifi

    url = package.get("archive_url")
    expected = str(package.get("archive_hash", "")).removeprefix("sha256:").lower()
    if not isinstance(url, str) or not url:
        raise ValueError("扩展缺少 archive_url")
    if not expected:
        raise ValueError("扩展缺少 archive_hash")
    context = ssl.create_default_context(cafile=certifi.where())
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "scene-kit-modeling-extension-check"},
    )
    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=context,
    ) as response:
        destination.write_bytes(response.read())
    actual = hashlib.sha256(destination.read_bytes()).hexdigest()
    if actual != expected:
        destination.unlink(missing_ok=True)
        raise ValueError(f"SHA-256 不一致：期望 {expected}，实际 {actual}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argument_argv(argv))
    try:
        import addon_utils
        import bpy
    except ImportError:
        print("该脚本必须在 Blender 内运行。", file=sys.stderr)
        return 2

    if args.install:
        bpy.context.preferences.system.use_online_access = True
        bpy.context.preferences.system.network_timeout = max(
            int(getattr(bpy.context.preferences.system, "network_timeout", 10)),
            args.timeout,
        )

    tag = current_platform_tag()
    enabled_modules = set(bpy.context.preferences.addons.keys())
    records: list[dict[str, Any]] = []
    missing: list[str] = []

    for package_id, display_name in RECOMMENDED_EXTENSIONS:
        module = module_name(package_id)
        enabled = module in enabled_modules
        installed_version = manifest_version(package_id)
        installed = enabled or installed_version is not None
        record: dict[str, Any] = {
            "id": package_id,
            "name": display_name,
            "module": module,
            "installed": installed,
            "enabled": enabled,
            "version": installed_version,
            "action": "already_enabled" if enabled else "missing",
        }
        if installed and not enabled:
            try:
                addon_utils.enable(module, default_set=True)
                record["enabled"] = module in bpy.context.preferences.addons
                record["action"] = "enabled"
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
        if not record["enabled"]:
            missing.append(package_id)
        records.append(record)

    if missing and args.install:
        catalog = fetch_catalog(args.timeout)
        with tempfile.TemporaryDirectory(prefix="scene-kit-extensions-") as temp:
            temp_dir = Path(temp)
            for record in records:
                if record["enabled"]:
                    continue
                package = choose_package(catalog, record["id"], tag)
                if package is None:
                    record["error"] = f"官方目录中没有适用于 {tag} 的版本"
                    continue
                archive = temp_dir / f"{record['id']}-{package['version']}.zip"
                try:
                    download_archive(package, archive, args.timeout)
                    result = bpy.ops.extensions.package_install_files(
                        filepath=str(archive),
                        repo=USER_REPO,
                        enable_on_install=True,
                    )
                    if "FINISHED" not in result:
                        raise RuntimeError(f"Blender 安装返回 {sorted(result)}")
                    addon_utils.enable(module_name(record["id"]), default_set=True)
                    record.update(
                        {
                            "installed": True,
                            "enabled": module_name(record["id"])
                            in bpy.context.preferences.addons,
                            "version": package.get("version"),
                            "catalog_version": package.get("version"),
                            "action": "installed",
                        }
                    )
                except Exception as exc:
                    record["error"] = f"{type(exc).__name__}: {exc}"

    ready = all(record.get("enabled") is True for record in records)
    report = {
        "schema_version": 1,
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "blender_version": bpy.app.version_string,
        "platform": tag,
        "extensions": records,
        "polyhaven_addon": polyhaven_addon_status(bpy),
        "ready": ready,
    }
    if args.output:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
