#!/usr/bin/env python3
"""
validate_sequence.py — is a STORY OVER TIME coherent?

The third question. `validate.py` asks whether a message is valid. `som_lint.py` asks
whether the schema agrees with itself. This asks whether a sequence of snapshots of the
same story holds together — which no single payload can answer, and which is where the
expensive bugs have actually been:

  * a wire feed minting a fresh story_id for every revision, so a category upgrade
    arrived as a second story instead of the next snapshot
  * a republish that never re-stamped originating_system, so a correction was
    attributed to whoever first minted the story
  * snapshot-not-delta violations, where a writer omits what it did not touch and
    silently erases another system's work

USAGE
-----
    validate_sequence.py DIR                  # every *.json in DIR, sorted by name
    validate_sequence.py a.json b.json c.json # explicit order
    validate_sequence.py DIR --schema PATH    # override schema discovery
    validate_sequence.py DIR --strict         # warnings fail too (CI)
    validate_sequence.py DIR --envelopes      # inputs are wire messages, not payloads

Exit 0 = coherent, 1 = at least one error (or warning under --strict).
Needs jsonschema>=4.20.
"""

import glob
import json
import os
import sys

try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.exit("validate_sequence.py needs jsonschema>=4.20 — pip install 'jsonschema>=4.20'")

HERE = os.path.dirname(os.path.abspath(__file__))

errors, warnings = [], []


def err(where, msg, detail=""):
    errors.append((where, msg, detail))


def warn(where, msg, detail=""):
    warnings.append((where, msg, detail))


# ------------------------------------------------------------------ discovery

def find_schema(explicit=None):
    if explicit:
        return explicit
    for cand in (
        os.path.join(HERE, "v0.3.2-proposed", "som-v0.3.2-story-context.schema.json"),
        os.path.join(HERE, "som-v0.3.2-story-context.schema.json"),
        os.path.join(HERE, "..", "v0.3.2-proposed", "som-v0.3.2-story-context.schema.json"),
        os.path.join(HERE, "v0.3.1-proposed", "som-v0.3.1-story-context.schema.json"),
    ):
        if os.path.exists(cand):
            return os.path.normpath(cand)
    hits = glob.glob(os.path.join(HERE, "**", "*story-context*.schema.json"), recursive=True)
    return sorted(hits)[-1] if hits else None


def load_inputs(args, envelopes):
    paths = []
    for a in args:
        if os.path.isdir(a):
            paths += sorted(p for p in glob.glob(os.path.join(a, "*.json"))
                            if not os.path.basename(p).startswith("_"))
        else:
            paths.append(a)
    out = []
    for p in paths:
        doc = json.load(open(p, encoding="utf-8"))
        env = None
        if envelopes or ("payload" in doc and "message_id" in doc):
            env, doc = doc, doc.get("payload", {})
        out.append((os.path.basename(p), doc, env))
    return out


# ------------------------------------------------------------------ the rules

