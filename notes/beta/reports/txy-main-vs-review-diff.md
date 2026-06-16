# txy-main.md ↔ txy-review.md — Difference Report (v0.1-beta-2)

Descriptive diff only. Merge planning deferred by request.
Inputs: `atelier-webdocs/notes/beta/txy/{txy-main.md, txy-review.md}`, disk state 2026-06-04.
Date: 2026-06-15.

## 1. Headline

- Different document kinds, not two versions of one document.
- `txy-main.md` = definitions — *what each term is*.
- `txy-review.md` = audit method — *how to check a repo uses the terms correctly*.
- `txy-review.md` defines zero terms.
- Only real content overlap: review `§3` "canonical surface" table = a derived index of main.
- That overlap is also the only place the two have drifted.

## 2. Identity comparison

| Attribute | txy-main.md | txy-review.md |
|---|---|---|
| Title | Atelier Engine — Taxonomy v0.1-beta-2 | Taxonomy Review Companion — v0.1-beta-2 |
| Role | Normative definitions | Operational review method |
| Question answered | "What is X?" | "How do I check repo R speaks X correctly?" |
| Content type | Term ontology | QA procedure + violation taxonomy |
| Normativity | Source of truth (static defs) | Non-normative; cites main as authority |
| Reach | Every repo that names an entity | Reviewers running an audit pass |
| Organizing scheme | WHO / WHAT / WHERE / HOW / OBJECTS / DESTINATIONS / ACTIVATION / STRUCTURAL / IDENTIFIERS | 10 numbered sections (§1 role … §10 citations) |
| Length | 397 lines / ~49 KB | 142 lines / ~14 KB |
| Registered in `CLAUDE.md` file table? | Yes | No — unregistered |
| Produces output? | No (it IS the reference) | Yes (per-repo violation list → reconciliation plan) |
| Lifespan | Durable | Method durable; embedded "known findings" decay |

## 3. Section-by-section function

### txy-main.md — every section is definitional

| Section | Defines |
|---|---|
| Naming Conventions | prefix+suffix composition rule |
| WHO: Agents / System Processes / Personas | Agent, RemoteAgent, PlatformAgent, Gateway, Overseer, Researcher/Operator/User |
| WHAT: Skills & Tasks | Skill (5), Task, acceptance/rejection |
| WHAT: Operations | System / Data / Infrastructure operations |
| WHAT: System Health / Recovery | Overseer modes, subsystems, 3-stage recovery |
| WHERE: Scopes | Domain, Session, Workspace, ComputeSlot |
| HOW: Channels | 5 channel types |
| OBJECTS / DESTINATIONS | Artifact kinds (4), Sink types (3) |
| ACTIVATION MODES | Service, Experiment |
| STRUCTURAL TERMS / IDENTIFIERS | Skill, Task, Manifest, Binding, Pipeline; 16 IDs |
| NOT COVERED | deferred items |

Function: 100% definition.

### txy-review.md — method, plus one summary section

| Section | Function | Relation to main |
|---|---|---|
| §1 Role (Taxonomy vs Atlas) | framing | about main |
| §2 Reach | framing | about main |
| §3 Canonical surface (7 surfaces) | **summary of main** | derived index — the overlap |
| §4 Sources of authority + precedence | governance | references main |
| §5 Seven checks C1–C7 | method | operates on main |
| §6 Per-repo primary surfaces | method | operates on main |
| §7 Violation taxonomy A–H | method | classification |
| §8 Planning passes (3 waves) | method | workflow |
| §9 Interaction w/ ownership | governance | cross-lens |
| §10 Source citations | refs | — |

Function: 1 summary section (§3) + 9 method/governance sections. Zero definitions.

## 4. The single content overlap — review §3 vs main

- review §3 condenses main into 7 "surfaces": Nouns, Verbs, Identifiers, Typologies, Scopes, Modes, Lifecycle concepts.
- This is the only content both docs carry.
- It is a one-way derivation (review summarizes main) → it can fall out of sync. It has (see §5).

| review §3 surface | Home in txy-main.md |
|---|---|
| Nouns | WHO + STRUCTURAL TERMS + WHERE |
| Verbs | WHAT — Operations |
| Identifiers | IDENTIFIERS — Summary |
| Typologies | Skills, Sinks, Artifacts, System Health, Activation |
| Scopes | WHERE — Scopes |
| Modes | System Health, Naming (Remote/Platform), Activation |
| Lifecycle concepts | Recovery, Drain, Restart (Ghost entity = Atlas, not main) |

## 5. Drift & inconsistency (main ↔ review)

| ID | Finding | main | review | Type |
|---|---|---|---|---|
| X1 | System Operations count. main defines **9** (incl. Drain). review §3 "Verbs" lists **8**, omits Drain; review §5 C3 says "The 8 System Operations". | Operations §, 9 ops | §3 table; §5 C3 | count drift |
| X2 | main internal: System-Health "all mutating System Operations" list = 8, **omits Command**. | System Health table | — | internal inconsistency (main) |
| X3 | review §3 names wire-layer typologies main never uses: `AgentType` (main uses Remote/Platform prefix + RemoteAgent/PlatformAgent) and `SubsystemLoss` (main says "infrastructure subsystems" / System Health). | Naming; System Health | §3 Typologies | naming blur (wire vocab in taxonomy index) |
| X4 | review §3 "Nouns" omits **Experiment** and **Domain** — both normative nouns in main. | Experiment (Activation, IDs); Domain (WHERE) | §3 Nouns | incomplete index |
| X5 | review §3 "Identifiers" asserts wire shape (UUIDv4 flat `string`, `*_alias` optional) that main never states. | IDENTIFIERS Summary (IDs + scope/purpose; no wire shape) | §3; §5 C2 | scope gap (review richer; sourced from proto-catalog) |
| X6 | Precedence model differs. main asserts its own primacy inline ("this document is source of truth"). review defers to an external `INDEX.md`. | top preface | §1, §4, §9 | model inconsistency (+ dangling, see §6) |

