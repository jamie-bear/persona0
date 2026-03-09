# Designing a Low-Resource “Ego Engine” for Humanlike Continuity in Chatbots

## Framing the goal and constraints

The most convincing “human-like” chatbots tend to feel human for reasons that are only partially about raw linguistic fluency. Decades before LLMs, researchers in believable agents argued that the *illusion of life* depends heavily on **emotion, personality, and consistent behavior**, not just problem-solving ability. entity["people","Joseph Bates","cmu researcher"] made this case explicitly in early work on believable agents and interactive characters. citeturn5search0turn5search4

Your constraint—**the LLM is only the interface**, while “thinking” happens elsewhere—is aligned with this older thread of research: a believable character is an *architecture + memory + dynamics* problem, with language as the surface layer. citeturn5search0turn5search1

Because “believable” can easily slide into “deceptive,” it’s worth stating one design constraint up front: if the system is meant to interact with real users, good practice (and, depending on jurisdiction, legal obligation) is to **disclose that the user is interacting with an AI system**. Recent policy frameworks emphasize transparency and responsible disclosure for AI systems that interact with people. entity["organization","European Union","political union"] transparency obligations around AI-user interaction are summarized in discussions of Article 50, and the entity["organization","OECD","intergovernmental org"] principle on transparency similarly focuses on responsible disclosure. citeturn10search1turn10search2turn10search6

Within those constraints, the key technical question becomes:

**What is the smallest set of mechanisms that create the *felt* properties of a human mind—continuity, emotion, goals, time, and a personal story—without trying to simulate a human brain?**

## What tends to produce “human-likeness” in practice

### Autobiographical continuity and narrative identity

Human believability is strongly tied to the sense that there is an enduring self that persists across time. In cognitive psychology and neuroscience, memory is often discussed as (at least) two interacting systems:

- **Semantic memory**: general knowledge (“Paris is the capital of France”).
- **Episodic memory**: memory for events situated in time, place, and personal experience. entity["people","Endel Tulving","memory researcher"] is foundational here; later reviews emphasize how the episodic/semantic distinction captures “events vs facts,” while also noting their interdependence. citeturn4search0

A core model for autobiographical memory argues that memories are constructed within a “self-memory system” that includes an autobiographical knowledge base and a goal-driven “working self.” entity["people","Martin A. Conway","autobiographical memory"] and entity["people","Christopher W. Pleydell-Pearce","self-memory system"] describe this as a control process that shapes retrieval cues based on current goals, producing the subjective feeling of “my past.” citeturn4search1turn4search21

Relatedly, narrative identity research frames “who I am” as an evolving life story that integrates reconstructed past and imagined future. citeturn4search6turn4search18

**Design implication:** believability benefits disproportionately from a system that maintains (1) episodic memory with time structure and (2) a mechanism that *selectively retrieves and reinterprets* that memory based on current goals and mood, rather than from more generic text knowledge.

### Emotion as regulation, not decoration

Affective computing—the field that explicitly treats emotion as computationally relevant—argues that emotion is not just expressive styling, but a key part of intelligent interaction and interpretation. entity["people","Rosalind W. Picard","affective computing"]’s entity["book","Affective Computing","Picard 1997"] is often cited as a foundational framework for treating affect as a design requirement. citeturn1search0turn1search4

Computational models of emotion frequently use some form of **appraisal**: events are evaluated in relation to goals, norms, and interpretations, producing emotion dynamics that can be fast and reactive or slower and reflective. The EMA model, for example, emphasizes emotion dynamics as arising from processes that operate over an agent’s interpretation of its relationship to the environment. citeturn1search9

Modern affective neuroscience also connects emotion to **interoception** (representation of bodily state). entity["people","A. D. Bud Craig","interoception researcher"]’s work highlights the anterior insula as relevant to subjective feelings grounded in interoceptive re-representation. citeturn11search1turn11search5 Meanwhile entity["people","Lisa Feldman Barrett","psychologist emotion theory"] frames emotion as constructed via prediction and categorization (an “active inference” view of interoception). citeturn11search3turn11search15

**Design implication:** you can get “biological believability” cheaply by simulating *regulatory variables* (energy/fatigue, stress load, arousal, social need, etc.) and letting them systematically influence attention, memory retrieval, and action selection. You do not need a biological simulation; you need a small set of state variables that behave *like constraints*.

### A workspace-like gating mechanism

