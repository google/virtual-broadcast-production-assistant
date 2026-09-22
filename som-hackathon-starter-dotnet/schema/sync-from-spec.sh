#!/usr/bin/env bash
# Re-vendor the SOM JSON Schemas from the spec folder (source of truth) into this repo.
# Usage:  bash schema/sync-from-spec.sh            # uses default SOM_SPEC_DIR below
#         bash schema/sync-from-spec.sh --check    # no writes: exit 1 if repo drifted from spec
#         bash schema/sync-from-spec.sh --status   # no writes: report the computed state, always exit 0
#         SOM_SPEC_DIR=/path/to/SOM bash schema/sync-from-spec.sh
set -euo pipefail

SOM_SPEC_DIR="${SOM_SPEC_DIR:-$HOME/Library/CloudStorage/OneDrive-NBCUniversal/Documents/SOM}"
SRC="$SOM_SPEC_DIR/schema"
DST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECK=0
STATUS=0
if [ $# -gt 0 ]; then
  case "$1" in
    --check)  CHECK=1 ;;
    --status) STATUS=1 ;;
    *) echo "Unknown argument: $1 (supported: --check, --status)"; exit 2 ;;
  esac
  [ $# -gt 1 ] && { echo "Too many arguments (supported: --check, --status)"; exit 2; }
fi
NOWRITE=$(( CHECK + STATUS ))

[ -d "$SRC" ] || { echo "Spec schema folder not found: $SRC"; echo "Set SOM_SPEC_DIR to your SOM spec folder."; exit 1; }

# Pre-flight: everything the sync hard-requires must exist BEFORE anything is written,
# so a stale/renamed spec folder fails with nothing touched — never a half-vendored tree.
for req in \
    v0.3.2-proposed/som-v0.3.2-story-context.schema.json \
    v0.3.2-proposed/som-v0.3.2-telling-event.schema.json \
    v0.3.2-proposed/som-v0.3.2-delivery-media-available.schema.json \
    som_lint.py som_diff.py validate_sequence.py SCHEMA-TOOLS.md; do
  [ -f "$SRC/$req" ] || { echo "Spec is missing $req — nothing written. Spec folder older than this script?"; exit 1; }
done

OUT="$DST"
if [ "$NOWRITE" != 0 ]; then
  OUT="$(mktemp -d)"
  trap 'rm -rf "$OUT"' EXIT
fi

[ "$STATUS" = 1 ] || echo "Vendoring from: $SRC"
mkdir -p "$OUT/examples" "$OUT/v0.3.1-proposed/examples" "$OUT/v0.3.2-proposed/examples"
cp "$SRC"/som-v0.3-*.schema.json            "$OUT"/
cp "$SRC"/examples/*.json                    "$OUT/examples/"            2>/dev/null || true
cp "$SRC"/v0.3.1-proposed/*.json             "$OUT/v0.3.1-proposed/"     2>/dev/null || true
cp "$SRC"/v0.3.1-proposed/examples/*.json    "$OUT/v0.3.1-proposed/examples/" 2>/dev/null || true
cp "$SRC"/v0.3.1-proposed/README.md          "$OUT/v0.3.1-proposed/"     2>/dev/null || true
# v0.3.2 — the IBC pack (only story-context/telling/delivery change; link/audit stay v0.3.1,
# envelope/skill-warning stay flat v0.3). Scaffold's validate.py/generator are NOT vendored —
# this repo's schema/validate.py covers the whole pack. The schema cp is NOT error-suppressed:
# validate.py hard-requires these three files, so a missing/renamed spec folder must fail HERE,
# not print "Vendored." over a silent no-op.
cp "$SRC"/v0.3.2-proposed/som-v0.3.2-*.schema.json "$OUT/v0.3.2-proposed/"
cp -R "$SRC"/v0.3.2-proposed/examples/.      "$OUT/v0.3.2-proposed/examples/" 2>/dev/null || true
cp "$SRC"/v0.3.2-proposed/README.md          "$OUT/v0.3.2-proposed/"     2>/dev/null || true
# Schema tools travel with the schemas they check (som_lint checks the schema against its
# own claims; som_diff prices deltas). Existence already asserted by the pre-flight.
cp "$SRC"/som_lint.py "$SRC"/som_diff.py "$SRC"/validate_sequence.py "$SRC"/SCHEMA-TOOLS.md "$OUT"/
ls "$OUT"/v0.3.2-proposed/som-v0.3.2-*.schema.json >/dev/null

# ---- shared comparison: fills DRIFT_LIST, used by both --check and --status
compare_trees() {
  DRIFT_LIST=""
  while IFS= read -r f; do
    cmp -s "$OUT/$f" "$DST/$f" || DRIFT_LIST="${DRIFT_LIST}DRIFT: $f
"
  done < <(cd "$OUT" && find . -type f | sed 's|^\./||')
  while IFS= read -r f; do
    [ -f "$OUT/$f" ] || DRIFT_LIST="${DRIFT_LIST}ORPHANED (spec no longer provides): $f
"
  done < <(cd "$DST" && find . -type f \( \
      -path "./v0.3.1-proposed/*" -o -path "./v0.3.2-proposed/*" \
      -o -path "./examples/*" -o -name "som-v0.3-*.schema.json" \
      -o -name "som_lint.py" -o -name "som_diff.py" -o -name "validate_sequence.py" \
      -o -name "SCHEMA-TOOLS.md" \
    \) | sed 's|^\./||')
}

if [ "$STATUS" = 1 ]; then
  # Everything here is COMPUTED. The ledger records intent, which cannot be computed;
  # it does not record state, which can — and a recorded state goes stale silently
  # (it has twice), whereas a computed one cannot.
  compare_trees
  n_drift=$(printf '%s' "$DRIFT_LIST" | grep -c . || true)

  echo "SOM spec <-> repo status                                  (nothing written)"
  echo
  echo "  spec  $SRC"
  echo "  repo  $DST"
  echo

  if [ "$n_drift" = 0 ]; then
    echo "SYNC     in sync — repo matches the spec folder byte for byte"
  else
    echo "SYNC     $n_drift file(s) differ — run: bash schema/sync-from-spec.sh"
    printf '%s' "$DRIFT_LIST" | sed 's/^/           /'
  fi

  # "when did the spec CONTENT last move" — the ledger is bookkeeping, not content, so
  # excluding it stops the file answering a question about itself.
  newest=$(cd "$SRC" && find . -type f \( -name "*.json" -o -name "*.py" -o -name "*.md" \) \
            -not -path "./_superseded/*" -not -name "SYNC-STATE.md" \
            -exec stat -f '%m %N' {} + 2>/dev/null | sort -rn | head -1)
  if [ -n "$newest" ]; then
    echo "SPEC     newest file $(date -r "${newest%% *}" '+%Y-%m-%d %H:%M') — ${newest#* }"
  fi
  ledger_date=$(grep -m1 '^LAST REPO VENDOR:' "$SRC/SYNC-STATE.md" 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
  [ -n "$ledger_date" ] && echo "           ledger claims last vendored $ledger_date (claim, not proof — SYNC above is the proof)"

  zip=$(cd "$SRC" && ls -t SOM-v0.3.2-schema-pack-*.zip 2>/dev/null | head -1)
  nsup=$(ls "$SRC/_superseded"/*.zip 2>/dev/null | wc -l | tr -d ' ')
  [ -n "$zip" ] && echo "PACK     current $zip${nsup:+   ($nsup superseded)}"

  if git -C "$DST" rev-parse --git-dir >/dev/null 2>&1; then
    br=$(git -C "$DST" rev-parse --abbrev-ref HEAD 2>/dev/null)
    sha=$(git -C "$DST" rev-parse --short HEAD 2>/dev/null)
    if git -C "$DST" fetch --quiet --prune origin >/dev/null 2>&1; then
      if git -C "$DST" merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
        echo "GIT      $br @ $sha — on origin/main (fetched just now)"
      else
        ahead=$(git -C "$DST" rev-list --count origin/main..HEAD 2>/dev/null || echo "?")
        echo "GIT      $br @ $sha — NOT on origin/main, $ahead commit(s) unmerged (fetched just now)"
      fi
    else
      echo "GIT      $br @ $sha — fetch failed, merge state unknown (never read from a stale remote ref)"
    fi
  fi

  echo
  echo "LEDGER   the un-computable half — what changed and why:"
  grep -E '^(LAST SPEC CHANGE|MERGE NOTE):' "$SRC/SYNC-STATE.md" 2>/dev/null \
    | cut -c1-150 | sed 's/^/           /'
  exit 0
fi

if [ "$CHECK" = 1 ]; then
  # Compare exactly the vendored file set against the repo copy. Anything different or
  # missing means the repo has drifted from the spec since the last sync — the failure
  # mode that let a superseded time_range description sit in the repo unnoticed.
  drift=0
  while IFS= read -r f; do
    if ! cmp -s "$OUT/$f" "$DST/$f"; then
      echo "DRIFT: $f"
      drift=1
    fi
  done < <(cd "$OUT" && find . -type f | sed 's|^\./||')
  # The reverse direction: repo files in the vendored footprint that the spec no longer
  # provides (deleted/renamed spec-side). cp never deletes, so a plain sync would leave
  # them behind and the tools would keep reasoning over a schema the spec withdrew.
  while IFS= read -r f; do
    if [ ! -f "$OUT/$f" ]; then
      echo "ORPHANED (spec no longer provides): $f"
      drift=1
    fi
  done < <(cd "$DST" && find . -type f \( \
      -path "./v0.3.1-proposed/*" -o -path "./v0.3.2-proposed/*" \
      -o -path "./examples/*" -o -name "som-v0.3-*.schema.json" \
      -o -name "som_lint.py" -o -name "som_diff.py" -o -name "validate_sequence.py" \
      -o -name "SCHEMA-TOOLS.md" \
    \) | sed 's|^\./||')
  if [ "$drift" = 1 ]; then
    echo "Repo schema/ has drifted from the spec. Run: bash schema/sync-from-spec.sh"
    exit 1
  fi
  echo "In sync — repo schema/ matches the spec folder."
  exit 0
fi

# Stamp the spec-side sync ledger so cowork/spec sessions can see the repo pulled
# the spec as of today. Line-replace, so the value must stay on one line. Missing
# ledger (older spec snapshot) is fine — skip, don't fail the vendor over it.
STATE="$SRC/SYNC-STATE.md"
if [ -f "$STATE" ]; then
  BRANCH=$(git -C "$DST" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
  SHA=$(git -C "$DST" rev-parse --short HEAD 2>/dev/null || echo "?")
  stamp_tmp=$(mktemp)
  awk -v line="LAST REPO VENDOR:  $(date +%F) — branch $BRANCH, HEAD $SHA at vendor time (sync not yet committed on top of it)" \
    '/^LAST REPO VENDOR:/ {print line; next} {print}' "$STATE" > "$stamp_tmp" && mv "$stamp_tmp" "$STATE"
  echo "Stamped $STATE"
fi

echo "Vendored. Now validate:"
echo "  python3 schema/validate.py"
echo "Then note the sync in docs/SOM-v0.3.1-Migration-Log.md."
