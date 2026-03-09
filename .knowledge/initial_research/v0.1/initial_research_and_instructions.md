# Designing a Low-Resource “Ego Engine” for Humanlike Continuity in Chatbots

## Framing the goal and constraints

The most convincing “human-like” chatbots tend to feel human for reasons that are only partially about raw linguistic fluency. Decades before LLMs, researchers in believable agents argued that the illusion of life depends heavily on emotion, personality, and consistent behavior, not just problem-solving ability. Joseph Bates [1] made this case explicitly in early work on believable agents and interactive characters. [2]

Your constraint—the LLM is only the interface, while “thinking” happens elsewhere—is aligned with this older thread of research: a believable character is an architecture + memory + dynamics problem, with language as the surface layer. [3]

Because “believable” can easily slide into “deceptive,” it’s worth stating one design constraint up front: if the system is meant to interact with real users, good practice (and, depending on jurisdiction, legal obligation) is to disclose that the user is interacting with an AI system. Recent policy frameworks emphasize transparency and responsible disclosure for AI systems that interact with people. European Union [4] transparency obligations around AI-user interaction are summarized in discussions of Article 50, and the OECD [5] principle on transparency similarly focuses on responsible disclosure. [6]

Within those constraints, the key technical question becomes:

> What is the smallest set of mechanisms that create the felt properties of a human mind—continuity, emotion, goals, time, and a personal story—without trying to simulate a human brain?

## What tends to produce “human-likeness” in practice

### Autobiographical continuity and narrative identity

Human believability is strongly tied to the sense that there is an enduring self that persists across time. In cognitive psychology and neuroscience, memory is often discussed as (at least) two interacting systems:

- Semantic memory: general knowledge (“Paris is the capital of France”).

- Episodic memory: memory for events situated in time, place, and personal experience. Endel Tulving [7] is foundational here; later reviews emphasize how the episodic/semantic distinction captures “events vs facts,” while also noting their interdependence. [8]


A core model for autobiographical memory argues that memories are constructed within a “self-memory system” that includes an autobiographical knowledge base and a goal-driven “working self.” Martin A. Conway [9] and Christopher W. Pleydell-Pearce [10] describe this as a control process that shapes retrieval cues based on current goals, producing the subjective feeling of “my past.” [11]

Relatedly, narrative identity research frames “who I am” as an evolving life story that integrates reconstructed past and imagined future. [12]

Design implication: believability benefits disproportionately from a system that maintains (1) episodic memory with time structure and (2) a mechanism that selectively retrieves and reinterprets that memory based on current goals and mood, rather than from more generic text knowledge.

### Emotion as regulation, not decoration

Affective computing—the field that explicitly treats emotion as computationally relevant—argues that emotion is not just expressive styling, but a key part of intelligent interaction and interpretation. Rosalind W. Picard [13]’s Affective Computing [14] is often cited as a foundational framework for treating affect as a design requirement. [15]

Computational models of emotion frequently use some form of appraisal: events are evaluated in relation to goals, norms, and interpretations, producing emotion dynamics that can be fast and reactive or slower and reflective. The EMA model, for example, emphasizes emotion dynamics as arising from processes that operate over an agent’s interpretation of its relationship to the environment. [16]

Modern affective neuroscience also connects emotion to interoception (representation of bodily state). A. D. Bud Craig [17]’s work highlights the anterior insula as relevant to subjective feelings grounded in interoceptive re-representation. [18] Meanwhile Lisa Feldman Barrett [19] frames emotion as constructed via prediction and categorization (an “active inference” view of interoception). [20]

Design implication: you can get “biological believability” cheaply by simulating regulatory variables (energy/ fatigue, stress load, arousal, social need, etc.) and letting them systematically influence attention, memory retrieval, and action selection. You do not need a biological simulation; you need a small set of state variables that behave like constraints.

### A workspace-like gating mechanism

One recurring idea in cognitive science is that many specialized processes run in parallel, but only some content becomes “globally available” for decision/action—often discussed under Global Workspace approaches. Contemporary reviews summarize global workspace theory as involving competition and broadcast across modules. [21]

