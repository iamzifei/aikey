#!/usr/bin/env python3
"""
Consistency gate — README and the skills must never drift apart.

Writing "keep the README updated" in a markdown file means "probably". This runs
inside build_public.sh and fails the build instead, so a drifted README can never
reach the public repo.

Checks, against the BUILT tree:
  1. every skill folder is listed in README.md
  2. README's per-suite counts match the real ones
  3. every skill has a Chinese display name registered in publish_clawhub.sh
  4. every skill's frontmatter has an ASCII-slug name matching its folder
  5. (2026-11-06) every member skill has exactly one 「## 接手与交出」 section
     with its four lines — the hub's next-step routing reads it
  6. (2026-11-06) every member's start block reads its own skill memory, and
     every content member's start block reads the family covenant
  7. (2026-11-06) every description is at most DESC_MAX characters

Usage: python3 scripts/check_consistency.py <built tree>
"""

import re
import sys
from pathlib import Path

from skillprefix import ALIASES, member

# The content half of the family, by suffix — the prefix comes from skillprefix,
# so a rename touches one line there instead of sixteen here.
CONTENT_SUFFIXES = {"", "topic", "benchmark", "script", "title", "hook", "review",
                    "flow", "cut", "retro", "post", "mvp", "resonate",
                    "concept", "skillify", "drama", "cover", "aivideo"}
CONTENT = {member(s) for s in CONTENT_SUFFIXES}

# Hosts and skill indexes truncate or drop long descriptions; three skills sat
# at 1,100–1,270 characters before this cap existed (2026-11-06).
DESC_MAX = 1024
# The start block is whatever precedes the first point where a skill starts
# doing its own work; 60 lines covers every member's preamble today.
START_LINES = 60
HANDOFF_LINES = ("- **接手**：", "- **交出**：", "- **不交出**：", "- **之后常接**：")


