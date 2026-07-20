#!/usr/bin/env python3
"""
Validate this repo's SOM JSON against the VENDORED schemas in this folder.

Checks: seed-stories/*.json, schema/examples/*.json, schema/v0.3.1-proposed/examples/*.json,
and mos-bridge/samples/*.expected.json — envelope + the right payload schema for each.

Run:  python3 schema/validate.py        (exits non-zero on any failure)
Requires: pip install jsonschema
"""
import json, sys, glob, os

try:
    from jsonschema.validators import validator_for
except ImportError:
    sys.exit("pip install jsonschema first")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo/som-hackathon-starter-dotnet
SCH  = os.path.join(ROOT, "schema")
def load(p): return json.load(open(p))

ENV   = load(os.path.join(SCH, "som-v0.3-envelope.schema.json"))
STORY = load(os.path.join(SCH, "som-v0.3-story-context.schema.json"))
WARN  = load(os.path.join(SCH, "som-v0.3-skill-warning.schema.json"))
# v0.3.1-proposed (PENDING the 30 June lock — used for distribution + the story-context point update)
P = os.path.join(SCH, "v0.3.1-proposed")
STORY31 = load(os.path.join(P, "som-v0.3.1-story-context.schema.json"))
LINK    = load(os.path.join(P, "som-v0.3.1-link-event.schema.json"))
TELL    = load(os.path.join(P, "som-v0.3.1-telling-event.schema.json"))
DELIV   = load(os.path.join(P, "som-v0.3.1-delivery-media-available.schema.json"))
AUDIT   = load(os.path.join(P, "som-v0.3.1-system-audit.schema.json"))

# Payload schema by message_type. Seeds are v0.3.1-shaped → use the point-update story-context.
BY_TYPE = {
    "story.context": STORY31,
    "skill.warning.raised": WARN,
    "link.committed": LINK, "link.gate_changed": LINK, "link.withdrawn": LINK,
    "telling.started": TELL, "telling.ended": TELL, "telling.exposed": TELL,
    "delivery.media_available": DELIV,
    "system.audit": AUDIT,
}

def errs(schema, inst):
    V = validator_for(schema)
    return sorted(V(schema).iter_errors(inst), key=str)

def payload_schema(d, path, released_story):
    """Pick the payload schema from message_type, then shape, then filename."""
    name = os.path.basename(path).lower()
    mt = d.get("message_type")
    if mt in BY_TYPE:
        return STORY if (released_story and mt == "story.context") else BY_TYPE[mt]
    if "skill-warning" in name or "warning_id" in d:           return WARN
    if "audit" in name or "audit_id" in d:                      return AUDIT
    if "link" in name:                                          return LINK
    if "telling" in name:                                       return TELL
    if "delivery" in name:                                      return DELIV
    if "story" in name or ("story_id" in d and "slug" in d):    return STORY if released_story else STORY31
    return None

def check_message(path, *, released_story=False):
    """Validate either a full envelope (envelope + payload) or a bare payload fixture."""
    d = load(path)
    if isinstance(d, dict) and "payload" in d and "som_version" in d:   # full envelope
        sch = payload_schema(d, path, released_story)
        return errs(ENV, d) + (errs(sch, d["payload"]) if sch else [])
    sch = payload_schema(d, path, released_story)                        # bare payload fixture
    return errs(sch, d) if sch else [type("E", (), {"message": "no schema matched"})()]

def main():
    # (glob_dir, min_expected) — a deleted fixture directory must FAIL, not read as "all valid".
    groups = [
        (glob.glob(os.path.join(ROOT, "seed-stories", "*.json")), {}, 5, "seed-stories"),
        (glob.glob(os.path.join(SCH, "examples", "*.json")), {"released_story": True}, 1, "schema/examples"),
        (glob.glob(os.path.join(P, "examples", "*.json")), {}, 5, "v0.3.1-proposed/examples"),
        (glob.glob(os.path.join(ROOT, "mos-bridge", "samples", "*.expected.json")), {}, 1, "mos-bridge fixtures"),
    ]
    targets = []
    for files, opts, minimum, label in groups:
        if len(files) < minimum:
            print(f"FATAL: expected at least {minimum} fixture(s) in {label}, found {len(files)} — glob broken or files deleted")
            sys.exit(1)
        targets += [(f, opts) for f in files]

    bad = 0
    for path, opts in sorted(targets):
        rel = os.path.relpath(path, ROOT)
        es = check_message(path, **opts)
        if es:
            bad += 1
            print(f"FAIL  {rel}")
            for x in es[:4]:
                print("        -", x.message[:120])
        else:
            print(f"PASS  {rel}")
    print(f"\n{'OK — all valid' if not bad else f'{bad} file(s) FAILED'}")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
