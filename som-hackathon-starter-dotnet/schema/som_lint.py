#!/usr/bin/env python3
"""
som_lint.py — schema self-consistency linter for the SOM JSON Schema pack.

WHY THIS EXISTS
---------------
`validate.py` checks MESSAGES against the SCHEMA. Nothing checked the SCHEMA against
its own claims — and that is where two real bugs lived:

  * `assertion.target` was described as "reuses the audit target set" while its enum
    carried STORY, which that set does not have. The description was false as shipped.
  * The ORPHAN lifecycle promised an "asset-targeted som.system.audit records the
    association change" that the action vocabulary (CLEARED/SUPPRESSED/WITHHELD/
    OVERRIDDEN) cannot express.

Both passed 22/22 message validation. Descriptions are load-bearing in this project —
vendors build from them — so they need checking too.

USAGE
-----
    python3 som_lint.py [SCHEMA_DIR]      # default: this file's directory
    python3 som_lint.py --strict          # WARN counts as failure (for CI)

Exit code 0 = clean, 1 = at least one ERROR (or WARN under --strict).
No third-party dependencies. Python 3.8+.
"""

import json
import os
import re
import sys
from collections import defaultdict

# ---------------------------------------------------------------- config

# Words that look like snake_case fields in prose but are not fields.
PROSE_STOPWORDS = {
    "e_g", "i_e", "et_al", "read_only", "write_only", "per_story", "per_asset",
    "single_writer", "owner_only", "snake_case", "upper_snake_case", "date_time",
    "additional_properties", "non_tams", "sha256", "utf_8", "json_schema",
    "story_object_model", "must_not", "should_not", "content_type",
}

# UPPER_SNAKE tokens in prose that are not enum values.
ENUMLIKE_STOPWORDS = {
    "MUST", "MUST_NOT", "SHOULD", "SHOULD_NOT", "MAY", "NOT", "AND", "OR",
    "ALWAYS", "NEVER", "ONLY", "TODO", "TBD", "NOTE", "YES", "NO", "OPEN",
    "DEPRECATED", "PROPOSED", "REQUIRED", "OPTIONAL", "NORMATIVE", "TAMS",
    "SOM", "JSON", "UUID", "URI", "URL", "API", "UTC", "MOS", "NRCS", "MAM",
    "UGC", "AI", "ID", "IDS", "PR", "WG", "IBC", "BBC", "ITV", "NBCU", "AWS",
    "GCP", "CI", "HTTP", "HTTPS", "MOVES", "NEW", "OLD", "ONE", "TWO", "SOM_048",
}

# Phrases that assert one construct reuses/mirrors another. These are the claims
# that go stale silently — the assertion.target bug was exactly this shape.
REUSE_PATTERNS = [
    r"reuses? the ([a-z][\w .\-]{2,40}?) (?:set|vocabulary|enum)",
    r"mirrors? ([a-z][\w .\-\[\]]{2,40})",
    r"same (?:as|shape as) ([a-z][\w .\-\[\]]{2,40})",
    r"reusing the ([a-z][\w .\-]{2,40}?) (?:set|vocabulary|enum)",
]

# References to another message family inside a description. Each is a cross-family
# promise that the other family has to be able to honour.
FAMILY_REF = re.compile(r"\b(som\.[a-z_.]+|[a-z_]+\.[a-z_]+\.(?:raised|available|completed|started|ended|exposed))\b")

