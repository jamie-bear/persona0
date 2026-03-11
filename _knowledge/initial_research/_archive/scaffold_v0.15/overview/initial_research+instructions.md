# Designing a Low-Resource "Ego Engine" for Humanlike Continuity in Chatbots

* Version: 0.15
* Status: Revised from v0.1 with structural corrections, tightened scope, and actionable integration points

---

## 1. Framing the Goal and Constraints

The most convincing "human-like" chatbots feel human for reasons that go beyond linguistic fluency. The illusion of life depends on emotion, personality, and consistent behavior. Joseph Bates [1] established this in early believable-agent research: a believable character is an architecture + memory + dynamics problem, with language as the surface layer.

The core constraint of this project is that the LLM serves only as an interface layer. Persistent "thinking" happens in external, deterministic systems. This separates language rendering from cognition, keeping the cognitive architecture inspectable, editable, and model-agnostic.

### Ethical Framing

If the system interacts with real users, transparency is a design requirement, not an afterthought. The EU AI Act (Article 50) [2] and OECD transparency principles [3] require disclosure that the user is interacting with an AI system. This project treats disclosure as a hard constraint, not an optional feature.

### Central Question

> What is the smallest set of mechanisms that create the felt properties of a human mind -- continuity, emotion, goals, time, and a personal story -- without simulating a human brain?

---

## 2. What Produces "Human-Likeness" in Practice

### 2.1 Autobiographical Continuity and Narrative Identity

Human believability is tied to the sense of an enduring self across time. The episodic/semantic memory distinction (Tulving [4], later reviews [5]) captures "events vs facts" while acknowledging their interdependence.

Conway and Pleydell-Pearce [6] describe a "self-memory system" where retrieval cues are shaped by current goals, producing the subjective sense of "my past." Narrative identity research [7] frames identity as an evolving life story integrating reconstructed past and imagined future.

**Design implication:** Believability benefits disproportionately from (1) episodic memory with time structure and (2) a mechanism that selectively retrieves and reinterprets memory based on current goals and mood.

### 2.2 Emotion as Regulation, Not Decoration

Affective computing (Picard [8]) treats emotion as computationally relevant to intelligent interaction, not cosmetic styling. The EMA model [9] frames emotion as arising from appraisal: events evaluated against goals, norms, and interpretations.

Modern affective neuroscience connects emotion to interoception. Craig [10] highlights the anterior insula in subjective feelings grounded in bodily re-representation. Barrett [11] frames emotion as constructed via prediction and categorization (active inference over interoception).

**Design implication:** Simulate regulatory variables (energy, fatigue, stress, arousal, social need) and let them systematically influence attention, memory retrieval, and action selection. A small set of state variables that behave like constraints is sufficient.

### 2.3 A Workspace-Like Gating Mechanism

Global Workspace Theory [12] proposes that many processes run in parallel, but only some content becomes globally available for decision and action.

**Design implication:** The system needs a mechanism analogous to "attention" that selects (a) which memories surface, (b) which concerns dominate, and (c) what gets verbalized versus what stays internal.

**v0.1 gap addressed:** The original research identified this as important but the architecture omitted it entirely. In v0.15, an explicit **Salience Gate** module is added to the architecture (see `architecture.md` section 4.6).

---

## 3. Ego-Perspective Training Data

### 3.1 How Ego-Perspective Data Differs from Generic Web Text

Standard corpora emphasize third-person reportage and expository writing. Ego-perspective data contains first-person reference, feelings, bodily cues, self-justification, uncertainty, autobiographical time, and selective recall.

Empirical precedent exists:
- **Persona grounding:** PERSONA-CHAT [13] demonstrates that persona facts improve engagement and consistency.
- **Emotion grounding:** EmpatheticDialogues [14] shows models perceived as more empathetic when trained on emotionally situated conversations.

### 3.2 "Qualitatively Predetermined, Quantitatively Randomized" Ego Memories

If ego episodes are qualitatively predetermined (kinds of experiences, relationships, values) but quantitatively randomized (intensity, timing, details), this shapes a prior over lived experience.

**Probable upsides:**
- Stable first-person stance and natural self-reference [13]
- Human-like affective narration with ambiguity and mixed feelings [8]
- Smoother time continuity via episodic structures [5]

