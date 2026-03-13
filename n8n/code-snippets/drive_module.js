/**
 * DriveModule — homeostatic drive growth, satisfaction, desire generation,
 * and desire→goal crystallization for n8n Code nodes.
 *
 * Translates src/engine/modules/drive.py into JavaScript.
 *
 * Reference: drive_system.md §3-§5, config/defaults.yaml [drives.*]
 */

const DRIVE_NAMES = ["social_need", "mastery_need", "rest_need", "curiosity"];

// Default configuration (mirrors config/defaults.yaml [drives.*])
const DRIVES_DEFAULTS = {
  growth_rate: {
    social_need: 0.04,
    mastery_need: 0.02,
    rest_need: 0.03,
    curiosity: 0.01,
  },
  impulse_threshold: {
    social_need: 0.65,
    mastery_need: 0.7,
    rest_need: 0.7,
    curiosity: 0.75,
  },
  satisfaction_map: {
    social_need: {
      satisfied_by: ["conversation", "social_activity", "group_event"],
      reduction_per_event: 0.25,
    },
    mastery_need: {
      satisfied_by: ["goal_progress", "task_completion", "learning_episode"],
      reduction_per_event: 0.2,
    },
    rest_need: {
      satisfied_by: ["sleep", "low_arousal_idle_period"],
      reduction_per_event: 0.4,
    },
    curiosity: {
      satisfied_by: ["reading", "exploring_topic", "creative_activity"],
      reduction_per_event: 0.3,
    },
  },
  crystallization_threshold_ticks: 6,
  crystallization_urgency_min: 0.65,
  max_proposals_per_drive_per_tick: 1,
  persistence_threshold: 0.5,
};

function clamp01(v) {
  return Math.max(0.0, Math.min(1.0, v));
}

/**
 * Apply growth rates and activity-based satisfaction for one fast tick.
 *
 * @param {Object} drives - Current drive state {social_need, mastery_need, rest_need, curiosity}
 * @param {Array}  activityEvents - List of event objects with a 'type' key
 * @param {number} restBoost - Additional rest_need growth from stress coupling
 * @param {Object} config - Optional config override
 * @returns {Object} Updated drive state
 */
function updateDrives(drives, activityEvents, restBoost = 0.0, config = null) {
  const cfg = config || DRIVES_DEFAULTS;
  const growthRates = cfg.growth_rate || {};
  const satisfactionMap = cfg.satisfaction_map || {};

  const values = { ...drives };

  // Growth per tick
  for (const drive of DRIVE_NAMES) {
    values[drive] += growthRates[drive] || 0.0;
  }

  // Additional rest boost from high stress
  values.rest_need += restBoost;

  // Satisfaction from activity events
  const eventTypes = (activityEvents || []).map((e) => e.type || "");
  for (const drive of DRIVE_NAMES) {
    const driveCfg = satisfactionMap[drive] || {};
    const satisfiers = driveCfg.satisfied_by || [];
    const reduction = driveCfg.reduction_per_event || 0.0;
    for (const eventType of eventTypes) {
      if (satisfiers.includes(eventType)) {
        values[drive] -= reduction;
      }
    }
  }

  // Clamp all to [0, 1]
  for (const drive of DRIVE_NAMES) {
    values[drive] = clamp01(values[drive]);
  }

  return values;
}

/**
 * Generate a desire dict if drive_value >= impulse_threshold.
 */
function generateDesire(driveName, driveValue, tickCounter, config = null) {
  const cfg = config || DRIVES_DEFAULTS;
  const thresholds = cfg.impulse_threshold || {};
  const threshold = thresholds[driveName] || 1.0;

  if (driveValue < threshold) return null;

  const contentTemplates = {
    social_need: "want to connect with someone",
    mastery_need: "want to work on something meaningful",
    rest_need: "want to slow down and rest",
    curiosity: "want to explore something new",
  };

  const content = `${contentTemplates[driveName] || `want to address ${driveName}`} (intensity ${driveValue.toFixed(2)})`;

  return {
    id: `desire-${driveName}-${tickCounter}`,
    source_drive: driveName,
    urgency: Math.round(driveValue * 10000) / 10000,
    approach: true,
    expires_after_ticks: 3,
    age_in_ticks: 0,
    created_at_tick: tickCounter,
    content: content,
  };
}

/**
 * Generate desires for all drives that exceed their impulse threshold.
 */
function generateAllDesires(drives, tickCounter, config = null) {
  const results = [];
  for (const driveName of DRIVE_NAMES) {
    const desire = generateDesire(driveName, drives[driveName], tickCounter, config);
    if (desire) results.push(desire);
  }
  return results;
}

/**
 * Check crystallization: return goal proposals for desires that meet criteria.
 */
function checkCrystallization(persistedDesires, currentGoals, config = null) {
  const cfg = config || DRIVES_DEFAULTS;
  const thresholdTicks = cfg.crystallization_threshold_ticks || 6;
  const urgencyMin = cfg.crystallization_urgency_min || 0.65;
  const dampen = 0.6; // crystallization_priority_dampen from goals config

  const activeDriveGoals = new Set(
    currentGoals
      .filter((g) => g.status === "active" && g.crystallized_from_drive)
      .map((g) => g.crystallized_from_drive)
  );

  const proposals = [];
  const proposedDrives = new Set();

  for (const desire of persistedDesires) {
    const drive = desire.source_drive || "";
    const age = desire.age_in_ticks || 0;
    const urgency = desire.urgency || 0.0;

    if (proposedDrives.has(drive)) continue;
    if (age < thresholdTicks) continue;
    if (urgency < urgencyMin) continue;
    if (activeDriveGoals.has(drive)) continue;

    proposals.push({
      label: `Address ${drive.replace(/_/g, " ")}`,
      motive: drive,
      priority: Math.round(urgency * dampen * 10000) / 10000,
      horizon: "short",
      progress: 0.0,
      crystallized_from_drive: drive,
      crystallized_at: `tick:${desire.created_at_tick || 0}`,
      source_desire_id: desire.id,
    });
    proposedDrives.add(drive);
  }

  return proposals;
}

/**
 * Increment age_in_ticks and remove expired desires.
 */
function ageAndExpireDesires(persistedDesires) {
  return persistedDesires
    .map((d) => ({ ...d, age_in_ticks: (d.age_in_ticks || 0) + 1 }))
    .filter((d) => d.age_in_ticks < (d.expires_after_ticks || 3));
}

// ── n8n Code Node entry point ──────────────────────────────────────────────
const items = $input.all();
const results = [];

for (const item of items) {
  const state = item.json.state || item.json;
  const activityEvents = item.json.activity_events || [];
  const restBoost = (item.json._emotion_meta || {}).rest_boost || 0.0;

  const updatedDrives = updateDrives(state.drives, activityEvents, restBoost);

  results.push({
    json: {
      ...item.json,
      state: {
        ...state,
        drives: updatedDrives,
      },
    },
  });
}

return results;
