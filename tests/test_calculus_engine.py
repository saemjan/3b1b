import math
import unittest

from calculus_engine import build_calculus_visual, compile_expression
from render_universal import UniversalPhysicsScene


class CalculusEngineTests(unittest.TestCase):
    def test_safe_expression_evaluates_math_and_rejects_code(self):
        function = compile_expression("sin(x)^2 + x^2 + pi")
        self.assertAlmostEqual(function(0), math.pi)
        self.assertAlmostEqual(function(2), 2 ** 2 + math.pi + math.sin(2) ** 2)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            compile_expression("__import__('os').system('true')")(0)
        with self.assertRaisesRegex(ValueError, "could not evaluate"):
            compile_expression("sqrt(x)")(-1)

    def test_builds_graph_derivative_integral_and_riemann_visuals(self):
        base = {
            "expression": "x^2",
            "x_range": [-2, 2],
            "y_range": [0, 4],
            "x_length": 5,
            "y_length": 3,
        }
        graph = build_calculus_visual(base, kind="calculus_graph")
        derivative = build_calculus_visual(
            {**base, "x0": 1, "delta": 0.5},
            kind="derivative_tangent",
        )
        integral = build_calculus_visual(
            {**base, "a": 0, "b": 2, "samples": 12},
            kind="integral_area",
        )
        riemann = build_calculus_visual(
            {**base, "a": 0, "b": 2, "rectangles": 7, "sample": "midpoint"},
            kind="riemann_sum",
        )
        self.assertEqual(len(graph), 2)
        self.assertEqual(len(derivative), 6)
        self.assertEqual(len(integral[1]), 12)
        self.assertEqual(len(riemann[1]), 7)

    def test_scene_routes_calculus_visuals_and_validates_bounds(self):
        scene = UniversalPhysicsScene(scene_kwargs={})
        for kind in (
                "calculus_graph", "derivative_tangent",
                "integral_area", "riemann_sum"):
            visual = scene._build_primitive({
                "type": kind,
                "expression": "x^2",
                "x_range": [-2, 2],
                "y_range": [0, 4],
                "a": 0,
                "b": 2,
            }, 0)
            self.assertIsNotNone(visual, kind)

        with self.assertRaisesRegex(ValueError, "within x_range"):
            build_calculus_visual(
                {"expression": "x", "x_range": [-1, 1], "a": -2, "b": 0},
                kind="integral_area",
            )
        with self.assertRaisesRegex(ValueError, "between 1 and 256"):
            build_calculus_visual(
                {"expression": "x", "rectangles": 300},
                kind="riemann_sum",
            )
        with self.assertRaisesRegex(ValueError, "integer between 1 and 256"):
            build_calculus_visual(
                {"expression": "x", "rectangles": 3.5},
                kind="riemann_sum",
            )


if __name__ == "__main__":
    unittest.main()
