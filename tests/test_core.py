import random
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


class RechargeCapTest(unittest.TestCase):
    def test_partial_wait_recovers_one_step(self):
        charges = book()
        charges.cast("a", 0)
        self.assertEqual(charges.charges("a", 999), 1)
        self.assertEqual(charges.charges("a", 1000), 2)

    def test_recharge_caps_at_max_charges(self):
        charges = Cooldowns()
        charges.register(Skill("a", 2, 1000))
        charges.cast("a", 0)
        self.assertEqual(charges.charges("a", 5000), 2)

    def test_recharge_preserves_partial_remainder(self):
        charges = Cooldowns(gcd_ms=0)
        charges.register(Skill("a", 2, 1000))
        charges.cast("a", 400)
        self.assertEqual(charges.charges("a", 400), 1)
        self.assertEqual(charges.charges("a", 999), 1)
        self.assertEqual(charges.charges("a", 1000), 2)
        charges.cast("a", 1000)
        self.assertEqual(charges.charges("a", 1999), 1)
        self.assertEqual(charges.charges("a", 2000), 2)

    def test_recharge_does_not_depend_on_refresh_calls(self):
        charges_a = Cooldowns()
        charges_b = Cooldowns()
        for charges in (charges_a, charges_b):
            charges.register(Skill("a", 3, 1000))
            charges.cast("a", 0)
        for now_ms in range(0, 3500, 37):
            charges_a.refresh(now_ms)
            self.assertEqual(
                charges_a.charges("a", now_ms), charges_b.charges("a", now_ms)
            )


class CastValidationTest(unittest.TestCase):
    def test_empty_charge_is_rejected(self):
        charges = Cooldowns(gcd_ms=0)
        charges.register(Skill("a", 1, 100000))
        self.assertTrue(charges.cast("a", 0))
        self.assertFalse(charges.cast("a", 1000))
        self.assertEqual(charges.charges("a", 1000), 0)

    def test_gcd_blocks_second_cast(self):
        charges = Cooldowns(gcd_ms=1500)
        charges.register(Skill("a", 2, 1000))
        charges.register(Skill("b", 2, 1000))
        self.assertTrue(charges.cast("a", 1000))
        self.assertFalse(charges.cast("b", 1999))
        self.assertEqual(charges.charges("b", 1999), 2)
        self.assertTrue(charges.cast("b", 2500))
        self.assertEqual(charges.charges("b", 2500), 1)

    def test_failed_cast_does_not_refresh_gcd(self):
        charges = Cooldowns(gcd_ms=1500)
        charges.register(Skill("a", 3, 100000))
        self.assertTrue(charges.cast("a", 0))
        self.assertFalse(charges.cast("a", 1000))
        self.assertEqual(charges.charges("a", 1000), 2)
        self.assertTrue(charges.cast("a", 1500))

    def test_three_casts_at_same_time_use_one_charge(self):
        charges = Cooldowns()
        charges.register(Skill("a", 2, 1000))
        results = [charges.cast("a", 0) for _ in range(3)]
        self.assertEqual(results, [True, False, False])
        self.assertEqual(charges.charges("a", 0), 1)


class ClockBackTest(unittest.TestCase):
    def test_charges_never_decrease_on_clock_back(self):
        charges = Cooldowns()
        charges.register(Skill("a", 5, 1000))
        charges.refresh(3000)
        charges.cast("a", 3000)
        before = charges.charges("a", 3000)
        charges.refresh(2000)
        after = charges.charges("a", 2000)
        self.assertEqual((before, after), (4, 4))

    def test_settled_charges_survive_repeated_back_and_forth(self):
        charges = Cooldowns()
        charges.register(Skill("a", 2, 1000))
        charges.cast("a", 0)
        self.assertEqual(charges.charges("a", 2000), 2)
        self.assertEqual(charges.charges("a", 500), 2)
        self.assertEqual(charges.charges("a", 2000), 2)
        self.assertEqual(charges.charges("a", 1), 2)

    def test_gcd_holds_under_clock_back(self):
        charges = Cooldowns(gcd_ms=1500)
        charges.register(Skill("a", 2, 1000))
        self.assertTrue(charges.cast("a", 3000))
        self.assertFalse(charges.cast("a", 2000))


