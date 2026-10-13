import unittest
import csv
import json
import os

import numpy as np

from physics_simulation import accelerations, simulate_system
from render_universal import UniversalPhysicsScene


class PhysicsSimulationTests(unittest.TestCase):
    def test_spring_csv_builds_and_animates(self):
        demo_path = os.path.join(
            os.path.dirname(__file__), "..", "examples",
            "physics_simulation_spring_demo.csv",
        )
        with open(demo_path, newline="", encoding="utf-8") as demo_file:
            row = next(csv.DictReader(demo_file))
        scene = UniversalPhysicsScene(scene_kwargs={})
        visuals = scene._build_visuals(json.loads(row["visual_data_json"]))
        self.assertIn("model", scene.visuals_by_id)
        visuals.update(0.1)
        scene.global_time.set_value(2.0)
        visuals.update(0.1)

    def test_uniform_acceleration_matches_analytic_trajectory(self):
        bodies = [{
            "mass": 2.0,
            "position": [1.0, 3.0],
            "velocity": [4.0, -1.0],
        }]
        forces = [{
            "type": "uniform_acceleration",
            "acceleration": [0.0, -9.81],
        }]
        _, normalized_forces, states = simulate_system(
            bodies, forces, duration=2.0, steps=100,
        )
        final = states[-1, 0]
        np.testing.assert_allclose(final[:2], [9.0, -18.62], atol=1e-10)
        np.testing.assert_allclose(final[2:], [4.0, -20.62], atol=1e-10)
        np.testing.assert_allclose(
            accelerations(states[0].reshape(-1), np.array([2.0]),
                          normalized_forces),
            [[0.0, -9.81]],
        )

    def test_spring_and_drag_accelerations_have_physical_sign(self):
        bodies = [
            {"mass": 1.0, "position": [0, 0], "velocity": [0, 0]},
            {"mass": 2.0, "position": [2, 0], "velocity": [1, 0]},
        ]
        forces = [
            {
                "type": "spring",
                "body": 0,
                "other": 1,
                "stiffness": 4,
                "rest_length": 1,
            },
            {"type": "linear_drag", "coefficient": 1},
        ]
        masses, normalized_forces, states = simulate_system(
            bodies, forces, duration=0.5, steps=50,
        )
        acceleration = accelerations(
            states[0].reshape(-1), masses, normalized_forces,
        )
        self.assertGreater(acceleration[0, 0], 0)
        self.assertLess(acceleration[1, 0], 0)

    def test_central_gravity_accelerates_toward_source(self):
        bodies = [
            {"mass": 1000, "position": [0, 0], "velocity": [0, 0]},
            {"mass": 1, "position": [2, 0], "velocity": [0, 0]},
        ]
        masses, forces, states = simulate_system(
            bodies,
            [{"type": "central_gravity", "source": 0, "mu": 8.0}],
            duration=0.2,
            steps=20,
        )
        initial_acceleration = accelerations(
            states[0].reshape(-1), masses, forces,
        )
        self.assertLess(initial_acceleration[1, 0], 0)
        self.assertLess(states[-1, 1, 0], 2.0)

    def test_rejects_unknown_force_and_singular_gravity(self):
        body = [{"mass": 1, "position": [0, 0], "velocity": [0, 0]}]
        with self.assertRaisesRegex(ValueError, "Unsupported force"):
            simulate_system(body, [{"type": "magic"}], 1.0, steps=10)

        coincident = [
            {"mass": 1, "position": [0, 0], "velocity": [0, 0]},
            {"mass": 1, "position": [0, 0], "velocity": [0, 0]},
        ]
        with self.assertRaisesRegex(ValueError, "positions coincide"):
            simulate_system(
                coincident,
                [{"type": "central_gravity", "source": 0, "mu": 1}],
                1.0,
                steps=10,
            )


if __name__ == "__main__":
    unittest.main()