Design implication: even a lightweight chatbot can feel more human if it has a mechanism analogous to “attention” that selects (a) which memories come to mind, (b) which concerns dominate, and (c) what gets verbalized vs stays internal.

## Ego-perspective training data and what it changes

### How ego-perspective fine-tuning differs from generic web text

By default, large corpora heavily emphasize third-person reportage, expository writing, argumentation, and generic conversational patterns. Ego-perspective data, by contrast, disproportionately contains:

- first-person reference (“I,” “my,” “I remember…”),

- feelings and bodily cues,

- self-justification and uncertainty,

- autobiographical time,

- selective recall and reinterpretation.


There is empirical precedent that persona- or emotion-grounded data can shift human perception of a dialogue model:

- Persona grounding: The PERSONA-CHAT dataset was created specifically to encourage more engaging, personal chit-chat grounded in explicit persona facts, and it is widely used to benchmark persona consistency. [22]

- Emotion grounding: EmpatheticDialogues was introduced as a benchmark of conversations grounded in emotional situations; the authors report that models using the dataset are perceived as more empathetic than models trained only on large generic conversation data. [23]


So: ego-perspective data is not speculative as a lever—persona and emotion supervision already measurably change user perception.

### Likely impacts of “qualitatively predetermined, quantitatively randomized” ego memories

If you pretrain or fine-tune on “memories/thoughts/experiences” that are:

- qualitatively predetermined: you decide the kinds of experiences, relationships, values, conflicts;

- quantitatively randomized: you randomize intensity, timing, minor details, and sampling;


then you are effectively shaping the model to internalize a prior over lived experience.

Probable upsides (if done carefully):

- More stable first-person stance: the model learns to write from a consistent “I” perspective and to reference personal history naturally. [22]

- More human-like affective narration: especially if episodes include ambiguity, mixed feelings, and bodily cues (consistent with affective computing and interoception-informed accounts). [24]

- Smoother time continuity: training on episodic structures (yesterday/today/tomorrow, routines, reflections) nudges outputs toward autobiographical time framing, consistent with the role of episodic/autobiographical memory in “mental time travel.” [25]


Probable downsides and failure modes you should plan around:

- Catastrophic forgetting during narrow fine-tuning: continual or domain-focused fine-tuning can reduce previously learned capabilities; empirical studies document forgetting effects in LLMs during continual/instruction tuning. [26]

- Synthetic-data degeneration if most “memories” are model-generated: training on generated data can cause “model collapse,” reducing distributional diversity and amplifying artifacts over generations. [27]

- Contradictory life history unless constrained: randomization without global constraints tends to produce mutually incompatible autobiographical facts (timeline errors, impossible relationships, inconsistent traits). This is exactly why architectures that store experiences and then retrieve them selectively (rather than baking everything into weights) have shown value for believability. [28]


### Should ego-perspective training data be the first step?

It is a reasonable early research direction, but as a first step it is often mis-ordered.

A practical ordering (supported by both older believable-agent work and newer LLM-agent architectures) is:

1. Define the mechanisms you want (memory, affect, time) and how you will measure believability. [29]

2. Build a minimal system where ego data can be plugged in either as retrieval memory or as a fine-tuning set.

3. Only then invest heavily in ego-perspective dataset construction.


Why: the biggest early gains in believability often come from memory + reflection + planning structure rather than from more training tokens. The “Generative Agents” work is instructive here: it emphasizes storing a comprehensive record of experiences, synthesizing reflections, and retrieving them dynamically for planning, with ablations showing these components matter for believability. [30]

That said, scoping and specifying ego-perspective data is absolutely a good early milestone—just keep the initial dataset small and tightly coupled to your architecture experiments, and avoid a large up-front data effort before you can evaluate outcomes.

## A resourceful architecture that does not rely on “the LLM doing the thinking”

### Reference points from cognitive architectures and modern LLM-agent memory

