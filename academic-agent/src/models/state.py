from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class AgentState(BaseModel):
    """Master Agent state for LangGraph"""

    user_query: str = Field(description="User's natural language query")
    intent: Optional[str] = Field(default=None, description="Detected intent")
    workflow: Optional[Dict[str, Any]] = Field(default=None, description="Workflow to execute")
    step_results: List[Dict[str, Any]] = Field(
        default_factory=list, description="Step execution results"
    )
    context: Dict[str, Any] = Field(default_factory=dict, description="Conversation context")
    final_response: Optional[str] = Field(default=None, description="Final response to user")
    error: Optional[str] = Field(default=None, description="Error message if failed")
