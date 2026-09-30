"""命令行入口：跑技能冷却样例。"""

import argparse

from .core import Cooldowns, Skill


def build_parser():
    parser = argparse.ArgumentParser(prog="skill-cooldown", description="技能冷却与充能")
    parser.add_argument("--sample", default="charges", help="charges / recharge / clockback / gcd / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "charges":
        book = Cooldowns()
        book.register(Skill("a", 2, 1000))
        for _ in range(3):
            book.cast("a", 0)
        print("charges=%d" % book.charges("a", 0))
    elif args.sample == "recharge":
        book = Cooldowns()
        book.register(Skill("a", 2, 1000))
        book.cast("a", 0)
        book.refresh(5000)
        print("charges=%d" % book.charges("a", 5000))
    elif args.sample == "clockback":
        book = Cooldowns()
        book.register(Skill("a", 5, 1000))
        book.refresh(3000)
        book.cast("a", 3000)
        before = book.charges("a", 3000)
        book.refresh(2000)
        print("before=%d after=%d" % (before, book.charges("a", 2000)))
    elif args.sample == "gcd":
        book = Cooldowns()
        book.register(Skill("a", 2, 1000))
        book.register(Skill("b", 2, 1000))
        book.cast("a", 1000)
        print("second=%s" % ("true" if book.cast("b", 1100) else "false"))
    elif args.sample == "scan":
        book = Cooldowns()
        for index in range(2000):
            book.register(Skill("s-%d" % index, 2, 1000))
        for _ in range(2000):
            book.charges("s-0", 0)
        print("scanned=%d" % book.scanned_count())
    else:
        raise SystemExit("需要 --sample charges|recharge|clockback|gcd|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