class DeterminismTest(unittest.TestCase):
    def test_same_sequence_replays_identically(self):
        rng = random.Random(1234)
        sequence = []
        names = ["a", "b", "c"]
        now = 0
        for _ in range(60):
            kind = rng.choice(("cast", "query", "wait", "back"))
            if kind == "wait":
                now += rng.randint(0, 2000)
            elif kind == "back":
                now = max(0, now - rng.randint(0, 2000))
            else:
                sequence.append((kind, rng.choice(names), now))

        specs = {name: (rng.randint(1, 4), rng.choice((500, 1000, 3000))) for name in names}

        def run():
            charges = Cooldowns(gcd_ms=1500)
            for name in names:
                max_charges, cooldown_ms = specs[name]
                charges.register(Skill(name, max_charges, cooldown_ms))
            output = []
            for kind, name, at in sequence:
                if kind == "cast":
                    output.append(charges.cast(name, at))
                else:
                    output.append(charges.charges(name, at))
            return output

        self.assertEqual(run(), run())


class ScaleTest(unittest.TestCase):
    def test_charges_query_is_constant_work(self):
        charges = Cooldowns()
        total = 5000
        for index in range(total):
            charges.register(Skill("s-%d" % index, 2, 1000))
        for _ in range(100):
            charges.charges("s-0", 0)
        self.assertEqual(charges.scanned_count(), 100)

    def test_invariant_with_many_skills(self):
        charges = Cooldowns(gcd_ms=1000)
        for index in range(2000):
            charges.register(Skill("s-%d" % index, 3, 700))
        rng = random.Random(99)
        now = 0
        for _ in range(5000):
            now += rng.randint(0, 100)
            name = "s-%d" % rng.randrange(2000)
            charges.cast(name, now)
            level = charges.charges(name, now)
            self.assertGreaterEqual(level, 0)
            self.assertLessEqual(level, 3)


class ReferenceBook:
    """参考实现：按时间恢复 + 充能/全局冷却两道校验。"""

    def __init__(self, gcd_ms):
        self.gcd_ms = gcd_ms
        self.specs = {}
        self.level = {}
        self.since = {}
        self.last_cast = None

    def register(self, name, max_charges, cooldown_ms):
        self.specs[name] = (max_charges, cooldown_ms)
        self.level[name] = max_charges
        self.since[name] = 0

    def settle(self, name, now_ms):
        max_charges, cooldown_ms = self.specs[name]
        last = self.since[name]
        if now_ms > last:
            steps = (now_ms - last) // cooldown_ms
            if steps:
                self.level[name] = min(max_charges, self.level[name] + steps)
                self.since[name] = last + steps * cooldown_ms

    def cast(self, name, now_ms):
        self.settle(name, now_ms)
        if self.level[name] < 1:
            return False
        if self.last_cast is not None and now_ms - self.last_cast < self.gcd_ms:
            return False
        self.level[name] -= 1
        self.last_cast = now_ms
        return True

    def charges(self, name, now_ms):
        self.settle(name, now_ms)
        return self.level[name]


class ReferenceCompareTest(unittest.TestCase):
    def test_200_random_sequences_match_reference(self):
        rng = random.Random(20260930)
        for trial in range(200):
            gcd_ms = rng.choice((0, 500, 1500))
            actual = Cooldowns(gcd_ms=gcd_ms)
            expect = ReferenceBook(gcd_ms=gcd_ms)
            names = []
            for index in range(rng.randint(1, 4)):
                name = "s%d" % index
                max_charges = rng.randint(1, 5)
                cooldown_ms = rng.choice((500, 1000, 2000))
                actual.register(Skill(name, max_charges, cooldown_ms))
                expect.register(name, max_charges, cooldown_ms)
                names.append(name)
            now = 0
            for step in range(rng.randint(5, 40)):
                move = rng.choice(("cast", "wait", "back", "query"))
                if move == "wait":
                    now += rng.randint(0, 5000)
                    continue
                if move == "back":
                    now = max(0, now - rng.randint(0, 3000))
                    continue
                name = rng.choice(names)
                if move == "cast":
                    got = actual.cast(name, now)
                    want = expect.cast(name, now)
                    self.assertEqual(
                        got, want,
                        "trial=%d step=%d name=%s now=%d cast" % (trial, step, name, now),
                    )
                got = actual.charges(name, now)
                want = expect.charges(name, now)
                self.assertEqual(
                    got, want,
                    "trial=%d step=%d name=%s now=%d charges" % (trial, step, name, now),
                )
                self.assertGreaterEqual(got, 0)
                self.assertLessEqual(got, actual.skills[name].max_charges)
            for name in names:
                self.assertEqual(actual.charges(name, now), expect.charges(name, now))


if __name__ == "__main__":
    unittest.main()