## 6. Stale / dangling references

| Reference | Appears in | Actual | Status |
|---|---|---|---|
| `INDEX.md` | review §1/§4/§9/§10; txy `CLAUDE.md` | not found anywhere under `notes/` | **dangling** — cited precedence authority is missing |
| `txy-v0.1-beta-2/` path prefix | review §4/§10; `CLAUDE.md` | dir is `txy/` | stale path |
| `fsm-v0.1-beta-2/` path prefix | main (multiple); review (multiple); `CLAUDE.md` | dir is `fsm/` | stale path |
| `use-case.md` | review §4/§10; `CLAUDE.md` | `use-case-1.md` | stale name |
| `fsm-examples-v0.1-beta-2.md` | main (preface, illustrative companion) | `use-case-1.md` | wrong name |
| `txy-examples-v0.1-beta-2.md` | main (Illustrative Companion section) | `use-case-1.md` | wrong name |
| `fsm-v0.1-beta-2/main.md` | main (Activation beta-scope note) | `fsm/fsm-main.md` | stale name |
| `export TEXINPUTS=…` / `pdflatex main.tex` | main lines 1–2 | n/a | stray build/shell artifact atop a normative doc |
| `txy-review.md` itself | txy `CLAUDE.md` "Files in this tree" | absent | unregistered third doc |

Note: main names its illustrative companion **two different (both wrong) ways** — preface `fsm-examples-…`, footer `txy-examples-…`; the real file is `use-case-1.md`.

## 7. Method vs decaying findings (inside review)

- review interleaves durable **method** (C1–C7, classes A–H, the 3 passes) with time-stamped **findings**.
- The method is stable. The findings are a snapshot — several are already superseded by the current `fsm/proto-catalog.md`.

| review item | Embedded claim | Current status |
|---|---|---|
| §5 C4 | proto `AgentCapability`, 4 members, missing SYNC @ `identity.proto:105` | `proto-catalog.md §control.proto` defines `Skill` with **5** members incl. SYNC → **stale** |
| §5 C3 (missing ops) | `SERVICE_ARCHIVE`, `AGENT_TERMINATE`, `BINDING_RELEASE`, `SESSION_RENEW`, `SESSION_FORCE_CLOSE` absent from proto `CommandType` | `proto-catalog.md §control.proto` `CommandKind` now includes **all five** → **stale** |
| §5 C1 (known hits) | `AgentCapability`→Skill, `AgentLocation`→AgentType, Worker-as-Task, TerminalSink/Terminal | wire now uses `Skill`/`AgentType`; **Worker-as-Task still live in SDK** (confirmed in the SDK audit) → **mixed** |
| §5 C6 | proto exposes active `ExperimentId` `Manifest.activation` @ `manifest_channel.proto:33` | `proto-catalog.md §data.proto` reserves `experiment_id` post-beta; re-verify vs live `atelier-proto` → **likely stale** |
| §4 / §7 | embeds 2026-04-24 resolutions; cites predecessor `atelier-v0.1/divergence-*.md` | dated snapshot / predecessor docs |

Observation (not a recommendation): the method ages well, the findings layer does not. This is the same split the SDK audit already used — method stays in review, findings go to `reports/`.

## 8. Where they agree (no diff)

- Same version target: v0.1-beta-2.
- Same precedence principle: Taxonomy wins on static definition; Atlas wins on dynamic behavior.
- review §3 typology counts match main's content: Skill 5, SinkType 3, ArtifactKind 3 + ManifestArtifact, SubsystemLoss 4, AgentType 2, Activation (Service in-scope / Experiment deferred).
- Co-dated last edit: 2026-06-04.
- Complementary at the method level: C1–C7 and classes A–H exist only in review; main has no audit content. No redundancy there.

## 9. One-line characterization

- main = the dictionary. review = the spell-checker's rulebook + a (decaying) list of words it already caught misspelled.
- They share only the word list (review §3), and that copy has drifted.

## 10. Evidence index

- `txy-main.md`: lines 1–2 (build artifact); preface + footer (two companion names); Operations section (9 ops incl. Drain); System Health table (8-op mutating list, omits Command); Activation beta-scope note (`fsm-v0.1-beta-2/main.md`).
- `txy-review.md`: §3 table (7 surfaces; Nouns omit Experiment/Domain; Typologies name AgentType/SubsystemLoss); §5 C3 ("8 System Operations"; missing-ops list); §5 C4 (AgentCapability/SYNC); §10 (old `*-v0.1-beta-2/` paths, `use-case.md`).
- `txy/CLAUDE.md`: file table lists only `txy-main.md` + `use-case.md`; cites `../INDEX.md`.
- `INDEX.md`: `find notes -iname INDEX.md` → none.
- `fsm/proto-catalog.md §control.proto`: `Skill` (5), `CommandKind` (incl. SERVICE_ARCHIVE/AGENT_TERMINATE/BINDING_RELEASE/SESSION_RENEW/SESSION_FORCE_CLOSE) — basis for the §7 staleness column.
