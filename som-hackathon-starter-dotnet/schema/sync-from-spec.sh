#!/usr/bin/env bash
# Re-vendor the SOM JSON Schemas from the spec folder (source of truth) into this repo.
# Usage:  bash schema/sync-from-spec.sh            # uses default SOM_SPEC_DIR below
#         bash schema/sync-from-spec.sh --check    # no writes: exit 1 if repo drifted from spec
#         SOM_SPEC_DIR=/path/to/SOM bash schema/sync-from-spec.sh
set -euo pipefail

SOM_SPEC_DIR="${SOM_SPEC_DIR:-$HOME/Library/CloudStorage/OneDrive-NBCUniversal/Documents/SOM}"
SRC="$SOM_SPEC_DIR/schema"
DST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHECK=0
if [ $# -gt 0 ]; then
  case "$1" in
    --check) CHECK=1 ;;
    *) echo "Unknown argument: $1 (only --check is supported)"; exit 2 ;;
  esac
  [ $# -gt 1 ] && { echo "Too many arguments (only --check is supported)"; exit 2; }
fi

[ -d "$SRC" ] || { echo "Spec schema folder not found: $SRC"; echo "Set SOM_SPEC_DIR to your SOM spec folder."; exit 1; }

# Pre-flight: everything the sync hard-requires must exist BEFORE anything is written,
# so a stale/renamed spec folder fails with nothing touched — never a half-vendored tree.
for req in \
    v0.3.2-proposed/som-v0.3.2-story-context.schema.json \
    v0.3.2-proposed/som-v0.3.2-telling-event.schema.json \
    v0.3.2-proposed/som-v0.3.2-delivery-media-available.schema.json \
    som_lint.py som_diff.py SCHEMA-TOOLS.md; do
  [ -f "$SRC/$req" ] || { echo "Spec is missing $req — nothing written. Spec folder older than this script?"; exit 1; }
done

OUT="$DST"
if [ "$CHECK" = 1 ]; then
  OUT="$(mktemp -d)"
  trap 'rm -rf "$OUT"' EXIT
fi

echo "Vendoring from: $SRC"
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
cp "$SRC"/v0.3.2-proposed/examples/*.json    "$OUT/v0.3.2-proposed/examples/" 2>/dev/null || true
cp "$SRC"/v0.3.2-proposed/README.md          "$OUT/v0.3.2-proposed/"     2>/dev/null || true
# Schema tools travel with the schemas they check (som_lint checks the schema against its
# own claims; som_diff prices deltas). Existence already asserted by the pre-flight.
cp "$SRC"/som_lint.py "$SRC"/som_diff.py "$SRC"/SCHEMA-TOOLS.md "$OUT"/
ls "$OUT"/v0.3.2-proposed/som-v0.3.2-*.schema.json >/dev/null

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
      -o -name "som_lint.py" -o -name "som_diff.py" -o -name "SCHEMA-TOOLS.md" \
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