**Probable failure modes:**
- **Catastrophic forgetting** during narrow fine-tuning [15]
- **Synthetic-data degeneration** when most memories are model-generated [16]
- **Contradictory life history** unless globally constrained [17]

### 3.3 Correct Ordering: Architecture First, Then Data

**v0.1 gap addressed:** The original document recommended ego data as a "reasonable early research direction" while simultaneously warning it is "often mis-ordered." This is contradictory. The v0.15 position is clear:

1. Define mechanisms (memory, affect, time) and evaluation criteria [1]
2. Build minimal system where ego data plugs in via retrieval or fine-tuning
3. Only then invest in ego-perspective dataset construction

The biggest early gains come from memory + reflection + planning structure, not from more training tokens [17]. Start with a small, tightly-coupled dataset and expand based on experimental results.

---

## 4. The "Ego Engine" Architecture

### 4.1 Reference Points

Classic cognitive architectures (ACT-R [18], Soar [19]) demonstrate modular decomposition of cognition. On the LLM side, RAG [20] separates parametric memory (weights) from non-parametric memory (retrieval). MemGPT [21] motivates tiered memory with explicit storage and retrieval policies.

### 4.2 Architecture Summary

**A. Ego Engine (the mind):** A lightweight stateful system performing homeostatic regulation, event appraisal, episodic memory logging, reflection, salience gating (attention/workspace selection), and conversational policy.

**B. LLM Renderer (the mouth + ears):** A small open-weight model that parses user input into internal representations and generates natural language conditioned on the engine's state.

**C. Memory Store (the autobiography):** Append-only event-sourced log with retrieval weighted by similarity x recency x importance, plus periodic summarization ("reflections") [17].

**v0.1 gap addressed:** The original architecture listed modules but never specified their interactions within a single cognitive cycle. See `cognitive_loop.md` for the formal tick specification.

### 4.3 Why External Memory Beats Ego-Heavy Fine-Tuning

Even with parameter-efficient methods (LoRA/QLoRA [22]), fine-tuning risks forgetting [15] and synthetic-data degeneration [16]. External memory keeps base language competence intact, personalization editable, contradictions traceable, and the off-screen life implementable as an event log.

### 4.4 Renderer Model Choices

For early-stage work, viable open-weight options include Mistral 7B [23], Llama 3 (8B/70B) [24], and Gemma [25]. The choice depends on licensing, hardware, and target style. The architectural point is that "LLM as renderer" works with modest models.

---

## 5. Simulating Life Outside the User's Perception

The off-screen life simulation (cf. Generative Agents [17]) uses three event streams:

### 5.1 Routine Stream (circadian + habits)
Schedule-driven events ("made coffee," "worked," "walked"), modulated by state variables. Cheapest passage-of-time mechanism. Grounded in allostasis/allostatic load [26].

### 5.2 Impulse Stream (affect-driven cognitive noise)
Stochastic process conditioned on drives: social need triggers "urge to text someone," curiosity triggers "read about X." Higher stress produces intrusive thoughts. Sleep produces dream fragments. Approximates interoception [10] cheaply.

### 5.3 World-Event Stream (real-world inputs)
Real-world events (news, weather) framed as "I read/saw/heard that..." and integrated into mood/goals. Retrieved via RAG-like mechanisms and stored as observed events [20].

---

## 6. Making Time Feel Real in Conversation

Four mechanisms matter more than raw event volume:

