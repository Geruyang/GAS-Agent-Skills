#!/usr/bin/env python3
"""Check shared standalone assets; --write copies canonical files, never SKILL text."""

import argparse
from pathlib import Path
import sys

# A default check must not create an import cache, even when invoked without -B.
sys.dont_write_bytecode = True
from update_manifest import atomic_write, checked_path, configure_output, read_regular


CANON = "gas-centralized-development"
PEERS = ("gas-decentralized-development", "gas-combined-development")
SHARED = ("scripts/gas_runtime.py", "references/runtime-evidence.md", "references/research-basis.md")
AGENT_HEADING = "## 子 Agent 创建前的人类交互（AGENT-01）"
END_HEADING = "## 权责边界"


def agent_block(path):
    text = read_regular(path).decode("utf-8").replace("\r\n", "\n")
    lines = text.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.rstrip("\n") == AGENT_HEADING]
    ends = [index for index, line in enumerate(lines) if line.rstrip("\n") == END_HEADING]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise ValueError("Missing/ambiguous AGENT-01 section boundaries: " + str(path))
    return "".join(lines[starts[0]:ends[0]])


def main(argv=None):
    configure_output()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[1],
                        help="Package directory (default: this script's parent package).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Check without writing (default).")
    mode.add_argument("--write", action="store_true", help="Copy canonical assets to the two peer packages.")
    args = parser.parse_args(argv)
    try:
        root = checked_path(args.root)
        block = agent_block(root / CANON / "SKILL.md")
        mismatches = [peer for peer in PEERS if agent_block(root / peer / "SKILL.md") != block]
        if mismatches:
            print("AGENT-01 differs: " + ", ".join(mismatches) +
                  ". Reconcile SKILL.md manually; no assets were written.", file=sys.stderr)
            return 1
        changes = []
        # Preflight every source and destination before any writes.
        for rel in SHARED:
            data = read_regular(root / CANON / rel)
            for peer in PEERS:
                target = checked_path(root / peer / rel, missing_leaf=True)
                if not target.exists() or read_regular(target) != data:
                    changes.append((target, data))
        for target, data in changes:
            print("differs: " + target.relative_to(root).as_posix())
        if changes and not args.write:
            print("Shared assets differ. Review canonical edits before running --write.", file=sys.stderr)
            return 1
        for target, data in changes:
            atomic_write(target, data)
        print("Shared assets and AGENT-01 are consistent." if not changes else
              "Synchronized {} shared assets; SKILL.md was not changed.".format(len(changes)))
        return 0
    except (OSError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
