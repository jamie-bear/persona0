# Ego-Perspective Cognitive Agent Architecture

* Version: 0.1 (Prototype Architecture)
* Objective: Rapid validation of ego-perspective cognition hypothesis

---

## 1. Purpose

This document describes the architecture for a lightweight cognitive agent system designed to generate believable human-like internal life and conversational behavior.

The goal is not full human simulation. Instead, the objective is to reproduce a minimal set of mechanisms sufficient for believable:

* internal thoughts
* emotional state
* autobiographical continuity
* passage of time
* personal goals
* imperfect reasoning

The conversational LLM serves primarily as an interface layer. The agent's "mind" exists as a separate system of state, memory, and processes.

---

## 2. Key Design Principles

### 2.1 Interface / Mind Separation

Conversation generation must be decoupled from cognition.

```
User
 ↓
Dialogue Interface
 ↓
Cognitive State + Memory
 ↓
LLM Renderer
```

The LLM does not perform the underlying reasoning or state management. It renders responses conditioned on internal state.

### 2.2 Explicit Internal State

Human-like believability depends on persistent state.

Core state variables include:

```
mood
energy
stress
curiosity
goals
current activity
recent thoughts
relationships
```

State is stored explicitly rather than inferred implicitly by the LLM.

### 2.3 Autobiographical Continuity

The system maintains a personal narrative history.

Memory types:

| Type       | Description            |
| ---------- | ---------------------- |
| episodic   | specific events        |
| semantic   | learned knowledge      |
| emotional  | affective associations |
| self-model | identity beliefs       |

### 2.4 Continuous Time Simulation

The agent continues to "live" between conversations.

The system periodically simulates:

```
thought generation
activity changes
memory consolidation
mood drift
goal updates
```

### 2.5 Small Modular Components

Following modular agent design principles, the architecture favors:

* explicit tools
* modular services
* observable state transitions
* deterministic pipelines

This improves debuggability, interpretability, and iteration speed.

---

## 3. High-Level System Architecture

```
                ┌──────────────────────┐
                │   External World     │
                │ (news, time, events) │
                └──────────┬───────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │   World State Adapter  │
               └──────────┬─────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│                   Cognitive Core                     │
│                                                      │
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Emotion Sys  │  │ Goal System │  │ Thought Gen │  │
│  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘  │
│         │                 │                │         │
│         ▼                 ▼                ▼         │
│              ┌───────────────────────┐               │
│              │   Memory System       │               │
│              │                       │               │
│              │ episodic              │               │
│              │ semantic              │               │
│              │ emotional             │               │
│              │ self narrative        │               │
│              └──────────┬────────────┘               │
│                         │                            │
└─────────────────────────┼────────────────────────────┘
                          │
                          ▼
               ┌────────────────────────┐
               │ Dialogue Context       │
               │ Builder                │
               └──────────┬─────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  LLM Renderer   │
                 └─────────────────┘
```

---

## 4. Core Modules

### 4.1 Memory System

Memory acts as the central organizing structure.

Directory structure example:

```
memory/
    episodic/
    semantic/
    emotional/
    identity/
```

Each memory record contains:

```
timestamp
event description
emotional valence
importance
associated entities
```

Example memory entry:

```
memory_event:
"I argued with a colleague today."

emotion:
    frustration: 0.7
    sadness: 0.2

importance: 0.6
```

### 4.2 Emotion System

Emotion drives behavior and thought selection.

Minimal emotional state representation:

```
valence
arousal
stress
curiosity
attachment
```

State evolves through:

```
events
memories
internal thoughts
time decay
```

Example update rule:

```
stress += workload * 0.3
mood += positive_memory * 0.4
```

### 4.3 Thought Generator

Produces internal thoughts periodically.

Thought categories:

```
reflection
planning
rumination
curiosity
fantasy
self-evaluation
```

Example output:

```
"I wonder if I should call my sister."
```

Generated thoughts are stored as episodic memory.

### 4.4 Goal System

Maintains active goals.

Example structure:

```
goal:

description: improve career
priority: 0.7
frustration: 0.3
progress: 0.2
```

Goals influence:

```
thought generation
emotional updates
activity choices
```

### 4.5 World State Adapter

Imports external signals such as:

```
time of day
weather
news
calendar events
```

These inputs may trigger:

```
thoughts
memories
activities
mood shifts
```

Example:

```
Rain → reflective mood
```

### 4.6 Dialogue Context Builder

When conversation begins the system assembles contextual state:

```
recent thoughts
current emotional state
recent activities
relevant memories
active goals
```

Example prompt context:

```
Current mood: slightly tired but curious
Recent thought: "I should learn more about neuroscience"
Current activity: browsing articles
```

### 4.7 LLM Renderer

The LLM receives structured context and generates:

* dialogue responses
* internal monologue (optional)
* behavioral decisions

Constraint:

The LLM cannot modify internal state directly. All state changes must pass through explicit modules.

---

## 5. Simulated Passage of Time

A scheduler periodically runs life simulation cycles.

Example interval loop:

```
every 30 minutes:
    generate thought
    update emotional state
    progress goals
    write memory
```

Daily rhythm example:

```
morning: planning
day: activity
evening: reflection
night: memory consolidation
```

---

## 6. Ego-Perspective Data Integration

Instead of generic web text, training data emphasizes first-person cognition such as:

```
diaries
internal monologues
life reflections
decision reasoning
emotional narratives
```

Example formats:

```
"I felt embarrassed after the meeting."

"I keep thinking about whether I made the right choice."
```

Such data strengthens:

* introspection
* autobiographical reasoning
* emotional coherence

---

## 7. Minimal Prototype Stack

| Component       | Implementation    |
| --------------- | ----------------- |
| LLM             | Mistral or Llama  |
| Vector database | Chroma            |
| Scheduler       | Python loop       |
| State store     | JSON or SQLite    |
| Embeddings      | Instructor models |

---

## 8. Evaluation Metrics

Success metrics focus on perceived believability rather than raw intelligence.

Possible measures:

```
perceived continuity
emotional consistency
memory recall coherence
behavior stability
```

Human testers should rate questions such as:

```
"Does this feel like a person with a life?"
```

---

## 9. Development Strategy

Follow an iterative prototype loop:

```
1 build minimal cognition
2 attach LLM interface
3 run simulated time
4 observe emergent behavior
5 refine modules
```

Avoid premature scaling.

---

## 10. Future Extensions

Potential expansions include:

```
body simulation
social relationships
dream generation
personality development
habit learning
```

These should only be introduced after validating the core architecture.

---

## 11. Expected Failure Modes

Early systems may exhibit:

```
memory incoherence
emotional oscillation
goal instability
```

These behaviors are expected during early experimentation.

---

## 12. Conclusion

Believable artificial agents likely require:

```
persistent identity
emotional dynamics
autobiographical memory
time-based cognition
```

This architecture provides a minimal experimental platform for testing whether these components are sufficient to produce the perception of a living mind.
