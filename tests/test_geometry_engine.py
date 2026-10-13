import csv
import json
import os
import unittest

import numpy as np
from manim import VGroup

from geometry_engine import add_rigid_motion, build_geometry
from render_universal import Universal3DPhysicsScene, UniversalPhysicsScene


class GeometryEngineTests(unittest.TestCase):
    def test_dimension_one_segment_and_two_dimensional_polygon(self):
        segment = build_geometry({
            "dimension": 1,
            "kind": "segment",
            "points": [[-2], [2]],
        }, allow_3d=False)
        polygon = build_geometry({
            "dimension": 2,
            "kind": "polygon",
            "points": [[0, 0], [1, 0], [0, 1]],
        }, allow_3d=False)
        self.assertGreater(segment.width, 3.9)
        self.assertGreater(polygon.height, 0.9)

    def test_three_dimensional_solid_builds_and_translates_in_place(self):
        cube = build_geometry({
            "dimension": 3,
            "kind": "cube",
            "position": [1, 2, 3],
            "side_length": 2,
        }, allow_3d=True)
        initial = cube.get_center().copy()
        add_rigid_motion(
            cube,
            {
                "motion": {
                    "velocity": [1, 0, -1],
                    "angular_velocity": 0.4,
                    "axis": [0, 1, 0],
                }
            },
            dimension=3,
        )
        cube.update(0.5)
        np.testing.assert_allclose(
            cube.get_center(), initial + np.array([0.5, 0, -0.5]),
            atol=1e-6,
        )

    def test_three_dimensional_scene_routes_geometry_and_text(self):
        scene = Universal3DPhysicsScene(scene_kwargs={})
        solid = scene._build_3d_primitive({
            "type": "geometry",
            "dimension": 3,
            "kind": "sphere",
            "position": [1, 2, 3],
        })
        label = scene._build_3d_primitive({
            "type": "text",
            "text": "sphere",
            "pos": [1, 2, 4],
        })
        self.assertIsNotNone(solid)
        self.assertIsNotNone(label)

    def test_geometry_csv_builds_every_dimensional_example(self):
        csv_path = os.path.join(
            os.path.dirname(__file__), "..", "examples",
            "geometry_dimensions_demo.csv",
        )
        with open(csv_path, newline="", encoding="utf-8") as csv_file:
            row = next(csv.DictReader(csv_file))
        visuals = json.loads(row["visual_data_json"])
        scene_2d = UniversalPhysicsScene(scene_kwargs={})
        two_d_visuals = [
            scene_2d._prim_geometry(item)
            for item in visuals
            if item.get("type") == "geometry" and item["dimension"] < 3
        ]
        self.assertEqual(len(two_d_visuals), 2)

        scene_3d = Universal3DPhysicsScene(scene_kwargs={})
        all_visuals = VGroup(*[
            scene_3d._build_3d_primitive(item)
            for item in visuals
        ])
        all_visuals.update(0.1)
        self.assertEqual(len(all_visuals), len(visuals))

    def test_invalid_dimension_and_incompatible_projection_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "dimension must be"):
            build_geometry({
                "dimension": 4, "kind": "point", "position": [0, 0, 0, 0],
            }, allow_3d=True)
        with self.assertRaisesRegex(ValueError, "3D geometry"):
            build_geometry({
                "dimension": 3,
                "kind": "sphere",
                "position": [0, 0, 0],
            }, allow_3d=False)


if __name__ == "__main__":
    unittest.main()