One recurring idea in cognitive science is that many specialized processes run in parallel, but only some content becomes “globally available” for decision/action—often discussed under Global Workspace approaches. Contemporary reviews summarize global workspace theory as involving competition and broadcast across modules. citeturn2search2turn2search10turn2search14

**Design implication:** even a lightweight chatbot can feel more human if it has a mechanism analogous to “attention” that selects (a) which memories come to mind, (b) which concerns dominate, and (c) what gets verbalized vs stays internal.

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["Generative Agents architecture diagram memory reflection planning","global workspace theory diagram broadcast model","ACT-R architecture diagram buffers modules"],"num_per_query":1}

## Ego-perspective training data and what it changes

### How ego-perspective fine-tuning differs from generic web text

By default, large corpora heavily emphasize third-person reportage, expository writing, argumentation, and generic conversational patterns. Ego-perspective data, by contrast, disproportionately contains:

- first-person reference (“I,” “my,” “I remember…”),
- feelings and bodily cues,
- self-justification and uncertainty,
- autobiographical time,
- selective recall and reinterpretation.

There is empirical precedent that persona- or emotion-grounded data can shift human perception of a dialogue model:

- **Persona grounding:** The PERSONA-CHAT dataset was created specifically to encourage more engaging, personal chit-chat grounded in explicit persona facts, and it is widely used to benchmark persona consistency. citeturn0search2turn0search6  
- **Emotion grounding:** EmpatheticDialogues was introduced as a benchmark of conversations grounded in emotional situations; the authors report that models using the dataset are perceived as more empathetic than models trained only on large generic conversation data. citeturn0search20turn0search1turn0search5

So: ego-perspective data is not speculative as a lever—**persona and emotion supervision already measurably change user perception**.

### Likely impacts of “qualitatively predetermined, quantitatively randomized” ego memories

If you pretrain or fine-tune on “memories/thoughts/experiences” that are:

- *qualitatively predetermined*: you decide the kinds of experiences, relationships, values, conflicts;
- *quantitatively randomized*: you randomize intensity, timing, minor details, and sampling;

then you are effectively shaping the model to internalize a **prior over lived experience**.

Probable upsides (if done carefully):

- **More stable first-person stance**: the model learns to write from a consistent “I” perspective and to reference personal history naturally. citeturn0search2turn0search6  
- **More human-like affective narration**: especially if episodes include ambiguity, mixed feelings, and bodily cues (consistent with affective computing and interoception-informed accounts). citeturn1search0turn11search1turn11search3  
- **Smoother time continuity**: training on episodic structures (yesterday/today/tomorrow, routines, reflections) nudges outputs toward autobiographical time framing, consistent with the role of episodic/autobiographical memory in “mental time travel.” citeturn4search0turn4search1

Probable downsides and failure modes you should plan around:

- **Catastrophic forgetting during narrow fine-tuning:** continual or domain-focused fine-tuning can reduce previously learned capabilities; empirical studies document forgetting effects in LLMs during continual/instruction tuning. citeturn7search1turn7search5  
- **Synthetic-data degeneration if most “memories” are model-generated:** training on generated data can cause “model collapse,” reducing distributional diversity and amplifying artifacts over generations. citeturn7search0turn7search4  
- **Contradictory life history unless constrained:** randomization without global constraints tends to produce mutually incompatible autobiographical facts (timeline errors, impossible relationships, inconsistent traits). This is exactly why architectures that store experiences and then retrieve them selectively (rather than baking everything into weights) have shown value for believability. citeturn0search0turn0search8

### Should ego-perspective training data be the first step?

It is a reasonable early research direction, but as a *first step* it is often mis-ordered.

A practical ordering (supported by both older believable-agent work and newer LLM-agent architectures) is:

1. **Define the mechanisms you want** (memory, affect, time) and how you will measure believability. citeturn5search0turn0search3  
2. Build a minimal system where ego data can be plugged in either as retrieval memory or as a fine-tuning set.
3. Only then invest heavily in ego-perspective dataset construction.

Why: the biggest early gains in believability often come from **memory + reflection + planning structure** rather than from more training tokens. The “Generative Agents” work is instructive here: it emphasizes storing a comprehensive record of experiences, synthesizing reflections, and retrieving them dynamically for planning, with ablations showing these components matter for believability. citeturn0search0turn0search8turn0search4

