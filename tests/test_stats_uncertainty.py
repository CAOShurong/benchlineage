import math
import unittest

from benchlineage.stats import interpolate_crossing, linear_regression, summary
from benchlineage.uncertainty import Component, combine, component_from_limit, from_records


class StatisticsTests(unittest.TestCase):
    def test_summary(self):
        result = summary([1, 2, 3, 4])
        self.assertEqual(result["count"], 4)
        self.assertEqual(result["mean"], 2.5)
        self.assertAlmostEqual(result["standard_deviation"], 1.2909944487358056)

    def test_single_value_summary(self):
        result = summary([5])
        self.assertEqual(result["standard_deviation"], 0)
        self.assertEqual(result["standard_error"], 0)

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            summary([1, math.inf])

    def test_linear_regression(self):
        result = linear_regression([0, 1, 2, 3], [1, 3, 5, 7])
        self.assertAlmostEqual(result["slope"], 2)
        self.assertAlmostEqual(result["intercept"], 1)
        self.assertAlmostEqual(result["r_squared"], 1)

    def test_linear_regression_rejects_flat_x(self):
        with self.assertRaisesRegex(ValueError, "not all be equal"):
            linear_regression([1, 1], [2, 3])

    def test_crossing(self):
        self.assertAlmostEqual(interpolate_crossing([0, 10], [4, -6], 0), 4)

    def test_missing_crossing(self):
        self.assertIsNone(interpolate_crossing([0, 1], [2, 3], 0))


class UncertaintyTests(unittest.TestCase):
    def test_rectangular_limit(self):
        component = component_from_limit("resolution", 3, distribution="rectangular")
        self.assertAlmostEqual(component.standard_uncertainty, math.sqrt(3))

    def test_triangular_limit(self):
        component = component_from_limit("resolution", math.sqrt(6), distribution="triangular")
        self.assertAlmostEqual(component.standard_uncertainty, 1)

    def test_invalid_distribution(self):
        with self.assertRaisesRegex(ValueError, "unsupported distribution"):
            component_from_limit("x", 1, distribution="mystery")

    def test_rss_combination(self):
        result = combine([Component("a", 3), Component("b", 4)], coverage_factor=2)
        self.assertEqual(result["combined_standard_uncertainty"], 5)
        self.assertEqual(result["expanded_uncertainty"], 10)
        self.assertAlmostEqual(sum(row["variance_share"] for row in result["components"]), 1)

    def test_sensitivity(self):
        result = combine([Component("a", 2, sensitivity=3)])
        self.assertEqual(result["combined_standard_uncertainty"], 6)

    def test_records_accept_mixed_component_forms(self):
        result = from_records(
            [
                {"name": "direct", "standard_uncertainty": 1},
                {"name": "limit", "limit": 2, "distribution": "normal"},
            ]
        )
        self.assertAlmostEqual(result["combined_standard_uncertainty"], math.sqrt(2))

    def test_empty_budget_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            combine([])


if __name__ == "__main__":
    unittest.main()
