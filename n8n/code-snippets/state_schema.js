/**
 * Persona0 Agent State Schema — n8n Code Node adaptation
 *
 * This module defines the complete agent state structure used across all
 * Persona0 n8n workflows. Import this schema into any Code node that
 * needs to read or modify agent state.
 *
 * Reference: src/schema/state.py
 */

/**
 * Create a fresh default agent state.
 * Call this once at bootstrap, then persist to your chosen store.
 */
function createDefaultState(personaConfig = {}) {
  return {
    // CONST — loaded from persona config at bootstrap; never modified at runtime
    persona: {
      name: personaConfig.name || "",
      schema_version: "0.1",
      primary_language: personaConfig.primary_language || "en",
      core_values: personaConfig.core_values || [],
      hard_limits: personaConfig.hard_limits || [],
      founding_traits: personaConfig.founding_traits || [],
      voice_style: personaConfig.voice_style || {},
      disclosure_policy: personaConfig.disclosure_policy || {},
      privacy_tier_defaults: personaConfig.privacy_tier_defaults || {},
    },

    // SELF — Ego Engine adaptive state
    affect: {
      valence: 0.10,
      arousal: 0.30,
      stress: 0.10,
      energy: 0.70,
    },

    drives: {
      social_need: 0.20,
      mastery_need: 0.15,
      rest_need: 0.10,
      curiosity: 0.30,
    },

    self_model: {
      beliefs: [],
    },

    goals: [],

    activity: {
      current_activity: "idle",
    },

    // EPH — ephemeral, cleared each tick
    attention: {
      current_focus: null,
      salience_buffer: [],
    },

    active_desires: [],
    persisted_desires: [],
    consecutive_thought_categories: [],

    // Safety / governance
    safety: {
      disclosure_last_shown_at: null,
    },

    // Versioning
    state_schema_version: "0.1",
    tick_counter: 0,
  };
}

/**
 * Seed self-model beliefs from founding traits in the persona constitution.
 */
function seedBeliefsFromConstitution(state) {
  if (state.self_model.beliefs.length > 0) return state;

  state.self_model.beliefs = (state.persona.founding_traits || []).map(
    (trait, index) => ({
      id: `const-seed-${String(index + 1).padStart(3, "0")}`,
      statement: trait.statement,
      confidence: trait.initial_confidence || 0.55,
      supporting_reflections: [],
      last_challenged_at: null,
      stability: null,
      source_type: "CONST_SEED",
    })
  );

  return state;
}

/**
 * Clear ephemeral fields at the end of a tick/turn.
 */
function clearEphemeral(state) {
  state.attention = { current_focus: null, salience_buffer: [] };
  state.active_desires = [];
  return state;
}

/**
 * Get only active goals from state.
 */
function activeGoals(state) {
  return state.goals.filter((g) => g.status === "active");
}

// Export for use in n8n Code nodes
return { createDefaultState, seedBeliefsFromConstitution, clearEphemeral, activeGoals };
