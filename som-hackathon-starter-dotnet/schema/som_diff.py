#!/usr/bin/env python3
"""
som_diff.py — schema delta pricer for the SOM JSON Schema pack.

WHY THIS EXISTS
---------------
When a vendor proposes a change ("add audio_metrics to the Asset", "constrain
relation_type to an enum"), the question that decides it is always the same: what
does this break, and for whom? That arithmetic has been done by hand every time —
and it is easy to get wrong. The relations proposal was priced at "two enum values"
before a careful second pass found four enum values, one new required field, two new
optional fields and two constraint changes.

The cost of a proposal should not depend on how much time the reviewer had that week.

This prices a delta mechanically and classifies every change by who it breaks:

  PRODUCERS  — messages that were valid before are invalid now. The expensive kind.
  CONSUMERS  — a field they read is gone, or an enum grew a value their switch will
               not recognise. Cheap IF the consumer rules say tolerate-and-preserve.
  NOBODY     — relaxations and additive optional fields.

USAGE
-----
    som_diff.py --from 0.3.1 --to 0.3.2 [SCHEMA_DIR]   # version-to-version in a tree
    som_diff.py OLD.schema.json NEW.schema.json        # two files (a proposal)
    som_diff.py OLD_DIR NEW_DIR                        # two packs
    som_diff.py ... --examples DIR                     # also run impact on examples
    som_diff.py ... --markdown                         # emit a sequencing table

Exit 0 = no producer-breaking changes, 1 = at least one. Impact failures also exit 1.
jsonschema is needed only for --examples; the structural diff has no dependencies.
"""

import json
import os
import re
import sys
from collections import defaultdict

# ------------------------------------------------------------------ severity

PRODUCERS = "PRODUCERS"     # previously-valid messages are now rejected
CONSUMERS = "CONSUMERS"     # readers must cope; producers unaffected
NOBODY = "NOBODY"

RANK = {PRODUCERS: 0, CONSUMERS: 1, NOBODY: 2}

changes = []


def note(sev, kind, path, detail, guidance=""):
    changes.append({"sev": sev, "kind": kind, "path": path,
                    "detail": detail, "guidance": guidance})


# ------------------------------------------------------------------ shape map

INTERESTING = ("type", "enum", "const", "pattern", "format", "$ref",
               "additionalProperties", "minimum", "maximum", "minItems",
               "maxItems", "minLength", "maxLength", "dependentRequired")


def shape_map(schema):
    """Flatten a schema to {readable_path: {facet: value}}.

    Paths skip the JSON Schema plumbing ('properties', '$defs') so they read like the
    thing being described — `assets[].status`, `$assertion.target.kind` — which is how
    a reviewer thinks about them.
    """
    out = {}

    def rec(node, path):
        if not isinstance(node, dict):
            return
        facets = {k: node[k] for k in INTERESTING if k in node}
        if facets or "required" in node:
            if "required" in node:
                facets["required"] = sorted(node["required"])
            out.setdefault(path or "<root>", {}).update(facets)

        for name, sub in (node.get("properties") or {}).items():
            rec(sub, f"{path}.{name}" if path else name)
        for name, sub in (node.get("patternProperties") or {}).items():
            rec(sub, f"{path}.{{{name}}}" if path else f"{{{name}}}")
        for name, sub in (node.get("$defs") or {}).items():
            rec(sub, f"${name}")
        if isinstance(node.get("items"), dict):
            rec(node["items"], f"{path}[]")
        for i, sub in enumerate(node.get("prefixItems") or []):
            rec(sub, f"{path}[{i}]")
        if isinstance(node.get("additionalProperties"), dict):
            rec(node["additionalProperties"], f"{path}.{{*}}" if path else "{*}")
        for name, sub in (node.get("dependentSchemas") or {}).items():
            rec(sub, f"{path}|dependentSchemas.{name}")
        for kw in ("anyOf", "oneOf", "allOf"):
            for i, sub in enumerate(node.get(kw) or []):
                rec(sub, f"{path}|{kw}[{i}]")
        for kw in ("if", "then", "else", "not", "contains",
                   "propertyNames", "unevaluatedProperties"):
            if isinstance(node.get(kw), dict):
                rec(node[kw], f"{path}|{kw}")

    rec(schema, "")
    return out


