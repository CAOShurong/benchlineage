import math
import unittest

from benchlineage.units import compatible, convert, normalize_unit, registry, unit_definition


class UnitTests(unittest.TestCase):
    def test_voltage_conversion(self):
        self.assertAlmostEqual(convert(2500, "mV", "V"), 2.5)

    def test_frequency_conversion(self):
        self.assertAlmostEqual(convert(2.4, "GHz", "MHz"), 2400)

    def test_unicode_ohm_alias(self):
        self.assertEqual(normalize_unit("kΩ"), "kohm")

    def test_micro_alias(self):
        self.assertEqual(normalize_unit("µF"), "uF")

    def test_angle_conversion(self):
        self.assertAlmostEqual(convert(math.pi, "rad", "deg"), 180.0)

    def test_incompatible_units_raise(self):
        with self.assertRaisesRegex(ValueError, "incompatible"):
            convert(1, "V", "A")

    def test_unknown_unit_raises(self):
        with self.assertRaisesRegex(ValueError, "unknown unit"):
            normalize_unit("furlong")

    def test_compatibility(self):
        self.assertTrue(compatible("mA", "A"))
        self.assertFalse(compatible("mA", "V"))
        self.assertFalse(compatible("made-up", "V"))

    def test_definition(self):
        definition = unit_definition("ns")
        self.assertEqual(definition.dimension, "time")
        self.assertEqual(definition.scale, 1e-9)

    def test_registry_is_stable_and_nonempty(self):
        records = registry()
        self.assertGreater(len(records), 20)
        self.assertEqual(
            records, sorted(records, key=lambda item: (item["dimension"], item["scale"]))
        )


if __name__ == "__main__":
    unittest.main()
