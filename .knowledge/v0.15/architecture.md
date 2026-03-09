# Ego-Perspective Cognitive Agent Architecture

* Version: 0.15 (Revised from v0.1)
* Objective: Rapid validation of ego-perspective cognition hypothesis
* Changes from v0.1: Added Salience Gate, Appraisal module, Input Processor, memory retrieval policy, inter-module data flow, and formal cognitive loop reference.

---

## 1. Purpose

This document describes the architecture for a lightweight cognitive agent designed to produce believable human-like conversational behavior through persistent internal state.

The objective is to reproduce a minimal set of mechanisms sufficient for:

* autobiographical continuity
* emotional dynamics
* internal thought
* passage of time
* personal goals
* imperfect, selective reasoning

The conversational LLM serves as an interface layer only. The agent's "mind" is a separate system of state, memory, and deterministic processes.

---

## 2. Key Design Principles

### 2.1 Interface / Mind Separation

```
User Input
    |
    v
Input Processor (parse intent, affect cues, topic)
    |
    v
Cognitive Core (state, memory, appraisal, salience)
    |
    v
Dialogue Context Builder (assemble prompt context)
    |
    v
LLM Renderer (generate natural language)
    |
    v
Output to User
```

The LLM does not perform reasoning or state management. It renders responses conditioned on internal state provided by the Cognitive Core.

**v0.1 gap addressed:** The original architecture had no explicit Input Processor. User messages went directly to the "Dialogue Interface" with no specification of how conversational events update internal state. The Input Processor now converts user input into structured events that feed the Appraisal module.

### 2.2 Explicit Internal State

All state is stored externally, never inferred by the LLM at runtime.

Core state variables:

| Variable         | Type    | Range / Domain            |
|------------------|---------|---------------------------|
| valence          | float   | [-1.0, 1.0]              |
| arousal          | float   | [0.0, 1.0]               |
| energy           | float   | [0.0, 1.0]               |
| stress           | float   | [0.0, 1.0]               |
| curiosity        | float   | [0.0, 1.0]               |
| social_need      | float   | [0.0, 1.0]               |
| current_activity | string  | activity label            |
| recent_thoughts  | list    | last N thought fragments  |
| active_goals     | list    | goal objects              |

**v0.1 gap addressed:** Original state variables were listed as informal strings ("mood", "energy") without types, ranges, or semantics. Now formalized.

### 2.3 Autobiographical Continuity

The system maintains a structured personal history.

Memory types:

| Type        | Description                          | Update Frequency |
|-------------|--------------------------------------|-----------------|
| episodic    | specific events with time/place      | per event       |
| semantic    | learned knowledge and generalizations| via reflection  |
| emotional   | affective associations with entities | per appraisal   |
| self-model  | identity beliefs and trait patterns  | via reflection  |

### 2.4 Continuous Time Simulation

The agent "lives" between conversations via a scheduled cognitive loop.

Each tick performs (see `cognitive_loop.md` for formal specification):

```
1. ingest world events
2. appraise events against goals/identity
3. update emotional state
4. generate internal thought
5. evaluate salience
6. update goals
7. write memory
8. consolidate (on longer intervals)
```

### 2.5 Modularity and Observability

The architecture favors:

* explicit, typed interfaces between modules
* observable state transitions (full logging)
* deterministic pipelines (stochastic elements confined to specific, seeded RNG points)
* independent testability per module

---

## 3. High-Level System Architecture

```
                +--------------------------+
                |    External World        |
                | (news, time, weather)    |
                +-----------+--------------+
                            |
                            v
                +-----------+--------------+
                | World State Adapter      |
                +-----------+--------------+
                            |
                            v
+-----------------------------------------------------------+
|                    Cognitive Core                          |
|                                                           |
|  +----------------+  +---------------+  +--------------+  |
|  | Input Processor|  | Appraisal     |  | Thought Gen  |  |
|  | (user events)  |  | (event eval)  |  | (cognition)  |  |
|  +-------+--------+  +-------+-------+  +------+-------+  |
|          |                    |                  |          |
|          v                    v                  v          |
|  +-------+--------------------+-----------------+-------+  |
|  |              Salience Gate                           |  |
|  |  (attention selection: what surfaces, what stays     |  |
|  |   internal, what gets verbalized)                    |  |
|  +-------+----------------------------------------------+  |
|          |                                                 |
|          v                                                 |
|  +-------+--------+  +---------------+  +--------------+  |
|  | Emotion System |  | Goal System   |  | Self-Model   |  |
|  +-------+--------+  +-------+-------+  +------+-------+  |
|          |                    |                  |          |
|          v                    v                  v          |
|  +-------+--------------------+-----------------+-------+  |
|  |              Memory System                           |  |
|  |  episodic | semantic | emotional | self-narrative    |  |
|  +-------+----------------------------------------------+  |
|          |                                                 |
+----------+-------------------------------------------------+
           |
           v
+----------+--------------+
| Dialogue Context Builder|
+----------+--------------+
           |
           v
+----------+--------------+
|     LLM Renderer        |
+--------------------------+
```