Classic cognitive architectures like ACT-R and Soar are useful here not because you should reimplement them fully, but because they demonstrate a modular decomposition of cognition (distinct “kinds” of memory, procedural rules, and limited buffers/working memory). ACT-R is described as a cognitive architecture for simulating and understanding human cognition by researchers at Carnegie Mellon University [31], and Soar is positioned as a general cognitive architecture with a long history of development and use, hosted by University of Michigan [32]. [33]

On the LLM side, memory-augmented approaches explicitly distinguish parametric memory (weights) from non-parametric external memory (retrieval). Retrieval-Augmented Generation (RAG) is a canonical example of combining a generator with a retriever over an external index to improve specificity and factuality. [34] More recent “memory manager” approaches (e.g., MemGPT) motivate tiered memory systems that manage context limitations via explicit storage and retrieval policies. [35]

### Proposed “Ego Engine” architecture

The simplest “innovative but resourceful” architecture that matches your constraints is:

**A. Ego Engine (the mind)**

A lightweight stateful system that performs:

- homeostatic-ish regulation (energy, stress, arousal, social need),

- event appraisal (what does this mean for my goals/identity?),

- episodic memory logging (time-stamped experiences),

- reflection (periodic synthesis into beliefs/traits/plans),

- attention/workspace selection (what is salient now?),

- policy (what am I trying to do in this conversation?).


This can be implemented as deterministic code + small learned components (classifiers/embedders).

**B. LLM Renderer (the mouth + ears)**

A small open-weight instruction-tuned model that:

- parses user input into lightweight internal representations (topic, intent, affect cues),

- writes natural language given the ego engine’s selected memories, mood, and goals.


This is consistent with the “LLM as interface” constraint: the LLM is a natural-language surface, not the owner of persistent cognition.

**C. Memory store (the autobiography)**

A database plus a vector index:

- append-only event-sourcing log,

- retrieval weighted by similarity × recency × importance,

- periodic summarization (“reflections”) to keep memory scalable (an idea explored explicitly in generative agent architectures). [36]


### Why this is plausibly cheaper than ego-heavy fine-tuning

Fine-tuning can be compute-cheap with parameter-efficient methods like LoRA and QLoRA, which were designed to reduce training memory and cost by adapting only small components or adapters. [37] But even cheap fine-tuning risks:
- forgetting [26]
- and synthetic-data degeneration if ego data is largely generated. [27]

In contrast, putting autobiographical specifics in external memory keeps:
- the base language competence intact
- personalization editable
- contradictions traceable
- and the “life outside perception” implementable as an event log rather than weight changes.

### Minimal model choices for the renderer layer

For early-stage low-budget work, strong open-weight options exist in the small-to-mid range:

- Mistral AI [38] explicitly released Mistral 7B under Apache 2.0, emphasizing efficiency features like GQA and sliding-window attention. [39]

- Meta [40]’s Llama 3 family announcement describes 8B/70B models optimized for dialogue; smaller releases (e.g., 1B/3B variants in later collections) are often positioned for local or constrained settings. [41]

- Google [42] publishes release documentation for the Gemma family, including smaller parameter sizes intended for broader deployment contexts. [43]


(Which one is “best” depends on your licensing needs, hardware, and target style; the broader point is that “LLM as renderer” is feasible with relatively modest models.)

## Simulating a life outside the user’s perception to create time passage

Your idea—an internal life that continues “off-screen,” shaped by real-world events plus internal impulses— is a direct extension of patterns demonstrated in modern generative agent simulations. The “Generative Agents” paper explicitly describes agents that wake, cook, work, form opinions, remember, reflect, and plan, in a sandbox inspired by The Sims [44], with believability supported by memory + reflection + planning modules. [28]

A resourceful approach is to treat “life outside perception” as an event-sourced simulation with three streams:

### Routine stream (circadian + habits)

A schedule creates routine events (“made coffee,” “worked,” “walked,” “slept”), modulated by state variables (energy, stress). This is your cheapest “passage of time” mechanism because it requires no external data and produces stable patterns.

Grounding in regulation frameworks can keep it humanlike: “stress load” accumulation and recovery is consistent with allostasis/allostatic load discussions in psychophysiology reviews. [45]

### Impulse stream (affect-driven “cognitive noise”)

