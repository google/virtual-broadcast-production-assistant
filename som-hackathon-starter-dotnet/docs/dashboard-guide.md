# Dashboard guide

_A walkthrough of the SOM Skill Bus dashboard (`http://localhost:5050`): what every control does, what each lane means, and the three workflows it exists to support. Companion to the [README](../README.md) quick start and [`SOM-v0.3.1-distribution-contracts.md`](./SOM-v0.3.1-distribution-contracts.md) for the message shapes._

The dashboard is a **window onto a Kafka bus** carrying SOM (Story Object Model) messages. Stories arrive on `som.story.context`, the skill worker runs skills against them, outputs are staged for a human decision, and every decision goes back onto the bus. The dashboard renders that flow live over a WebSocket and gives you tools to generate traffic without any upstream newsroom system.

## Layout at a glance

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ SOM Skill Bus  [Seed stories: Informal|Breaking|…]   [⚡Auto ON] [🎬 Simulator] │
│                                        [🗑 Reset bus] [Topology] [Skills] [?]  │
├──────────────┬──────────────┬───────────────────┬─────────────────────────────┤
│ Stories on   │ Skill Runs   │ Pending Approval  │ Decisions                   │
│ Bus          │              │  [Approve][Reject]│                             │
├──────────────┴──────────────┴───────────────────┴─────────────────────────────┤
│ Bus event log   [all] [story.context] [delivery.media_available] [skills.…]   │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Three ways to put traffic on the bus

These are separate surfaces — knowing which is which is most of the learning curve:

| Surface | Where | What it does |
|---|---|---|
| **Seed stories** | Header buttons (Informal, Breaking, …) | One click = **one** `story.context` seed published. No timing, no lifecycle. The quickest way to make something happen. Hover any button for what it demonstrates. |
| **Simulator** | Header 🎬 button — three tabs | **Scripted scenarios**: timed multi-step storylines (publish, then mutate/emit over N seconds); one at a time, starting another cancels the current, Stop cancels remaining steps. **Mock MAM**: emit `som.delivery.media_available` per catalog source. **Auto-stream**: one *random* seed story every N seconds until stopped. |
| **Lifecycle panel** | Click any story card | Mutates *that* story — advance phase, add a compliance flag, re-run skills. Each action republishes a new version, so skills re-fire against it. |

**The auto-stream trap (and its guard):** auto-stream keeps publishing after the Simulator modal closes. While it's on, the header shows a green **"Auto-stream ON · Ns"** chip — click it to jump straight to the Auto-stream tab and stop it. If your lanes are filling with stories you didn't ask for, this is why.

## The four lanes

| Lane | Fed by | Card shows |
|---|---|---|
| **Stories on Bus** | `som.story.context` | Latest version of each story: phase, priority, warnings count, phase timeline. Click → lifecycle panel. |
| **Skill Runs** | `som.skills.runs` | One card per skill execution: outcome (COMPLETED/SKIPPED), latency, output counts (w/s/e). Click → full run record. |
| **Pending Approval** | `som.skills.staging` | Staged skill outputs awaiting your call: rule, severity, story, detail, **Approve** / **Reject**. |
| **Decisions** | your clicks | Approvals republish to `som.skills.events`; rejections to `som.skills.rejected` — both with reviewer + timestamp stamped on the envelope. |

## Bus event log (bottom)

Every message on every subscribed topic, newest first — one line per message with a per-topic summary (stories show headline; runs show outcome + latency; MAM emits show `MEDIA <source> range=<timerange>`). The **topic chips** filter the view and double as live counters. **Clear** empties only this log display.

Note `som.delivery.media_available` appears here for **observability** — the dashboard tails it for the log but doesn't act on it. The real consumer (maintaining `usage[]` etc.) is the WS1 August build.

## Other header controls

| Control | What it does |
|---|---|
| **Reset bus** | Clears only the dashboard **view** (lanes, pending queue, timeline); older bus messages are suppressed from re-rendering. Kafka topics and messages are **not** deleted — they stay replayable via Kafka UI. Truly empty bus: `docker compose down -v && docker compose up -d`. |
| **Topology** | Live map of producers → topics → consumers with message counts. |
| **Skills** | Skill registry: rules per skill, live stats (runs, latency, approval rate), and the 3 validation layers — static check, dry-run against all seeds, AI review. |
| **SOM JSON** | Raw seed envelopes as published — the ground truth for what a `story.context` looks like on the wire. |
| **? Help** | In-app condensed version of this guide. |
| **ws pill** | WebSocket health. "reconnecting…" = the app is down or restarting; the dashboard self-heals when it returns. |

## Workflows

### 1. Test your vendor skill
1. Register/edit your skill (**Skills** → add, or `POST /api/skills`) — static validation runs automatically.
2. **Dry-run** it against all five seeds to see which stories fire which rules, without touching the bus.
3. Publish a seed (header button) or run the **multi-vendor-stream** scenario for load.
4. Watch your skill's run cards appear; approve/reject its staged outputs; check the approval-rate stat.

### 2. Drive a demo
1. Open **Simulator → Scripted scenarios**, pick the storyline that matches your beat (hover for what each demonstrates).
2. Narrate as it plays out — story arrives → skill fires → warning staged → approve → event on the production bus.
3. For a continuously "alive" dashboard between beats, switch on **Auto-stream** (and mind the header chip).

### 3. Prove the D1·B5 media-arrival beat (TAMS junction)
1. **Simulator → Scripted scenarios → media-arrival**: publishes the hurricane story, then the mock MAM emits `delivery.media_available` three times with a **growing** TAMS timerange (`[0:0_30:0)` → `[0:0_75:0)` → `[0:0_1260:0)`) — a recording addressable while still being captured.
2. Watch the `MEDIA` lines land in the bus event log (filter chip `delivery.media_available`), or inspect full envelopes in Kafka UI (:8080).
3. One-off emits per source: **Simulator → Mock MAM → Emit media_available**; custom ranges via `POST /api/mam/emit/{sourceId}` with `{"timeRange": "[0:0_30:0)"}`.

## Troubleshooting

- **Values render as `undefined`** → your browser is running an old copy of the page; reload (Cmd+R).
- **Lanes flooding with random stories** → auto-stream is on; click the green header chip → Stop.
- **"Run scenario" buttons disabled** → a scenario is already running; Stop it or let it finish.
- **Mock MAM section empty** → `content/mam-catalog.json` missing or unparseable; check the app log.
- **Everything frozen, ws pill says "reconnecting…"** → the app is down; restart `dotnet run`, the page reconnects itself.
