# Cognitive Loop Specification

* Version: 0.15
* Status: New document (not present in v0.1)
* Purpose: Define the formal tick-by-tick execution cycle of the Ego Engine cognitive core.

---

## 1. Why This Document Exists

The v0.1 architecture described individual modules (Memory, Emotion, Thought Generator, Goal System) but never specified **how they interact within a single cognitive cycle**. This is the most critical gap in the original design: without a defined loop, the modules are just components with no orchestration.

This document defines:
- The exact sequence of operations per cognitive tick
- The data that flows between modules at each step
- The different tick types (fast, slow, conversational)
- Entry/exit conditions for each phase

---

## 2. Tick Types

The cognitive loop runs at three frequencies, each performing a different scope of work:

| Tick Type      | Interval     | Purpose                                  |
|----------------|-------------|------------------------------------------|
| **fast_tick**  | 30 minutes   | Thought generation, emotion drift, state maintenance |
| **slow_tick**  | 2-4 hours    | Activity changes, routine events, goal review |
| **daily_tick** | Once per day  | Memory consolidation, reflection, self-model review, daily diary |

Additionally, a **conversation_tick** runs on-demand whenever a user interaction occurs.

---

## 3. Fast Tick (every 30 minutes)

The fast tick maintains the agent's ongoing internal life between conversations.

### Execution Sequence

```
FAST_TICK(current_state, memory_store, clock):

  1. WORLD_INGEST
     - Query World State Adapter for new events since last tick
     - events = world_adapter.get_recent(since=last_tick_time)

  2. APPRAISE
     - For each event in events:
       appraisal = appraisal_module.evaluate(
         event=event,
         active_goals=current_state.goals,
         self_model=current_state.identity,
         current_emotion=current_state.emotion
       )
     - Collect appraisal_results[]

  3. UPDATE_EMOTION
     - For each appraisal in appraisal_results:
       current_state.emotion = emotion_system.update(
         current=current_state.emotion,
         appraisal=appraisal,
         time_elapsed=tick_interval
       )
     - Apply time-based decay (stress recovery, energy drain/recovery)
     - Apply circadian modulation (time-of-day effects on energy, arousal)

  4. GENERATE_THOUGHT
     - Select thought category based on current state:
       category = thought_generator.select_category(
         emotion=current_state.emotion,
         goals=current_state.goals,
         recent_thoughts=current_state.recent_thoughts
       )
     - Retrieve relevant memories for context:
       context_memories = memory_store.retrieve(
         query=category_seed_query(category),
         emotion_state=current_state.emotion,
         top_k=3
       )
     - Generate thought:
       thought = thought_generator.generate(
         category=category,
         context_memories=context_memories,
         emotion=current_state.emotion,
         goals=current_state.goals
       )

  5. SALIENCE_FILTER
     - Collect candidates: new events + appraisals + generated thought
     - salient_items = salience_gate.filter(
         candidates=candidates,
         current_emotion=current_state.emotion,
         active_goals=current_state.goals,
         capacity=5
       )
     - Update current_state.recent_thoughts with salient items

  6. UPDATE_GOALS
     - For each goal in current_state.goals:
       goal_system.tick(
         goal=goal,
         appraisals=appraisal_results,
         emotion=current_state.emotion
       )
     - Increment frustration for stalled goals
     - Check for goal suspension/abandonment thresholds

  7. WRITE_MEMORY
     - Store generated thought as episodic memory
     - Store any significant appraisals as episodic memories
     - memory_store.append(thought_as_memory)

  8. LOG
     - Write full tick state snapshot to observation log
     - Include: timestamp, emotion_state, thought, salient_items, goal_states

  RETURN current_state
```

### Data Flow Diagram (Fast Tick)

```
World Events ──> [Appraisal] ──> appraisal_results
                      |                    |
                      v                    v
              [Emotion Update] <── time decay + circadian
                      |
                      v
              [Thought Generator] <── Memory Retrieval
                      |
                      v
              [Salience Gate] ──> salient_items
                      |
                      v
              [Goal Update] <── appraisal_results
                      |
                      v
              [Memory Write] ──> new episodic record
                      |
                      v
                   [Log]
```

---

## 4. Slow Tick (every 2-4 hours)

The slow tick handles activity transitions and routine events.

### Execution Sequence

