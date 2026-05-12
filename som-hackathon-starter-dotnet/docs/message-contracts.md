# SOM Message Contracts — Skill Outputs

Companion to [`som-v02-envelope.md`](./som-v02-envelope.md). That doc covers the inbound `story.context` shape; this one covers the **outbound** messages skills produce, and two cross-cutting v0.2.1 conventions:

1. **`instance_ref`** — how a skill output binds to a specific story instance.
2. **`extensions.com.{vendor}.{...}`** — how vendors add fields without changing the spec.

Wire baseline: SOM v0.2 plus Amendments A1–A5 (the "v0.2.1-hackathon" label). v0.3 ratifies post-event.

---

## Topic reference

| Topic | Producer | Consumer | Message types |
|---|---|---|---|
| `som.story.context` | AP / TestProducer | SkillWorker, Dashboard | `story.context` |
| `som.skills.staging` | SkillWorker | Dashboard (Pending lane) | `skill.warning.raised`, `skill.suggestion.created` |
| `som.skills.events` | Dashboard (approve) | Downstream | approved skill outputs |
| `som.skills.rejected` | Dashboard (reject) | Audit | rejected skill outputs |
| `som.skills.runs` | SkillWorker | Dashboard (audit) | `skill.run.completed` |

Use the **suffixed** message type names on the wire. The unsuffixed forms in the v0.2 spec body are tracked as **SOM-049** for cleanup; the dashboard parses suffixed only.

---

## `instance_ref` — instance scoping in the payload

A story can air across many surfaces simultaneously — a linear newscast, a web live-blog, a social card. Each surface is represented by an entry in `payload.instances[]` on the inbound `story.context` message, identified by `instance_id`.

When a skill produces a warning or suggestion that applies **to a specific instance** (not the whole story), it sets a singular `instance_ref` field on its output payload, pointing back to the relevant `instance_id`.

### Field — hackathon shape (v0.2.1)

| Field | Type | Required | Description |
|---|---|---|---|
| `instance_ref` | string | no | Value of an `instances[].instance_id` on the originating story. Omit for story-wide warnings. |

### v0.3 target shape (Amendment A4)

Amendment A4 (instance-scoped skills, part of the v0.2.1-hackathon label) proposes the richer **object** form for v0.3:

```yaml
instance_ref:
  story_id: string         # the originating story
  instance_id: string      # matches payload.instances[].instance_id
  instance_type: string    # e.g. "broadcast" | "social_twitter" | "article"
```

For the hackathon day, use the **string** form — `story_id` and platform metadata are already derivable from the envelope and from `payload.instances[]`. The object form is the migration target; producers and consumers SHOULD plan for it but MUST NOT block on it at the hackathon.

### Why singular, not an array

The shape is `instance_ref` (singular), not `instance_refs[]`. A single skill output binds to **one** instance. If the same warning applies to two instances, emit two warnings with two `warning_id`s and two `instance_ref` values. Keeping it singular keeps decision routing on the dashboard deterministic — one warning, one Pending row, one approve/reject per surface.

### What's on the wire

The inbound story carries the `instances[]` array; the outbound skill output carries the singular `instance_ref` referencing one of them.

```json
// payload.instances[] on story.context (inbound)
"instances": [
  { "instance_id": "inst-nbc-nightly-001", "platform": "linear",  "program": "NBC Nightly News" },
  { "instance_id": "inst-nbcnews-web-001",  "platform": "web",     "program": "NBCNews.com" }
]
```

```json
// skill.warning.raised — hackathon minimum (itinerary §06) + instance_ref
// On the wire, .NET starter also emits skill_version, story_id, non_overridable,
// message_type, and timestamp. See "Spec fields" below for the full §4.4.2 shape.
{
  "warning_id":  "wrn-019536b1-0001",
  "skill_id":    "nbcu/editorial-standards",
  "severity":    "flag",
  "rule_id":     "nbcu-style-001",
  "affected_fields": ["headline"],
  "detail":      "Informal term 'cops' in headline. Consider formal alternative.",
  "blocks":      [],
  "instance_ref": "inst-nbcnews-web-001"
}
```

### Scoping rules

| Skill intent | Set `instance_ref`? |
|---|---|
| Warning applies to the whole story | **No** — omit the field |
| Warning applies only to the linear broadcast version | **Yes** — set to the linear `instance_id` |
| Warning applies to both linear and web | Emit **two** warnings, one per `instance_ref` |
| Warning applies to a non-existent `instance_id` | Consumer SHOULD reject — fail closed |

Per itinerary §06: instance scoping rides in the payload, **not via dedicated topics**. Do not split skill warnings across `som.skills.staging.{instance}` style topics.

---

## `skill.warning.raised` — payload

Editorial warning emitted by a skill against a story (or a specific instance).

Two reference points apply:

- **Skills Integration Spec §4.4.2** is the normative source for the 12-field SkillWarning payload.
- **Itinerary §06** lists a 7-field minimum — the day-of subset producers MUST emit to satisfy hackathon validation. It is a strict subset of §4.4.2.

