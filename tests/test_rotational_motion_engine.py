import unittest

from render_universal import UniversalPhysicsScene
from rotational_motion_engine import (
    angular_acceleration,
    angular_momentum,
    angular_velocity,
    moment_of_inertia,
    rotational_kinetic_energy,
)


class RotationalMotionEngineTests(unittest.TestCase):
    def test_rigid_body_rotational_calculations(self):
        inertia = moment_of_inertia("solid_disk", mass=2, radius=0.5)
        self.assertAlmostEqual(inertia, 0.25)
        self.assertAlmostEqual(angular_acceleration(3, inertia), 12)
        self.assertAlmostEqual(rotational_kinetic_energy(inertia, 2), 0.5)
        self.assertAlmostEqual(angular_momentum(inertia, 2), 0.5)
        self.assertAlmostEqual(angular_velocity(1, 2, 3), 7)

    def test_invalid_rotation_inputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            angular_acceleration(1, 0)
        with self.assertRaisesRegex(ValueError, "shape"):
            moment_of_inertia("unknown", mass=1, radius=1)

    def test_rotation_visual_builds_and_routes(self):
        scene = UniversalPhysicsScene(scene_kwargs={})
        visual = scene._build_primitive({
            "type": "rotational_motion",
            "shape": "solid_disk",
            "mass": 2.0,
            "radius": 1.0,
            "angular_velocity": 1.5,
            "torque": 0.5,
        }, 0)
        self.assertIsNotNone(visual)
        visual.update(0.1)

    def test_rod_body_rotates_about_its_center_axis(self):
        scene = UniversalPhysicsScene(scene_kwargs={})
        visual = scene._build_primitive({
            "type": "rotational_motion",
            "shape": "rod_center",
            "mass": 2.0,
            "length": 2.0,
            "angular_velocity": 1.0,
            "torque": 0.0,
        }, 0)
        rod = visual[0]
        initial_end = rod.get_end().copy()
        scene.global_time.set_value(1.0)
        visual.update(0.1)
        self.assertGreater(abs(rod.get_end()[1] - initial_end[1]), 0.1)


if __name__ == "__main__":
    unittest.main()