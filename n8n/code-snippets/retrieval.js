/**
 * Hybrid memory retrieval ranking for n8n Code nodes.
 *
 * Translates src/engine/retrieval.py into JavaScript.
 * Scores memory candidates by weighted combination of:
 *   - Semantic similarity (from vector store)
 *   - Recency (time-based decay)
 *   - Importance (event significance)
 *   - Self-relevance (alignment with self-model)
 *
 * Reference: config/defaults.yaml [retrieval.*]
 */

const RETRIEVAL_DEFAULTS = {
  recency_weight: 0.30,
  importance_weight: 0.25,
  semantic_similarity_weight: 0.30,
  self_relevance_weight: 0.15,
  candidate_limit: 20,
  salience_buffer_capacity: 5,
  min_importance_threshold: 0.15,
};

/**
 * Rank memory records by weighted hybrid score and return top-k.
 *
 * @param {Array}  memoryRecords - Array of memory record objects
 * @param {number} topK - Max records to return (default: candidate_limit)
 * @param {Object} config - Optional config override
 * @returns {Array} Ranked records with hybrid_score and why_selected
 */
function rankMemoryCandidates(memoryRecords, topK = null, config = null) {
  const cfg = config || RETRIEVAL_DEFAULTS;

  const weights = {
    similarity: cfg.semantic_similarity_weight || 0.30,
    recency: cfg.recency_weight || 0.30,
    importance: cfg.importance_weight || 0.25,
    self_relevance: cfg.self_relevance_weight || 0.15,
  };

  const limit = topK || cfg.candidate_limit || 20;
  const minImportance = cfg.min_importance_threshold || 0.15;

  const ranked = [];

  for (const record of memoryRecords) {
    const importance = record.importance || 0.0;
    if (importance < minImportance) continue;

    const similarity = record.similarity || 0.0;
    const recency = record.recency || 0.0;
    const selfRelevance = record.self_relevance || record.goal_relevance || 0.0;

    const score =
      weights.similarity * similarity +
      weights.recency * recency +
      weights.importance * importance +
      weights.self_relevance * selfRelevance;

    ranked.push({
      ...record,
      hybrid_score: score,
      why_selected: {
        score_components: { similarity, recency, importance, self_relevance: selfRelevance },
        weights: weights,
        hybrid_score: score,
      },
    });
  }

  // Sort by score descending, then by id for determinism
  ranked.sort((a, b) => {
    if (b.hybrid_score !== a.hybrid_score) return b.hybrid_score - a.hybrid_score;
    return (a.id || "").localeCompare(b.id || "");
  });

  return ranked.slice(0, limit);
}

/**
 * Select top entries for the salience buffer (working memory).
 *
 * @param {Array}  rankedCandidates - Output from rankMemoryCandidates
 * @param {number} capacity - Salience buffer size (default: 5)
 * @returns {Array} Top candidates for context assembly
 */
function salienceCompetition(rankedCandidates, capacity = 5) {
  return rankedCandidates.slice(0, capacity);
}

// ── n8n Code Node entry point ──────────────────────────────────────────────
const items = $input.all();
const results = [];

for (const item of items) {
  const memoryCandidates = item.json.memory_candidates || [];
  const salienceCapacity = item.json.salience_buffer_capacity || 5;

  const ranked = rankMemoryCandidates(memoryCandidates);
  const salient = salienceCompetition(ranked, salienceCapacity);

  results.push({
    json: {
      ...item.json,
      ranked_memories: ranked,
      salience_buffer: salient.map((r) => r.id),
      salience_records: salient,
    },
  });
}

return results;