def check_sequence(run):
    """Every rule here needs at least two snapshots to mean anything."""
    if len(run) < 2:
        warn("<run>", "only one snapshot — nothing cross-snapshot can be checked")

    first_id = run[0][1].get("story_id")
    seen_assets = {}
    terminal = {"KILLED", "SPIKED", "ARCHIVED"}

    for i, (name, p, env) in enumerate(run):
        # --- identity
        if p.get("story_id") != first_id:
            err(name, "story_id changed mid-run",
                f"{first_id!r} -> {p.get('story_id')!r}. An update is a new snapshot of the "
                f"same story, never a new story.")

        if i == 0:
            for a in p.get("assets", []):
                seen_assets[a["asset_id"]] = a.get("asset_type")
            continue

        _pn, q, qenv = run[i - 1]

        # --- ordering
        sn, sq = p.get("sequence_number"), q.get("sequence_number")
        if isinstance(sn, int) and isinstance(sq, int):
            if sn <= sq:
                err(name, "sequence_number did not increase",
                    f"{sq} -> {sn}. It is owner-only and strictly monotonic; equal values "
                    f"across two writers is a collision, not a tie.")
            elif sn > sq + 1:
                warn(name, "sequence_number gap",
                     f"{sq} -> {sn}. Legal, and gaps are how a missing snapshot becomes "
                     f"visible at all — but worth knowing it happened.")

        if p.get("updated_at", "") < q.get("updated_at", ""):
            err(name, "updated_at goes backwards",
                f"{q.get('updated_at')} -> {p.get('updated_at')}")

        # --- snapshot-not-delta
        gone = set(q) - set(p)
        if gone:
            err(name, "top-level member(s) disappeared",
                f"{sorted(gone)}. Every message is a whole snapshot; omitting what you did "
                f"not change erases it for every consumer.")

        prev_assets = {a["asset_id"]: a for a in q.get("assets", [])}
        now_assets = {a["asset_id"]: a for a in p.get("assets", [])}
        dropped = set(prev_assets) - set(now_assets)
        if dropped:
            err(name, "asset(s) dropped from the snapshot", f"{sorted(dropped)}")

        # --- identity of things inside the story
        for aid, a in now_assets.items():
            was = seen_assets.get(aid)
            if was and a.get("asset_type") != was:
                err(name, f"asset {aid} changed asset_type",
                    f"{was} -> {a.get('asset_type')}. An asset_id is minted once and means "
                    f"one thing for its whole life.")
            seen_assets.setdefault(aid, a.get("asset_type"))

        # --- lifecycle sanity
        if q.get("story_type") in terminal and p.get("story_type") not in terminal:
            err(name, "story left a terminal story_type",
                f"{q.get('story_type')} -> {p.get('story_type')}")

        # --- review states should settle, not oscillate
        for kind, prev_map, now_map in (
            ("assertion", _reviews(q, "assertions", "assertion_id"),
             _reviews(p, "assertions", "assertion_id")),
        ):
            for k, now in now_map.items():
                was = prev_map.get(k)
                if was in ("CONFIRMED", "REJECTED") and now == "PENDING":
                    warn(name, f"{kind} {k} review went back to PENDING",
                         f"{was} -> PENDING. Legal, but a settled review re-opening is worth "
                         f"an audit record.")

        # --- attribution, only checkable when envelopes were supplied
        if env and qenv:
            changed = _content_changed(q, p)
            same_sys = (env.get("originating_system", {}).get("system_id")
                        == qenv.get("originating_system", {}).get("system_id"))
            if changed and same_sys and env.get("message_id") == qenv.get("message_id"):
                err(name, "republished with a stale message_id",
                    "A new snapshot is a new message and needs its own message_id.")


def _reviews(payload, key, idfield):
    out = {}
    for x in payload.get(key, []) or []:
        st = (x.get("review") or {}).get("state")
        if st:
            out[x.get(idfield)] = st
    return out


def _content_changed(a, b):
    ia = {k: v for k, v in a.items() if k not in ("sequence_number", "updated_at")}
    ib = {k: v for k, v in b.items() if k not in ("sequence_number", "updated_at")}
    return ia != ib


# ------------------------------------------------------------------ main

def main():
    argv = sys.argv[1:]
    strict = "--strict" in argv
    envelopes = "--envelopes" in argv
    schema_path = None
    if "--schema" in argv:
        schema_path = argv[argv.index("--schema") + 1]
    inputs = [a for i, a in enumerate(argv)
              if not a.startswith("--") and (i == 0 or argv[i - 1] != "--schema")]
    if not inputs:
        print(__doc__)
        return 2

    sp = find_schema(schema_path)
    if not sp:
        return print("no story-context schema found; pass --schema PATH") or 2
    schema = json.load(open(sp, encoding="utf-8"))
    v = Draft202012Validator(schema)

    run = load_inputs(inputs, envelopes)
    if not run:
        return print("no snapshots found") or 2

    print(f"validate_sequence — {len(run)} snapshot(s) against {os.path.basename(sp)}\n")

    print("Each snapshot on its own:")
    bad = 0
    for name, p, _e in run:
        errs = list(v.iter_errors(p))
        if errs:
            bad += 1
            print(f"  [FAIL] {name}")
            for e in errs[:3]:
                loc = "/".join(str(x) for x in e.absolute_path) or "<root>"
                print(f"         {loc}: {e.message[:110]}")
        else:
            sn = p.get("sequence_number")
            print(f"  [ok]   {name}   seq {sn}")

    print("\nAcross the run:")
    check_sequence(run)
    for where, msg, detail in errors:
        print(f"  [ERROR] {where}: {msg}")
        if detail:
            print(f"          {detail}")
    for where, msg, detail in warnings:
        print(f"  [warn]  {where}: {msg}")
        if detail:
            print(f"          {detail}")
    if not errors and not warnings:
        print("  [ok]    story_id immutable · sequence_number increasing · updated_at forward")
        print("  [ok]    nothing dropped between snapshots · asset identity stable")

    print(f"\n{len(run) - bad}/{len(run)} valid · {len(errors)} error(s) · {len(warnings)} warning(s)")
    if not envelopes:
        print("note: originating_system / message_id checks need --envelopes with wire messages")
    return 1 if (bad or errors or (strict and warnings)) else 0


if __name__ == "__main__":
    sys.exit(main())