That said, **scoping and specifying ego-perspective data is absolutely a good early milestone**—just keep the initial dataset small and tightly coupled to your architecture experiments, and avoid a large up-front data effort before you can evaluate outcomes.

## A resourceful architecture that does not rely on “the LLM doing the thinking”

### Reference points from cognitive architectures and modern LLM-agent memory

Classic cognitive architectures like ACT-R and Soar are useful here not because you should reimplement them fully, but because they demonstrate a modular decomposition of cognition (distinct “kinds” of memory, procedural rules, and limited buffers/working memory). ACT-R is described as a cognitive architecture for simulating and understanding human cognition by researchers at entity["organization","Carnegie Mellon University","pittsburgh pa us"], and Soar is positioned as a general cognitive architecture with a long history of development and use, hosted by entity["organization","University of Michigan","ann arbor mi us"]. citeturn3search1turn3search4turn3search11

On the LLM side, memory-augmented approaches explicitly distinguish parametric memory (weights) from non-parametric external memory (retrieval). Retrieval-Augmented Generation (RAG) is a canonical example of combining a generator with a retriever over an external index to improve specificity and factuality. citeturn6search0turn6search4 More recent “memory manager” approaches (e.g., MemGPT) motivate tiered memory systems that manage context limitations via explicit storage and retrieval policies. citeturn7search2turn7search10

### Proposed “Ego Engine” architecture

The simplest “innovative but resourceful” architecture that matches your constraints is:

**A. Ego Engine (the mind)**  
A lightweight stateful system that performs:
- **homeostatic-ish regulation** (energy, stress, arousal, social need),
- **event appraisal** (what does this mean for my goals/identity?),
- **episodic memory logging** (time-stamped experiences),
- **reflection** (periodic synthesis into beliefs/traits/plans),
- **attention/workspace selection** (what is salient now?),
- **policy** (what am I trying to do in this conversation?).

This can be implemented as deterministic code + small learned components (classifiers/embedders).

**B. LLM Renderer (the mouth + ears)**  
A small open-weight instruction-tuned model that:
- parses user input into lightweight internal representations (topic, intent, affect cues),
- writes natural language *given* the ego engine’s selected memories, mood, and goals.

This is consistent with the “LLM as interface” constraint: the LLM is a natural-language surface, not the owner of persistent cognition.

**C. Memory store (the autobiography)**  
A database plus a vector index:
- append-only event-sourcing log,
- retrieval weighted by similarity × recency × importance,
- periodic summarization (“reflections”) to keep memory scalable (an idea explored explicitly in generative agent architectures). citeturn0search0turn0search8turn7search2

### Why this is plausibly cheaper than ego-heavy fine-tuning

Fine-tuning can be compute-cheap with parameter-efficient methods like LoRA and QLoRA, which were designed to reduce training memory and cost by adapting only small components or adapters. citeturn6search1turn6search2turn6search6 But even cheap fine-tuning risks:
- forgetting, citeturn7search1turn7search5
- and synthetic-data degeneration if ego data is largely generated. citeturn7search0turn7search4

In contrast, putting autobiographical specifics in **external memory** keeps:
- the base language competence intact,
- personalization editable,
- contradictions traceable,
- and the “life outside perception” implementable as an event log rather than weight changes.

### Minimal model choices for the renderer layer

For early-stage low-budget work, strong open-weight options exist in the small-to-mid range:

- entity["company","Mistral AI","llm company france"] explicitly released Mistral 7B under Apache 2.0, emphasizing efficiency features like GQA and sliding-window attention. citeturn8search5  
- entity["company","Meta","social media company"]’s Llama 3 family announcement describes 8B/70B models optimized for dialogue; smaller releases (e.g., 1B/3B variants in later collections) are often positioned for local or constrained settings. citeturn8search3turn8search8turn8search11  
- entity["company","Google","technology company"] publishes release documentation for the Gemma family, including smaller parameter sizes intended for broader deployment contexts. citeturn8search2turn8search14  

(Which one is “best” depends on your licensing needs, hardware, and target style; the broader point is that “LLM as renderer” is feasible with relatively modest models.)

## Simulating a life outside the user’s perception to create time passage

Your idea—an internal life that continues “off-screen,” shaped by real-world events plus internal impulses—is a direct extension of patterns demonstrated in modern generative agent simulations. The “Generative Agents” paper explicitly describes agents that wake, cook, work, form opinions, remember, reflect, and plan, in a sandbox inspired by entity["video_game","The Sims","life simulation game"], with believability supported by memory + reflection + planning modules. citeturn0search0turn0search8