def description_of(text: str) -> str:
    """Frontmatter description, block-scalar or inline, whitespace-collapsed."""
    fm = text.split("---", 2)[1] if text.startswith("---") else ""
    m = re.search(r"^description:[ \t]*\|?[ \t]*\n?(.*?)(?=^[A-Za-z_][\w-]*:|\Z)",
                  fm, re.S | re.M)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def main(root: Path) -> int:
    problems = []

    skills = sorted(d.name for d in (root / "skills").iterdir()
                    if (d / "SKILL.md").is_file())
    if not skills:
        print("❌ 产出树里没有技能，check 无法进行")
        return 1

    readme = (root / "README.md").read_text(encoding="utf-8")

    # 1. every skill listed
    for slug in skills:
        if f"`{slug}`" not in readme:
            problems.append(f"README 没有列出技能 `{slug}`")

    # 2. counts match
    # Aliases forward to the hub and are not capabilities — they must still be
    # listed in the README, but counting them would make a suite look bigger.
    counted = [s for s in skills if s not in ALIASES]
    n_content = sum(1 for s in counted if s in CONTENT)
    n_biz = len(counted) - n_content
    for label, actual in (("内容操盘手", n_content), ("生意操盘手", n_biz)):
        m = re.search(rf"{label}（(\d+) 个技能）", readme)
        if not m:
            problems.append(f"README 找不到「{label}（N 个技能）」抬头")
        elif int(m.group(1)) != actual:
            problems.append(
                f"README 写「{label}（{m.group(1)} 个技能）」，实际 {actual} 个")

    # 4. every built skill got its display name injected. The MAP in
    # build_public.sh is a second registry; zmm-path and zmm-trend shipped
    # without it for two releases because only publish_clawhub.sh was checked.
    for slug in skills:
        head = (root / "skills" / slug / "SKILL.md").read_text(encoding="utf-8")[:3000]
        if not re.search(r"^displayName:\s*\S", head, re.M):
            problems.append(
                f"`{slug}` 的产出 SKILL.md 没有 displayName —— build_public.sh 的中文名表漏了它")

    # 3. display name registered
    pub = (root / "scripts" / "publish_clawhub.sh").read_text(encoding="utf-8")
    for slug in skills:
        if not re.search(rf"^\s*{re.escape(slug)}\)\s+echo", pub, re.M):
            problems.append(
                f"`{slug}` 在 publish_clawhub.sh 的 display_name() 里没有中文名")

    # 4. frontmatter name is the ASCII slug
    for slug in skills:
        text = (root / "skills" / slug / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"^name:\s*(.+)$", text, re.M)
        if not m:
            problems.append(f"`{slug}/SKILL.md` 没有 name 字段")
        elif m.group(1).strip() != slug:
            problems.append(
                f"`{slug}/SKILL.md` 的 name 是 {m.group(1).strip()!r}，应为 {slug!r} —— "
                "非 ASCII slug 会让 skills.sh 把所有技能装进同一个 unnamed-skill 目录")

    # 8. (2026-11-06) the hub's own audience table states the same suite counts as
    # the README — it drifted to 17 while the README said 18.
    hub_md = root / "skills" / member("") / "SKILL.md"
    if hub_md.is_file():
        hub_text = hub_md.read_text(encoding="utf-8")
        for label, actual in (("内容操盘手", n_content), ("生意操盘手", n_biz)):
            m = re.search(rf"\*\*{label}\*\*（(\d+) 个）", hub_text)
            if m and int(m.group(1)) != actual:
                problems.append(f"入口 SKILL.md 写「{label}（{m.group(1)} 个）」，实际 {actual} 个")

    hub = member("")
    for slug in skills:
        text = (root / "skills" / slug / "SKILL.md").read_text(encoding="utf-8")

        # 7. description length
        desc = description_of(text)
        if len(desc) > DESC_MAX:
            problems.append(f"`{slug}` 的 description {len(desc)} 字符，超过上限 {DESC_MAX}")

        if slug == hub or slug in ALIASES:
            continue   # the hub routes; aliases forward — neither has its own work

        # 5. handoff section
        n = len(re.findall(r"^## 接手与交出\s*$", text, re.M))
        if n != 1:
            problems.append(f"`{slug}` 有 {n} 个「## 接手与交出」，应为 1 个")
        else:
            # Anchor at line start: an inline mention of the heading elsewhere
            # (the hub quotes it in backticks) must not be taken as the section.
            sec = re.split(r"^## 接手与交出\s*$", text, maxsplit=1, flags=re.M)[1].split("\n## ", 1)[0]
            for line in HANDOFF_LINES:
                if line not in sec:
                    problems.append(f"`{slug}` 的「接手与交出」缺一行 {line.strip('- *：')}")

        # 6. start block reads memory (and covenant, for content members)
        body = text.split("---", 2)[2] if text.startswith("---") else text
        start = "\n".join(body.splitlines()[:START_LINES])
        # Must name THIS skill's own memory dir — reading only _通用/ or a
        # neighbour's memory is the drift this check exists for. The suffix match
        # tolerates the build's prefix rewrite (aikey-flow → aikey-flow, zmm-flow …).
        own = re.escape(slug.split("-", 1)[1]) if "-" in slug else re.escape(slug)
        # Accepted forms: `技能记忆/aikey-x/`, `{config.paths.memory}/aikey-x/`,
        # `config.paths.memory` 下 `aikey-x/`; a skill that reads every memory
        # dir (the retro) says so with 全部子目录.
        reads_own = re.search(rf"(技能记忆|paths\.memory)[^\n]{{0,12}}?[\w-]*{own}/", start)
        if not (reads_own or re.search(r"技能记忆/`?（\**全部子目录", start)):
            problems.append(f"`{slug}` 的启动块（正文前 {START_LINES} 行）没有读本技能记忆")
        if slug in CONTENT and "家族公约" not in start:
            problems.append(f"`{slug}` 是内容技能，启动块没有读家族公约")

    if problems:
        print(f"\n❌ 一致性检查未通过（{len(problems)} 项）：")
        for p in problems:
            print(f"   · {p}")
        return 1

    print(f"✅ 一致性检查通过：{len(skills)} 个技能，README、中文名表、frontmatter、接手与交出、启动块、description 长度一致")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