```
SLOW_TICK(current_state, memory_store, clock):

  1. RUN fast_tick first (inherits all fast_tick steps)

  2. ACTIVITY_TRANSITION
     - Determine current circadian phase (morning/day/evening/night)
     - Select activity appropriate to:
       - time of day
       - energy level
       - active goals
       - day of week (weekday/weekend patterns)
     - new_activity = activity_selector.choose(
         time=clock.current_time(),
         energy=current_state.emotion.energy,
         goals=current_state.goals,
         current_activity=current_state.current_activity
       )
     - Generate activity event:
       event = create_activity_event(
         old=current_state.current_activity,
         new=new_activity
       )
     - current_state.current_activity = new_activity

  3. ROUTINE_EVENT
     - Based on activity, generate a routine experience:
       routine = routine_generator.generate(
         activity=new_activity,
         emotion=current_state.emotion,
         randomness_seed=clock.current_time()
       )
     - Store as episodic memory

  4. IMPULSE_CHECK
     - Check if any drive exceeds impulse threshold:
       if current_state.emotion.social_need > 0.7:
         generate social impulse thought
       if current_state.emotion.curiosity > 0.8:
         generate curiosity-driven impulse
       if current_state.emotion.stress > 0.8:
         generate intrusive/ruminative thought

  RETURN current_state
```

---

## 5. Daily Tick (once per day, typically during "sleep")

The daily tick performs memory consolidation and reflection.

### Execution Sequence

```
DAILY_TICK(current_state, memory_store, clock):

  1. MEMORY_CONSOLIDATION
     - Retrieve all episodic memories from the past 24 hours
     - Cluster by theme (using embedding similarity)
     - For each cluster:
       reflection = reflection_generator.synthesize(
         memories=cluster,
         self_model=current_state.identity,
         goals=current_state.goals
       )
       memory_store.append(reflection, type="semantic")

  2. DAILY_DIARY
     - Generate DRM-style diary entry summarizing the day:
       diary = diary_generator.create(
         day_memories=today_memories,
         emotion_trajectory=today_emotion_log,
         activities=today_activities
       )
     - Store as episodic memory with high importance

  3. SELF_MODEL_REVIEW
     - Check if any reflections suggest identity-relevant patterns:
       for each reflection:
         if identity_relevance(reflection) > threshold:
           update_or_create_identity_statement(reflection)
     - Check stability of existing identity statements against recent evidence

  4. GOAL_REVIEW
     - Review all active goals:
       for each goal:
         if goal.frustration > abandonment_threshold:
           consider goal suspension or abandonment
         if goal.progress >= 1.0:
           mark as completed, generate completion memory
     - Reprioritize remaining goals based on current state

  5. MEMORY_DECAY
     - Apply decay to old, low-importance, low-access memories:
       for each memory older than decay_window:
         memory.decay_factor *= decay_rate
     - Memories below decay_threshold are not deleted but become
       much less likely to be retrieved

  6. SLEEP_SIMULATION
     - Reset energy toward baseline (modulated by stress)
     - Reduce stress by recovery rate
     - Optionally generate dream fragment:
       if random() < dream_probability:
         dream = dream_generator.create(
           recent_memories=high_importance_memories,
           unresolved_emotions=unresolved_reflections
         )
         memory_store.append(dream, type="episodic", subtype="dream")

  RETURN current_state
```

---

## 6. Conversation Tick (on-demand, during user interaction)

The conversation tick runs for each turn of a user conversation. It integrates the conversation into the cognitive system.

### Pre-Conversation Setup

```
CONVERSATION_START(current_state, memory_store, user_message):

  1. PARSE_INPUT
     - input_analysis = input_processor.parse(user_message)
     - Extract: intent, topic_entities, affect_cues, references_past

  2. APPRAISE_CONVERSATION
     - appraisal = appraisal_module.evaluate(
         event=conversation_event(input_analysis),
         active_goals=current_state.goals,
         self_model=current_state.identity,
         current_emotion=current_state.emotion
       )

  3. UPDATE_EMOTION (from conversation event)
     - current_state.emotion = emotion_system.update(
         current=current_state.emotion,
         appraisal=appraisal,
         time_elapsed=0  # immediate
       )

  4. RETRIEVE_CONTEXT
     - relevant_memories = memory_store.retrieve(
         query=input_analysis.topic_entities + input_analysis.raw_text,
         emotion_state=current_state.emotion,
         top_k=5
       )

  5. SALIENCE_FILTER
     - salient_items = salience_gate.filter(
         candidates=relevant_memories + current_state.recent_thoughts,
         current_emotion=current_state.emotion,
         active_goals=current_state.goals,
         capacity=5
       )

  6. DETERMINE_POLICY
     - policy = conversation_policy.select(
         emotion=current_state.emotion,
         relationship=get_relationship(user_entity),
         appraisal=appraisal,
         goals=current_state.goals
       )
     - Policy controls: sharing_depth, topic_steering, emotional_expression

  7. BUILD_CONTEXT
     - prompt_context = context_builder.assemble(
         emotion=current_state.emotion,
         salient_items=salient_items,
         relevant_memories=relevant_memories,
         active_goals=filtered_goals,
         policy=policy,
         input_analysis=input_analysis
       )

  8. RENDER
     - response = llm_renderer.generate(prompt_context)

  RETURN response, current_state
```

### Post-Turn Update