# ------------------------------------------------------------------ combinators
#
# A new subschema under an always-applied combinator (allOf / then / else / not /
# contains) can only NARROW what validates — the opposite of an optional addition.
# Only anyOf / oneOf branches genuinely widen. Without this distinction the DETECTION
# claim constraint (a new allOf[if/then] making claim.detection_class + claim.verdict
# required) priced as "field added — breaks nobody", which is exactly backwards.

NARROWING = ("allOf", "then", "else", "not", "contains",
             "dependentSchemas", "propertyNames", "unevaluatedProperties")
WIDENING = ("anyOf", "oneOf")


def combinator_context(path):
    """The innermost combinator segment a shape path sits inside, or None."""
    last, ctx = -1, None
    for kw in NARROWING + WIDENING + ("if",):
        i = path.rfind(f"|{kw}")
        if i > last:
            last, ctx = i, kw
    return ctx


def host_of(path):
    """The constrained node: everything before the first combinator segment.
    A combinator hanging directly off the schema root ('|allOf[0]|then...')
    constrains the root object itself."""
    i = path.find("|")
    if i < 0:
        return path
    return path[:i] if i > 0 else "<root>"


def host_exists(path, paths):
    """Whether the constrained node is part of the given shape map — a narrowing
    branch inside a brand-new structure is just part of an optional addition; it
    only prices as breaking when it tightens a contract that already existed."""
    h = host_of(path)
    if h == "<root>":
        return True   # both sides of a family diff always have a root object
    return h in paths or any(
        q.startswith(h + ".") or q.startswith(h + "[") or q.startswith(h + "|")
        for q in paths)


# ------------------------------------------------------------------ the rules

