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
