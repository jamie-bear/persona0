# Persona0 Memory Lifecycle

* Version: 0.1
* Purpose: define the full lifecycle for all persistent record types — from creation through archival and deletion
* Depends on: `ego_data.md §2` (record schemas), `self_editability_policy.md §3.2` (SELF mutability rules)

---

## 1) Lifecycle Overview

All persistent records move through a sequence of lifecycle states. The lifecycle is enforced by the memory module during nightly macro-cycles and by explicit user/operator deletion requests.

```
ACTIVE → COOLING → ARCHIVED → DELETED
```

| State | Meaning | Operations permitted |
|-------|---------|---------------------|
| `active` | Record is in regular retrieval rotation | read, append (episodic only), update `decay_factor` |
| `cooling` | Record TTL has elapsed or importance has dropped below threshold | read-only; excluded from retrieval by default |
| `archived` | Record has passed compaction; kept for audit/traceability | read-only; accessible via explicit archive queries only |
| `deleted` | Record has been physically removed | none (tombstone only) |

**Append-only guarantee (episodic_log):** Records in the episodic log are never modified. The only permitted in-place change is the `decay_factor` field. Archival means the record is moved to a cold partition, not altered. Deletion from episodic_log is only permitted via a user deletion request (forget API).

---

## 2) TTL Rules Per Record Type

TTLs are measured from `created_at`. Defaults are set in `persona_constitution.md §privacy_tier_defaults` and overridden per record by user preference.

| Record type | Default TTL | Cooling threshold | Archival trigger | Deletion |
|-------------|-------------|-------------------|------------------|---------|
| `EpisodicEvent` | 90 days | TTL elapsed | 180 days after cooling | User forget request only |
| `ThoughtFragment` | 90 days | TTL elapsed | 180 days after cooling | User forget request only |
| `Reflection` | 365 days | 365 days elapsed | 2 years after creation | User forget request or operator reset |
| `Goal` (completed/abandoned) | n/a | Goal status = completed or abandoned | 30 days after status change | Explicit operator action |
| `Goal` (active/suspended) | n/a | n/a — kept active | Goal abandoned | Explicit operator action |
| `SelfBelief` | null (indefinite) | Confidence < 0.15 | 30 days in cooling | Operator persona reset |
| `Desire` | EPH — not persisted | n/a | n/a | Cleared at tick end |

---

## 3) Promotion and Demotion Criteria

### 3.1 Cooling (demotion from active)

A record is moved to `cooling` when any of the following apply:

- **TTL elapsed**: `now - created_at > ttl_days`
- **Low importance**: `EpisodicEvent.importance < 0.15` after 3 macro-cycles
- **Belief underconfidence**: `SelfBelief.confidence < 0.15` (unreinforced over time)
- **Goal completion**: `Goal.status in [completed, abandoned]`
- **Explicit user request**: user marks a record for archival via preference API

A record entering `cooling` is excluded from the default retrieval index but remains queryable.

### 3.2 Archival (demotion from cooling)

A record is archived when:

- It has been in `cooling` for 180 days (episodic/thought) or 30 days (completed goals)
- Reflection records are archived after 2 years regardless of cooling state if confidence is stable
- Operator triggers a compaction pass

Archived records move to a cold partition of the store. They are excluded from all background retrieval scoring. They remain accessible via explicit `archive_query` calls (for audit and traceability).

### 3.3 Deletion

Deletion is the only irreversible lifecycle action. Permitted triggers:

1. **User forget request** (via forget API): propagates to all stores (episodic, semantic, self-model). A tombstone record is kept with the `source_ref` and deletion timestamp. The content is zeroed.
2. **Operator persona reset**: full deletion of all SELF-class state. CONST fields are re-read from `persona_constitution.md`.
3. **Privacy tier enforcement**: records with `privacy_tier = high` and TTL expired are hard-deleted (no archival step).

Episodic log records tied to a SelfBelief's `supporting_reflections` must be archived (not deleted) before the belief can be archived. This ensures belief traceability is maintained.

---

## 4) Semantic Store and Self-Model Lifecycle

The semantic store and self-model do not have individual TTLs. Their lifecycle is governed by:

### Semantic store
- **Promotion into active**: when a nightly reflection produces a semantic generalisation from ≥3 episodic records
- **Archival**: when all source episodic records have been archived and the derived semantic entry has not been reinforced in 365 days
- **Deletion**: only via user forget request propagation

### Self-model (SelfBelief records)
- **Created**: in nightly macro-cycle with initial confidence from reflection
- **Updated**: confidence delta applied per macro-cycle (max Δ +0.15, rate-limited)
- **Cooling trigger**: `confidence < 0.15` after decay
- **Archival**: 30 days in cooling; record is moved to archived self-model partition
- **Deletion**: only via operator persona reset

---

## 5) Retrieval Index Synchronisation

The retrieval index must be updated atomically with lifecycle state changes:

| Event | Index action |
|-------|-------------|
| Record enters `cooling` | Remove from default retrieval index |
| Record archived | Remove from archive-eligible retrieval scope; add to audit index |
| Record deleted | Remove all index entries; write tombstone |
| `decay_factor` updated | Update retrieval score weighting (no removal) |

Index updates are committed in the same transaction as the lifecycle state change. Partial updates (index changed but lifecycle not committed, or vice versa) must trigger rollback.

---

## 6) Decay Factor

`EpisodicEvent` records carry a `decay_factor` field (float, `[0.0, 1.0]`, default `1.0`) that modulates their retrieval weight over time without altering the record content.

Decay rule (applied at each nightly macro-cycle):

```
decay_factor = decay_factor * (1 - decay_rate_per_cycle)
```

Default `decay_rate_per_cycle = 0.005` (approximately 1% per week at nightly cadence).

Records with `decay_factor < 0.10` are flagged for cooling review at the next macro-cycle.

---

## 7) Compaction Pass (Nightly Macro-Cycle Step)

At step 8 of the nightly macro-cycle ("Goal review"), the memory module runs a compaction pass:

1. **Cooling candidates**: query all active records where TTL or importance threshold is breached; move to cooling
2. **Archival candidates**: query cooling records past archival threshold; move to cold partition
3. **Index sync**: update retrieval index for all state-changed records
4. **Decay update**: apply `decay_factor` update to all active episodic records
5. **Log**: emit compaction summary (records cooled, archived, decay updates applied) to cycle log

The compaction pass must complete before self-belief updates in the nightly cycle, so that archived source episodes are excluded from new reflection evidence.

---

## 8) What Is Never Stored

Per `self_editability_policy.md §3.4` (EPH class) and `drive_system.md §4`:

- **Desire objects** — ephemeral; never written to any persistent store
- **Appraisal results** — per-tick; discarded after use
- **Context packages** — per-turn; discarded after LLM render
- **Candidate responses** — per-turn; discarded on policy check completion or rollback
- **Salience buffer contents** — per-tick; rebuilt each tick

Only the **thought fragments** triggered by desires are stored (as episodic records with `trigger = desire` and `source_desire_drive` set).