def diff_shapes(old, new, label):
    old_paths, new_paths = set(old), set(new)

    for p in sorted(new_paths - old_paths):
        facets = new[p]
        if facets.get("type") is False or facets == {"type": False}:
            continue
        ctx = combinator_context(p)
        if ctx in NARROWING and host_exists(p, old_paths):
            note(PRODUCERS, "narrowing subschema added", f"{label}{p}",
                 f"new: {compact(facets)}",
                 f"A new subschema under `{ctx}` can only narrow what validates. "
                 "Messages valid before may be rejected now — price it like a new "
                 "required field, not an optional addition.")
        elif ctx == "if" and host_exists(p, old_paths):
            note(NOBODY, "condition subschema added", f"{label}{p}",
                 f"new: {compact(facets)}",
                 "Condition for a conditional constraint — the bite is in the "
                 "matching then/else branch, reported separately.")
        else:
            note(NOBODY, "field added", f"{label}{p}",
                 f"new: {compact(facets)}",
                 "Optional additions break nobody. Confirm it is genuinely optional.")

    for p in sorted(old_paths - new_paths):
        ctx = combinator_context(p)
        if ctx in WIDENING and host_exists(p, new_paths):
            note(PRODUCERS, "alternative removed", f"{label}{p}",
                 f"was: {compact(old[p])}",
                 f"A `{ctx}` branch is gone — producers relying on that alternative "
                 "are now invalid.")
        elif (ctx in NARROWING or ctx == "if") and host_exists(p, new_paths):
            note(NOBODY, "narrowing subschema removed", f"{label}{p}",
                 f"was: {compact(old[p])}",
                 "Removing a narrowing subschema relaxes validation. Breaks nobody.")
        else:
            note(CONSUMERS, "field removed", f"{label}{p}",
                 f"was: {compact(old[p])}",
                 "Consumers reading this field get nothing. Producers are unaffected "
                 "unless it was required — checked separately below.")

    for p in sorted(old_paths & new_paths):
        a, b = old[p], new[p]

        # ---- required set
        ra, rb = set(a.get("required") or []), set(b.get("required") or [])
        for f in sorted(rb - ra):
            note(PRODUCERS, "new required field", f"{label}{p}",
                 f"`{f}` is now required",
                 "Every previously-valid message lacking this field is now invalid. "
                 "The most expensive change shape there is.")
        for f in sorted(ra - rb):
            note(NOBODY, "required relaxed", f"{label}{p}",
                 f"`{f}` no longer required")

        # ---- dependentRequired ("if you carry X you must also carry Y")
        da, db = a.get("dependentRequired") or {}, b.get("dependentRequired") or {}
        if da != db:
            for k in sorted(db):
                extra = sorted(set(db[k]) - set(da.get(k, [])))
                if extra:
                    note(PRODUCERS, "dependent requirement added", f"{label}{p}",
                         f"carrying `{k}` now also requires {extra}",
                         "Previously-valid messages carrying the trigger field "
                         "without its new companions are invalid now.")
            for k in sorted(da):
                dropped = sorted(set(da[k]) - set(db.get(k, [])))
                if dropped:
                    note(NOBODY, "dependent requirement relaxed", f"{label}{p}",
                         f"`{k}` no longer requires {dropped}")

        # ---- enums
        ea, eb = a.get("enum"), b.get("enum")
        if isinstance(ea, list) and isinstance(eb, list) and ea != eb:
            sa, sb = set(map(str, ea)), set(map(str, eb))
            for v in sorted(sa - sb):
                note(PRODUCERS, "enum value removed", f"{label}{p}",
                     f"`{v}` removed",
                     "Producers still emitting this value are now invalid. Needs a "
                     "migration map, not just a removal.")
            for v in sorted(sb - sa):
                note(CONSUMERS, "enum value added", f"{label}{p}",
                     f"`{v}` added",
                     "Producers unaffected. Consumers with a strict switch and no "
                     "default branch will fall through — which is what the "
                     "must-ignore/must-preserve rule exists to cover.")
        elif isinstance(eb, list) and ea is None and "enum" not in a:
            if a.get("type") == "string":
                note(PRODUCERS, "free string constrained to enum", f"{label}{p}",
                     f"now one of {eb}",
                     "Any value outside the set is now invalid. Cheap ONLY while the "
                     "field has no producers — which is the argument for doing it early.")
        elif isinstance(ea, list) and "enum" not in b:
            note(NOBODY, "enum relaxed to free value", f"{label}{p}",
                 f"was one of {ea}")

        # ---- additionalProperties
        aa, ab = a.get("additionalProperties"), b.get("additionalProperties")
        if aa != ab and (aa is not None or ab is not None):
            if ab is False and aa is not False:
                note(PRODUCERS, "additionalProperties closed", f"{label}{p}",
                     "true/absent -> false",
                     "Any message carrying an extra key is now rejected. Check whether "
                     "vendors are using extras here as an extension point.")
            elif ab is True and aa is False:
                note(NOBODY, "additionalProperties opened", f"{label}{p}",
                     "false -> true")

        # ---- type
        ta, tb = a.get("type"), b.get("type")
        if ta != tb and (ta is not None and tb is not None):
            note(PRODUCERS, "type changed", f"{label}{p}", f"{ta} -> {tb}",
                 "Breaks producers and consumers together. Almost always wants a new "
                 "field rather than a changed one.")

        # ---- constraints
        for facet, tighter in (("pattern", None), ("format", None),
                               ("minimum", "raise"), ("maximum", "lower"),
                               ("minLength", "raise"), ("maxLength", "lower"),
                               ("minItems", "raise"), ("maxItems", "lower")):
            va, vb = a.get(facet), b.get(facet)
            if va == vb:
                continue
            if va is None and vb is not None:
                note(PRODUCERS, "constraint added", f"{label}{p}",
                     f"{facet} = {vb!r}",
                     "Previously-valid values may now fail.")
            elif va is not None and vb is None:
                note(NOBODY, "constraint removed", f"{label}{p}", f"{facet} was {va!r}")
            else:
                sev = PRODUCERS
                if tighter == "raise" and isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    sev = PRODUCERS if vb > va else NOBODY
                elif tighter == "lower" and isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                    sev = PRODUCERS if vb < va else NOBODY
                note(sev, "constraint changed", f"{label}{p}",
                     f"{facet}: {va!r} -> {vb!r}")

        # ---- hard rejections (property: false)
        if a.get("type") is not False and b.get("type") is False:
            note(PRODUCERS, "hard-rejected", f"{label}{p}", "now rejected outright")


