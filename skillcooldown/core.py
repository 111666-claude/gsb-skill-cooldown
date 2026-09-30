"""技能冷却与充能：按时间恢复充能、全局冷却互斥、时间回拨保护。

充能按查询/施放时刻惰性结算：每过 cooldown_ms 恢复 1 层，封顶 max_charges，
不依赖外部调用 refresh 的次数；施放需通过充能层数与全局冷却两道校验；
now_ms 回拨时充能不减少；charges 查询只碰目标技能，O(1)。
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

    def _settle(self, name, now_ms):
        """把单个技能的充能惰性结算到 now_ms。

        每过 cooldown_ms 恢复 1 层并封顶 max_charges；只按整步推进结算基准，
        保留不足一步的余量；now_ms 回拨（小于上次结算时刻）时不做任何扣减。
        """
        skill = self.skills[name]
        last = self.last_refresh[name]
        if now_ms <= last:
            return
        steps = (now_ms - last) // skill.cooldown_ms
        if steps <= 0:
            return
        self.charges_now[name] = min(skill.max_charges, self.charges_now[name] + steps)
        self.last_refresh[name] = last + steps * skill.cooldown_ms

    def refresh(self, now_ms):
        """兼容旧接口：充能改为查询时惰性结算，结果与调用本方法的次数无关。"""
        return

    def cast(self, name, now_ms):
        """施放技能。

        先按 now_ms 惰性结算；剩余层数不足 1 层、或距上次成功施放不足
        gcd_ms（含时间回拨）时拒绝，返回 False 且不扣层；成功才扣 1 层
        并刷新全局冷却基准。
        """
        if name not in self.skills:
            raise KeyError(name)
        self._settle(name, now_ms)
        if self.charges_now[name] < 1:
            return False
        if self.last_cast is not None and now_ms - self.last_cast < self.gcd_ms:
            return False
        self.charges_now[name] -= 1
        self.last_cast = now_ms
        return True

    def charges(self, name, now_ms):
        """查询某个技能当前的充能层数：只结算该技能，O(1)。"""
        self.scanned += 1
        if name not in self.skills:
            return 0
        self._settle(name, now_ms)
        return self.charges_now[name]

    def scanned_count(self):
        return self.scanned
