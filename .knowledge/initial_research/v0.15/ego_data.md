# Ego-Perspective Training Data Specification

* Version: 0.15 (Revised from v0.1)
* Objective: Define the structure, sources, and generation strategy for ego-perspective datasets used in the cognitive agent architecture.
* Changes from v0.1: Added global consistency constraints, lifecycle management, quality gates, anti-degeneration strategy, and formal schema definitions.

---

## 1. Purpose

This document defines the ego-perspective dataset layer used by the cognitive agent architecture described in `architecture.md`.

The dataset provides structured representations of:

* autobiographical experiences
* internal thoughts
* emotional interpretation
* personal goals
* identity beliefs

These elements populate the Memory System to simulate a continuous subjective inner life.

**Critical design decision:** Ego data is consumed primarily through **retrieval** (RAG-style), not through fine-tuning. Fine-tuning is reserved for style calibration only. This avoids catastrophic forgetting and keeps the agent's life history editable and traceable.

---

## 2. Design Goals

The ego-perspective dataset should support believable first-person cognition.

Required characteristics:

| Characteristic        | Description                                           |
|-----------------------|-------------------------------------------------------|
| First-person stance   | All records use "I" perspective                       |
| Subjective framing    | Events described through personal interpretation      |
| Emotional grounding   | Affect states accompany all experiential records       |
| Incomplete knowledge  | The agent doesn't know everything; uncertainty is explicit |
| Temporal continuity   | Records form a coherent timeline                      |
| Imperfect reasoning   | Self-justifications, biases, and contradictions appear naturally |

The dataset emphasizes **how humans think**, not only **what humans know**.

---

## 3. Data Categories

| Category              | Architecture Module | Purpose                    | Primary Use         |
|-----------------------|---------------------|----------------------------|---------------------|
| episodic memories     | Memory System       | personal experiences       | retrieval           |
| internal thoughts     | Thought Generator   | spontaneous cognition      | retrieval + seeding |
| emotional reflections | Emotion System      | affective reasoning        | retrieval           |
| goals and plans       | Goal System         | intentional behavior       | state initialization|
| identity statements   | Self-Model          | stable personality anchors | state initialization|
| relationship records  | Memory System       | social context             | retrieval           |

**v0.1 addition:** Relationship records are now a formal category, since social context is critical for believable conversation and was missing from v0.1.

---

## 4. Core Data Types

### 4.1 Episodic Memory Entries

```json
{
  "id": "uuid",
  "type": "episodic_memory",
  "timestamp": "2025-06-11T14:30:00Z",
  "location": "office",
  "people_involved": ["coworker_mark"],
  "event_description": "I had an uncomfortable meeting about the project timeline.",
  "emotion_state": {
    "valence": -0.4,
    "arousal": 0.5,
    "stress": 0.6
  },
  "importance": 0.7,
  "reflection": "I keep thinking I should have prepared better.",
  "tags": ["work", "conflict", "self-doubt"],
  "consistency_group": "career_arc_2025"
}
```

**v0.1 changes:**
- Formal JSON schema with types (was informal pseudo-YAML)
- Added `consistency_group` to link related memories and prevent contradictions
- Emotion state uses the dimensional model (valence/arousal) matching architecture.md
- Added `tags` for thematic retrieval

### 4.2 Internal Thought Fragments

```json
{
  "id": "uuid",
  "type": "thought_fragment",
  "timestamp": "2025-06-11T16:00:00Z",
  "content": "Maybe I should start exercising again.",
  "category": "planning",
  "trigger": "low_energy_state",
  "emotional_context": {
    "valence": -0.1,
    "arousal": 0.2
  }
}
```

Characteristics: short, incomplete, emotionally contextual.

**v0.1 change:** Added `category` and `trigger` fields so thoughts can be matched to the Thought Generator's category system (see architecture.md section 4.4).

### 4.3 Emotional Reflection Records

```json
{
  "id": "uuid",
  "type": "emotional_reflection",
  "timestamp": "2025-06-11T21:00:00Z",
  "trigger_event_id": "uuid_of_episode",
  "emotion": {
    "valence": -0.5,
    "arousal": 0.3,
    "dominant_label": "sadness"
  },
  "interpretation": "I feel like I might have been too defensive.",
  "reappraisal": "But maybe I was just stressed and it wasn't that bad.",
  "resolution": "unresolved"
}
```

