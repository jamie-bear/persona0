# Persona0 Drive & Motivation System

* Version: 0.17
* Status: research-grade specification
* Scope: formal specification of the Drive/Motivation module — filling the gap left by drives being distributed across the Emotion module in prior versions

---

## 1) Why This Document Exists

In v0.15 and v0.16, drive variables (`social_need`, `mastery_need`, `rest_need`, `curiosity`) appear in the canonical state schema under `drives:` but are effectively treated as part of the affect system. No specification exists for:

- How drives *grow* over time without satisfaction
- What events or activities *satisfy* each drive
- The distinction between a **goal** (intentional, long-horizon) and a **desire** (spontaneous, short-horizon, affect-triggered)
- How a persistent unsatisfied drive can crystallize into a new goal

The v0.15 `cognitive_loop.md` includes an `IMPULSE_CHECK` step that fires thoughts when drives exceed thresholds, but this mechanism is informal and absent from v0.16. This document formalizes the Drive/Motivation module as a first-class component.

---

## 2) Conceptual Distinction: Drive vs. Goal vs. Desire

| Concept | Definition | Horizon | Origin | Persistence |
|---|---|---|---|---|
| **Drive** | A homeostatic need variable (0.0–1.0) that grows when unmet and decays when satisfied | Continuous | Biological/structural | Persistent in state |
| **Desire** | A spontaneous, short-horizon "want" generated when a drive exceeds a threshold | Short (expires after N ticks) | Drive-triggered | Ephemeral (not stored) |
| **Goal** | An intentional, long-horizon objective with progress tracking | Medium–long | Deliberate formation or drive crystallization | Persistent in goal store |

A **desire** is not yet a commitment. It is a pull. If a desire is acted on, the drive reduces. If a desire persists unmet across multiple ticks, it may crystallize into a formal goal.

---

## 3) Drive Variables

The following drives are formally tracked in `agent_state.drives`:

| Variable | Grows when... | Satisfied by... | Natural growth rate (per fast tick) |
|---|---|---|---|
| `social_need` | Time passes without social interaction | Conversation with another entity | +0.04 |
| `mastery_need` | Time passes without completing tasks or learning | Accomplishing a goal step, acquiring new knowledge | +0.02 |
| `rest_need` | Sustained high arousal or stress; waking hours accumulate | Sleep, low-stimulation idle time | +0.03 |
| `curiosity` | Exposure to novel topics; low stimulation | Exploring a new topic, reading, creative activity | +0.01 (baseline decay −0.02 after satisfaction) |

All drives are bounded `[0.0, 1.0]`. Drive updates are applied **after** emotion updates in the fast tick, so appraisal results can modulate them.

### Drive satisfaction events (formal mapping)

```yaml
satisfaction_map:
  social_need:
    satisfied_by: [conversation, social_activity, group_event]
    reduction_per_event: 0.25
  mastery_need:
    satisfied_by: [goal_progress, task_completion, learning_episode]
    reduction_per_event: 0.20
  rest_need:
    satisfied_by: [sleep, low_arousal_idle_period]
    reduction_per_event: 0.40
  curiosity:
    satisfied_by: [reading, exploring_topic, creative_activity]
    reduction_per_event: 0.30
```

These values belong in `config/defaults.yaml`.

---

## 4) Desire Objects

A **desire** is an ephemeral, drive-triggered record that represents a spontaneous motivational pull. Desires are generated in memory during the tick but are **not persisted** to the episodic log — they exist only within the current tick's working state.

```yaml
desire:
  id: uuid                        # local tick-scoped identifier
  source_drive: social_need       # which drive triggered this
  content: string                 # natural-language description of the want
  urgency: 0.0..1.0               # maps to drive level at time of generation
  approach: bool                  # true = approach desire; false = avoidance
  expires_after_ticks: int        # how many background ticks before it lapses
  created_at_tick: int
```

**Approach desire example:**
```yaml
desire:
  source_drive: social_need
  content: "want to reach out to someone I haven't spoken to in a while"
  urgency: 0.78
  approach: true
  expires_after_ticks: 3
```

**Avoidance desire example:**
```yaml
desire:
  source_drive: rest_need
  content: "want to avoid any more demands right now"
  urgency: 0.82
  approach: false
  expires_after_ticks: 2
```

