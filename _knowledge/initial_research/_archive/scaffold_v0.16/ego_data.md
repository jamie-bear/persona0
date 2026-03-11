# Persona0 Ego Data Specification (Refined)

* Version: 0.15
* Purpose: define training/conditioning data that supports stable first-person continuity

---

## 1) Key corrections from v0.1

1. **Data category overlap** was too high (thoughts vs reflections vs memories).
2. **No provenance scoring** for synthetic vs human-authored material.
3. **No drift controls** to prevent exaggerated persona artifacts over time.
4. **No retention lifecycle** to prune stale or low-value entries.

v0.15 adds normalized schemas, provenance fields, and quality gates.

---

## 2) Data model overview

All records use shared metadata:

```yaml
meta:
  id: uuid
  created_at: ISO8601
  source_type: human|synthetic|derived
  source_ref: string
  confidence: 0.0..1.0
  privacy_tier: low|medium|high
  ttl_days: integer|null
```

### 2.1 Episodic event record

```yaml
episode:
  when: ISO8601
  context: {location: string, participants: [string]}
  event_text: string
  affect_snapshot: {valence: float, arousal: float, stress: float}
  goal_links: [goal_id]
  importance: 0.0..1.0
  reflection_pending: bool
```

### 2.2 Thought fragment record

```yaml
thought:
  trigger: internal|external|memory_recall
  text: string
  intrusiveness: 0.0..1.0
  relevance_goal_id: goal_id|null
```

### 2.3 Reflection record

```yaml
reflection:
  source_episode_ids: [uuid]
  pattern_statement: string
  confidence_delta: float
  proposed_self_belief_update: string|null
```

### 2.4 Goal record

```yaml
goal:
  label: string
  motive: string
  priority: 0.0..1.0
  horizon: short|medium|long
  progress: 0.0..1.0
  blocked_by: [string]
```

### 2.5 Self-model belief record

```yaml
self_belief:
  statement: string
  confidence: 0.0..1.0
  supporting_reflections: [uuid]
  last_challenged_at: ISO8601|null
```

---

## 3) Dataset composition targets (bootstrapping)

For initial offline corpus:

* episodic events: 1,000
* thought fragments: 4,000
* reflections: 500
* goals: 120
* self-beliefs: 80

Rationale: smaller, higher-quality set beats larger synthetic-heavy set for early behavior calibration.

---

## 4) Quality gates

Reject any record that fails one or more checks:

1. empty or generic affect signal,
2. no temporal anchor,
3. no relation to goals/self model,
4. duplicated near-clone content,
5. inconsistent pronoun perspective.

Additional synthetic gate:

* Keep synthetic ratio below 70% until human validation loop is running.

---

## 5) Drift prevention controls

* Cap daily self-belief updates.
* Require at least 2 independent reflections before raising confidence > 0.75.
* Decay confidence for unreinforced beliefs after N days.

---

## 6) Privacy and ethics controls

* Do not store sensitive user identifiers in long-term memory by default.
* Separate interaction logs from autobiographical abstraction layer.
* Attach deletion hooks by `source_ref` for user-requested erasure.

---

## 7) Data generation workflow

1. Seed from curated first-person micro-narratives.
2. Generate structured variants with strict templates.
3. Run lint checks + dedup + perspective check.
4. Human review sample (>=5%).
5. Import to staging store only.
6. Promote to production memory seed after acceptance metrics pass.