def parents(path):
    """Ancestor paths of a shape path, outermost last."""
    out = []
    cur = path
    while True:
        cut = max(cur.rfind("."), cur.rfind("|"))
        if cur.endswith("[]"):
            cur = cur[:-2]
        elif cut > 0:
            cur = cur[:cut]
        else:
            break
        if cur and cur not in out:
            out.append(cur)
    return out


ADD_KINDS = ("field added", "narrowing subschema added", "condition subschema added")
REMOVE_KINDS = ("field removed", "alternative removed", "narrowing subschema removed")


def rollup():
    """Collapse subtree noise: if a whole object was added or removed, its children
    are not separate findings — they are the same finding, and listing 40 of them
    buries the one line that matters. A child never folds into a LESS severe parent:
    a PRODUCERS finding buried inside a NOBODY parent would vanish from the count
    that gates CI."""
    global changes
    added = {c["path"]: c["sev"] for c in changes if c["kind"] in ADD_KINDS}
    removed = {c["path"]: c["sev"] for c in changes if c["kind"] in REMOVE_KINDS}
    kept, folded = [], defaultdict(int)
    for c in changes:
        parent_map = added if c["kind"] in ADD_KINDS else removed if c["kind"] in REMOVE_KINDS else None
        if parent_map is not None:
            tops = [p for p in parents(c["path"])
                    if p in parent_map and RANK[parent_map[p]] <= RANK[c["sev"]]]
            if tops:
                folded[tops[0]] += 1
                continue
        kept.append(c)
    for c in kept:
        n = folded.get(c["path"], 0)
        if n:
            c["detail"] += f"  (+{n} field(s) beneath it, folded)"
    changes = kept


def compact(facets):
    bits = []
    for k in ("type", "$ref", "enum", "const", "format", "pattern",
              "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems"):
        if k in facets:
            v = facets[k]
            if isinstance(v, list) and len(v) > 6:
                v = v[:6] + ["..."]
            bits.append(f"{k}={v}")
    if facets.get("required"):
        bits.append(f"required={facets['required']}")
    return ", ".join(bits) or "(no constraints)"


# ------------------------------------------------------------------ tombstones

def find_tombstones(schema):
    """Properties written as `false` — the hard-rejection idiom this pack uses."""
    out = set()

    def rec(node, path):
        if not isinstance(node, dict):
            return
        for name, sub in (node.get("properties") or {}).items():
            p = f"{path}.{name}" if path else name
            if sub is False:
                out.add(p)
            else:
                rec(sub, p)
        for name, sub in (node.get("$defs") or {}).items():
            rec(sub, f"${name}")
        if isinstance(node.get("items"), dict):
            rec(node["items"], f"{path}[]")

    rec(schema, "")
    return out


# ------------------------------------------------------------------ discovery

def family_of(path):
    m = re.match(r"som-v[\d.]+-(.+)\.schema\.json", os.path.basename(path))
    return m.group(1) if m else os.path.basename(path)


def version_of(path):
    m = re.search(r"v(\d+\.\d+(?:\.\d+)?)-proposed", path)
    if m:
        return m.group(1)
    m = re.search(r"som-v(\d+\.\d+(?:\.\d+)?)-", os.path.basename(path))
    return m.group(1) if m else None


def vkey(v):
    return tuple(int(x) for x in v.split("."))


