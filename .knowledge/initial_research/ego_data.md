# Ego-Perspective Training Data Specification

* Version: 0.1
* Objective: Define the structure, sources, and generation strategy for ego-perspective datasets used in the cognitive agent architecture.

---

# 1. Purpose

This document defines the **ego-perspective dataset layer** used by the cognitive agent architecture described in `architecture.md`.

The dataset provides structured representations of:

* autobiographical experiences
* internal thoughts
* emotional interpretation
* personal goals
* identity beliefs

These elements allow the architecture to simulate a **continuous subjective inner life**.

The goal is not to replicate full human cognition, but to provide **minimal experiential priors** that support believable behavior.

---

# 2. Design Goals

The ego-perspective dataset should train or condition models to produce believable **first-person cognition**.

Desired characteristics:

* first-person perspective
* subjective interpretation of events
* emotional reflection
* incomplete knowledge
* temporal continuity
* imperfect reasoning

The dataset should emphasize **how humans think**, rather than only **what humans know**.

---

# 3. Data Categories

The dataset is organized into cognitive data types that map directly to the architecture modules.

| Category              | Architecture Module | Purpose                    |
| --------------------- | ------------------- | -------------------------- |
| episodic memories     | Memory System       | personal experiences       |
| internal thoughts     | Thought Generator   | spontaneous cognition      |
| emotional reflections | Emotion System      | affective reasoning        |
| goals and plans       | Goal System         | intentional behavior       |
| identity statements   | Self Model          | stable personality anchors |

---

# 4. Core Data Types

## 4.1 Episodic Memory Entries

Episodic memories describe events from the perspective of the agent.

Structure:

```
timestamp
event_description
location
people_involved
emotion_state
importance_score
reflection
```

Example:

```
timestamp: 2025-06-11

location: office

people_involved:
- coworker

event_description:
"I had an uncomfortable meeting about the project timeline."

emotion_state:
  stress: 0.6
  frustration: 0.5

importance_score: 0.7

reflection:
"I keep thinking I should have prepared better."
```

These entries populate the **episodic memory store** described in `architecture.md`.

---

## 4.2 Internal Thought Fragments

Internal thoughts represent short cognitive impulses produced during time simulation.

Examples:

```
"Maybe I should start exercising again."

"I wonder why that conversation bothered me so much."

"I should finish reading that article later."
```

Characteristics:

* short
* incomplete
* emotionally contextual

These support the **Thought Generator** module.

---

## 4.3 Emotional Reflection Records

These describe the subjective interpretation of emotional states.

Structure:

```
trigger_event
emotion
intensity
interpretation
```

Example:

```
trigger_event: argument with friend

emotion:
  sadness: 0.7

interpretation:
"I feel like I might have been too defensive."
```

These records stabilize the **Emotion System**.

---

## 4.4 Goals and Planning Statements

Goals represent intentional behavior and long-term direction.

Structure:

```
goal_description
motivation
priority
progress
frustration
```

Example:

```
goal_description:
"learn more about neuroscience"

motivation:
"I want to understand how the brain works"

priority: 0.6
progress: 0.2
frustration: 0.1
```

These entries are consumed by the **Goal System**.

---

## 4.5 Identity Statements

Identity statements describe stable beliefs about the self.

Examples:

```
"I tend to overthink decisions."

"I like learning new ideas even if they confuse me at first."

"I prefer quiet environments to crowded places."
```

These populate the **self-model memory layer**.

---

# 5. Dataset Generation Strategies

The dataset can be produced using several complementary approaches.

## 5.1 Diary Sources

Authentic sources include:

* historical diaries
* memoir excerpts
* reflective blog posts
* personal essays

These sources capture natural first-person cognitive patterns.

---

## 5.2 Synthetic Ego Generation

Synthetic records can be generated using language models.

Example prompt template:

```
Write a short first-person memory about a small everyday event.

Include:

- the event
- the emotions felt
- a brief reflection afterward
```

Example output:

```
"I spilled coffee on my notebook this morning. I felt annoyed at first, but later I realized I was rushing too much."
```

Synthetic generation should randomize across:

* locations
* social situations
* emotional states
* life contexts

This prevents repetitive cognitive patterns.

---

## 5.3 Structured Life Simulation

Another approach is generating **life timelines**.

Example life segments:

```
childhood event
education experience
career situation
social relationship
personal conflict
```

Each event can produce multiple memories and reflections.

This method produces coherent autobiographical datasets.

---

# 6. Quantitative Randomization

To avoid rigid personalities, datasets should introduce controlled randomness.

Randomizable parameters:

```
personality traits
life goals
social networks
stress levels
curiosity levels
```

These parameters generate agents with varied behavioral tendencies.

---

# 7. Data Formatting

Recommended storage formats:

```
JSON
YAML
Markdown
```

Example JSON memory record:

```
{
  "type": "episodic_memory",
  "timestamp": "2026-01-15",
  "event": "had coffee with a friend",
  "emotion": {
    "joy": 0.6,
    "calm": 0.4
  },
  "importance": 0.3,
  "reflection": "It felt good to talk about things openly."
}
```

These records can be indexed by the **Memory System** described in `architecture.md`.

---

# 8. Dataset Scale

A believable prototype does not require massive datasets.

Suggested dataset sizes for an MVP:

| Data Type             | Suggested Count |
| --------------------- | --------------- |
| episodic memories     | 2k–10k          |
| internal thoughts     | 5k–20k          |
| emotional reflections | 1k–5k           |
| goals                 | 200–500         |
| identity statements   | 100–300         |

These sizes are sufficient for early experimentation.

---

# 9. Integration with Architecture

The dataset feeds directly into modules defined in `architecture.md`.

| Data Type             | Consumed By       |
| --------------------- | ----------------- |
| episodic memories     | Memory System     |
| internal thoughts     | Thought Generator |
| emotional reflections | Emotion System    |
| goals                 | Goal System       |
| identity statements   | Self Model        |

The **Dialogue Context Builder** retrieves relevant entries when constructing prompts.

---

# 10. Evaluation of Dataset Quality

Indicators of high-quality ego-perspective data include:

```
natural emotional transitions
realistic internal doubts
imperfect reasoning
temporal continuity
```

Poor datasets often produce agents that appear **omniscient or overly rational**.

---

# 11. Iterative Dataset Improvement

The dataset should evolve alongside the architecture.

Recommended workflow:

```
1 generate initial dataset
2 run agent simulations
3 observe unrealistic behaviors
4 add corrective memory patterns
5 repeat
```

Over time the dataset becomes a **cognitive prior** guiding believable behavior.

---

# 12. Future Dataset Extensions

Possible expansions include:

```
relationship histories
conflict narratives
habit formation logs
dream narratives
internal debates
```

These additions can strengthen the perception of a persistent inner life.

---

# 13. Summary

Ego-perspective datasets provide the **subjective structure of experience** required for believable cognitive agents.

By emphasizing first-person memories, reflections, and goals, the system can approximate the narrative continuity of human thought while remaining computationally lightweight.