**v0.1 change:** Added `reappraisal` (how the agent might revise the emotional interpretation over time) and `resolution` status. This supports the architecture's reflection/consolidation cycle.

### 4.4 Goals and Planning Statements

```json
{
  "id": "uuid",
  "type": "goal",
  "description": "learn more about neuroscience",
  "motivation": "I want to understand how the brain works",
  "priority": 0.6,
  "progress": 0.2,
  "frustration": 0.1,
  "status": "active",
  "created": "2025-05-01T00:00:00Z",
  "deadline": null,
  "parent_goal": null,
  "conflicts_with": []
}
```

**v0.1 change:** Schema now matches the Goal System in architecture.md (added `status`, `created`, `deadline`, `parent_goal`, `conflicts_with`).

### 4.5 Identity Statements

```json
{
  "id": "uuid",
  "type": "identity_statement",
  "content": "I tend to overthink decisions.",
  "confidence": 0.8,
  "domain": "cognitive_style",
  "evidence_memories": ["uuid_1", "uuid_2"],
  "stability": "stable"
}
```

**v0.1 change:** Identity statements now link to supporting evidence (episodic memories) and have confidence/stability scores. This supports the self-model update mechanism in the architecture: if contradicting evidence accumulates, stability drops and the statement may be revised during reflection.

### 4.6 Relationship Records (New)

```json
{
  "id": "uuid",
  "type": "relationship",
  "entity_id": "coworker_mark",
  "entity_label": "Mark from work",
  "relationship_type": "colleague",
  "familiarity": 0.6,
  "trust": 0.4,
  "valence": 0.1,
  "history_summary": "We've worked together for about a year. Sometimes tense about deadlines.",
  "last_interaction": "2025-06-11T14:30:00Z"
}
```

---

## 5. Global Consistency Constraints

**New in v0.15.** The v0.1 specification had no mechanism to prevent contradictory life histories. Randomization without constraints produces impossible timelines and inconsistent personalities.

### 5.1 Life Skeleton

Before generating any ego data, define a **life skeleton** -- a small set of fixed biographical facts:

```yaml
birth_year: 1995
gender: non-specified  # or specified per persona
education_level: college_graduate
career_domain: technology
relationship_status: single
location_history:
  - {period: "childhood", location: "suburban midwest"}
  - {period: "college", location: "east coast city"}
  - {period: "current", location: "west coast city"}
core_traits:
  - introspective
  - curious
  - conflict-averse
core_values:
  - honesty
  - growth
  - independence
```

All generated memories must be consistent with the life skeleton. The skeleton is immutable during a generation run.

### 5.2 Timeline Validation

After generation, validate:

1. No event references a person/place/job before the relationship/residency/employment began
2. Emotional arcs are plausible (no instant recovery from major events)
3. Age-appropriate experiences at each timeline point
4. No contradictory facts about the same entity/event

### 5.3 Personality Coherence

Generated memories should reflect the core traits with some variance:

- A conflict-averse agent shouldn't have frequent aggressive confrontations
- An introspective agent should have more reflection entries than average
- Variance is allowed (personality isn't perfectly consistent), but the center of mass should match the trait profile

---

## 6. Dataset Generation Strategies

### 6.1 Authentic Sources

* Historical diaries and memoir excerpts (public domain)
* Reflective blog posts and personal essays
* Oral history transcripts

These capture natural first-person cognitive patterns. Use for calibration and style reference, not as raw training data.

### 6.2 Synthetic Ego Generation

Use LLMs with structured prompts, but with anti-degeneration controls:

**Anti-degeneration strategy (v0.1 gap addressed):**

1. **Diverse prompt templates:** Rotate across 50+ prompt variants to avoid repetitive patterns
2. **Human-written seeds:** At least 20% of episodic memories should be human-written or human-edited
3. **Multiple generator models:** Use 2-3 different models to prevent single-model artifacts
4. **Post-generation deduplication:** Embed all records and remove near-duplicates (cosine similarity > 0.92)
5. **Human review sample:** Review a random 10% sample for quality

Example prompt template:

```
Write a short first-person memory about [CATEGORY] from the perspective
of someone who is [TRAIT_1] and [TRAIT_2].

The memory should:
- describe a specific moment, not a generalization
- include what was felt physically or emotionally
- end with an incomplete or ambiguous thought
- be 2-4 sentences

Context: [LIFE_SKELETON_EXCERPT]
```

### 6.3 Structured Life Simulation

Generate life timelines by period:

```
childhood  -> formative memories, family dynamics
education  -> learning experiences, social development
early career -> professional identity, competence anxiety
current life -> daily routines, active relationships, ongoing goals
```

Each period produces episodic memories, relationship records, and identity-relevant reflections.

---

## 7. Quantitative Randomization (Within Constraints)

Randomizable parameters per persona:

| Parameter          | Range           | Constraint                     |
|--------------------|-----------------|--------------------------------|
| trait intensity     | [0.3, 0.9]     | must match core_traits direction |
| stress baseline    | [0.1, 0.5]     | affects all stress-related memories |
| social_need baseline| [0.2, 0.8]    | affects social memory frequency |
| memory detail level| [low, med, high]| consistent within a persona    |
| emotional volatility| [0.1, 0.7]    | affects emotion range in memories|

---

## 8. Data Formatting

All records use JSON with the schemas defined in section 4.

Storage structure:

```
data/
  personas/
    persona_001/
      skeleton.yaml
      memories.jsonl
      thoughts.jsonl
      reflections.jsonl
      goals.json
      identity.json
      relationships.json
  shared/
    prompt_templates/
    validation_rules/
```

**v0.1 change:** Moved from flat file lists to persona-scoped directories. Using JSONL (one record per line) for large collections to support streaming ingestion.

---

## 9. Dataset Scale

| Data Type              | MVP Target | Notes                          |
|------------------------|-----------|--------------------------------|
| episodic memories      | 2k-5k    | covering 2-3 years of simulated life |
| internal thoughts      | 5k-10k   | diverse categories             |
| emotional reflections  | 1k-3k    | linked to episodic memories    |
| goals                  | 50-100   | active + completed + abandoned |
| identity statements    | 50-100   | with evidence links            |
| relationship records   | 20-50    | with history summaries         |

**v0.1 change:** Reduced identity/goal counts (original was 100-500 which is unrealistic for a coherent persona) and added relationship records. Quality over quantity.

---

## 10. Integration with Architecture

| Data Type              | Consumed By              | Integration Method        |
|------------------------|--------------------------|---------------------------|
| episodic memories      | Memory System            | Loaded into vector DB     |
| internal thoughts      | Thought Generator        | Seed corpus for generation|
| emotional reflections  | Emotion System + Memory  | Retrieved during appraisal|
| goals                  | Goal System              | State initialization      |
| identity statements    | Self-Model               | State initialization      |
| relationship records   | Memory System            | Entity-linked retrieval   |

The Dialogue Context Builder retrieves relevant entries via the Memory Retrieval Policy (see architecture.md section 4.1).

---

## 11. Quality Gates

**New in v0.15.** Before ego data enters the system, it must pass:

1. **Schema validation:** All required fields present and correctly typed
2. **Timeline consistency:** No temporal paradoxes within a persona
3. **Personality coherence:** Statistical check that trait-relevant memories match the trait profile (within 2 standard deviations)
4. **Deduplication:** No near-duplicate records
5. **Emotional plausibility:** Emotion values are within expected ranges for the described event type
6. **Entity consistency:** All referenced people/places exist in the relationship/location records

---

## 12. Iterative Dataset Improvement

```
1. generate initial dataset with life skeleton constraints
2. load into Memory System and run agent simulations
3. log retrieval patterns (what gets retrieved, what never surfaces)
4. observe unrealistic behaviors in conversation
5. identify gaps (missing memory types, underrepresented emotions)
6. add targeted corrective records
7. prune low-quality or never-retrieved records
8. repeat
```

**v0.1 change:** Added retrieval monitoring and pruning steps. The original workflow only added data; it never removed low-value records, leading to retrieval noise over time.

---

## 13. Summary

Ego-perspective datasets provide the subjective structure of experience required for believable cognitive agents. By emphasizing first-person memories, reflections, and goals -- constrained by a coherent life skeleton and validated by quality gates -- the system approximates narrative continuity while remaining computationally lightweight and editable.

The key v0.15 insight: **ego data quality depends on global consistency, not volume.** A smaller, coherent dataset outperforms a larger, contradictory one.