### Spec fields (Skills Integration Spec §4.4.2)

| Field | Type | §4.4.2 required | In itinerary §06 | In .NET starter |
|---|---|:-:|:-:|:-:|
| `warning_id` | string (UUIDv7) | MUST | ✓ | ✓ |
| `skill_id` | string | MUST | ✓ | ✓ |
| `skill_version` | string (semver) | MUST | — | ✓ |
| `story_id` | string | MUST | — | ✓ |
| `scope` | string | MUST | — | **gap** |
| `severity` | enum `hold`\|`flag`\|`inform` | MUST | ✓ | ✓ |
| `rule_id` | string | MUST | ✓ | ✓ |
| `non_overridable` | boolean | MUST | — | ✓ |
| `affected_fields` | string[] | MUST | ✓ | ✓ |
| `detail` | string | MUST | ✓ | ✓ |
| `blocks` | string[] | MUST | ✓ | ✓ |
| `skill_warning_ref` | string | MUST | — | **gap** |

`scope` and `skill_warning_ref` are not yet emitted by the .NET starter — tracked as follow-ups against SOM-048 / SOM-049, **out of scope for the hackathon day**.

### Severity semantics (normative per §4.4.2)

| Severity | Executor MUST | Subscriber MUST |
|---|---|---|
| `hold` | Withhold all output on affected fields until the warning is resolved | NOT use held content |
| `flag` | Mark output as requiring review | MAY display a visual warning |
| `inform` | Advisory only, no blocking action | No mandatory action |

Dashboard treatment in the hackathon starter: `hold` lands red and cannot be approved via single click; `flag` lands yellow with standard approve/reject; `inform` lands blue and auto-clears after acknowledgement.

### Envelope / routing fields emitted by the .NET starter

These are not part of §4.4.2 but ride on the wire to support topic-suffix routing and audit. Consumers SHOULD ignore-if-unknown:

| Field | Type | Notes |
|---|---|---|
| `message_type` | string | Always `"skill.warning.raised"`. The dashboard parses this for topic routing — SOM-049 tracks the spec-doc cleanup to add the `.raised` suffix in Table 4. |
| `timestamp` | string (ISO 8601) | When the warning was raised. Envelope-level concept; likely moves to the outer envelope in v0.3. |

### Optional v0.2.1 fields

| Field | Type | Description |
|---|---|---|
| `instance_ref` | string | Bind the warning to one `instances[].instance_id` per Amendment A4. See above. |
| `extensions` | object | Vendor-namespaced additions per A1–A5. See next section. |

---

## `extensions` — vendor namespace

Any field outside the canonical SOM schema rides under `payload.extensions.com.{vendor}.{...}`. The namespace prevents collisions between broadcasters and keeps a clean upgrade path: anything that graduates to the spec drops its `com.{vendor}.` prefix on promotion.

### Pattern

```
extensions.com.{vendor}.{field}
```

`{vendor}` is the reverse-DNS short form of the broadcaster or skill author (e.g. `nbcu`, `bbc`, `itn`). `{field}` is open.

### NBCU extensions on `skill.warning.raised`

Two NBCU fields exercised at the hackathon:

| Path | Type | Description |
|---|---|---|
| `extensions.com.nbcu.citations` | array of `{ source_id, quote }` | Backing material that supports the warning — usually a quote from a rule definition or a referenced source. |
| `extensions.com.nbcu.rationale` | string | Plain-language reason the rule fired, intended for editorial review. |

### Example

```json
{
  "warning_id": "wrn-019536b1-0001",
  "skill_id": "nbcu/editorial-standards",
  "severity": "flag",
  "rule_id": "nbcu-style-001",
  "affected_fields": ["headline"],
  "detail": "Informal term 'cops' in headline. Consider formal alternative.",
  "blocks": [],
  "extensions": {
    "com.nbcu.citations": [
      { "source_id": "nbcu-style-guide-2026", "quote": "Use 'police' or 'officers'. Avoid 'cops' in headlines and lower thirds." }
    ],
    "com.nbcu.rationale": "Term 'cops' is on the NBCU Standards informal-terms list; headlines must use formal register."
  }
}
```

### Consumer behaviour

- Consumers that don't recognise an `extensions.com.{vendor}.*` key MUST ignore it silently.
- The dashboard's warning detail panel renders `extensions.com.nbcu.citations` and `extensions.com.nbcu.rationale` as a structured block above the raw JSON dump.
- Promoting an extension to the spec is a v0.3 conversation — see SOM-047 / EX-8 in the UDE extensions catalogue.

---

## See also

- [`som-v02-envelope.md`](./som-v02-envelope.md) — inbound `story.context` field reference
- [`architecture.md`](./architecture.md) — runtime topology and dashboard data flow
- [`skill-validation.md`](./skill-validation.md) — skill JSON schema and registry rules
- Hackathon itinerary §06 — decided enums and shapes for the day
