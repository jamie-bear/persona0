# Prototype Development Action Plan

* Version: 0.15 (Revised from v0.1)
* Objective: Provide a practical roadmap for implementing and testing the ego-perspective cognitive agent architecture defined in `architecture.md`, using the dataset strategy described in `ego_data.md` and the cognitive loop defined in `cognitive_loop.md`.
* Changes from v0.1: Reordered phases (architecture before data), added feedback loops between phases, concrete deliverables per phase, risk mitigations, and go/no-go criteria.

---

## 1. Purpose

This document defines a rapid experimentation roadmap for building a minimal working prototype of the ego-perspective cognitive agent.

The primary goal is to test the central thesis:

> A believable artificial conversational agent can emerge from a system that combines autobiographical memory, emotional state, internal thoughts, and simulated time -- with the LLM serving only as a language renderer.

### Priorities

1. Validate the cognitive loop before scaling data
2. Maintain observable internal state at every step
3. Iterate in short cycles with concrete evaluation
4. Avoid premature optimization or scaling

---

## 2. Development Philosophy

### 2.1 Architecture First, Data Second

**v0.1 gap addressed:** The original plan placed dataset generation (Phase 2) before the time simulation loop (Phase 3). This is backwards -- you cannot know what data the system needs until you see it running. The corrected order:

1. Build the cognitive loop
2. Run it with minimal seed data
3. Observe what's missing
4. Generate targeted data to fill gaps

### 2.2 Explicit State, Always

All agent state stored outside the LLM in structured storage (SQLite + vector DB). Every cognitive tick produces a log entry. No hidden state.

### 2.3 Go/No-Go Gates

Each phase ends with explicit criteria that must be met before proceeding. This prevents building on broken foundations.

---

## 3. Implementation Phases

### Phase 1: Cognitive Core Skeleton

**Objective:** Implement the cognitive loop (see `cognitive_loop.md`) with stub modules.

**Deliverables:**
- `agent/modules/memory_system.py` -- CRUD + retrieval with scoring
- `agent/modules/emotion_system.py` -- bounded state updates with decay
- `agent/modules/appraisal.py` -- rule-based event evaluation
- `agent/modules/thought_generator.py` -- category-based generation
- `agent/modules/goal_system.py` -- goal lifecycle management
- `agent/modules/salience_gate.py` -- attention filtering
- `agent/modules/input_processor.py` -- user input parsing
- `agent/modules/context_builder.py` -- prompt assembly
- `agent/core/cognitive_loop.py` -- orchestrator implementing the tick cycle
- `agent/core/scheduler.py` -- time-based tick scheduling
- `agent/state/schema.sql` -- SQLite schema for state + memory
- `agent/config/defaults.yaml` -- tunable parameters (decay rates, weights, intervals)

**Directory structure:**

```
agent/
  core/
    cognitive_loop.py
    scheduler.py
  modules/
    memory_system.py
    emotion_system.py
    appraisal.py
    thought_generator.py
    goal_system.py
    salience_gate.py
    input_processor.py
    context_builder.py
  state/
    schema.sql
  config/
    defaults.yaml
  tests/
    test_memory.py
    test_emotion.py
    test_appraisal.py
    test_cognitive_loop.py
```

**Go/No-Go criteria:**
- [ ] Cognitive loop runs 100 ticks without error
- [ ] State variables remain within bounds across all ticks
- [ ] Memory retrieval returns relevant results for test queries
- [ ] Emotion dynamics show plausible rise/decay patterns
- [ ] All modules have unit tests passing

**Estimated duration:** 1-2 weeks

---

### Phase 2: Minimal Seed Data + Time Simulation

**Objective:** Run the cognitive loop with minimal ego data and observe emergent behavior.

**Deliverables:**
- Life skeleton for one test persona (`data/personas/test_001/skeleton.yaml`)
- 200 hand-written or hand-curated episodic memories
- 50 internal thought seeds
- 20 identity statements
- 10 goals (mix of active/completed/abandoned)
- 10 relationship records
- Time simulation running for 7 simulated days
- Observation log documenting emergent behaviors and anomalies

**Key activities:**
1. Load seed data into Memory System
2. Initialize Emotion System and Goal System from seed data
3. Run scheduler for 7 simulated days at accelerated clock
4. Log every cognitive tick (state snapshots, generated thoughts, memory writes)
5. Manually review logs for:
   - Repetitive thought patterns
   - Emotional oscillation or flatness
   - Memory retrieval relevance
   - Goal progress dynamics

**Go/No-Go criteria:**
- [ ] Agent generates diverse thought categories (not just one type)
- [ ] Emotional state shows circadian-like patterns
- [ ] Memory retrieval surfaces contextually relevant memories
- [ ] No state variable gets stuck at 0 or 1 for extended periods
- [ ] Generated thoughts reference actual memories (not hallucinated ones)

**Estimated duration:** 1 week

---

### Phase 3: LLM Renderer Integration

**Objective:** Connect the cognitive core to an LLM for natural language conversation.

**Deliverables:**
- LLM renderer module (`agent/modules/llm_renderer.py`)
- Prompt templates for dialogue generation
- Input Processor implementation (can reuse renderer model)
- Post-conversation state update pipeline
- 5 sample conversations demonstrating state-conditioned responses

**Key activities:**
1. Set up local LLM inference (Llama 3 8B or Mistral 7B via llama.cpp/vLLM)
2. Implement Context Builder prompt assembly
3. Implement Input Processor (parse user messages into structured events)
4. Implement post-conversation feedback loop:
   - User message -> Input Processor -> Appraisal -> Emotion update -> Memory write
