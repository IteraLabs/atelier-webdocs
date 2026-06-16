# Atelier Engine — Spec Cross-Tree Index (v0.1-beta-2)

The `../INDEX.md` referenced by `fsm/CLAUDE.md` and `txy/CLAUDE.md` as the cross-tree spec index. Three legs define the platform's design language: the **nouns** (Taxonomy), the **dynamics** (FSM Atlas), and the **reconciliation to code**.

| Leg | Location | Owns |
|---|---|---|
| **Taxonomy** | [`txy/`](txy/) → `txy-beta.md` (start at `txy/CLAUDE.md`) | Names, identifiers, scopes, typologies, operation surface; the C1–C7 review method + violation Classes A–H. **Wins on static definition.** |
| **FSM Atlas** | [`fsm/`](fsm/) → `fsm-beta.md` (start at `fsm/CLAUDE.md`) | States, transitions, guards, effects, invariants, wire catalog, 12-table DDL, errors, timeouts, sequences; the §2.4.1 Ownership Matrix. **Wins on dynamic behavior.** |
| **Reconciliation ↔ code** | [`txy-fsm-code-beta.md`](txy-fsm-code-beta.md) | **Master, priority-ranked tracker** to close the gap between txy, fsm, and the codebase. Status/Owner per action; step-by-step plan for the highest-leverage item. |

**Evidence base for the tracker:** `../../v0.1-integration.md` (repo root) — live deployment (SEQ-1/SEQ-2 driven end-to-end) + a 50-agent static audit, all load-bearing findings adversarially verified.

**Other material under `notes/beta/`:** `manuals/` (boot/operations), `plans/` (implementation plans), `reports/` (dated, per-repo audit findings — per the taxonomy, findings live here, not in the durable spec).

**Precedence:** Atlas wins on dynamics; Taxonomy wins on naming/ontology. A conflict must be resolved on both sides within the same version cut.
