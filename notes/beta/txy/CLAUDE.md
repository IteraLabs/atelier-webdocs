# CLAUDE.md - Taxonomy v0.1-beta-2

Seed file for any Claude session scoped to `txy-v0.1-beta-2/`. The taxonomy is the noun layer of the Atelier Engine spec at this version. For dynamics (states, transitions, wire format, persistence), descend into `../fsm-v0.1-beta-2/`.

Workspace root context: `../CLAUDE.md`. Cross-tree spec index: `../INDEX.md`.

## Files in this tree

| File | Status | Use it for |
|---|---|---|
| `txy-main.md` | normative | Naming conventions; Agents (Remote / Platform); System Processes (Gateway, Overseer); Skills & Tasks; Operations; Channels; Artifacts & Sinks; Activation modes (Service, Experiment); Structural terms; Identifiers; Scope boundary for v0.1-beta-2 |
| `use-case.md` | illustrative | End-to-end narrative threading every term in runtime order; seven-step Bring-Your-Own-Infra Market Data Collection (Service) walkthrough |

If `use-case.md` and `txy-main.md` disagree, **`txy-main.md` wins**. The example exists to check a mental model, not to define a term.

## Precedence vs FSM Atlas

- This tree owns: term names, identifier naming, scoping rules, the prefix+suffix composition convention, the operation surface, the inventory of channel and sink types.
- The FSM Atlas owns: state shapes, transition triggers and guards, effects, invariants, interaction rules, wire encoding, persistence DDL, error semantics, timeouts.
- A taxonomy term that gains dynamics must land an FSM in `../fsm-v0.1-beta-2/` in the same change set. A new FSM whose subject is not yet a taxonomy term must land the term in `txy-main.md` in the same change set.

## Naming conventions (load-bearing)

Three orthogonal axes compose every entity term:

- **Location prefix** - `Remote` (client-side) or `Platform` (server-side, IteraLabs).
- **Type suffix** - `Agent`, `Workspace`, `ComputeSlot`, `Channel`, `Sink`, `Task`, `Skill`.
- **Composition** - any prefix + any suffix produces a self-describing term. The name is the definition.

System Processes (`Gateway`, `Overseer`) are **outside** the prefix+suffix model. They have no Skills, execute no Tasks, occupy no ComputeSlots. Named by function. Do not retrofit them into the Agent model.

## Identifier conventions

Every entity carries a typed ID (`Agent ID`, `Task ID`, `Binding ID`, `Service ID`, `Experiment ID`, `Artifact ID`, `Channel ID`, `Session ID`, `Overseer ID`, `Gateway ID`). When prose introduces an entity for the first time it should name the ID. The Atlas treats these as the persistent join keys (see `../fsm-v0.1-beta-2/schema.md`).

## House conventions for edits in this tree

- **Don't edit `use-case.md` to fix a definition.** Fix `txy-main.md` and re-derive the example.
- **Add a term in the right WHO/WHAT/WHERE/HOW section.** Don't append to the end of the file.
- **A new term needs a one-sentence "the name is the definition" gloss** consistent with the prefix+suffix model.
- **Beta scope is fixed.** Experiment FSM, full Channel lifecycle, and full Sink lifecycle are deferred - adding terms or behavior for them belongs in v0.1-beta-3, not here.

---

## Session Log

Append-only. Each session adds a dated entry. Format:

```
### YYYY-MM-DD - <session purpose, ≤8 words>
- Scope:        <files / sections touched>
- Decisions:    <one bullet per decision worth recovering later>
- Open issues:  <unresolved questions, with owner if known>
- Next:         <handoff for the next session>
```

### 2026-04-23 - Taxonomy CLAUDE.md seeded
- Scope:        `txy-v0.1-beta-2/CLAUDE.md` (new). No edits to `txy-main.md` or `use-case.md`.
- Decisions:    Codified the taxonomy's role vs the FSM Atlas (nouns vs dynamics) and the requirement that new terms with dynamics ship a co-resident FSM change.
- Open issues:  None so far
- Next:         When v0.1-beta-3 opens, decide whether the Experiment surface lives as §2.6 in the Atlas with a parallel taxonomy section, or whether it earns its own subtree.
