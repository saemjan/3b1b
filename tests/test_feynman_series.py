import csv
import importlib.util
import json
import os
import unittest

from render_universal import UniversalPhysicsScene


SERIES_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'tools', 'generate_feynman_series.py',
)
SPEC = importlib.util.spec_from_file_location('feynman_series', SERIES_PATH)
SERIES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERIES)


class FeynmanSeriesAnimationTests(unittest.TestCase):
    def test_complete_projectile_demo_csv_builds_and_updates(self):
        demo_path = os.path.join(
            os.path.dirname(__file__), '..', 'examples',
            'projectile_complete_object.csv',
        )
        with open(demo_path, newline='', encoding='utf-8') as demo_file:
            rows = list(csv.DictReader(demo_file))

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['orientation'], 'horizontal')
        self.assertEqual(row['target_duration_sec'], '60')
        visuals = json.loads(row['visual_data_json'])
        model = next(item for item in visuals
                     if item.get('id') == 'model')

        scene = UniversalPhysicsScene(scene_kwargs={})
        animated_object = scene._prim_projectile_motion(model)
        self.assertEqual(len(animated_object), 10)
        animated_object.update(0.1)
        scene.global_time.set_value(1.2)
        animated_object.update(0.1)

    def test_projectile_animation_rejects_invalid_physics(self):
        scene = UniversalPhysicsScene(scene_kwargs={})
        for invalid in (
            {'v0': 0},
            {'g': -1},
            {'angle': 90},
            {'period': float('nan')},
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    scene._prim_projectile_motion(invalid)

    def test_each_storyboard_builds_and_updates(self):
        rows = SERIES.build_batch()
        self.assertEqual(len(rows), 20)

        for row in rows:
            with self.subTest(video_id=row['video_id']):
                scene = UniversalPhysicsScene(scene_kwargs={})
                visuals = scene._build_visuals(
                    json.loads(row['visual_data_json']),
                )
                self.assertIn('model', scene.visuals_by_id)
                self.assertEqual(len(visuals), 3)
                visuals.update(0.1)
                visuals.update(0.1)

    def test_momentum_animation_rejects_non_colliding_inputs(self):
        scene = UniversalPhysicsScene(scene_kwargs={})
        with self.assertRaises(ValueError):
            scene._prim_momentum_exchange({
                'mass_1': 1.0,
                'mass_2': 1.0,
                'velocity_1': -1.0,
                'velocity_2': 1.0,
            })


if __name__ == '__main__':
    unittest.main()
