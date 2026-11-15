#!/usr/bin/env python3
"""Deterministic tests for the Blender extension preflight helper."""

from __future__ import annotations

import sys
import types
import unittest

import ensure_modeling_extensions as extensions


class ModelingExtensionTests(unittest.TestCase):
    def test_choose_package_prefers_current_platform(self) -> None:
        items = [
            {
                "id": "CAD_Sketcher",
                "version": "0.32.1",
                "platforms": ["linux-x64"],
                "archive_url": "linux",
            },
            {
                "id": "CAD_Sketcher",
                "version": "0.32.1",
                "platforms": ["windows-x64"],
                "archive_url": "windows",
            },
        ]
        selected = extensions.choose_package(
            items,
            "CAD_Sketcher",
            "windows-x64",
        )
        self.assertEqual(selected["archive_url"], "windows")

    def test_choose_package_uses_generic_archive(self) -> None:
        items = [
            {
                "id": "archimesh",
                "version": "1.2.5",
                "platforms": [],
                "archive_url": "generic",
            }
        ]
        selected = extensions.choose_package(
            items,
            "archimesh",
            "windows-x64",
        )
        self.assertEqual(selected["archive_url"], "generic")

    def test_version_key_orders_numeric_parts(self) -> None:
        self.assertGreater(
            extensions.version_key("1.10.2"),
            extensions.version_key("1.9.9"),
        )

    def test_argument_separator_is_stripped(self) -> None:
        original = sys.argv
        try:
            sys.argv = [
                "blender",
                "--background",
                "--python",
                "ensure_modeling_extensions.py",
                "--",
                "--install",
                "--output",
                "toolchain.json",
            ]
            self.assertEqual(
                extensions.argument_argv(None),
                ["--install", "--output", "toolchain.json"],
            )
        finally:
            sys.argv = original

    def test_polyhaven_addon_is_optional_and_not_auto_installed(self) -> None:
        fake_bpy = types.SimpleNamespace(
            context=types.SimpleNamespace(
                preferences=types.SimpleNamespace(
                    addons={"polyhaven_assets": object()}
                )
            ),
            utils=types.SimpleNamespace(
                user_resource=lambda *args, **kwargs: "Z:/missing/path"
            ),
        )
        status = extensions.polyhaven_addon_status(fake_bpy)
        self.assertTrue(status["optional"])
        self.assertFalse(status["auto_install"])
        self.assertTrue(status["enabled"])
        self.assertEqual(status["modules"], ["polyhaven_assets"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
