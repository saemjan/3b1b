import unittest

from fluid_dynamics_engine import (
    bernoulli_pressure,
    build_fluid_visual,
    continuity_velocity,
    hydrostatic_pressure,
    reynolds_number,
)
from render_universal import UniversalPhysicsScene


class FluidDynamicsEngineTests(unittest.TestCase):
    def test_hydrostatic_continuity_bernoulli_and_reynolds(self):
        self.assertAlmostEqual(hydrostatic_pressure(1000, 2), 19613.3)
        self.assertAlmostEqual(continuity_velocity(0.04, 2, 0.01), 8)
        self.assertAlmostEqual(bernoulli_pressure(200000, 1000, 2, 8), 170000)
        self.assertAlmostEqual(reynolds_number(1000, 2, 0.05, 0.001), 100000)

    def test_invalid_fluid_inputs_are_rejected(self):
        for call in (
            lambda: hydrostatic_pressure(-1, 2),
            lambda: continuity_velocity(0, 2, 1),
            lambda: bernoulli_pressure(100000, 0, 1, 2),
            lambda: bernoulli_pressure(-1, 1000, 1, 2),
            lambda: reynolds_number(1000, 1, 0.1, 0),
        ):
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()

    def test_venturi_visual_rejects_reverse_flow(self):
        with self.assertRaisesRegex(ValueError, "inlet_velocity must be positive"):
            build_fluid_visual({
                "type": "fluid_dynamics",
                "operation": "venturi",
                "inlet_velocity": -1,
            })

    def test_fluid_visual_builds_and_routes(self):
        scene = UniversalPhysicsScene(scene_kwargs={})
        visual = scene._build_primitive({
            "type": "fluid_dynamics",
            "operation": "venturi",
            "inlet_height": 1.8,
            "throat_height": 0.9,
            "inlet_velocity": 2.0,
            "density": 1000.0,
        }, 0)
        self.assertIsNotNone(visual)
        tracer = visual[3][0]
        start = tracer.get_center().copy()
        visual.update(0.1)
        self.assertNotEqual(tuple(start), tuple(tracer.get_center()))


if __name__ == "__main__":
    unittest.main()