---

## 4. Core Modules

### 4.1 Memory System

Central storage with structured retrieval.

Each memory record:

```json
{
  "id": "uuid",
  "type": "episodic | semantic | emotional | self_model",
  "timestamp": "ISO-8601",
  "content": "description string",
  "emotional_valence": {"valence": 0.0, "arousal": 0.0},
  "importance": 0.0,
  "entities": ["entity_id"],
  "access_count": 0,
  "last_accessed": "ISO-8601",
  "decay_factor": 1.0,
  "source": "experience | reflection | world_event | conversation"
}
```

#### Memory Retrieval Policy

**v0.1 gap addressed:** The original architecture described memory storage but had no retrieval algorithm. The retrieval score is now:

```
score(memory, query) =
    w_sim * cosine_similarity(embed(memory.content), embed(query))
  + w_rec * recency_decay(now - memory.timestamp)
  + w_imp * memory.importance
  + w_emo * emotional_resonance(memory.emotional_valence, current_emotion_state)
```

Default weights: `w_sim=0.4, w_rec=0.2, w_imp=0.2, w_emo=0.2`

Recency decay: `recency_decay(dt) = exp(-lambda * dt.total_hours())` where `lambda` is tunable.

Top-k memories are returned and passed to the Salience Gate for filtering.

#### Memory Consolidation

On longer intervals (daily), the system:
1. Clusters recent episodic memories by theme
2. Generates reflection summaries (semantic memories derived from episodic clusters)
3. Updates self-model if reflections indicate trait-relevant patterns
4. Applies decay to low-importance, low-access episodic memories

### 4.2 Emotion System

Emotion is a regulatory system, not a label.

State representation:

| Variable   | Type  | Dynamics                                      |
|------------|-------|-----------------------------------------------|
| valence    | float | Driven by appraisal output                    |
| arousal    | float | Driven by event novelty + stress              |
| stress     | float | Accumulates from negative appraisals, decays via rest |
| energy     | float | Depletes with activity, recovers with sleep/rest |
| curiosity  | float | Rises with novel stimuli, decays with satiation|
| social_need| float | Rises over time without interaction, drops after conversation |

#### Update Rules

**v0.1 gap addressed:** The original architecture used simplistic linear rules (`stress += workload * 0.3`). The v0.15 model uses bounded, interacting dynamics:

```python
# Bounded update with saturation
def update(current, delta, rate=0.1):
    new = current + delta * rate
    return max(0.0, min(1.0, new))

# Stress accumulates from appraisal, decays toward baseline
stress = update(stress, appraisal.threat_level - stress_baseline, rate=0.15)
stress = update(stress, -recovery_rate * is_resting, rate=0.1)

# Energy depletes and recovers
energy = update(energy, -activity_cost, rate=0.05)
energy = update(energy, sleep_recovery * is_sleeping, rate=0.2)

# Cross-variable interactions
# High stress reduces energy recovery
energy_recovery_modifier = 1.0 - (stress * 0.3)
# Low energy amplifies stress
stress_amplifier = 1.0 + max(0, 0.5 - energy) * 0.4
```

### 4.3 Appraisal Module

**v0.1 gap addressed:** This module was completely absent from the original architecture despite being identified as important in the research document (EMA model reference).

The Appraisal module evaluates events against the agent's goals and identity:

Input: an event (from user input, world events, or internal thoughts)

