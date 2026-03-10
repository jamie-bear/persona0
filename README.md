**Persona0** is a design for an ego-perspective cognitive agent architecture.

---

A lightweight "Ego Engine" architecture for humanlike AI chatbots. Featuring episodic memory, simulated affect/body states, and an off-screen life loop to create the illusion of continuity, personality, and time passage. The LLM acts only as a natural language renderer; all persistent "thinking" lives in external memory and deterministic state machines.

## Evaluation harness

This repo includes checkpoint-aligned evaluation helpers in `src/eval/` and pytest coverage in `tests/eval/`.

- Retrieval evaluation checks Precision@5 and top-5 self-relevant memory presence (CP-2).
- Self-belief safety evaluation checks confidence delta cap (`+0.15`) and contradiction rejection against core values/founding traits (CP-4).
- Threshold documentation is in `tests/eval/README.md`.

## Deployment and Operations

- Container build/runtime: `Dockerfile`
- Kubernetes manifests: `deploy/kubernetes/`
- Environment overlays: `config/environments/{dev,staging,prod}.yaml`
- Runbook: `docs/operations.md`
