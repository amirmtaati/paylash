import unittest
from decimal import Decimal

from bot.handlers import _parse_addepense_payload


class TestAddEpenseParser(unittest.TestCase):
    def test_parses_multiword_group_and_amount(self):
        group, amount, description, error = _parse_addepense_payload("Trip to Rome 120.50 Hotel stay")
        self.assertIsNone(error)
        self.assertEqual(group, "Trip to Rome")
        self.assertEqual(amount, Decimal("120.50"))
        self.assertEqual(description, "Hotel stay")

    def test_defaults_description(self):
        group, amount, description, error = _parse_addepense_payload("Pizza Night 45")
        self.assertIsNone(error)
        self.assertEqual(group, "Pizza Night")
        self.assertEqual(amount, Decimal("45"))
        self.assertEqual(description, "Shared expense")

    def test_requires_group_name(self):
        group, amount, description, error = _parse_addepense_payload("30 dinner")
        self.assertEqual(error, "Missing group name before amount.")


if __name__ == '__main__':
    unittest.main()
