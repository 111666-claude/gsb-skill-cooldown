"""技能冷却与充能：按时间惰性恢复、全局冷却互斥、时间回拨保护。

口径（README 为准）：
- 充能按时间恢复：每过 cooldown_ms 恢复 1 层，封顶 max_charges；
  查询/施放时按 now_ms 惰性结算，不依赖外部调用 refresh 的次数。
- 施放两道校验：剩余层数不足 1 层、或距上次施放不足 gcd_ms 时拒绝，
  返回 False 且不扣层；成功才扣 1 层并刷新全局冷却基准。
- 时间回拨保护：now_ms 小于上次结算时刻时，充能不许减少。
- 查询代价：charges(name, now) 只碰该技能，单次 O(1)。
"""


class Skill:
    """一个带充能的技能。"""

    def __init__(self, name, max_charges, cooldown_ms):
        self.name = name
        self.max_charges = max_charges
        self.cooldown_ms = cooldown_ms


class Cooldowns:
    """技能充能与全局冷却台账。

    每个技能保存 (charges, next_ready, last_now)：
    - charges：已结算到 last_now 时刻的层数，恒在 [0, max_charges]；
    - next_ready：充能不满时下一层恢复的时刻，充满时为 None；
    - last_now：该技能上次结算时刻，时间回拨时不倒扣充能。
    """

    def __init__(self, gcd_ms=1500):
        self.gcd_ms = gcd_ms
        self.skills = {}
        self.charges_now = {}
        self.next_ready = {}
        self.last_now = {}
        self.last_cast = None
        self.scanned = 0

    def register(self, skill):
        """注册技能，初始充满。"""
        self.skills[skill.name] = skill
        self.charges_now[skill.name] = skill.max_charges
        self.next_ready[skill.name] = None
        self.last_now[skill.name] = None

    def _settle(self, name, now_ms):
        """把单个技能按时间惰性结算到 now_ms，返回结算时刻。

        时间回拨（now_ms 早于上次结算时刻）时不做任何增减，充能不许减少。
        """
        last = self.last_now[name]
        if last is None:
            self.last_now[name] = now_ms
            return now_ms
        if now_ms <= last:
            return last
        ready = self.next_ready[name]
        if ready is not None and now_ms >= ready:
            skill = self.skills[name]
            gained = (now_ms - ready) // skill.cooldown_ms + 1
            charges = self.charges_now[name] + gained
            if charges >= skill.max_charges:
                self.charges_now[name] = skill.max_charges
                self.next_ready[name] = None
            else:
                self.charges_now[name] = charges
                self.next_ready[name] = ready + gained * skill.cooldown_ms
        self.last_now[name] = now_ms
        return now_ms

    def refresh(self, now_ms):
        """把所有技能结算到 now_ms（惰性恢复的显式入口，可选调用）。"""
        for name in self.skills:
            self.scanned += 1
            self._settle(name, now_ms)

    def cast(self, name, now_ms):
        """施放技能：层数不足 1 层或全局冷却未到时拒绝，返回 False 且不扣层。"""
        if name not in self.skills:
            raise KeyError(name)
        settled_now = self._settle(name, now_ms)
        if self.charges_now[name] < 1:
            return False
        if self.last_cast is not None and now_ms - self.last_cast < self.gcd_ms:
            return False
        self.charges_now[name] -= 1
        if self.charges_now[name] >= self.skills[name].max_charges - 1:
            # 施放前是满的，从这一扣开始重新计时；回拨时以结算时刻为基准。
            self.next_ready[name] = settled_now + self.skills[name].cooldown_ms
        self.last_cast = now_ms
        return True

    def charges(self, name, now_ms):
        """查询某个技能在 now_ms 的充能层数，只结算该技能，O(1)。"""
        if name not in self.skills:
            return 0
        self.scanned += 1
        self._settle(name, now_ms)
        return self.charges_now[name]

    def scanned_count(self):
        return self.scanned
