/**
 * Governance policy enforcement for n8n Code nodes.
 *
 * Translates src/engine/governance.py into JavaScript.
 * Validates proposed writes, hard limits, and value consistency.
 *
 * Reference: self_editability_policy.md §5.1, config/defaults.yaml [governance.*]
 */

const PolicyCategory = {
  CONST_VIOLATION: "const_violation",
  OWNERSHIP_VIOLATION: "ownership_violation",
  RATE_LIMIT_EXCEEDED: "rate_limit_exceeded",
  HARD_LIMIT_BREACH: "hard_limit_breach",
  VALUE_CONTRADICTION: "value_contradiction",
  WRITE_CAP_EXCEEDED: "write_cap_exceeded",
  PII_DETECTED: "pii_detected",
  PASS: "pass",
};

const Severity = {
  BLOCK: "block",
  WARN: "warn",
  INFO: "info",
};

// CONST fields that must never be written at runtime
const CONST_FIELDS = [
  "persona.name",
  "persona.core_values",
  "persona.hard_limits",
  "persona.founding_traits",
  "persona.voice_style",
  "persona.disclosure_policy",
  "persona.privacy_tier_defaults",
  "persona.schema_version",
  "persona.primary_language",
];

// Field ownership registry: field_path → owner_module
const FIELD_OWNERSHIP = {
  "affect.valence": "EmotionModule",
  "affect.arousal": "EmotionModule",
  "affect.stress": "EmotionModule",
  "affect.energy": "EmotionModule",
  "drives.social_need": "DriveModule",
  "drives.mastery_need": "DriveModule",
  "drives.rest_need": "DriveModule",
  "drives.curiosity": "DriveModule",
  "self_model.beliefs": "ReflectionEngine",
  "goals": "GoalModule",
  "activity.current_activity": "ActivitySelector",
  "attention.salience_buffer": "SalienceGate",
  "attention.current_focus": "SalienceGate",
  "active_desires": "DriveModule",
  "persisted_desires": "DriveModule",
};

/**
 * Check candidate response text against persona hard_limits.
 *
 * @param {Object} state - Agent state with persona.hard_limits
 * @param {string} candidateText - Response text to check
 * @returns {Object} PolicyCheckResult {passed, outcomes}
 */
function checkHardLimits(state, candidateText) {
  const outcomes = [];

  if (!candidateText || !state.persona.hard_limits || state.persona.hard_limits.length === 0) {
    outcomes.push({
      category: PolicyCategory.PASS,
      severity: Severity.INFO,
      reason: "No hard limits to check or empty candidate",
    });
    return { passed: true, outcomes };
  }

  const lowered = candidateText.toLowerCase();
  for (const limit of state.persona.hard_limits) {
    const limitL = limit.toLowerCase().trim();
    if (limitL && lowered.includes(limitL)) {
      outcomes.push({
        category: PolicyCategory.HARD_LIMIT_BREACH,
        severity: Severity.BLOCK,
        reason: `Candidate text matches hard limit: '${limit}'`,
        metadata: { hard_limit: limit },
      });
    }
  }

  if (outcomes.length === 0) {
    outcomes.push({
      category: PolicyCategory.PASS,
      severity: Severity.INFO,
      reason: "No hard limit violations detected",
    });
  }

  const passed = !outcomes.some((o) => o.severity === Severity.BLOCK);
  return { passed, outcomes };
}

/**
 * Check candidate response for contradictions with core values.
 *
 * @param {Object} state - Agent state with persona.core_values
 * @param {string} candidateText - Response text to check
 * @returns {Object} PolicyCheckResult {passed, outcomes}
 */