1. **Time-stamped episodic recall** ("Earlier today...", "Last week I noticed...") [5]
2. **Compression into reflections** (daily/weekly summaries that update beliefs/plans) [17]
3. **Emotion drift + recovery** (stress rises, sleep reduces it; moods carry over but decay) [26]
4. **Humanlike reconstruction bias** (memories are reconstructed, not replayed; cf. Kahneman's Day Reconstruction Method [27])

Practical implementation: generate a daily "DRM-style diary" internally and let the agent reference it selectively.

---

## 7. Core Thesis to Test

> A system that adds episodic memory + reflection, an affective body state, and an off-screen life loop will be rated as more humanlike, more emotionally coherent, and more temporally continuous than the same base LLM used as a stateless chatbot.

Testable via small-scale human evaluation using comparative protocols such as ACUTE-Eval [28].

---

## 8. References

### Related Documents
* [v0.15_summary](.knowledge/initial_research/v0.15/overview/v0.15_summary)
* [architecture.md](.knowledge/initial_research/v0.15/architecture.md)
* [ego_data.md](.knowledge/initial_research/v0.15/ego_data.md)
* [action_plan.md](.knowledge/initial_research/v0.15/action_plan.md)
* [cognitive_loop.md](.knowledge/initial_research/v0.15/cognitive_loop.md)

### Citations
1. Bates, J. "The role of emotion in believable agents." Communications of the ACM, 1994. https://dl.acm.org/doi/10.1145/176789.176803
2. EU AI Act, Article 50: Transparency Obligations. https://artificialintelligenceact.eu/article/50/
3. OECD AI Principle: Transparency and Explainability. https://oecd.ai/en/dashboards/ai-principles/P7
4. Tulving, E. Episodic and semantic memory distinction. (Foundational work.)
5. Greenberg, D.L. & Verfaellie, M. "Interdependence of episodic and semantic memory." https://pmc.ncbi.nlm.nih.gov/articles/PMC2952732/
6. Conway, M.A. & Pleydell-Pearce, C.W. "The construction of autobiographical memories in the self-memory system." https://pubmed.ncbi.nlm.nih.gov/10789197/
7. McAdams, D.P. & McLean, K.C. "Narrative Identity." https://journals.sagepub.com/doi/abs/10.1177/0963721413475622
8. Picard, R.W. Affective Computing. MIT Press, 1997. https://direct.mit.edu/books/monograph/4296/Affective-Computing
9. Gratch, J. & Marsella, S. "EMA: A process model of appraisal dynamics." https://www.sciencedirect.com/science/article/abs/pii/S1389041708000314
10. Craig, A.D.B. "How do you feel -- now? The anterior insula and human awareness." https://pubmed.ncbi.nlm.nih.gov/19096369/
11. Barrett, L.F. "Theory of constructed emotion: an active inference account." https://academic.oup.com/scan/article/12/1/1/2823712
12. Mashour, G.A. et al. "Global Workspace Theory and Prefrontal Cortex." https://pmc.ncbi.nlm.nih.gov/articles/PMC8660103/
13. Zhang, S. et al. "Personalizing Dialogue Agents (PERSONA-CHAT)." https://arxiv.org/pdf/1801.07243
14. Rashkin, H. et al. "Towards Empathetic Open-domain Conversation Models." https://aclanthology.org/P19-1534/
15. Luo, Y. et al. "An Empirical Study of Catastrophic Forgetting in LLMs During Continual Fine-tuning." https://arxiv.org/abs/2308.08747
16. Shumailov, I. et al. "Training on Generated Data Makes Models Forget." https://arxiv.org/abs/2305.17493
17. Park, J.S. et al. "Generative Agents: Interactive Simulacra of Human Behavior." https://arxiv.org/abs/2304.03442
18. Anderson, J.R. et al. ACT-R: A Cognitive Architecture. Carnegie Mellon University. https://act-r.psy.cmu.edu/
19. Laird, J.E. Soar: A General Cognitive Architecture. University of Michigan. https://soar.eecs.umich.edu/
20. Lewis, P. et al. "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." https://arxiv.org/abs/2005.11401
21. Packer, C. et al. "MemGPT: Towards LLMs as Operating Systems." https://arxiv.org/abs/2310.08560
22. Hu, E.J. et al. "LoRA: Low-Rank Adaptation of Large Language Models." https://arxiv.org/abs/2106.09685
23. Mistral AI. "Mistral 7B." https://mistral.ai/news/announcing-mistral-7b
24. Meta. "Introducing Meta Llama 3." https://ai.meta.com/blog/meta-llama-3/
25. Google. "Gemma Releases." https://ai.google.dev/gemma/docs/releases
26. Ramsay, D.S. & Woods, S.C. "Clarifying the Roles of Homeostasis and Allostasis." https://pmc.ncbi.nlm.nih.gov/articles/PMC4166604/
27. Kahneman, D. et al. "A survey method for characterizing daily life experience." https://pubmed.ncbi.nlm.nih.gov/15576620/
28. Li, M. et al. "ACUTE-EVAL: Improved Dialogue Evaluation." https://arxiv.org/abs/1909.03087
