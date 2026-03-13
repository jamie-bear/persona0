/**
 * EmotionModule — EMA-based affect updates for n8n Code nodes.
 *
 * Translates src/engine/modules/emotion.py into JavaScript for use in
 * n8n workflow Code nodes.
 *
 * Steps per tick:
 *   1. EMA decay toward baseline for each affect variable
 *   2. Circadian energy modulation (cosine wave)
 *   3. Appraisal-driven deltas (goal-congruence → valence, threat → stress)
 *   4. Clamp all values to [-1.0, 1.0]
 */

// Default configuration (mirrors config/defaults.yaml [affect.*])
const AFFECT_DEFAULTS = {
  baseline: { valence: 0.10, arousal: 0.30, stress: 0.10, energy: 0.70 },
  decay_rate: { valence: 0.05, arousal: 0.08, stress: 0.06, energy: 0.04 },
  bounds: { min: -1.0, max: 1.0 },
  circadian: {
    energy_peak_hour: 10,
    energy_trough_hour: 15,
    energy_modulation_amplitude: 0.15,
  },
  stress_high_threshold: 0.70,
  stress_rest_need_boost: 0.01,
};

function ema(value, baseline, rate) {
  return value + (baseline - value) * rate;
}

function clamp(value, lo = -1.0, hi = 1.0) {
  return Math.max(lo, Math.min(hi, value));
}

/**
 * Update affect state for one fast tick.
 *
 * @param {Object} affect - Current affect state {valence, arousal, stress, energy}
 * @param {Array}  appraisalResults - Array of appraisal dicts from APPRAISE step
 * @param {number} tickCounter - Monotonic tick index (for circadian phase)
 * @param {Object} config - Optional config override
 * @returns {Object} Updated affect state
 */
function updateEmotion(affect, appraisalResults, tickCounter, config = null) {
  const cfg = config || AFFECT_DEFAULTS;
  const baseline = cfg.baseline;
  const decay = cfg.decay_rate;
  const bounds = cfg.bounds || { min: -1.0, max: 1.0 };
  const circ = cfg.circadian || {};

  // 1. EMA decay toward baseline
  let valence = ema(affect.valence, baseline.valence, decay.valence);
  let arousal = ema(affect.arousal, baseline.arousal, decay.arousal);
  let stress = ema(affect.stress, baseline.stress, decay.stress);
  let energy = ema(affect.energy, baseline.energy, decay.energy);

  // 2. Circadian energy modulation
  const fastIntervalS = 1800; // 30 minutes
  const ticksPerDay = Math.max(1, Math.round(86400 / fastIntervalS));
  const amplitude = circ.energy_modulation_amplitude || 0.15;
  const peakTick = (circ.energy_peak_hour || 10) * Math.round(ticksPerDay / 24);
  const phase =
    (2 * Math.PI * ((tickCounter % ticksPerDay) - peakTick)) / ticksPerDay;
  energy += amplitude * Math.cos(phase);

  // 3. Appraisal-driven deltas
  for (const appraisal of appraisalResults || []) {
    const goalCongruence = appraisal.goal_congruence || 0.0;
    const threat = appraisal.threat || 0.0;
    const arousalCue = appraisal.arousal_cue || 0.0;
    valence += goalCongruence * 0.1;
    stress += threat * 0.1;
    arousal += arousalCue * 0.05;
  }

  // 4. Clamp
  return {
    valence: clamp(valence, bounds.min, bounds.max),
    arousal: clamp(arousal, bounds.min, bounds.max),
    stress: clamp(stress, bounds.min, bounds.max),
    energy: clamp(energy, bounds.min, bounds.max),
  };
}

/**
 * Return additional rest_need growth when stress is high.
 */
function stressRestBoost(stress, config = null) {
  const cfg = config || AFFECT_DEFAULTS;
  const threshold = cfg.stress_high_threshold || 0.70;
  const boost = cfg.stress_rest_need_boost || 0.01;
  return stress > threshold ? boost : 0.0;
}

// ── n8n Code Node entry point ──────────────────────────────────────────────
// Reads state from previous node, applies emotion update, outputs updated state.
const items = $input.all();
const results = [];

for (const item of items) {
  const state = item.json.state || item.json;
  const appraisals = item.json.appraisals || [];
  const tickCounter = state.tick_counter || 0;

  const updatedAffect = updateEmotion(state.affect, appraisals, tickCounter);
  const restBoost = stressRestBoost(updatedAffect.stress);

  results.push({
    json: {
      ...item.json,
      state: {
        ...state,
        affect: updatedAffect,
      },
      _emotion_meta: {
        rest_boost: restBoost,
        circadian_tick: tickCounter,
      },
    },
  });
}

return results;