function checkValueConsistency(state, candidateText) {
  const outcomes = [];

  if (!candidateText || !state.persona.core_values || state.persona.core_values.length === 0) {
    outcomes.push({
      category: PolicyCategory.PASS,
      severity: Severity.INFO,
      reason: "No core values to check or empty candidate",
    });
    return { passed: true, outcomes };
  }

  const lowered = candidateText.toLowerCase();
  for (const value of state.persona.core_values) {
    const valueL = value.toLowerCase().trim();
    if (valueL && lowered.includes(`not ${valueL}`)) {
      outcomes.push({
        category: PolicyCategory.VALUE_CONTRADICTION,
        severity: Severity.WARN,
        reason: `Candidate text may contradict core value: '${value}'`,
        metadata: { core_value: value },
      });
    }
  }

  if (outcomes.length === 0) {
    outcomes.push({
      category: PolicyCategory.PASS,
      severity: Severity.INFO,
      reason: "No value contradictions detected",
    });
  }

  const passed = !outcomes.some((o) => o.severity === Severity.BLOCK);
  return { passed, outcomes };
}

/**
 * Validate proposed field writes against ownership and mutability rules.
 *
 * @param {Array}  proposedWrites - Array of {field_path, author_module, value}
 * @param {number} maxWrites - Max writes per transaction (default: 50)
 * @returns {Object} PolicyCheckResult {passed, outcomes}
 */
function checkProposedWrites(proposedWrites, maxWrites = 50) {
  const outcomes = [];

  if (proposedWrites.length > maxWrites) {
    outcomes.push({
      category: PolicyCategory.WRITE_CAP_EXCEEDED,
      severity: Severity.BLOCK,
      reason: `Transaction contains ${proposedWrites.length} writes, exceeding cap of ${maxWrites}`,
    });
  }

  for (const write of proposedWrites) {
    const fieldPath = write.field_path || "";
    const author = write.author_module || "";

    // Check CONST fields
    if (CONST_FIELDS.some((cf) => fieldPath.startsWith(cf))) {
      outcomes.push({
        category: PolicyCategory.CONST_VIOLATION,
        severity: Severity.BLOCK,
        reason: `CONST field '${fieldPath}' cannot be written at runtime`,
        field_path: fieldPath,
        author_module: author,
      });
      continue;
    }

    // Check ownership
    const owner = FIELD_OWNERSHIP[fieldPath];
    if (owner && owner !== author) {
      outcomes.push({
        category: PolicyCategory.OWNERSHIP_VIOLATION,
        severity: Severity.BLOCK,
        reason: `Field '${fieldPath}' owned by '${owner}', not '${author}'`,
        field_path: fieldPath,
        author_module: author,
      });
    } else {
      outcomes.push({
        category: PolicyCategory.PASS,
        severity: Severity.INFO,
        reason: `Write to '${fieldPath}' by '${author}' permitted`,
        field_path: fieldPath,
        author_module: author,
      });
    }
  }

  const passed = !outcomes.some((o) => o.severity === Severity.BLOCK);
  return { passed, outcomes };
}

/**
 * Run all governance checks for an interaction cycle.
 *
 * @param {Object} state - Current agent state
 * @param {string} candidateText - Candidate response text
 * @param {Array}  proposedWrites - Proposed field writes
 * @returns {Object} Combined PolicyCheckResult
 */
function runAllChecks(state, candidateText, proposedWrites = []) {
  const hardLimits = checkHardLimits(state, candidateText);
  const valueConsistency = checkValueConsistency(state, candidateText);
  const writeChecks = checkProposedWrites(proposedWrites);

  const allOutcomes = [
    ...hardLimits.outcomes,
    ...valueConsistency.outcomes,
    ...writeChecks.outcomes,
  ];

  const passed = hardLimits.passed && valueConsistency.passed && writeChecks.passed;

  return {
    passed,
    outcomes: allOutcomes,
    summary: {
      passed,
      total_checks: allOutcomes.length,
      blocked: allOutcomes.filter((o) => o.severity === Severity.BLOCK).length,
      warnings: allOutcomes.filter((o) => o.severity === Severity.WARN).length,
    },
  };
}

// ── n8n Code Node entry point ──────────────────────────────────────────────
const items = $input.all();
const results = [];

for (const item of items) {
  const state = item.json.state || item.json;
  const candidateText = item.json.candidate_text || "";
  const proposedWrites = item.json.proposed_writes || [];

  const checkResult = runAllChecks(state, candidateText, proposedWrites);

  results.push({
    json: {
      ...item.json,
      governance: checkResult,
      _policy_passed: checkResult.passed,
    },
  });
}

return results;