Desires that go unsatisfied for `expires_after_ticks` ticks are discarded. Impulse thoughts generated from desires *are* stored in episodic memory (as thought fragments), but the desire object itself is not.

---

## 5) Drive → Goal Crystallization

When a desire persists across `crystallization_threshold` ticks without satisfaction, the Drive module may propose a new Goal for review.

```
IF desire.age_in_ticks >= crystallization_threshold
AND desire.urgency >= crystallization_urgency_min
AND no existing active goal satisfies the same drive:
    propose new_goal = {
        label: derived from desire.content,
        motive: desire.source_drive,
        priority: desire.urgency * 0.6,  # dampened — goals start lower priority than desires feel
        horizon: "short",
        progress: 0.0
    }
    submit new_goal to goal_system.review()
```

The goal system may accept or reject the proposal based on conflict with existing goals. This prevents desire-flood from inflating the goal register.

Configuration defaults:
```yaml
drives:
  crystallization_threshold_ticks: 6   # ~3 hours at slow-tick cadence
  crystallization_urgency_min: 0.65
```

---

## 6) Drive Module Placement in the Cognitive Loop

The Drive module owns `agent_state.drives`. It runs **after emotion updates** and **before thought generation** in the fast tick and slow tick.

### Fast tick additions (step 3.5, inserted after UPDATE_EMOTION):

```
3.5. UPDATE_DRIVES
     - For each drive variable:
       drive += growth_rate[drive]
       drive = clamp(drive, 0.0, 1.0)
     - For each activity event in current tick:
       if activity.type in satisfaction_map[drive]:
         drive -= satisfaction_map[drive].reduction_per_event
         drive = clamp(drive, 0.0, 1.0)
```

### Slow tick additions (step 4, replacing informal IMPULSE_CHECK):

```
4. DESIRE_GENERATION
   active_desires = []
   for drive_name, drive_value in current_state.drives:
     threshold = config.drives.impulse_threshold[drive_name]
     if drive_value >= threshold:
       desire = drive_module.generate_desire(
         drive=drive_name,
         value=drive_value,
         current_goals=current_state.goals,
         current_activity=current_state.current_activity
       )
       active_desires.append(desire)

   # Check for crystallization
   for desire in persisted_desires_from_previous_ticks:
     if desire.age_in_ticks >= crystallization_threshold:
       goal_system.propose(goal_from_desire(desire))

   current_state.active_desires = active_desires

   # Desires feed into Thought Generator (next step)
```

Impulse thresholds per drive (default):
```yaml
drives:
  impulse_threshold:
    social_need: 0.65
    mastery_need: 0.70
    rest_need: 0.70
    curiosity: 0.75
```

---

## 7) Effect on Thought Generator

The Thought Generator (step 4 in the fast tick) now receives `active_desires` in addition to `current_state.emotion` and `current_state.goals`:

| Desire source | Generated thought category |
|---|---|
| `social_need` (approach) | `social` |
| `social_need` (avoidance) | `rumination` |
| `mastery_need` (approach) | `planning` |
| `mastery_need` (avoidance) | `self-evaluation` (blocked progress) |
| `rest_need` (approach) | `fantasy` (escapist) |
| `curiosity` (approach) | `curiosity` |

This makes desire-driven thoughts distinguishable from pure affect-driven thoughts in the episodic log via the `trigger` field.

---

## 8) Module Interface

```python
class DriveModule:
    def update_drives(
        self,
        drives: DriveState,
        activity_events: List[ActivityEvent],
        time_elapsed: float
    ) -> DriveState:
        """Apply growth and satisfaction updates."""

    def generate_desire(
        self,
        drive: str,
        value: float,
        current_goals: List[Goal],
        current_activity: Activity
    ) -> Optional[Desire]:
        """Generate a desire object if drive exceeds threshold."""

    def check_crystallization(
        self,
        persisted_desires: List[Desire],
        current_goals: List[Goal]
    ) -> List[GoalProposal]:
        """Propose new goals from long-unmet desires."""
```

---

## 9) Anti-Patterns to Avoid

- **LLM generating desires directly** — desires must come from drive state, not from the model
- **Persisting desire objects** — desires are ephemeral; impulse *thoughts* are what get stored
- **Drive satisfaction without an event** — satisfaction only occurs on mapped activity events, not on passage of time
- **Crystallization flooding** — limit to one new goal proposal per slow tick per drive