5. Test that identical user inputs produce different responses based on agent state

**Go/No-Go criteria:**
- [ ] Agent responses reflect current emotional state
- [ ] Agent references actual memories from its history
- [ ] Same question at different times/states produces different responses
- [ ] Post-conversation state updates are observable and plausible
- [ ] Agent does not hallucinate memories not in its store

**Estimated duration:** 1-2 weeks

---

### Phase 4: Ego Data Expansion

**Objective:** Generate a full ego dataset using the strategies in `ego_data.md`, informed by gaps observed in Phases 2-3.

**Deliverables:**
- Expanded dataset per `ego_data.md` section 9 targets
- Quality gate validation results
- Gap analysis report (what memory types were missing, what emotions were underrepresented)
- Updated seed data addressing identified gaps

**Key activities:**
1. Review Phase 2-3 observation logs to identify:
   - Memory types never retrieved (candidates for removal)
   - Situations where agent had no relevant memory (candidates for generation)
   - Emotional states never reached (missing triggers)
   - Goals that were unreferenced
2. Generate targeted ego data using templates from `ego_data.md` section 6
3. Run quality gates from `ego_data.md` section 11
4. Reload Memory System and re-run Phase 2 simulation
5. Compare behavior before and after data expansion

**Go/No-Go criteria:**
- [ ] Quality gates pass for all generated data
- [ ] Retrieval coverage improves (fewer "no relevant memory" situations)
- [ ] No increase in contradictory or repetitive behavior
- [ ] Memory retrieval noise does not increase

**Estimated duration:** 1-2 weeks

---

### Phase 5: Believability Testing

**Objective:** Evaluate perceived realism through structured human testing.

**Deliverables:**
- Test protocol document
- 10+ test conversations with diverse scenarios
- Tester evaluation forms (using adapted ACUTE-Eval questions)
- Comparative evaluation: ego-engine agent vs. bare LLM baseline
- Results analysis and findings report

**Testing protocol:**
1. Recruit 5-10 testers (can be informal for MVP)
2. Each tester conducts 2 conversations:
   - One with the ego-engine agent
   - One with the same LLM in stateless chatbot mode
   - Order randomized, tester blinded to which is which
3. After each conversation, tester rates on 5-point scale:
   - "This felt like talking to someone with a life"
   - "This person's emotions felt consistent and real"
   - "This person seemed to remember things naturally"
   - "I got the sense that time passes for this person"
4. After both conversations, comparative preference:
   - "Which conversation felt more like talking to a real person?"

**Go/No-Go criteria:**
- [ ] Ego-engine agent preferred over baseline in >60% of comparisons
- [ ] No tester reports "this feels broken or incoherent"
- [ ] At least 3/4 evaluation dimensions score above midpoint

**Estimated duration:** 1-2 weeks

---

## 4. Technology Stack

| Component        | Tool                    | Selection Rationale              |
|------------------|-------------------------|----------------------------------|
| LLM Renderer     | Llama 3 8B / Mistral 7B| Open-weight, runs locally        |
| Embeddings       | all-MiniLM-L6-v2        | Fast, good quality for retrieval |
| Vector DB        | ChromaDB                | Embedded, no infrastructure      |
| State store      | SQLite                  | ACID, queryable, single-file     |
| Scheduler        | Python asyncio          | Lightweight, configurable        |
| Inference server | llama.cpp / vLLM        | Efficient local inference        |
| Testing          | pytest                  | Standard, familiar               |

---

## 5. Risk Register

| Risk                           | Likelihood | Impact | Mitigation                                |
|--------------------------------|-----------|--------|-------------------------------------------|
| LLM ignores context           | Medium    | High   | Prompt engineering, test with multiple models |
| Memory retrieval noise         | High      | Medium | Tune retrieval weights, add quality gates  |
| Emotional dynamics too flat    | Medium    | High   | Tune decay/amplification rates early       |
| Computational cost too high    | Low       | High   | Use quantized models, batch inference      |
| Testers can't distinguish      | Medium    | High   | Improve evaluation protocol, longer conversations |
| Scope creep                    | High      | Medium | Strict go/no-go gates between phases       |

---

## 6. Iteration Strategy

After Phase 5, the development enters a continuous improvement loop:

```
1. identify weakest believability dimension from testing
2. trace to specific module(s) responsible
3. implement targeted fix (tune parameters, add data, refine logic)
4. re-run relevant simulation tests
5. re-run believability evaluation on the specific dimension
6. repeat
```

Do not add new modules or features until the core loop demonstrates reliable believability.

---

## 7. Success Criteria

The prototype is successful if it demonstrates:

| Criterion                          | Evidence                                    |
|------------------------------------|---------------------------------------------|
| Persistent autobiographical narrative | Agent references past events accurately   |
| Consistent emotional behavior      | Emotion state tracks plausibly across time  |
| Internally generated thoughts      | Thoughts are diverse and contextually relevant |
| Sense of ongoing life              | Testers perceive life outside conversation  |
| Measurable improvement over baseline| ACUTE-Eval preference > 60% over bare LLM  |

Full human realism is not required. The bar is **noticeable, measurable improvement** over a stateless LLM baseline.

---

## 8. Summary

This action plan provides a minimal, feedback-driven pathway to experimentally validate the ego-perspective cognitive architecture. The key v0.15 correction is ordering: build the cognitive loop first, observe its behavior, then generate data to fill gaps. Each phase has concrete deliverables and go/no-go criteria to prevent building on broken foundations.
