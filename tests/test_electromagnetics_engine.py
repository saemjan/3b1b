import unittest

import numpy as np

from electromagnetics_engine import (
    COULOMB_CONSTANT,
    SPEED_OF_LIGHT,
    build_electromagnetics_visual,
    electric_field,
    magnetic_field_from_wire,
    plane_wave_fields,
)
from render_universal import UniversalPhysicsScene


class ElectromagneticsEngineTests(unittest.TestCase):
    def test_electric_field_obeys_point_charge_direction_and_inverse_square(self):
        charges = [{"position": [0, 0, 0], "charge": 2e-9}]
        field_one = electric_field([1, 0, 0], charges)
        field_two = electric_field([2, 0, 0], charges)
        self.assertGreater(field_one[0], 0)
        np.testing.assert_allclose(field_one[1:], 0, atol=1e-12)
        self.assertAlmostEqual(field_one[0] / field_two[0], 4)
        self.assertAlmostEqual(field_one[0], COULOMB_CONSTANT * 2e-9)

    def test_finite_wire_field_has_right_hand_rule_direction(self):
        field = magnetic_field_from_wire(
            [1, 0, 0], [0, 0, -10], [0, 0, 10], 3,
        )
        self.assertGreater(field[1], 0)
        self.assertAlmostEqual(field[0], 0, delta=1e-12)
        self.assertAlmostEqual(field[2], 0, delta=1e-12)

    def test_plane_wave_fields_are_transverse_and_right_handed(self):
        electric, magnetic = plane_wave_fields(
            [0, 0, 0], 0, electric_amplitude=4,
            propagation_direction=[1, 0, 0],
            polarization=[0, 1, 0],
        )
        np.testing.assert_allclose(electric, [0, 4, 0])
        np.testing.assert_allclose(magnetic, [0, 0, 4 / SPEED_OF_LIGHT])
        self.assertAlmostEqual(np.dot(electric, [1, 0, 0]), 0)
        self.assertAlmostEqual(np.dot(magnetic, [1, 0, 0]), 0)

    def test_builds_and_routes_field_and_wave_visuals(self):
        scene = UniversalPhysicsScene(scene_kwargs={})
        electric = scene._build_primitive({
            "type": "electric_field",
            "charges": [{"position": [0.13, 0.17, 0], "charge": 1e-9}],
            "columns": 5,
            "rows": 4,
            "x_range": [-2, 2],
            "y_range": [-1, 1],
        }, 0)
        magnetic = build_electromagnetics_visual({
            "wires": [{
                "start": [0, 0, -1],
                "end": [0, 0, 1],
                "current": 2,
            }],
            "columns": 5,
            "rows": 4,
            "segments": 16,
            "x_range": [-2, 2],
            "y_range": [-1, 1],
        }, kind="magnetic_field")
        wave = scene._build_primitive({
            "type": "electromagnetic_wave",
            "amplitude": 1,
            "frequency": 1,
            "length": 6,
        }, 0)
        self.assertEqual(len(electric[0]), 20)
        self.assertEqual(len(magnetic[0]), 20)
        self.assertTrue(wave.get_updaters())
        wave.update(0.1)

    def test_rejects_singular_and_nonphysical_wave_inputs(self):
        with self.assertRaisesRegex(ValueError, "singular"):
            electric_field([0, 0, 0], [
                {"position": [0, 0, 0], "charge": 1},
            ])
        with self.assertRaisesRegex(ValueError, "perpendicular"):
            plane_wave_fields(
                [0, 0, 0], 0, propagation_direction=[1, 0, 0],
                polarization=[1, 0, 0],
            )
        with self.assertRaisesRegex(ValueError, "omega"):
            plane_wave_fields(
                [0, 0, 0], 0, angular_frequency=1, wave_number=1,
            )
        with self.assertRaisesRegex(ValueError, "at most 256"):
            build_electromagnetics_visual({
                "charges": [{"position": [0, 0, 0], "charge": 1}],
                "columns": 20,
                "rows": 20,
            }, kind="electric_field")


if __name__ == "__main__":
    unittest.main()
