#!/usr/bin/env python3
"""Unit test for the Blender-facing audit without requiring a Blender install."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("blender_audit.py")


class Vec(tuple):
    @property
    def x(self):
        return self[0]

    @property
    def y(self):
        return self[1]

    @property
    def z(self):
        return self[2]


class FakeCollection:
    def __init__(self, name):
        self.name = name


class FakeMaterial:
    name = "MAT_Project_Stone"
    use_nodes = False


class FakeMesh:
    def __init__(self, materials):
        self.name = "SK_Portal_Frame"
        self.vertices = []
        self.edges = []
        self.polygons = []
        self.loop_triangles = []
        self.materials = materials

    def calc_loop_triangles(self):
        return None


class FakeObject:
    def __init__(self, name, object_type, mesh=None):
        self.name = name
        self.type = object_type
        self.data = mesh
        self.parent = None
        self.hide_render = False
        self.location = Vec((0.0, 0.0, 0.0))
        self.rotation_euler = Vec((0.0, 0.0, 0.0))
        self.scale = Vec((1.0, 1.0, 1.0))
        self.dimensions = Vec((1.0, 1.0, 1.0))
        self.bound_box = []
        self.modifiers = []
        self.users_collection = [FakeCollection("SK_COL_AI")]
        self.matrix_world = None

    def hide_get(self):
        return False


class FakeBm:
    def __init__(self):
        self.verts = FakeSequence()
        self.edges = FakeSequence()
        self.faces = FakeSequence()

    def from_mesh(self, mesh):
        return None

    def ensure_lookup_table(self):
        return None

    def normal_update(self):
        return None

    def free(self):
        return None


class FakeSequence(list):
    def ensure_lookup_table(self):
        return None


class FakeImage:
    name = "T_Wall_BC"
    source = "FILE"
    filepath = "//textures/missing.png"
    packed_file = None


def install_fake_blender():
    mesh = FakeMesh([None, FakeMaterial()])
    obj = FakeObject("SK_Portal_Frame", "MESH", mesh)
    obj.scale = Vec((1.0, 0.0, 1.0))
    review_camera = FakeObject("CAM_Review_Front", "CAMERA")
    light = FakeObject("LGT_Key_Sun", "LIGHT")

    unit_settings = types.SimpleNamespace(system="METRIC", scale_length=1.0)
    render = types.SimpleNamespace(
        engine="BLENDER_EEVEE_NEXT",
        resolution_x=1440,
        resolution_y=900,
        resolution_percentage=100,
    )
    scene = types.SimpleNamespace(
        name="Scene",
        unit_settings=unit_settings,
        frame_start=1,
        frame_end=1,
        render=render,
    )
    bpy = types.ModuleType("bpy")
    bpy.context = types.SimpleNamespace(scene=scene)
    bpy.data = types.SimpleNamespace(
        filepath="C:/project/internal/model.blend",
        objects=[obj, review_camera, light],
        collections=[FakeCollection("SK_COL_AI")],
        materials=[FakeMaterial()],
        images=[FakeImage()],
    )
    bpy.path = types.SimpleNamespace(abspath=lambda value: "C:/project/textures/missing.png")
    bmesh = types.ModuleType("bmesh")
    bmesh.new = FakeBm
    sys.modules["bpy"] = bpy
    sys.modules["bmesh"] = bmesh


class AuditTests(unittest.TestCase):
    def setUp(self):
        install_fake_blender()
        spec = importlib.util.spec_from_file_location("blender_audit_under_test", SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(self.module)

    def tearDown(self):
        sys.modules.pop("bpy", None)
        sys.modules.pop("bmesh", None)

    def test_report_contains_inventory_and_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "audit.json"
            report, written = self.module.audit_scene(output, strict=True)
            self.assertEqual(written, output.resolve())
            self.assertTrue(output.is_file())
            stored = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stored["inventory"]["mesh_objects"], 1)
            self.assertEqual(stored["inventory"]["review_cameras"], ["CAM_Review_Front"])
            self.assertEqual(stored["totals"]["triangles"], 0)
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("zero_scale", codes)
            self.assertIn("missing_material_slots", codes)
            self.assertIn("missing_external_images", codes)

    def test_blender_argument_separator_is_stripped(self):
        original = sys.argv
        try:
            sys.argv = [
                "blender",
                "--background",
                "model.blend",
                "--python",
                "blender_audit.py",
                "--",
                "--output",
                "audit.json",
            ]
            self.assertEqual(
                self.module._argument_argv(None),
                ["--output", "audit.json"],
            )
        finally:
            sys.argv = original

    def test_flat_object_texture_projection_is_flagged(self):
        socket_name = types.SimpleNamespace(name="Object")
        texcoord = types.SimpleNamespace(
            type="TEX_COORD",
            name="Texture Coordinate",
            inputs={},
        )
        mapping = types.SimpleNamespace(
            type="MAPPING",
            name="Mapping",
            inputs={
                "Vector": types.SimpleNamespace(
                    links=[
                        types.SimpleNamespace(
                            from_node=texcoord,
                            from_socket=socket_name,
                        )
                    ]
                ),
                "Scale": types.SimpleNamespace(
                    default_value=(0.5, 0.5, 0.5)
                ),
            },
        )
        image_node = types.SimpleNamespace(
            type="TEX_IMAGE",
            name="Image Texture",
            projection="FLAT",
            extension="REPEAT",
            image=types.SimpleNamespace(
                name="stone.jpg",
                size=(2048, 2048),
            ),
            inputs={
                "Vector": types.SimpleNamespace(
                    links=[
                        types.SimpleNamespace(
                            from_node=mapping,
                            from_socket=types.SimpleNamespace(name="Vector"),
                        )
                    ]
                )
            },
        )
        material = types.SimpleNamespace(
            name="MAT_Stone",
            use_nodes=True,
            node_tree=types.SimpleNamespace(
                nodes=[image_node],
            ),
        )
        audit = self.module._audit_material_textures(material)
        self.assertEqual(audit["image_textures"][0]["projection"], "FLAT")
        self.assertEqual(
            audit["image_textures"][0]["coordinate_output"],
            "Object",
        )
        self.assertEqual(
            audit["risk_findings"][0]["code"],
            "flat_3d_coordinate_projection",
        )

    def test_box_projection_is_not_flagged_as_flat_stretch(self):
        image_node = types.SimpleNamespace(
            type="TEX_IMAGE",
            name="Box Image",
            projection="BOX",
            extension="REPEAT",
            image=types.SimpleNamespace(
                name="stone.jpg",
                size=(2048, 2048),
            ),
            inputs={},
        )
        material = types.SimpleNamespace(
            name="MAT_Stone",
            use_nodes=True,
            node_tree=types.SimpleNamespace(nodes=[image_node]),
        )
        audit = self.module._audit_material_textures(material)
        self.assertEqual(audit["risk_findings"], [])


if __name__ == "__main__":
    unittest.main()
