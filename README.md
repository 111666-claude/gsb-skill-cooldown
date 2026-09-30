# skill-cooldown

技能冷却与充能：按时间恢复充能、全局冷却互斥、时间回拨保护，只用 Python 标准库。

```
python3 -m skillcooldown.cli --sample charges
python3 -m skillcooldown.cli --sample recharge
python3 -m skillcooldown.cli --sample clockback
python3 -m skillcooldown.cli --sample gcd
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **充能按时间恢复**：每个技能每过 `cooldown_ms` 恢复 1 层，最多 `max_charges` 层；
  恢复必须按查询时刻惰性结算，不许依赖外部调用次数。
- **施放要过两道校验**：剩余层数不足 1 层、或距上次施放不足 `gcd_ms`（全局冷却）时拒绝施放，
  返回 `False` 且不扣层；成功时才扣 1 层并刷新全局冷却基准。
- **时间回拨保护**：`now_ms` 小于上次结算时刻时，充能不许减少。
- **查询代价**：`charges(name, now)` 只碰该技能，`scanned_count()` 不随注册技能数增长。
- **规模**：50 万个技能实例、每秒 20 万次查询，单次查询 O(1)，内存 O(技能数)。

## 输出契约（不改格式）

```
charges=1
charges=2
charges=1
second=false
scanned<=4000
```

## 目录

```
skillcooldown/core.py   充能与全局冷却
skillcooldown/cli.py    命令行入口
tests/                  unittest 用例
```
