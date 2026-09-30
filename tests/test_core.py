import random
import unittest
from fractions import Fraction

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


class CapTest(unittest.TestCase):
    def test_recharge_caps_at_max(self):
        charges = book()
        charges.cast("a", 0)
        charges.cast("a", 1500)
        self.assertEqual(charges.charges("a", 100000), 2)

    def test_recharge_one_step_then_cap(self):
        charges = book()
        charges.cast("a", 0)
        self.assertEqual(charges.charges("a", 999), 1)
        self.assertEqual(charges.charges("a", 1000), 2)
        self.assertEqual(charges.charges("a", 123456), 2)

    def test_charges_never_out_of_bounds_after_drain(self):
        charges = Cooldowns(gcd_ms=0)
        charges.register(Skill("a", 2, 1000))
        self.assertTrue(charges.cast("a", 0))
        self.assertTrue(charges.cast("a", 0))
        self.assertFalse(charges.cast("a", 0))
        self.assertEqual(charges.charges("a", 0), 0)
        self.assertEqual(charges.charges("a", 999), 0)
        self.assertEqual(charges.charges("a", 1000), 1)
        self.assertTrue(charges.cast("a", 1000))
        self.assertFalse(charges.cast("a", 1000))
        self.assertEqual(charges.charges("a", 5000), 2)


class GcdTest(unittest.TestCase):
    def test_second_cast_within_gcd_rejected(self):
        charges = Cooldowns()
        charges.register(Skill("a", 2, 1000))
        charges.register(Skill("b", 2, 1000))
        self.assertTrue(charges.cast("a", 1000))
        self.assertFalse(charges.cast("b", 1100))
        self.assertEqual(charges.charges("b", 1100), 2)

    def test_cast_exactly_at_gcd_boundary_allowed(self):
        charges = Cooldowns()
        charges.register(Skill("a", 2, 1000))
        self.assertTrue(charges.cast("a", 1000))
        self.assertTrue(charges.cast("a", 2500))

    def test_rejected_cast_does_not_refresh_gcd(self):
        charges = Cooldowns()
        charges.register(Skill("a", 1, 10000))
        charges.register(Skill("b", 1, 10000))
        self.assertTrue(charges.cast("a", 0))
        self.assertFalse(charges.cast("b", 100))
        self.assertTrue(charges.cast("b", 1500))

    def test_rejected_cast_costs_no_charge(self):
        charges = book()
        charges.cast("a", 0)
        self.assertFalse(charges.cast("a", 100))
        self.assertEqual(charges.charges("a", 100), 1)


class ClockBackTest(unittest.TestCase):
    def test_backtrack_does_not_remove_charges(self):
        charges = Cooldowns()
        charges.register(Skill("a", 5, 1000))
        charges.cast("a", 3000)
        self.assertEqual(charges.charges("a", 3000), 4)
        charges.refresh(2000)
        self.assertEqual(charges.charges("a", 2000), 4)

    def test_backtrack_recovery_not_lost(self):
        charges = Cooldowns()
        charges.register(Skill("a", 2, 1000))
        charges.cast("a", 0)
        self.assertEqual(charges.charges("a", 2500), 2)
        self.assertEqual(charges.charges("a", 500), 2)
        self.assertEqual(charges.charges("a", 3000), 2)


class ScanTest(unittest.TestCase):
    def test_scan_is_constant_per_query(self):
        charges = Cooldowns()
        for index in range(2000):
            charges.register(Skill("s-%d" % index, 2, 1000))
        for _ in range(2000):
            charges.charges("s-0", 0)
        self.assertEqual(charges.scanned_count(), 2000)


class DeterminismTest(unittest.TestCase):
    def test_repeated_sequence_has_same_result(self):
        actions = [
            ("cast", "a", 0), ("cast", "a", 0), ("query", "a", 0),
            ("query", "a", 1000), ("cast", "a", 1000),
            ("query", "a", 500), ("cast", "a", 2500), ("query", "a", 2600),
        ]

        def run():
            charges = book()
            out = []
            for kind, name, now in actions:
                if kind == "cast":
                    out.append(charges.cast(name, now))
                else:
                    out.append(charges.charges(name, now))
            return out

        self.assertEqual(run(), run())


class ReferenceCooldowns:
    """参考实现：按时间恢复 + 两道校验，用分数精算，与核心实现独立。"""

    def __init__(self, gcd_ms):
        self.gcd_ms = gcd_ms
        self.max = {}
        self.cooldown = {}
        self.credit = {}
        self.last_t = {}
        self.last_cast = None

    def register(self, name, max_charges, cooldown_ms):
        self.max[name] = max_charges
        self.cooldown[name] = cooldown_ms
        self.credit[name] = Fraction(max_charges)
        self.last_t[name] = None

    def _settle(self, name, now_ms):
        last = self.last_t[name]
        if last is None:
            self.last_t[name] = now_ms
            return
        if now_ms < last:
            return
        gained = Fraction(now_ms - last, self.cooldown[name])
        self.credit[name] = min(Fraction(self.max[name]), self.credit[name] + gained)
        self.last_t[name] = now_ms

    def cast(self, name, now_ms):
        self._settle(name, now_ms)
        if self.credit[name] < 1:
            return False
        if self.last_cast is not None and now_ms - self.last_cast < self.gcd_ms:
            return False
        self.credit[name] -= 1
        self.last_cast = now_ms
        return True

    def charges(self, name, now_ms):
        self._settle(name, now_ms)
        return self.credit[name].numerator // self.credit[name].denominator


class DifferentialTest(unittest.TestCase):
    def test_random_sequences_match_reference(self):
        deltas = [-5000, -2000, -1500, -1, -1, 0, 0, 1, 499, 500,
                  999, 1000, 1499, 1500, 2000, 3000, 7000]
        for group in range(200):
            rng = random.Random(1000 + group)
            gcd_ms = rng.choice([0, 1, 500, 1500])
            names = ["x", "y", "z"]
            actual = Cooldowns(gcd_ms=gcd_ms)
            reference = ReferenceCooldowns(gcd_ms)
            for name in names:
                max_charges = rng.randint(1, 4)
                cooldown_ms = rng.choice([300, 500, 1000, 1500, 3000])
                actual.register(Skill(name, max_charges, cooldown_ms))
                reference.register(name, max_charges, cooldown_ms)
            now = 5000
            for _ in range(60):
                now += rng.choice(deltas)
                name = rng.choice(names)
                if rng.random() < 0.5:
                    self.assertEqual(
                        actual.cast(name, now), reference.cast(name, now),
                        "cast mismatch group=%d name=%s now=%d" % (group, name, now))
                else:
                    got = actual.charges(name, now)
                    expected = reference.charges(name, now)
                    self.assertEqual(
                        got, expected,
                        "charges mismatch group=%d name=%s now=%d" % (group, name, now))
                    self.assertGreaterEqual(got, 0)
                    self.assertLessEqual(got, actual.skills[name].max_charges)


if __name__ == "__main__":
    unittest.main()
