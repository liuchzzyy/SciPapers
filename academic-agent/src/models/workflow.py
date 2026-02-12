from dataclasses import dataclass, field
from typing import List, Dict, Any
from src.models.intent import Intent


@dataclass
class WorkflowStep:
    """Single workflow step"""

    mcp_server: str  # "feedder", "zotero", "logseq"
    tool_name: str  # Tool name
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on


@dataclass
class Workflow:
    """Academic workflow definition"""

    intent: Intent
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow"""
        self.steps.append(step)

    def get_ready_steps(self, completed_steps: List[str]) -> List[WorkflowStep]:
        """Get steps whose dependencies are satisfied"""
        return [
            step
            for step in self.steps
            if all(dep in completed_steps for dep in step.depends_on)
        ]
