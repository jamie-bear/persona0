from src.engine.contracts import MACRO_STEPS
from src.engine.default_setup import register_default_steps
from src.engine.orchestrator import EgoOrchestrator
from src.schema.state import AgentState


def test_register_default_steps_registers_macro_steps() -> None:
    orchestrator = EgoOrchestrator(AgentState())
    register_default_steps(orchestrator)

    missing = [step for step in MACRO_STEPS if step not in orchestrator._step_registry]
    assert not missing, f"macro steps missing from default setup: {missing}"