Output:
```json
{
  "relevance": 0.0,
  "goal_congruence": 0.0,
  "novelty": 0.0,
  "threat_level": 0.0,
  "social_significance": 0.0,
  "identity_relevance": 0.0
}
```

Appraisal can be implemented as:
- **Phase 1 (prototype):** Rule-based keyword/entity matching against active goals and self-model
- **Phase 2:** Small classifier trained on labeled examples
- **Phase 3:** LLM-assisted appraisal (using the renderer model with a structured prompt)

### 4.4 Thought Generator

Produces internal thoughts conditioned on current state.

Thought categories and their triggers:

| Category        | Trigger Conditions                        |
|-----------------|-------------------------------------------|
| reflection      | high importance event + low arousal        |
| planning        | active goal with low progress              |
| rumination      | high stress + unresolved negative event    |
| curiosity       | high curiosity + novel stimulus            |
| fantasy         | low arousal + low stress                   |
| self-evaluation | self-model conflict or identity-relevant event |
| social          | high social_need                           |

Generated thoughts are stored as episodic memories and fed back through the Salience Gate.

### 4.5 Goal System

Maintains active goals with richer dynamics than v0.1.

Goal structure:

```json
{
  "id": "uuid",
  "description": "string",
  "motivation": "string (why this matters)",
  "priority": 0.0,
  "progress": 0.0,
  "frustration": 0.0,
  "created": "ISO-8601",
  "deadline": "ISO-8601 | null",
  "status": "active | suspended | completed | abandoned",
  "parent_goal": "uuid | null",
  "conflicts_with": ["uuid"]
}
```

**v0.1 gap addressed:** Goals now support hierarchy (sub-goals), conflict tracking (competing goals), and status lifecycle. Goal frustration increases when progress stalls, which feeds back into the Emotion System and can trigger rumination in the Thought Generator.

### 4.6 Salience Gate

**New in v0.15.** This module was identified as important in the v0.1 research document (Global Workspace Theory) but was never implemented in the architecture.

The Salience Gate determines what content becomes "globally available" -- surfacing in thoughts, conversation, or behavioral decisions.

Inputs: candidate memories, thoughts, appraisal outputs, goal states
Output: ranked and filtered set of salient items

Salience scoring:

```
salience(item) =
    emotional_intensity(item) * 0.3
  + goal_relevance(item) * 0.3
  + recency(item) * 0.2
  + novelty(item) * 0.2
```

The gate enforces a **capacity limit** (e.g., top-5 items), simulating bounded attention. Items that pass the gate are available to the Dialogue Context Builder and the Thought Generator. Items that don't pass remain in memory but don't influence current behavior.

### 4.7 Input Processor

**New in v0.15.** Converts user messages into structured events for the Cognitive Core.

Output:

```json
{
  "raw_text": "user message",
  "detected_intent": "question | statement | request | emotional_expression | greeting | farewell",
  "topic_entities": ["entity"],
  "affect_cues": {"valence": 0.0, "arousal": 0.0},
  "references_past": true,
  "conversational_pressure": "low | medium | high"
}
```

Implementation: lightweight classifier or small LLM call (can reuse the renderer model with a parsing prompt).

### 4.8 Dialogue Context Builder

Assembles the prompt context for the LLM Renderer.

Draws from:
- Current emotional state (from Emotion System)
- Salient items (from Salience Gate, top-k)
- Active goals (from Goal System, filtered by relevance)
- Relevant memories (from Memory System, via retrieval policy)
- Input analysis (from Input Processor)
- Conversational policy hints (see below)

#### Conversational Policy

**v0.1 gap addressed:** The original architecture had no mechanism for conversational strategy. The agent needs rules for:

- **Sharing depth:** How much internal state to reveal (modulated by social_need and relationship familiarity)
- **Topic steering:** Whether to follow the user's topic or introduce own concerns (modulated by goal urgency)
- **Emotional expression:** Whether to express current emotion directly or mask it (modulated by stress and social context)
- **Memory reference:** When to bring up past events vs. stay in the present

These policies are represented as simple rules in the prototype, potentially learned in later versions.

### 4.9 LLM Renderer

The LLM receives structured context and generates natural language.

The LLM **cannot** modify internal state directly. All state changes pass through the Input Processor and Appraisal module based on the conversation that occurred.