SNAKE_IN_PROSE = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`")
UPPER_IN_PROSE = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*)\b")
STATUS_WORDS = re.compile(
    r"(?:\b(?:is|are|remains?|stays?)\s+)?\b(PROPOSED|DRAFT|TBD|UNCONFIRMED)\b"
    r"|\bdo not build\b"
)  # case-SENSITIVE: the status marker is upper-case; "a proposed match" is ordinary prose

findings = []


def add(level, rule, where, msg, detail=""):
    findings.append((level, rule, where, msg, detail))


# ---------------------------------------------------------------- loading

def load_pack(root):
    """Every *.schema.json under root, keyed by path relative to root."""
    pack = {}
    for dirpath, _dirs, files in os.walk(root):
        if "examples" in dirpath.split(os.sep):
            continue
        for fn in sorted(files):
            if fn.endswith(".schema.json"):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root)
                try:
                    pack[rel] = json.load(open(full, encoding="utf-8"))
                except json.JSONDecodeError as e:
                    add("ERROR", "L0-parse", rel, f"does not parse: {e}")
    return pack


def walk(node, path="", file=""):
    """Yield (json_path, node) for every dict in the schema."""
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k, file)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]", file)


def index_pack(pack):
    """Collect every property name, every enum, and every description in the pack."""
    props, enums, descs = set(), {}, []
    for rel, schema in pack.items():
        for jpath, node in walk(schema, file=rel):
            if not isinstance(node, dict):
                continue
            if jpath.endswith("properties") or ".properties" in jpath.rsplit(".", 1)[-1:]:
                pass
            # property names
            if isinstance(node.get("properties"), dict):
                props.update(node["properties"].keys())
            # enums
            if isinstance(node.get("enum"), list):
                enums[f"{rel}::{jpath}"] = node["enum"]
            # descriptions
            if isinstance(node.get("description"), str):
                descs.append((rel, jpath, node["description"]))
    return props, enums, descs


# ---------------------------------------------------------------- rules

def l1_refs_resolve(pack):
    """Every internal $ref points at something that exists."""
    for rel, schema in pack.items():
        defs = schema.get("$defs", {})
        for jpath, node in walk(schema):
            ref = node.get("$ref") if isinstance(node, dict) else None
            if not isinstance(ref, str):
                continue
            if ref.startswith("#/$defs/"):
                name = ref[len("#/$defs/"):]
                if name not in defs:
                    add("ERROR", "L1-ref", f"{rel} @ {jpath}",
                        f"$ref '{ref}' does not resolve", f"known $defs: {sorted(defs)[:8]}")
            elif ref.startswith("#"):
                add("WARN", "L1-ref", f"{rel} @ {jpath}",
                    f"non-$defs internal $ref '{ref}' not checked")


def schema_version(rel):
    """Which pack generation a file belongs to. Cross-version differences are
    expected (that IS the delta); same-version differences are the suspicious kind."""
    m = re.search(r"v(\d+\.\d+(?:\.\d+)?)-proposed", rel)
    if m:
        return m.group(1)
    m = re.search(r"som-v(\d+\.\d+(?:\.\d+)?)-", os.path.basename(rel))
    return m.group(1) if m else "?"


# message_type is family-specific by definition — link.* and telling.* SHOULD differ.
L2_SLOT_DENYLIST = {"message_type"}


def family_of(rel):
    m = re.match(r"som-v[\d.]+-(.+)\.schema\.json", os.path.basename(rel))
    return m.group(1) if m else os.path.basename(rel)


def effective_pack(versions, target):
    """The files a consumer of version `target` actually reads.

    v0.3.2 changed only three families; link-event and system-audit are unchanged and
    remain authoritative in v0.3.1-proposed/. So the v0.3.2 EFFECTIVE pack is the v0.3.2
    files plus the v0.3.1 files it inherits — which is why assertion.target (v0.3.2) and
    audit target.kind (v0.3.1) sit side by side in one contract.
    """
    def key(v):
        return tuple(int(x) for x in v.split(".")) if v != "?" else (0,)
    chosen = {}
    for rel, ver in versions.items():
        if ver == "?" or key(ver) > key(target):
            continue
        fam = family_of(rel)
        if fam not in chosen or key(versions[chosen[fam]]) < key(ver):
            chosen[fam] = rel
    return set(chosen.values())


def l2_enum_divergence(enums, versions):
    """Enums at the same slot inside one EFFECTIVE pack carrying different value sets."""
    slots = defaultdict(list)
    for key_, vals in enums.items():
        rel, jpath = key_.split("::", 1)
        parts = [p for p in jpath.split(".") if p not in ("properties", "items", "enum", "$defs")]
        parts = [p for p in parts if not re.fullmatch(r"(anyOf|oneOf|allOf)\[\d+\]", p)]
        slot = ".".join(parts[-2:]) if len(parts) >= 2 else (parts[-1] if parts else jpath)
        slots[slot].append((rel, tuple(vals)))

    seen = set()
    for target in sorted({v for v in versions.values() if v != "?"}):
        eff = effective_pack(versions, target)
        for slot, entries in sorted(slots.items()):
            if slot.split(".")[-1] in L2_SLOT_DENYLIST:
                continue
            here = [(rel, vals) for rel, vals in entries if rel in eff]
            variants = {}
            for rel, vals in here:
                variants.setdefault(vals, []).append(rel)
            if len(variants) < 2:
                continue
            sig = (slot, tuple(sorted(variants)))
            if sig in seen:
                continue
            seen.add(sig)
            lines = []
            for vals, rels in variants.items():
                lines.append(f"    {sorted(set(os.path.basename(r) for r in rels))}: {list(vals)}")
            sets = [set(v) for v in variants]
            if len(sets) == 2:
                a, b = sets
                if a < b or b < a:
                    big, small = (b, a) if a < b else (a, b)
                    lines.append(f"    one is a strict superset of the other; extra: {sorted(big - small)}")
                else:
                    lines.append(f"    neither contains the other; only in one: {sorted(a ^ b)}")
            add("WARN", "L2-enum-divergence", f"effective pack v{target} :: {slot}",
                f"same slot carries {len(variants)} different value sets inside one contract",
                "\n".join(lines))


def l3_reuse_claims(descs, enums):
    """Descriptions asserting they reuse/mirror another construct."""
    for rel, jpath, text in descs:
        for pat in REUSE_PATTERNS:
            for m in re.finditer(pat, text, re.I):
                target = m.group(1).strip().rstrip(".,;")
                add("WARN", "L3-reuse-claim", f"{rel} @ {jpath}",
                    f'claims to reuse/mirror "{target}" — verify the two still match',
                    f"    ...{text[max(0, m.start()-40):m.end()+40].strip()}...")


def l4_cross_family_promises(descs, pack):
    """Descriptions that promise behaviour in another message family."""
    families = set()
    for rel in pack:
        base = os.path.basename(rel)
        m = re.match(r"som-v[\d.]+-(.+)\.schema\.json", base)
        if m:
            families.add(m.group(1))
    for rel, jpath, text in descs:
        own = os.path.basename(rel)
        for m in FAMILY_REF.finditer(text):
            fam = m.group(1)
            key = fam.replace("som.", "").replace(".", "-")
            if key.replace("system-audit", "system-audit") in own:
                continue
            add("INFO", "L4-cross-family", f"{rel} @ {jpath}",
                f"references '{fam}' — confirm that family can express what is claimed",
                f"    ...{text[max(0, m.start()-70):m.end()+70].strip()}...")


def l5_prose_fields(descs, props):
    """Backticked snake_case in prose that is not a property anywhere in the pack."""
    for rel, jpath, text in descs:
        for m in SNAKE_IN_PROSE.finditer(text):
            tok = m.group(1)
            if tok in PROSE_STOPWORDS or tok in props:
                continue
            add("WARN", "L5-unknown-field", f"{rel} @ {jpath}",
                f"prose names `{tok}` — not a property anywhere in the pack",
                f"    ...{text[max(0, m.start()-50):m.end()+50].strip()}...")


def l6_prose_enum_values(descs, enums):
    """UPPER_SNAKE in prose that is not a value in any enum in the pack."""
    known = set()
    for vals in enums.values():
        known.update(str(v) for v in vals)
    for rel, jpath, text in descs:
        for m in UPPER_IN_PROSE.finditer(text):
            tok = m.group(1)
            if tok in ENUMLIKE_STOPWORDS or tok in known or len(tok) < 4:
                continue
            # emphasis, not an enum value: a single all-caps word with no underscore
            # sitting mid-sentence (SYMMETRY, MOVES, ALWAYS...)
            if "_" not in tok and tok.isalpha() and tok.title() in text:
                continue
            if not re.search(r"[A-Z]{2,}", tok):
                continue
            add("INFO", "L6-unknown-enum-value", f"{rel} @ {jpath}",
                f"prose names {tok} — not a value in any enum in the pack",
                f"    ...{text[max(0, m.start()-50):m.end()+50].strip()}...")


def l7_status_drift(pack, descs):
    """A construct described as PROPOSED/DRAFT while the file header says it ships."""
    for rel, schema in pack.items():
        top = schema.get("description", "") or ""
        ships = bool(re.search(r"\bships\b|is the IBC target|resolved in this pack", top, re.I))
        if not ships:
            continue
        for drel, jpath, text in descs:
            if drel != rel or jpath == "":
                continue
            m = STATUS_WORDS.search(text)
            if m:
                add("WARN", "L7-status-drift", f"{rel} @ {jpath}",
                    f'says "{m.group(1)}" while the file header says this pack ships',
                    f"    ...{text[max(0, m.start()-60):m.end()+60].strip()}...")


def l8_required_documented(pack):
    """Required fields carrying no description at all."""
    for rel, schema in pack.items():
        for jpath, node in walk(schema):
            if not isinstance(node, dict):
                continue
            req = node.get("required")
            props = node.get("properties")
            if not isinstance(req, list) or not isinstance(props, dict):
                continue
            for name in req:
                sub = props.get(name)
                if isinstance(sub, dict) and not sub.get("description") and "$ref" not in sub:
                    add("INFO", "L8-undocumented-required", f"{rel} @ {jpath}",
                        f"required field `{name}` has no description")


# ---------------------------------------------------------------- main

def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    strict = "--strict" in sys.argv
    pedantic = "--pedantic" in sys.argv
    show_info = pedantic or "--info" in sys.argv
    root = argv[0] if argv else os.path.dirname(os.path.abspath(__file__))

    pack = load_pack(root)
    if not pack:
        print(f"no *.schema.json found under {root}", file=sys.stderr)
        return 2

    props, enums, descs = index_pack(pack)

    l1_refs_resolve(pack)
    versions = {rel: schema_version(rel) for rel in pack}
    l2_enum_divergence(enums, versions)
    l3_reuse_claims(descs, enums)
    l4_cross_family_promises(descs, pack)
    l5_prose_fields(descs, props)
    l6_prose_enum_values(descs, enums)
    l7_status_drift(pack, descs)
    if pedantic:
        l8_required_documented(pack)

    print(f"som_lint — {len(pack)} schema files · {len(props)} property names · "
          f"{len(enums)} enums · {len(descs)} descriptions\n")

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    counts = defaultdict(int)
    for level, rule, where, msg, detail in sorted(findings, key=lambda f: (order[f[0]], f[1])):
        counts[level] += 1
        if level == 'INFO' and not show_info:
            continue
        print(f"[{level:5}] {rule:24} {where}")
        print(f"          {msg}")
        if detail:
            for line in detail.splitlines():
                print(f"          {line}")
        print()

    hidden = "" if show_info else "  (--info to show notes)"
    print(f"{counts['ERROR']} error(s) · {counts['WARN']} warning(s) · {counts['INFO']} note(s){hidden}")
    if counts["ERROR"] or (strict and counts["WARN"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