```
CONVERSATION_POST_TURN(current_state, memory_store, user_message, agent_response):

  1. LOG_EXCHANGE
     - memory_store.append(
         type="episodic",
         content=summarize_exchange(user_message, agent_response),
         emotion_state=current_state.emotion,
         importance=appraisal.relevance,
         source="conversation"
       )

  2. UPDATE_RELATIONSHIP
     - Update familiarity, trust, valence for the user entity
       based on conversation quality signals

  3. GOAL_CHECK
     - Check if conversation contained goal-relevant information
     - Update goal progress if applicable
```

---

## 7. Module Interface Contracts

Each module must implement these interfaces:

### Appraisal Module
```python
def evaluate(event, active_goals, self_model, current_emotion) -> AppraisalResult
```

### Emotion System
```python
def update(current, appraisal, time_elapsed) -> EmotionState
def apply_decay(current, time_elapsed, circadian_phase) -> EmotionState
```

### Thought Generator
```python
def select_category(emotion, goals, recent_thoughts) -> ThoughtCategory
def generate(category, context_memories, emotion, goals) -> Thought
```

### Salience Gate
```python
def filter(candidates, current_emotion, active_goals, capacity) -> List[SalientItem]
```

### Memory System
```python
def retrieve(query, emotion_state, top_k) -> List[Memory]
def append(memory) -> None
def consolidate(time_window) -> List[Reflection]
def apply_decay(decay_window, decay_rate, decay_threshold) -> None
```

### Goal System
```python
def tick(goal, appraisals, emotion) -> Goal
def review_all(goals, emotion) -> List[Goal]
```

### Input Processor
```python
def parse(user_message) -> InputAnalysis
```

### Context Builder
```python
def assemble(emotion, salient_items, relevant_memories, active_goals, policy, input_analysis) -> PromptContext
```

### LLM Renderer
```python
def generate(prompt_context) -> str
```

---

## 8. State Invariants

The cognitive loop must maintain these invariants at all times:

1. **Bounded state:** All float state variables remain in [0.0, 1.0] (or [-1.0, 1.0] for valence)
2. **Monotonic time:** Tick timestamps are strictly increasing
3. **Memory immutability:** Episodic memories are append-only; existing records are never modified (only decay_factor changes)
4. **Goal consistency:** A goal cannot be both "active" and "completed"
5. **Salience capacity:** The salience gate never outputs more than `capacity` items
6. **Thought diversity:** The thought generator should not produce the same category more than 3 consecutive ticks
7. **No orphan references:** All entity references in memories must correspond to known entities

---

## 9. Configurability

All numeric parameters are externalized to `config/defaults.yaml`:

```yaml
tick_intervals:
  fast_tick_minutes: 30
  slow_tick_hours: 2
  daily_tick_hour: 23  # 11 PM

emotion:
  stress_decay_rate: 0.05
  energy_drain_rate: 0.02
  energy_recovery_rate: 0.15
  social_need_growth_rate: 0.01
  curiosity_decay_rate: 0.03

memory:
  retrieval_top_k: 5
  retrieval_weights:
    similarity: 0.4
    recency: 0.2
    importance: 0.2
    emotional_resonance: 0.2
  recency_decay_lambda: 0.01
  consolidation_cluster_threshold: 0.75
  decay_window_days: 30
  decay_rate: 0.95
  decay_threshold: 0.1

salience:
  capacity: 5
  emotional_intensity_weight: 0.3
  goal_relevance_weight: 0.3
  recency_weight: 0.2
  novelty_weight: 0.2

thought:
  max_consecutive_same_category: 3
  dream_probability: 0.3

goals:
  frustration_increment: 0.05
  abandonment_threshold: 0.9
  suspension_threshold: 0.7

circadian:
  wake_hour: 6
  sleep_hour: 22
  peak_energy_hour: 10
  low_energy_hour: 15
```

---

## 10. Observability and Debugging

Every tick produces a structured log entry:

```json
{
  "tick_id": "uuid",
  "tick_type": "fast | slow | daily | conversation",
  "timestamp": "ISO-8601",
  "emotion_state_before": {},
  "emotion_state_after": {},
  "events_ingested": [],
  "appraisal_results": [],
  "thought_generated": {},
  "salient_items": [],
  "goals_updated": [],
  "memories_written": [],
  "state_invariant_violations": []
}
```

A **state invariant violation** is logged but does not crash the system. Instead, the violating value is clamped and the violation is flagged for review. This supports rapid experimentation while maintaining safety.

---

## 11. Summary

The cognitive loop is the heartbeat of the Ego Engine. It transforms the static module descriptions in `architecture.md` into a running system with defined execution order, explicit data flow, typed interfaces, and observable state transitions. Without this specification, the modules are components without orchestration.

The three tick frequencies (fast/slow/daily) create a layered temporal experience: moment-to-moment thought, hourly activity rhythms, and daily reflection cycles. The conversation tick integrates user interaction into this ongoing cognitive process rather than treating conversation as a separate system.
