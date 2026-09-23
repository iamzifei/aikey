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


def member(suffix: str) -> str:
    """`member("topic")` → `aikey-topic`; `member("")` → the hub itself."""
    return f"{PREFIX}-{suffix}" if suffix else PREFIX


def is_family(name: str) -> bool:
    """True for the hub and for any member, false for anything else."""
    return name == PREFIX or name.startswith(f"{PREFIX}-")
