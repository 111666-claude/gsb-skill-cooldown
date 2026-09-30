"""技能冷却与充能：按时间恢复充能、全局冷却互斥、时间回拨保护。

缺陷：施放既不校验充能层数也不校验全局冷却、充能恢复不封顶、时间回拨会倒扣充能、
查询时把所有技能重扫一遍且不做惰性恢复。
"""


class Skill:
    """一个带充能的技能。"""

    def __init__(self, name, max_charges, cooldown_ms):
        self.name = name
        self.max_charges = max_charges
        self.cooldown_ms = cooldown_ms


class Cooldowns:
    """技能充能与全局冷却台账。"""

    def __init__(self, gcd_ms=1500):
        self.gcd_ms = gcd_ms
        self.skills = {}
        self.charges_now = {}
        self.last_refresh = {}
        self.last_cast = None
        self.scanned = 0

    def register(self, skill):
        """注册技能，初始充满。"""
        self.skills[skill.name] = skill
        self.charges_now[skill.name] = skill.max_charges
        self.last_refresh[skill.name] = 0

    def refresh(self, now_ms):
        """把所有技能的充能结算到 now_ms。

        缺陷：恢复不封顶（层数能超过 max_charges）；时间回拨时步数为负，会把充能倒扣。
        """
        for name, skill in self.skills.items():
            self.scanned += 1
            steps = int((now_ms - self.last_refresh[name]) // skill.cooldown_ms)
            self.charges_now[name] += steps
            self.last_refresh[name] = now_ms

    def cast(self, name, now_ms):
        """施放技能。

        缺陷：不看剩几层、也不看全局冷却，直接扣层（能扣成负数）。
        """
        if name not in self.skills:
            raise KeyError(name)
        self.charges_now[name] -= 1
        self.last_cast = now_ms
        return True

    def charges(self, name, now_ms):
        """查询某个技能当前的充能层数。

        缺陷：每次把全部技能重扫一遍，也不按 now_ms 做惰性恢复。
        """
        self.scanned += len(self.skills)
        return self.charges_now.get(name, 0)

    def scanned_count(self):
        return self.scanned
