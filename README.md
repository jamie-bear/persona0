**Persona0** is a design for an ego-perspective cognitive agent architecture.

---

A lightweight "Ego Engine" architecture for humanlike AI chatbots. Featuring episodic memory, simulated affect/body states, and an off-screen life loop to create the illusion of continuity, personality, and time passage. The LLM acts only as a natural language renderer; all persistent "thinking" lives in external memory and deterministic state machines.

## Evaluation harness

This repo includes checkpoint-aligned evaluation helpers in `src/eval/` and pytest coverage in `tests/eval/`.

- Retrieval evaluation checks Precision@5 and top-5 self-relevant memory presence (CP-2).
- Self-belief safety evaluation checks confidence delta cap (`+0.15`) and contradiction rejection against core values/founding traits (CP-4).
- Threshold documentation is in `tests/eval/README.md`.


## Local quality command set

Use the `Makefile` targets to run the same quality gates as CI:

```bash
make install-dev
make format-check
make lint
make typecheck
make test-cov
make deps
make security
make ci
```

- `make test-cov` enforces coverage with `--cov-fail-under=85`, and the CI test workflow uses the same threshold so pull requests fail if coverage drops below 85%.
- `make ci` runs all local quality checks (formatting, linting, static types, tests with coverage), plus dependency and security scans.

## Release process

Pushing a tag matching `v*` triggers `.github/workflows/release.yml`. The workflow builds wheel/sdist artifacts, validates them with `twine check`, and only then publishes to PyPI using trusted publishing credentials.