Humans have idle thoughts and urges that are not always rational. You can simulate this via:

- a small stochastic process conditioned on drives (social need → “urge to text someone,” curiosity → “read about X”),

- occasional intrusive thoughts under higher stress,

- dream fragments during sleep.


This is where “biology” can be approximated cheaply: not as organs, but as interoception-like state shaping subjective experience and choice. [46]

### World-event stream (real-world events as inputs, safely framed)

If you ingest real-world events (news, weather, sports, local calendars), the key believability trick is framing:
- not “I witnessed…,” but “I read/saw/heard that…,”
- and integrating it into mood/goals (“It made me uneasy,” “I’m hopeful,” etc.).

Technically, this can be as simple as a daily summary retrieved via RAG-like mechanisms and stored as an “observed world event.” [47] Socially/ethically, disclosure remains important: transparency frameworks emphasize users understanding when they engage with AI systems. [48]

## Making time feel real in conversation

To make the user feel time passage, four mechanisms matter more than raw event volume:

1. Time-stamped episodic recall (“Earlier today…”, “Last week I noticed…”), consistent with episodic/ autobiographical framing. [25]

2. Compression into reflections (daily/weekly summaries that change beliefs or plans), consistent with generative agent reflection patterns. [28]

3. Emotion drift + recovery (stress rises, sleep reduces it; moods carry over but not forever), consistent with regulation/allostasis framing. [45]

4. Humanlike reconstruction bias: people reconstruct experiences; methods like the Day Reconstruction Method were explicitly designed to capture daily life experience while reducing recall bias via structured reconstruction. Daniel Kahneman [49]’s DRM work emphasizes systematically reconstructing episodes of the preceding day and comparing to experience sampling. [50]


That last point suggests a practical hack: generate a daily “DRM-style diary” internally (episode blocks), and let the agent occasionally reference it without over-sharing.

## Fast architecture and action plan to test the thesis

### Core thesis to test

A system that adds:

- episodic memory + reflection,

- an affective “body state,”

- and an off-screen life loop,


will be rated as more humanlike, more emotionally coherent, and more temporally continuous than the same base LLM used as a stateless chatbot.

This is directly testable via small-scale human evaluation. Dialogue evaluation research argues that human judgements are central and that carefully designed comparative protocols improve signal; ACUTE-Eval is one influential framework using optimized questions and multi-turn comparisons. [51]

## Recommended position on ego-perspective data as a first step

Researching and specifying ego-perspective data is a good early step if you do it in a way that:

- starts with a schema (what counts as a “memory,” what fields exist, what constraints must hold), aligning with autobiographical memory and narrative identity concepts [52]

- avoids heavy early fine-tuning (because of forgetting risk), [26]

- avoids synthetic-data-only pipelines (because of model collapse risk), [27]

- integrates ego episodes first through retrieval memory (RAG-like), with fine-tuning reserved for style calibration (LoRA/QLoRA if needed). [53]

## References