def effective_pack(root, target):
    """Files a consumer of `target` actually reads: the target's own files plus any
    family it inherits unchanged from an earlier version."""
    best = {}
    for dirpath, _d, files in os.walk(root):
        if "examples" in dirpath.split(os.sep):
            continue
        for fn in sorted(files):
            if not fn.endswith(".schema.json"):
                continue
            full = os.path.join(dirpath, fn)
            v = version_of(os.path.relpath(full, root))
            if not v or vkey(v) > vkey(target):
                continue
            fam = family_of(fn)
            if fam not in best or vkey(version_of(best[fam])) < vkey(v):
                best[fam] = full
    return best


def load(p):
    return json.load(open(p, encoding="utf-8"))


# ------------------------------------------------------------------ impact

def run_impact(new_files, examples_dir):
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("  (jsonschema not installed — skipping impact run)\n")
        return 0, 0

    schemas = {fam: load(p) for fam, p in new_files.items()}
    payloads = []
    for dirpath, _d, files in os.walk(examples_dir):
        for fn in sorted(files):
            if fn.endswith(".json"):
                full = os.path.join(dirpath, fn)
                try:
                    payloads.append((full, load(full)))
                except json.JSONDecodeError:
                    pass

    failed = 0
    checked = 0
    for path, doc in payloads:
        rel = os.path.relpath(path, examples_dir)
        legs = []
        if is_envelope(doc):
            # A wire message: check the envelope AND the payload it wraps. Checking only
            # one leg is how a message that passes review still fails on the bus.
            env_fam = next((f for f in schemas if "envelope" in f), None)
            if env_fam:
                legs.append((env_fam, doc, "envelope"))
            inner = doc.get("payload")
            if isinstance(inner, dict):
                fam = guess_family(inner, schemas)
                if fam:
                    legs.append((fam, inner, "payload"))
        else:
            fam = guess_family(doc, schemas)
            if fam:
                legs.append((fam, doc, ""))

        if not legs:
            continue
        checked += 1
        bad = []
        for fam, obj, leg in legs:
            errs = list(Draft202012Validator(schemas[fam]).iter_errors(obj))
            if errs:
                bad.append((fam, leg, errs))
        tag = " + ".join(f"{fam}{'/' + leg if leg else ''}" for fam, _o, leg in legs)
        if bad:
            failed += 1
            print(f"  [FAIL] {rel}  (vs {tag})")
            for fam, leg, errs in bad:
                for e in errs[:3]:
                    loc = "/".join(str(x) for x in e.absolute_path) or "<root>"
                    print(f"         {leg or fam} {loc}: {e.message[:100]}")
        else:
            print(f"  [ok]   {rel}  (vs {tag})")
    return checked, failed


def is_envelope(doc):
    return isinstance(doc, dict) and "payload" in doc and (
        "message_id" in doc or "originating_system" in doc)


def guess_family(payload, schemas):
    mt = payload.get("message_type")
    if isinstance(mt, str):
        for fam in schemas:
            if fam.replace("-", ".").replace("media.available", "media_available") in mt:
                return fam
        if mt.startswith("delivery."):
            return next((f for f in schemas if "delivery" in f), None)
        if mt.startswith("telling."):
            return next((f for f in schemas if "telling" in f), None)
        if mt.startswith("link."):
            return next((f for f in schemas if "link" in f), None)
    if "story_id" in payload and "story_type" in payload:
        return next((f for f in schemas if "story-context" in f), None)
    if "audit_id" in payload:
        return next((f for f in schemas if "system-audit" in f), None)
    if "warning_id" in payload:
        return next((f for f in schemas if "skill-warning" in f), None)
    return None


# ------------------------------------------------------------------ output

def emit_markdown():
    print("\n### Sequencing table\n")
    print("| # | Change | Path | Breaks | Detail |")
    print("|---|---|---|---|---|")
    for i, c in enumerate(sorted(changes, key=lambda x: (RANK[x["sev"]], x["kind"])), 1):
        d = c["detail"].replace("|", "\\|")
        print(f"| S{i} | {c['kind']} | `{c['path']}` | **{c['sev']}** | {d} |")
    print()


