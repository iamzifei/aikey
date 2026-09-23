#!/usr/bin/env bash
# Publish every skill to ClawHub from a --clawhub build.
#
#   bash scripts/publish_clawhub.sh [构建目录] [--dry-run]
#
# Prerequisites:
#   1. `clawhub login`
#   2. clawhub CLI >= 0.23. Older builds (0.7.x) fail every publish with
#      "MIT-0 license terms must be accepted to publish skills" — that version
#      has no licence handling at all and just relays the server error. There is
#      nothing to click; upgrade with `npm i -g clawhub@latest`.
#
# Slugs stay English (npm-safe, and ClawHub requires it); the Chinese display
# name comes from --name. Version is read from each SKILL.md so this script
# never invents one.
#
# SkillHub needs nothing: it mirrors and auto-claims from ClawHub.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OWNER="${CLAWHUB_OWNER:-iamzifei}"     # publisher handle; skills appear as @iamzifei/<slug>
                                       # 2026-09-01: moved off the @aikey org so the ClawHub
                                       # handle matches the GitHub handle SkillHub links to.
                                       # Search still finds everything — ClawHub matches the
                                       # slug (aikey-*), not the owner.
CHANGELOG="${CLAWHUB_CHANGELOG:-更新}"  # CI passes the commit message
ONLY="${CLAWHUB_ONLY:-}"               # optional comma-separated slug allowlist
BUILD="${1:-}"
DRY=0
for a in "$@"; do [ "$a" = "--dry-run" ] && DRY=1; done
[ "${BUILD:-}" = "--dry-run" ] && BUILD=""
PREFIX="${SKILL_PREFIX:-aikey}"   # 技能族前缀，改名时改这里
BUILD="${BUILD:-$SRC/../${PREFIX}-clawhub}"

if [ ! -d "$BUILD" ]; then
  echo "❌ 构建目录不存在：$BUILD"
  echo "   先跑：bash scripts/build_public.sh $BUILD --clawhub"
  exit 1
fi

# ClawHub imposes MIT-0 and rejects conflicting terms. Only what sits INSIDE a
# skill folder is uploaded, so a repo-root LICENSE (CC BY-NC, for the GitHub
# copy) is fine — a LICENSE inside a skill folder is not.
for lic in "$BUILD"/skills/*/LICENSE "$BUILD"/skills/*/LICENSE.*; do
  [ -e "$lic" ] || continue
  echo "❌ 技能文件夹内有 LICENSE：$lic"
  echo "   ClawHub 统一 MIT-0 且拒绝冲突条款，停止。"
  exit 1
done


# ClawHub display names. Deliberately NOT read from SKILL.md: `name` there must
# stay an ASCII slug, because skills.sh derives the install directory from it and
# a Chinese value slugifies to nothing — all 20 skills then land in one
# `unnamed-skill` folder and overwrite each other (measured 2026-09-01).
# So the Chinese brand name lives here and is passed with --name at publish time.

# Next patch after whatever is published, so --version can always be explicit.
# Falls back to the frontmatter version when the skill is not published yet.
next_version() {
  local slug="$1" fallback="$2" cur
  cur="$(clawhub inspect "$OWNER/$slug" --json 2>/dev/null \
        | python3 -c "import sys,json;print(json.load(sys.stdin).get('latestVersion',{}).get('version',''))" 2>/dev/null)"
  if [ -z "$cur" ]; then
    echo "$fallback"
    return
  fi
  python3 -c "
import sys
major, minor, patch = (int(x) for x in '$cur'.split('.'))
print(f'{major}.{minor}.{patch + 1}')"
}