### Related Markdown files
* [architecture.md](https://github.com/jamie-bear/persona0/blob/main/.knowledge/initial_research/v0.1/architecture.md) 
* [ego_data.md](https://github.com/jamie-bear/persona0/blob/main/.knowledge/initial_research/v0.1/ego_data.md)  
* [action_plan.md](https://github.com/jamie-bear/persona0/blob/main/.knowledge/initial_research/v0.1/action_plan.md)

1. [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
2. [The role of emotion in believable agents](https://dl.acm.org/doi/10.1145/176789.176803)
3. [The role of emotion in believable agents](https://dl.acm.org/doi/10.1145/176789.176803)
4. [Training on Generated Data Makes Models Forget](https://arxiv.org/abs/2305.17493)
5. [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
6. [Article 50: Transparency Obligations for Providers and ...](https://artificialintelligenceact.eu/article/50/)
7. [Interdependence of episodic and semantic memory - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC2952732/)
8. [Interdependence of episodic and semantic memory - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC2952732/)
9. [An Empirical Study of Catastrophic Forgetting in Large Language Models During Continual Fine-tuning](https://arxiv.org/abs/2308.08747)
10. [Gemma releases | Google AI for Developers](https://ai.google.dev/gemma/docs/releases)
11. [The construction of autobiographical memories in the self ...](https://pubmed.ncbi.nlm.nih.gov/10789197/)
12. [Narrative Identity - Dan P. McAdams, Kate C. McLean, 2013](https://journals.sagepub.com/doi/abs/10.1177/0963721413475622)
13. [An Empirical Study of Catastrophic Forgetting in Large Language Models During Continual Fine-tuning](https://arxiv.org/abs/2308.08747)
14. [A survey method for characterizing daily life experience](https://pubmed.ncbi.nlm.nih.gov/15576620/)
15. [Affective Computing | Books Gateway](https://direct.mit.edu/books/monograph/4296/Affective-Computing)
16. [EMA: A process model of appraisal dynamics](https://www.sciencedirect.com/science/article/abs/pii/S1389041708000314)
17. [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
18. [How do you feel--now? The anterior insula and human ...](https://pubmed.ncbi.nlm.nih.gov/19096369/)
19. [Affective Computing | Books Gateway](https://direct.mit.edu/books/monograph/4296/Affective-Computing)
20. [theory of constructed emotion: an active inference account of ...](https://academic.oup.com/scan/article/12/1/1/2823712)
21. [Global Workspace Theory (GWT) and Prefrontal Cortex - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8660103/)
22. [arXiv:1801.07243v5 [cs.AI] 25 Sep 2018](https://arxiv.org/pdf/1801.07243)
23. [Towards Empathetic Open-domain Conversation Models](https://aclanthology.org/P19-1534/)
24. [Affective Computing | Books Gateway](https://direct.mit.edu/books/monograph/4296/Affective-Computing)
25. [Interdependence of episodic and semantic memory - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC2952732/)
26. [An Empirical Study of Catastrophic Forgetting in Large Language Models During Continual Fine-tuning](https://arxiv.org/abs/2308.08747)
27. [Training on Generated Data Makes Models Forget](https://arxiv.org/abs/2305.17493)
28. [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
29. [The role of emotion in believable agents](https://dl.acm.org/doi/10.1145/176789.176803)
30. [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
31. [theory of constructed emotion: an active inference account of ...](https://academic.oup.com/scan/article/12/1/1/2823712)
32. [Training on Generated Data Makes Models Forget](https://arxiv.org/abs/2305.17493)
33. [ACT-R - Carnegie Mellon University](https://act-r.psy.cmu.edu/)
34. [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
35. [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560)
36. [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
37. [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
38. [Clarifying the Roles of Homeostasis and Allostasis in ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4166604/)
39. [Mistral 7B](https://mistral.ai/news/announcing-mistral-7b)
40. [The construction of autobiographical memories in the self ...](https://pubmed.ncbi.nlm.nih.gov/10789197/)
41. [Introducing Meta Llama 3: The most capable openly available ...](https://ai.meta.com/blog/meta-llama-3/)
42. [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)
43. [Gemma releases | Google AI for Developers](https://ai.google.dev/gemma/docs/releases)
44. [Article 50: Transparency Obligations for Providers and ...](https://artificialintelligenceact.eu/article/50/)
45. [Clarifying the Roles of Homeostasis and Allostasis in ... - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4166604/)
46. [How do you feel--now? The anterior insula and human ...](https://pubmed.ncbi.nlm.nih.gov/19096369/)
47. [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
48. [Transparency and explainability (OECD AI Principle)](https://oecd.ai/en/dashboards/ai-principles/P7)
49. [Interdependence of episodic and semantic memory - PMC - NIH](https://pmc.ncbi.nlm.nih.gov/articles/PMC2952732/)
50. [A survey method for characterizing daily life experience](https://pubmed.ncbi.nlm.nih.gov/15576620/)
51. [ACUTE-EVAL: Improved Dialogue Evaluation with ...](https://arxiv.org/abs/1909.03087)
52. [The construction of autobiographical memories in the self ...](https://pubmed.ncbi.nlm.nih.gov/10789197/)
53. [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401)