def main():
    args = sys.argv[1:]
    markdown = "--markdown" in args
    examples = None
    if "--examples" in args:
        examples = args[args.index("--examples") + 1]
    frm = args[args.index("--from") + 1] if "--from" in args else None
    to = args[args.index("--to") + 1] if "--to" in args else None
    pos = [a for i, a in enumerate(args)
           if not a.startswith("--")
           and (i == 0 or args[i - 1] not in ("--from", "--to", "--examples"))]

    old_files, new_files = {}, {}

    if frm and to:
        root = pos[0] if pos else os.path.dirname(os.path.abspath(__file__))
        old_files = effective_pack(root, frm)
        new_files = effective_pack(root, to)
        title = f"effective pack v{frm}  ->  v{to}"
    elif len(pos) == 2 and all(os.path.isfile(p) for p in pos):
        old_files = {family_of(pos[0]): pos[0]}
        new_files = {family_of(pos[1]): pos[1]}
        title = f"{os.path.basename(pos[0])}  ->  {os.path.basename(pos[1])}"
    elif len(pos) == 2 and all(os.path.isdir(p) for p in pos):
        for d, store in ((pos[0], old_files), (pos[1], new_files)):
            for dirpath, _x, files in os.walk(d):
                for fn in files:
                    if fn.endswith(".schema.json"):
                        store[family_of(fn)] = os.path.join(dirpath, fn)
        title = f"{pos[0]}  ->  {pos[1]}"
    else:
        print(__doc__)
        return 2

    print(f"som_diff — {title}\n")

    for fam in sorted(set(old_files) | set(new_files)):
        if fam not in old_files:
            note(NOBODY, "family added", fam, "new message family")
            continue
        if fam not in new_files:
            note(PRODUCERS, "family removed", fam, "message family gone")
            continue
        a, b = load(old_files[fam]), load(new_files[fam])
        if old_files[fam] == new_files[fam]:
            continue
        diff_shapes(shape_map(a), shape_map(b), f"{fam}::")
        for t in sorted(find_tombstones(b) - find_tombstones(a)):
            note(PRODUCERS, "hard-rejected", f"{fam}::{t}",
                 "now rejected outright",
                 "Every message still carrying it is invalid. This is the shape that "
                 "needs a migration note, not just a changelog line.")

    rollup()

    buckets = defaultdict(list)
    for c in changes:
        buckets[c["sev"]].append(c)

    for sev in (PRODUCERS, CONSUMERS, NOBODY):
        items = buckets[sev]
        if not items:
            continue
        head = {PRODUCERS: "BREAKING FOR PRODUCERS",
                CONSUMERS: "BREAKING FOR STRICT CONSUMERS",
                NOBODY: "NON-BREAKING"}[sev]
        print(f"{head}  ({len(items)})")
        print("-" * (len(head) + 8))
        seen_guidance = set()
        for c in sorted(items, key=lambda x: x["kind"]):
            print(f"  {c['kind']:32} {c['path']}")
            print(f"  {'':32} {c['detail']}")
            if c["guidance"] and c["kind"] not in seen_guidance:
                seen_guidance.add(c["kind"])
                for line in wrap(c["guidance"], 74):
                    print(f"  {'':32} > {line}")
            print()
        print()

    n_break = len(buckets[PRODUCERS])
    print(f"{n_break} producer-breaking · {len(buckets[CONSUMERS])} consumer-affecting "
          f"· {len(buckets[NOBODY])} non-breaking")

    impact_failed = 0
    if examples:
        print(f"\nIMPACT — every example under {examples} against the NEW schemas\n")
        checked, impact_failed = run_impact(new_files, examples)
        print(f"\n  {checked - impact_failed}/{checked} still validate; {impact_failed} now fail")

    if markdown:
        emit_markdown()

    return 1 if (n_break or impact_failed) else 0


def wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
