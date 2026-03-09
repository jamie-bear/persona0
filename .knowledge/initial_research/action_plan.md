# Prototype Development Action Plan

* Version: 0.1
* Objective: Provide a practical roadmap for implementing and testing the ego‑perspective cognitive agent architecture defined in `architecture.md`, using the dataset strategy described in `ego_data.md`.

---

# 1. Purpose

This document defines a **rapid experimentation roadmap** for building a minimal working prototype of the ego‑perspective cognitive agent.

The primary goal is to **test the central thesis**:

> A believable artificial conversational agent can emerge from a system that combines autobiographical memory, emotional state, internal thoughts, and simulated time.

The plan prioritizes:

* minimal engineering overhead
* modular architecture
* observable internal state
* fast iteration cycles

---

# 2. Development Philosophy

The prototype should follow several principles.

### 2.1 Build the Smallest Cognitive Core

Only implement the modules necessary to support believable behavior:

* Memory System
* Emotion System
* Thought Generator
* Goal System
* Dialogue Context Builder

The LLM functions strictly as a **renderer of internal state**.

---

### 2.2 Maintain Explicit State

All agent state should be stored outside the LLM.

Examples:

```
agent_state.json
memories.json
goals.json
emotion_state.json
```

This ensures deterministic behavior and easier debugging.

---

### 2.3 Prioritize Observability

Every cognitive step should be logged.

Example log structure:

```
timestamp
cycle_type
emotion_state
new_thought
memory_written
```

Observability allows rapid diagnosis of unrealistic behavior.

---

# 3. Implementation Phases

## 3.1 Phase 1 — Cognitive Core Skeleton

Objective: Implement the basic cognitive loop.

Components to implement:

* memory storage
* emotion state model
* thought generation
* goal tracking

Minimal directory structure:

```
agent/

memory/
state/
modules/

main_loop.py
```

Core modules:

```
modules/

memory_system.py
emotion_system.py
thought_generator.py
goal_system.py
context_builder.py
```

---

## 3.2 Phase 2 — Dataset Bootstrapping

Objective: Generate the initial ego‑perspective dataset described in `ego_data.md`.

Steps:

1. generate synthetic episodic memories
2. generate internal thoughts
3. generate emotional reflections
4. generate goals and identity statements

Dataset storage example:

```
data/

memories.json
thoughts.json
reflections.json
goals.json
identity.json
```

Target dataset sizes:

| Type                  | Target |
| --------------------- | ------ |
| episodic memories     | 3k     |
| internal thoughts     | 10k    |
| emotional reflections | 2k     |
| goals                 | 300    |
| identity statements   | 150    |

---

## 3.3 Phase 3 — Time Simulation Loop

Objective: Allow the agent to "live" between conversations.

Create a scheduler that periodically runs a **cognitive cycle**.

Example cycle interval:

```
every 30 minutes
```

Cycle tasks:

```
update emotional state
generate internal thought
update goal progress
write memory
```

Pseudo‑loop:

```
while True:

    update_emotions()

    thought = generate_thought()

    update_goals()

    write_memory(thought)

    sleep(simulation_interval)
```

This process creates the **illusion of lived time**.

---

## 3.4 Phase 4 — Dialogue Interface

Objective: Connect the cognitive system to an LLM interface.

When a conversation begins:

The **Dialogue Context Builder** assembles relevant state.

Example prompt context:

```
Current mood: mildly curious

Recent thoughts:
"I keep wondering how people stay motivated."

Current goal:
"learn more about neuroscience"

Recent memory:
"I read an article about the brain yesterday."
```

The LLM then generates dialogue conditioned on this context.

Important constraint:

The LLM **cannot directly alter internal state**.

State updates must pass through architecture modules.

---

## 3.5 Phase 5 — Observational Testing

Objective: evaluate perceived realism.

Testing questions:

```
Does the agent appear to have a life outside the conversation?

Does it remember previous experiences?

Are emotional reactions consistent?
```

Collect qualitative feedback from testers.

---

# 4. Minimal Technology Stack

Recommended tools for the prototype:

| Component       | Tool              |
| --------------- | ----------------- |
| LLM             | Llama / Mistral   |
| Embeddings      | Instructor models |
| Vector database | Chroma            |
| State store     | JSON or SQLite    |
| Scheduler       | Python loop       |

This stack minimizes infrastructure requirements.

---

# 5. Experimental Metrics

Evaluation should prioritize **believability signals**.

Potential metrics:

```
perceived personality continuity
emotional consistency
memory recall accuracy
internal thought realism
```

Human observers should rate interactions on a scale such as:

```
"This feels like a person with a life."
```

---

# 6. Iteration Strategy

Development should follow a rapid iteration loop.

```
1 build minimal prototype
2 run continuous simulation
3 interact with the agent
4 observe unrealistic patterns
5 refine modules or dataset
6 repeat
```

Avoid early optimization.

---

# 7. Risk Areas

Common early failure modes:

```
memory fragmentation
emotional instability
goal oscillation
repetitive thoughts
```

These issues are expected during early experimentation.

---

# 8. Prototype Success Criteria

The prototype is considered successful if it demonstrates:

```
persistent autobiographical narrative
consistent emotional behavior
internally generated thoughts
sense of ongoing life between conversations
```

Full human realism is not required.

---

# 9. Suggested Timeline

Approximate timeline for a minimal prototype:

| Week | Milestone                     |
| ---- | ----------------------------- |
| 1    | implement cognitive core      |
| 2    | generate ego dataset          |
| 3    | run time simulation           |
| 4    | integrate dialogue interface  |
| 5    | conduct believability testing |

The timeline should remain flexible to accommodate rapid experimentation.

---

# 10. Future Expansion

Once the prototype demonstrates believable behavior, further research may explore:

```
social network simulation
habit formation
dream generation
multi‑agent interaction
body state simulation
```

These features should only be introduced after the baseline architecture proves effective.

---

# 11. Summary

This action plan provides a **minimal pathway to experimentally validate** the ego‑perspective cognitive architecture.

By combining structured autobiographical data, explicit internal state, and simulated time, the prototype aims to produce agents that appear to possess a coherent inner life while remaining computationally lightweight.
