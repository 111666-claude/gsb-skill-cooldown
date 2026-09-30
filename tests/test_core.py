import unittest

from skillcooldown.core import Cooldowns, Skill


def book():
    charges = Cooldowns()
    charges.register(Skill("a", 2, 1000))
    return charges


class RegisterTest(unittest.TestCase):
    def test_register_fills_charges(self):
        self.assertEqual(book().charges("a", 0), 2)

    def test_cast_costs_one_charge(self):
        charges = book()
        charges.cast("a", 0)
        self.assertEqual(charges.charges("a", 0), 1)

    def test_unknown_skill_raises(self):
        with self.assertRaises(KeyError):
            book().cast("missing", 0)


class RefreshTest(unittest.TestCase):
    def test_short_refresh_keeps_charges(self):
        charges = book()
        charges.cast("a", 0)
        charges.refresh(500)
        self.assertEqual(charges.charges("a", 500), 1)

    def test_scanned_starts_at_zero(self):
        self.assertEqual(Cooldowns().scanned_count(), 0)


if __name__ == "__main__":
    unittest.main()
