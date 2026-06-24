#!/usr/bin/env bash
# Re-vendor the SOM JSON Schemas from the spec folder (source of truth) into this repo.
# Usage:  bash schema/sync-from-spec.sh            # uses default SOM_SPEC_DIR below
#         SOM_SPEC_DIR=/path/to/SOM bash schema/sync-from-spec.sh
set -euo pipefail

SOM_SPEC_DIR="${SOM_SPEC_DIR:-$HOME/Library/CloudStorage/OneDrive-NBCUniversal/Documents/SOM}"
SRC="$SOM_SPEC_DIR/schema"
DST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ -d "$SRC" ] || { echo "Spec schema folder not found: $SRC"; echo "Set SOM_SPEC_DIR to your SOM spec folder."; exit 1; }

echo "Vendoring from: $SRC"
mkdir -p "$DST/examples" "$DST/v0.3.1-proposed/examples"
cp "$SRC"/som-v0.3-*.schema.json            "$DST"/
cp "$SRC"/examples/*.json                    "$DST/examples/"            2>/dev/null || true
cp "$SRC"/v0.3.1-proposed/*.json             "$DST/v0.3.1-proposed/"     2>/dev/null || true
cp "$SRC"/v0.3.1-proposed/examples/*.json    "$DST/v0.3.1-proposed/examples/" 2>/dev/null || true
cp "$SRC"/v0.3.1-proposed/README.md          "$DST/v0.3.1-proposed/"     2>/dev/null || true

echo "Vendored. Now validate:"
echo "  python3 schema/validate.py"
echo "Then note the sync in docs/SOM-v0.3.1-Migration-Log.md."
