import unittest

import numpy as np

from linear_algebra_engine import (
    build_linear_algebra_visual,
    cross_product,
    determinant,
    dot_product,
    matrix_inverse,
    matrix_multiply,
    matrix_vector_product,
    solve_linear_system,
    vector_add,
)
from render_universal import UniversalPhysicsScene


class LinearAlgebraEngineTests(unittest.TestCase):
    def test_vector_add_dot_and_cross_products(self):
        np.testing.assert_allclose(vector_add([1, 2], [3, 4]), [4, 6])
        self.assertEqual(dot_product([1, 2], [3, 4]), 11)
        self.assertEqual(cross_product([1, 0], [0, 1]), 1)
        np.testing.assert_allclose(
            cross_product([1, 0, 0], [0, 1, 0]), [0, 0, 1],
        )

    def test_determinant_uses_pivoting_and_handles_singular_matrices(self):
        self.assertEqual(determinant([[0, 1], [2, 3]]), -2)
        self.assertAlmostEqual(determinant([
            [2, 1, 3],
            [0, -1, 4],
            [5, 2, 0],
        ]), 19)
        self.assertEqual(determinant([[1, 2], [2, 4]]), 0)
        self.assertEqual(determinant([[7]]), 7)

    def test_vectors_require_matching_finite_dimensions(self):
        with self.assertRaisesRegex(ValueError, "dimensions must match"):
            dot_product([1, 2], [1, 2, 3])
        with self.assertRaisesRegex(ValueError, "finite"):
            vector_add([1, float("nan")], [1, 2])
        with self.assertRaisesRegex(ValueError, "3D vector"):
            cross_product([1], [2])

    def test_determinant_rejects_invalid_matrices(self):
        for matrix in ([[1, 2, 3], [4, 5, 6]], [[1, float("inf")],
                                                  [0, 1]], []):
            with self.subTest(matrix=matrix):
                with self.assertRaisesRegex(ValueError, "matrix must be"):
                    determinant(matrix)

    def test_matrix_products_and_inverse(self):
        matrix = [[2, 1], [1, 1]]
        np.testing.assert_allclose(
            matrix_vector_product(matrix, [3, 4]), [10, 7],
        )
        np.testing.assert_allclose(
            matrix_multiply(matrix, [[1, 2], [3, 4]]),
            [[5, 8], [4, 6]],
        )
        np.testing.assert_allclose(
            matrix_multiply(matrix, matrix_inverse(matrix)),
            np.eye(2), atol=1e-12,
        )

    def test_inverse_rejects_singular_matrix(self):
        with self.assertRaisesRegex(ValueError, "singular"):
            matrix_inverse([[1, 2], [2, 4]])

    def test_linear_system_solver_uses_pivoting(self):
        np.testing.assert_allclose(
            solve_linear_system([[0, 1], [2, 3]], [3, 13]),
            [2, 3],
        )
        with self.assertRaisesRegex(ValueError, "singular"):
            solve_linear_system([[1, 2], [2, 4]], [3, 6])

    def test_visuals_build_and_route_through_renderer(self):
        scene = UniversalPhysicsScene(scene_kwargs={})
        for operation, fields in (
            ("vectors", {"a": [2, 1], "b": [-1, 2]}),
            ("dot", {"a": [2, 1], "b": [-1, 2]}),
            ("cross", {"a": [2, 1], "b": [-1, 2]}),
            ("determinant", {"matrix": [[2, -1], [1, 2]]}),
            ("matrix_vector", {
                "matrix": [[2, 1], [1, 1]], "vector": [3, 4],
            }),
            ("transform", {"matrix": [[1, 1], [0, 1]]}),
            ("solve", {"matrix": [[2, 1], [1, 1]], "rhs": [5, 3]}),
        ):
            item = {"type": "linear_algebra", "operation": operation, **fields}
            visual = scene._build_primitive(item, 0)
            self.assertIsNotNone(visual, operation)
            self.assertGreater(len(visual), 0)

    def test_determinant_visual_requires_two_by_two_matrix(self):
        with self.assertRaisesRegex(ValueError, "2x2"):
            build_linear_algebra_visual({
                "operation": "determinant",
                "matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            })

    def test_zero_vector_dot_visual_does_not_claim_a_defined_angle(self):
        visual = build_linear_algebra_visual({
            "operation": "dot",
            "a": [0, 0],
            "b": [1, 0],
        })
        self.assertIn("undefined", visual[-1].text)


if __name__ == "__main__":
    unittest.main()