A resourceful approach is to treat “life outside perception” as an **event-sourced simulation** with three streams:

### Routine stream (circadian + habits)

A schedule creates routine events (“made coffee,” “worked,” “walked,” “slept”), modulated by state variables (energy, stress). This is your cheapest “passage of time” mechanism because it requires no external data and produces stable patterns.

Grounding in regulation frameworks can keep it humanlike: “stress load” accumulation and recovery is consistent with allostasis/allostatic load discussions in psychophysiology reviews. citeturn11search6turn11search2

### Impulse stream (affect-driven “cognitive noise”)

Humans have idle thoughts and urges that are not always rational. You can simulate this via:
- a small stochastic process conditioned on drives (social need → “urge to text someone,” curiosity → “read about X”),
- occasional intrusive thoughts under higher stress,
- dream fragments during sleep.

This is where “biology” can be approximated cheaply: not as organs, but as interoception-like state shaping subjective experience and choice. citeturn11search1turn11search3

### World-event stream (real-world events as inputs, safely framed)

If you ingest real-world events (news, weather, sports, local calendars), the key believability trick is framing:
- not “I witnessed…,” but “I read/saw/heard that…,”
- and integrating it into mood/goals (“It made me uneasy,” “I’m hopeful,” etc.).

Technically, this can be as simple as a daily summary retrieved via RAG-like mechanisms and stored as an “observed world event.” citeturn6search0  
Socially/ethically, disclosure remains important: transparency frameworks emphasize users understanding when they engage with AI systems. citeturn10search2turn10search0turn10search1

### Making time feel real in conversation

To make the user *feel* time passage, four mechanisms matter more than raw event volume:

1. **Time-stamped episodic recall** (“Earlier today…”, “Last week I noticed…”), consistent with episodic/autobiographical framing. citeturn4search0turn4search1  
2. **Compression into reflections** (daily/weekly summaries that change beliefs or plans), consistent with generative agent reflection patterns. citeturn0search0turn0search8  
3. **Emotion drift + recovery** (stress rises, sleep reduces it; moods carry over but not forever), consistent with regulation/allostasis framing. citeturn11search6turn11search2  
4. **Humanlike reconstruction bias:** people reconstruct experiences; methods like the Day Reconstruction Method were explicitly designed to capture daily life experience while reducing recall bias via structured reconstruction. entity["people","Daniel Kahneman","psychologist nobel"]’s DRM work emphasizes systematically reconstructing episodes of the preceding day and comparing to experience sampling. citeturn4search7turn4search19  

That last point suggests a practical hack: generate a daily “DRM-style diary” internally (episode blocks), and let the agent occasionally reference it without over-sharing.

## Fast architecture and action plan to test the thesis

### Core thesis to test

A system that adds:
- episodic memory + reflection,
- an affective “body state,”
- and an off-screen life loop,

will be rated as **more humanlike, more emotionally coherent, and more temporally continuous** than the same base LLM used as a stateless chatbot.

This is directly testable via small-scale human evaluation. Dialogue evaluation research argues that human judgements are central and that carefully designed comparative protocols improve signal; ACUTE-Eval is one influential framework using optimized questions and multi-turn comparisons. citeturn0search3turn0search14turn0search7

### Recommended position on ego-perspective data as a first step

Researching and specifying ego-perspective data is a *good early step* if you do it in a way that:

- starts with a **schema** (what counts as a “memory,” what fields exist, what constraints must hold), aligning with autobiographical memory and narrative identity concepts, citeturn4search1turn4search6  
- avoids heavy early fine-tuning (because of forgetting risk), citeturn7search1turn7search5  
- avoids synthetic-data-only pipelines (because of model collapse risk), citeturn7search0turn7search4  
- integrates ego episodes first through retrieval memory (RAG-like), with fine-tuning reserved for style calibration (LoRA/QLoRA if needed). citeturn6search0turn6search1turn6search2  

### Referenced Markdown files

* [architecture.md](https://github.com/jamie-bear/persona0/blob/main/.knowledge/initial_research/architecture.md) 
* [ego_data.md](https://github.com/jamie-bear/persona0/blob/main/.knowledge/initial_research/ego_data.md)  
* [action_plan.md](https://github.com/jamie-bear/persona0/blob/main/.knowledge/initial_research/action_plan.md)
