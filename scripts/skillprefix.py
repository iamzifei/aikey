"""Single source of truth for the skill-family prefix and the public repo name.

Renaming the family used to mean hunting the string "zmm" through nine scripts,
and the three kinds of reference do not move together: directory names, the
public repo name, and the slash commands inside skill text. A missed one does
not raise — it just quietly stops finding files. So the tooling reads the
prefix from here, and a rename changes one line.

`SKILL_PREFIX` / `SKILL_REPO` override at runtime, which is what makes a
dry run possible before anything is renamed on disk.
"""

import os

# The skill-family prefix: the hub is `<PREFIX>`, members are `<PREFIX>-<suffix>`.
PREFIX = os.environ.get("SKILL_PREFIX", "aikey")

# The PUBLIC distribution repo under github.com/iamzifei/. Deliberately separate
# from PREFIX: the repo can be renamed on its own, and the fixed download URL
# hangs off this one, not off the skill names.
REPO = os.environ.get("SKILL_REPO", "aikey")

# The command the BUNDLE registers on WorkBuddy / SkillHub / 豆包. Short on
# purpose: there the whole box is one skill, so this is the only thing a user
# types, and `aikey` was measured as too long to bother with. Deliberately
# separate from PREFIX — the flat distribution keeps `aikey-*`, where a bare
# `key` would collide with everything else in a shared skills folder.
BUNDLE_CMD = os.environ.get("SKILL_BUNDLE_CMD", "key")

# Short-command aliases: skill folders that are NOT part of the family prefix
# but ship with it. They only forward to the hub, so they are excluded from the
# suite counts and from the bundle (the bundle already registers `key` itself).
ALIASES = ("key",)




def member(suffix: str) -> str:
    """`member("topic")` → `aikey-topic`; `member("")` → the hub itself."""
    return f"{PREFIX}-{suffix}" if suffix else PREFIX


def is_family(name: str) -> bool:
    """True for the hub and for any member, false for anything else."""
    return name == PREFIX or name.startswith(f"{PREFIX}-")