After each conversation turn:
1. Input Processor analyzes the exchange
2. Appraisal evaluates the conversational event
3. Emotion System updates based on appraisal
4. Memory System logs the interaction as episodic memory
5. Goal System checks for goal-relevant information

---

## 5. Simulated Passage of Time

A scheduler runs the cognitive loop at configurable intervals.

### 5.1 Tick Intervals

| Interval    | Actions                                                |
|-------------|--------------------------------------------------------|
| 30 min      | thought generation, emotion update, goal check         |
| 2 hours     | activity change, routine event                         |
| Daily       | memory consolidation, reflection, daily diary          |
| Weekly      | self-model review, goal priority reassessment          |

### 5.2 Circadian Rhythm

```
06:00-08:00  wake, morning routine (energy rising)
08:00-12:00  primary activity (energy plateau)
12:00-13:00  midday break
13:00-17:00  secondary activity (energy declining)
17:00-20:00  evening leisure/social (stress recovering)
20:00-22:00  wind-down, reflection
22:00-06:00  sleep (energy recovery, memory consolidation, dream fragments)
```

Activity types and their effects on state variables should be defined in a configuration file.

---

## 6. Ego-Perspective Data Integration

Instead of baking ego-perspective data into model weights, the primary integration path is **retrieval memory**:

1. Ego-perspective episodes are stored in the Memory System
2. Retrieved by the retrieval policy based on conversational context
3. Surfaced through the Salience Gate
4. Included in dialogue context by the Context Builder

Fine-tuning (via LoRA/QLoRA) is reserved for **style calibration only** -- adjusting the renderer's tone, not its knowledge of the agent's life.

---

## 7. Minimal Prototype Stack

| Component        | Implementation         | Notes                        |
|------------------|------------------------|------------------------------|
| LLM Renderer     | Llama 3 8B or Mistral 7B | Via llama.cpp or vLLM       |
| Embeddings       | all-MiniLM-L6-v2 or similar | For memory retrieval      |
| Vector database  | ChromaDB               | Lightweight, embedded        |
| State store      | SQLite                 | Structured queries, ACID     |
| Scheduler        | Python asyncio loop    | With configurable intervals  |
| Appraisal        | Rule-based (phase 1)   | Upgrade to classifier later  |
| Input Processor  | Regex + small classifier| Or renderer model reuse     |

**v0.1 change:** Upgraded from JSON flat files to SQLite for state storage. JSON is fine for prototyping but breaks under concurrent access and lacks query capability.

---

## 8. Evaluation Metrics

| Metric                    | Method                              |
|---------------------------|-------------------------------------|
| Perceived continuity      | Human rating: "Does this feel like someone with a life?" |
| Emotional consistency     | Human rating + automated valence tracking |
| Memory recall coherence   | Automated: does agent reference correct past events? |
| Behavioral stability      | Automated: personality trait variance over time |
| Time passage believability| Human rating: "Does this agent experience time?" |

Use ACUTE-Eval comparative protocol for controlled human evaluation.

---

## 9. Development Strategy

See `action_plan.md` for detailed phasing.

Core loop:
```
1. build minimal cognitive core with cognitive loop
2. attach LLM renderer
3. run simulated time (observe emergent behavior)
4. bootstrap ego dataset based on observed gaps
5. conduct believability testing
6. refine modules based on results
```

---

## 10. Expected Failure Modes

| Failure Mode              | Cause                              | Mitigation                    |
|---------------------------|-------------------------------------|-------------------------------|
| Memory incoherence        | Contradictory episodic records      | Consistency checker in consolidation |
| Emotional oscillation     | Unbounded update rules              | Bounded dynamics + decay rates |
| Goal instability          | No frustration threshold            | Goal suspension after sustained frustration |
| Repetitive thoughts       | Low thought category diversity      | Category rotation + novelty bias |
| Flat affect               | Over-damped emotion dynamics        | Tune decay rates, add event amplification |
| Over-sharing              | No conversational policy            | Sharing depth modulation       |

---

## 11. Future Extensions

To be introduced only after validating the core architecture:

* Body simulation (hunger, pain, physical sensations)
* Social relationship modeling (familiarity, trust, history per entity)
* Dream generation (memory recombination during sleep cycles)
* Personality development (self-model drift over extended time)
* Habit learning (routine pattern detection and reinforcement)
* Multi-agent interaction
