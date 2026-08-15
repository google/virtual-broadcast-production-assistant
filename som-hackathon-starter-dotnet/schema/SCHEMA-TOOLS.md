# Schema tools

Three scripts, three different questions. All pure Python, no dependencies except
`jsonschema` where noted.

| Script | Question it answers |
|---|---|
| `validate.py` | Do **messages** conform to the schema? |
| `som_lint.py` | Does the **schema** agree with itself? |
| `som_diff.py` | What does a **proposed change** break, and for whom? |

---

## validate.py — messages against the schema

Two validators exist and they are not the same file. The **spec scaffold's**
(`v0.3.2-proposed/validate.py`, spec folder only — deliberately not vendored):

```
cd v0.3.2-proposed && python3 validate.py
```

24 checks: three schema-validity, six must-validate (four v0.3.2 worked examples plus
two v0.3.1 regressions), fifteen negative cases that must be **rejected**.

The **reference repo's** (`schema/validate.py`, repo only) covers the whole vendored
pack plus the repo's seeds, mos-bridge fixtures and the C#↔pack version pin — run
`python3 schema/validate.py` from `som-hackathon-starter-dotnet/`. In the repo, that
is the one to run; the scaffold validator does not exist there.

The negative half is the point. Positive tests only prove the schema accepts good
input — a schema that accepted everything would pass all of them. The negative cases
prove it actually constrains.

Needs `jsonschema>=4.20` (Draft 2020-12).

---

## som_lint.py — the schema against its own claims

```
python3 som_lint.py [SCHEMA_DIR]     # default: this directory
python3 som_lint.py --strict         # warnings fail the build (CI)
python3 som_lint.py --info           # show notes as well
python3 som_lint.py --pedantic       # + undocumented-required-field notes
```

`validate.py` checks messages against the schema. Nothing checked the schema against
itself — and that is where two real bugs lived: `assertion.target` described as
"reuses the audit target set" while carrying a value that set lacks, and the ORPHAN
lifecycle promising an audit record the action vocabulary cannot express. Both passed
22/22 message validation.

Descriptions are load-bearing here. Vendors build from them, so they need checking.

**Rules**

| Rule | Checks |
|---|---|
| L1 | every `$ref` resolves |
| L2 | enum divergence **within one effective pack** |
| L3 | prose claiming to reuse/mirror another construct |
| L4 | cross-family promises (a description saying another family records something) |
| L5 | backticked `snake_case` in prose that is not a property anywhere |
| L6 | `UPPER_SNAKE` in prose that is in no enum |
| L7 | status drift — PROPOSED/DRAFT inside a pack whose header says it ships |
| L8 | required fields with no description (`--pedantic`; noisy by design) |

**The effective pack** is the idea that makes L2 work. v0.3.2 changed only three
families, so a v0.3.2 consumer actually reads the v0.3.2 files *plus* the v0.3.1
files it inherits — which is why `assertion.target` (v0.3.2) and audit `target.kind`
(v0.3.1) sit inside one contract despite living in different folders. Group naively
by file version and that whole class of bug disappears.

---

## som_diff.py — pricing a proposed change

```
som_diff.py --from 0.3.1 --to 0.3.2 [DIR]      # version to version
som_diff.py OLD.schema.json NEW.schema.json    # a vendor's proposal
som_diff.py OLD_DIR NEW_DIR                    # two packs
som_diff.py ... --examples DIR                 # also run impact
som_diff.py ... --markdown                     # emit a sequencing table
```

Every change is classified by **who it breaks**:

| Bucket | Meaning |
|---|---|
| `PRODUCERS` | messages valid before are invalid now — the expensive kind |
| `CONSUMERS` | a field they read is gone, or an enum grew a value their switch won't know |
| `NOBODY` | relaxations and additive optional fields |

Combinators are priced by what they do to the accepted set, not by whether text was
added: a new subschema under `allOf`/`then`/`else`/`not`/`contains` can only *narrow*
what validates, so it prices as `PRODUCERS` (that is how a conditional
`claim.detection_class`+`verdict` requirement nearly shipped as "breaks nobody");
a removed `anyOf`/`oneOf` branch takes an accepted alternative away, same bucket.
A narrowing branch inside a *brand-new* structure stays `NOBODY` — it is part of an
optional addition, not a tightening of an existing contract.

`--examples` runs every example in a tree against the new schemas and reports which
now fail, so the delta comes with its blast radius attached. Wire messages are
unwrapped: the envelope and the payload are both checked, because passing one leg and
failing the other is how a reviewed message still breaks on the bus.

Exit 0 = nothing producer-breaking; 1 = at least one, or an example now fails.

**Why it exists.** The arithmetic behind "what does this break" has been done by hand
for every proposal, and it is easy to get wrong — the relations delta was priced at
two enum values before a second pass found four enum values, one new required field,
two new optional fields and two constraint changes. The argument for automating it is
consistency rather than accuracy: the cost of a proposal should not depend on how much
time the reviewer had that week.

---

## Suggested CI (reference repo)

```yaml
- run: bash schema/sync-from-spec.sh --check    # repo copy has not drifted from the spec
- run: python3 schema/validate.py               # messages conform (repo validator)
- run: python3 schema/som_lint.py schema        # schema agrees with itself (errors gate)
```

Two things deliberately NOT in that list:

- **`som_lint --strict`** promotes warnings to failures. Adopt it only once the pack
  is warning-clean — the v0.3.2 pack currently carries known L3/L7 warnings that are
  tracked spec-side, so `--strict` today is a permanently red check.
- **`som_diff --from 0.3.1 --to 0.3.2`** re-prices two *ratified* versions, and the
  delta between them contains a real, accepted producer-breaking change
  (`ai_enrichments` hard-rejection) — so as a CI gate it fails forever by design.
  som_diff gates **proposals**: run `som_diff CURRENT.schema.json PROPOSED.schema.json`
  (or two pack dirs) on the proposal branch, where exit 1 means the proposal breaks
  producers and should say so out loud.