display_name() {
  case "$1" in
    aikey)                echo "AI KEY" ;;
    aikey-topic)          echo "AI KEY·今天拍什么" ;;
    aikey-benchmark)      echo "AI KEY·找对标" ;;
    aikey-script)         echo "AI KEY·口播稿写作" ;;
    aikey-title)          echo "AI KEY·标题与封面" ;;
    aikey-hook)           echo "AI KEY·开头前五秒" ;;
    aikey-review)         echo "AI KEY·发布前审一遍" ;;
    aikey-flow)           echo "AI KEY·哪里会被划走" ;;
    aikey-cut)            echo "AI KEY·口播剪辑" ;;
    aikey-retro)          echo "AI KEY·发布后复盘" ;;
    aikey-post)           echo "AI KEY·公众号短文" ;;
    aikey-mvp)            echo "AI KEY·选题先试水" ;;
    aikey-resonate)       echo "AI KEY·戳不戳得中人" ;;
    aikey-concept)        echo "AI KEY·重讲一个概念" ;;
    aikey-product)        echo "AI KEY·我该卖什么" ;;
    aikey-portfolio)      echo "AI KEY·该投哪条线" ;;
    aikey-revenue)        echo "AI KEY·这个月钱去哪了" ;;
    aikey-concentration)  echo "AI KEY·大客户会不会跑" ;;
    aikey-dependency)     echo "AI KEY·这生意靠谁" ;;
    aikey-decide)         echo "AI KEY·拿不准的时候" ;;
    aikey-path)           echo "AI KEY·从哪儿下手" ;;
    aikey-trend)          echo "AI KEY·风口在哪" ;;
    aikey-drama)          echo "AI KEY·短剧编剧" ;;
    aikey-track)          echo "AI KEY·有什么到期了" ;;
    aikey-skillify)       echo "AI KEY·做成一个技能" ;;
    *)                  echo "" ;;   # unknown slug: caller reports and skips
  esac
}

ok=0; fail=0; failed=()

for d in "$BUILD"/skills/"$PREFIX"*/; do
  [ -f "$d/SKILL.md" ] || continue
  slug="$(basename "${d%/}")"

  # ONLY is a comma-separated allowlist. CI sets it from the push diff so an
  # ordinary commit does not cut a new version for all 20 untouched skills.
  if [ -n "${ONLY:-}" ] && ! printf '%s' ",$ONLY," | grep -q ",$slug,"; then
    continue
  fi
  name="$(display_name "$slug")"
  ver="$(awk 'NR>1 && /^---$/{exit} /^version:/{sub(/^version: */,""); print; exit}' "$d/SKILL.md")"
  # `ver` is only shown in the log; ClawHub picks the published version itself.

  if [ -z "$name" ] || [ -z "$ver" ]; then
    echo "⚠️  $slug 没有登记中文名或缺 version，跳过（请在 display_name() 里补一行）"
    fail=$((fail + 1)); failed+=("$slug (缺字段)")
    continue
  fi

  printf '%-20s → %-14s ' "$slug" "$name"

  if [ "$DRY" = "1" ]; then
    echo "[dry-run] → @$OWNER/$slug"
    ok=$((ok + 1))
    continue
  fi

  # --version must be explicit. Omitting it makes ClawHub pick the next patch but
  # ALSO drops --name, resetting the display name to the ASCII slug (measured
  # 2026-09-01: run 33475523450 reset all 20, a manual publish with an explicit
  # version restored them). The mechanism is unclear; the behaviour is not.
  # So compute the next patch here and pass both.
  next_ver="$(next_version "$slug" "$ver")"

  # "already exists" is NOT "unchanged". A version that was submitted and then
  # blocked by moderation is hidden from `inspect`, so latestVersion stays one
  # behind and next_version() lands on the blocked number again. 2026-09-22:
  # aikey-cut 0.2.7 was blocked, the fixed upload computed 0.2.7 again, got
  # "already exists", and the old branch printed 「内容未变」 and counted it as
  # a success — the fix never shipped and the log said all green.
  # So: bump the patch and retry; only a real no-change answer counts as a skip.
  attempt=0
  result=""
  while [ $attempt -lt 5 ]; do
    if clawhub skill publish "$d" \
        --slug "$slug" --name "$name" --owner "$OWNER" --version "$next_ver" \
        --changelog "$CHANGELOG" --tags latest >/tmp/clawhub_publish.log 2>&1; then
      result="ok"; break
    fi
    if grep -qi "already exists" /tmp/clawhub_publish.log; then
      next_ver="$(python3 -c "
major, minor, patch = (int(x) for x in '$next_ver'.split('.'))
print(f'{major}.{minor}.{patch + 1}')")"
      attempt=$((attempt + 1))
      continue
    fi
    if grep -qi "unchanged\|no changes" /tmp/clawhub_publish.log; then
      result="skip"
    else
      result="fail"
    fi
    break
  done

  case "$result" in
    ok)   echo "✅ $next_ver"; ok=$((ok + 1)) ;;
    skip) echo "⏭  内容未变"; ok=$((ok + 1)) ;;
    *)    echo "❌"
          sed 's/^/      /' /tmp/clawhub_publish.log | tail -3
          fail=$((fail + 1)); failed+=("$slug") ;;
  esac
done

echo
echo "成功 $ok · 失败 $fail"
if [ "$fail" -gt 0 ]; then
  printf '  失败：%s\n' "${failed[@]}"
  exit 1
fi
