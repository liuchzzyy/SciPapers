# Master Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Master Agent orchestration layer that integrates existing MCP submodules (feedder-mcp, logseq-mcp, zotero-mcp) into a unified academic research assistant.

**Architecture:**
- Master Agent uses LangGraph for workflow orchestration
- Communicates with existing MCP servers via stdio protocol
- Provides academic workflow templates (paper discovery, analysis, literature review)
- Maintains conversation context and manages Zotero-Logseq synchronization

**Tech Stack:**
- Python 3.12+
- MCP SDK for server communication
- LangGraph for agent orchestration
- Pydantic v2 for data models
- Pytest for testing

---

## Task 1: Project Foundation Setup

**Files:**
- Create: `src/__init__.py`
- Create: `src/main.py`
- Create: `src/server.py`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `README.md`

**Step 1: Create project structure**

```bash
# Create src directory structure
mkdir -p src/orchestrator src/integration src/workflows src/models
touch src/__init__.py
touch src/orchestrator/__init__.py
touch src/integration/__init__.py
touch src/workflows/__init__.py
touch src/models/__init__.py
```

**Step 2: Create pyproject.toml**

```toml
# pyproject.toml
[project]
name = "academic-agent"
version = "0.1.0"
description = "Academic research assistant with Master Agent orchestration"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "mcp>=0.9.0",
    "langgraph>=0.2.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.7.0",
    "mypy>=1.0.0",
]

[project.scripts]
academic-agent = "src.main:cli"
serve = "src.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 3: Run to verify structure**

Run: `ls -la src/`
Expected: List of directories (orchestrator, integration, workflows, models)

**Step 4: Commit**

```bash
git add pyproject.toml src/
git commit -m "feat: initialize project structure and configuration"
```

---

## Task 2: Core Data Models

**Files:**
- Create: `src/models/intent.py`
- Create: `src/models/workflow.py`
- Create: `src/models/context.py`
- Create: `src/models/state.py`
- Test: `tests/test_models.py`

**Step 1: Write intent model tests**

```python
# tests/test_models.py
import pytest
from src.models.intent import Intent, detect_intent_from_query

def test_detect_paper_discovery_intent():
    query = "帮我把最近一周arXiv上关于transformer的论文导入我的文献库"
    intent = detect_intent_from_query(query)
    assert intent == Intent.PAPER_DISCOVERY

def test_detect_paper_analysis_intent():
    query = "分析这篇论文ABCD1234"
    intent = detect_intent_from_query(query)
    assert intent == Intent.PAPER_ANALYSIS

def test_detect_literature_review_intent():
    query = "生成深度学习在NLP领域的综述"
    intent = detect_intent_from_query(query)
    assert intent == Intent.LITERATURE_REVIEW

def test_detect_knowledge_query_intent():
    query = "attention mechanism是什么"
    intent = detect_intent_from_query(query)
    assert intent == Intent.KNOWLEDGE_QUERY
```

**Step 2: Run tests (expected to fail)**

Run: `pytest tests/test_models.py::test_detect_paper_discovery_intent -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.models.intent'"

**Step 3: Implement Intent enum**

```python
# src/models/intent.py
from enum import Enum

class Intent(Enum):
    """User intent types"""
    PAPER_DISCOVERY = "paper_discovery"
    PAPER_ANALYSIS = "paper_analysis"
    LITERATURE_REVIEW = "literature_review"
    KNOWLEDGE_QUERY = "knowledge_query"
    WORKFLOW_AUTOMATION = "workflow_automation"
```

**Step 4: Implement intent detection**

```python
# src/models/intent.py (continued)
from typing import Optional

def detect_intent_from_query(query: str) -> Intent:
    """Detect user intent from natural language query"""
    query_lower = query.lower()

    # Check for paper discovery keywords
    discovery_keywords = ["找论文", "新论文", "导入", "发现", "fetch", "import", "discover"]
    if any(kw in query_lower for kw in discovery_keywords):
        return Intent.PAPER_DISCOVERY

    # Check for analysis keywords
    analysis_keywords = ["分析", "理解", "总结", "analyze", "understand", "summarize"]
    if any(kw in query_lower for kw in analysis_keywords):
        return Intent.PAPER_ANALYSIS

    # Check for literature review keywords
    review_keywords = ["综述", "回顾", "总结研究", "review", "survey"]
    if any(kw in query_lower for kw in review_keywords):
        return Intent.LITERATURE_REVIEW

    # Check for workflow automation
    automation_keywords = ["自动", "定期", "每天", "automate", "schedule", "daily"]
    if any(kw in query_lower for kw in automation_keywords):
        return Intent.WORKFLOW_AUTOMATION

    # Default to knowledge query
    return Intent.KNOWLEDGE_QUERY
```

**Step 5: Run tests to verify**

Run: `pytest tests/test_models.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/models/intent.py tests/test_models.py
git commit -m "feat: implement intent detection with keyword matching"
```

**Step 7: Implement workflow models**

```python
# src/models/workflow.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.models.intent import Intent

@dataclass
class WorkflowStep:
    """Single workflow step"""
    mcp_server: str      # "feedder", "zotero", "logseq"
    tool_name: str       # Tool name
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
            step for step in self.steps
            if all(dep in completed_steps for dep in step.depends_on)
        ]
```

**Step 8: Implement state models**

```python
# src/models/state.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class AgentState(BaseModel):
    """Master Agent state for LangGraph"""
    user_query: str = Field(description="User's natural language query")
    intent: Optional[str] = Field(default=None, description="Detected intent")
    workflow: Optional[Dict[str, Any]] = Field(default=None, description="Workflow to execute")
    step_results: List[Dict[str, Any]] = Field(default_factory=list, description="Step execution results")
    context: Dict[str, Any] = Field(default_factory=dict, description="Conversation context")
    final_response: Optional[str] = Field(default=None, description="Final response to user")
    error: Optional[str] = Field(default=None, description="Error message if failed")
```

**Step 9: Implement context models**

```python
# src/models/context.py
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path

@dataclass
class ConversationContext:
    """Maintains conversation state across interactions"""
    user_profile: Dict[str, Any] = field(default_factory=dict)
    active_items: Dict[str, Dict] = field(default_factory=dict)
    workflow_history: List[Dict] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)

    def remember(self, key: str, value: Any) -> None:
        """Store information for later use"""
        self.user_profile[key] = value
        self.last_update = datetime.now()

    def recall(self, key: str, default: Any = None) -> Any:
        """Retrieve previously stored information"""
        return self.user_profile.get(key, default)

    def add_active_item(self, item_key: str, metadata: Dict) -> None:
        """Add currently discussed paper"""
        self.active_items[item_key] = {
            "metadata": metadata,
            "added_at": datetime.now().isoformat()
        }
        self.last_update = datetime.now()

    def get_active_item(self, item_key: Optional[str] = None) -> Optional[Dict]:
        """Get current or most recent active item"""
        if item_key:
            return self.active_items.get(item_key)
        if self.active_items:
            return max(
                self.active_items.items(),
                key=lambda x: x[1]["added_at"]
            )[1]
        return None

    def add_workflow(self, workflow_data: Dict) -> None:
        """Record workflow to history"""
        self.workflow_history.append({
            "workflow": workflow_data,
            "timestamp": datetime.now().isoformat()
        })
        self.last_update = datetime.now()

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "user_profile": self.user_profile,
            "active_items": {
                k: {
                    "metadata": v["metadata"],
                    "added_at": v["added_at"]
                }
                for k, v in self.active_items.items()
            },
            "workflow_history": [
                {
                    "intent": w["workflow"].get("intent"),
                    "description": w["workflow"].get("description"),
                    "timestamp": w["timestamp"]
                }
                for w in self.workflow_history[-10:]
            ],
            "last_update": self.last_update.isoformat()
        }

    def save(self, path: str) -> None:
        """Save context to file"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> 'ConversationContext':
        """Load context from file"""
        if not Path(path).exists():
            return cls()
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ctx = cls()
        ctx.user_profile = data.get("user_profile", {})
        ctx.active_items = {
            k: {
                "metadata": v["metadata"],
                "added_at": v["added_at"]
            }
            for k, v in data.get("active_items", {}).items()
        }
        ctx.workflow_history = data.get("workflow_history", [])
        last_update = data.get("last_update")
        if last_update:
            ctx.last_update = datetime.fromisoformat(last_update)
        return ctx
```

**Step 10: Run all model tests**

Run: `pytest tests/test_models.py -v`
Expected: All tests PASS

**Step 11: Commit**

```bash
git add src/models/ tests/test_models.py
git commit -m "feat: implement workflow, state, and context models"
```

---

## Task 3: MCP Client Communication Layer

**Files:**
- Create: `src/orchestrator/mcp_client.py`
- Test: `tests/test_mcp_client.py`

**Step 1: Write MCP client tests**

```python
# tests/test_mcp_client.py
import pytest
from src.orchestrator.mcp_client import MCPClientManager

@pytest.mark.asyncio
async def test_create_feedder_client():
    manager = MCPClientManager()
    client = await manager.get_client("feedder")
    assert client is not None
    assert client.server_name == "feedder"
    await manager.close_all()

@pytest.mark.asyncio
async def test_create_zotero_client():
    manager = MCPClientManager()
    client = await manager.get_client("zotero")
    assert client is not None
    await manager.close_all()

@pytest.mark.asyncio
async def test_create_logseq_client():
    manager = MCPClientManager()
    client = await manager.get_client("logseq")
    assert client is not None
    await manager.close_all()

@pytest.mark.asyncio
async def test_execute_feedder_tool():
    manager = MCPClientManager()
    result = await manager.execute_tool(
        "feedder",
        "generate_keywords",
        {"topic": "transformer"}
    )
    assert "keywords" in result or "error" in result
    await manager.close_all()
```

**Step 2: Run tests (expected to fail)**

Run: `pytest tests/test_mcp_client.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement MCP client manager**

```python
# src/orchestrator/mcp_client.py
from typing import Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from pathlib import Path
import asyncio

class MCPClient:
    """Wrapper for MCP client session"""

    def __init__(self, server_name: str, server_path: str, session: ClientSession):
        self.server_name = server_name
        self.server_path = server_path
        self.session = session

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on this MCP server"""
        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
            return {
                "status": "success",
                "data": result.content[0] if result.content else None,
                "server": self.server_name
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "server": self.server_name,
                "tool": tool_name
            }

class MCPClientManager:
    """Manages connections to MCP servers"""

    def __init__(self, base_path: str = "../"):
        self.base_path = Path(base_path).resolve()
        self.clients: Dict[str, MCPClient] = {}
        self.sessions: Dict[str, ClientSession] = {}

    async def get_client(self, server_name: str) -> MCPClient:
        """Get or create client for server"""
        if server_name in self.clients:
            return self.clients[server_name]

        # Create new client
        server_path = self.base_path / f"{server_name}-mcp"

        if not server_path.exists():
            raise FileNotFoundError(f"MCP server not found: {server_path}")

        server_params = StdioServerParameters(
            command="uv",
            args=["--directory", str(server_path), "run", f"{server_name}-mcp"],
            env=None
        )

        session = ClientSession(server_params)
        await session.__aenter__()
        await session.initialize()

        self.sessions[server_name] = session
        self.clients[server_name] = MCPClient(server_name, str(server_path), session)

        return self.clients[server_name]

    async def execute_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool on specific MCP server"""
        client = await self.get_client(server_name)
        return await client.call_tool(tool_name, arguments)

    async def close_all(self) -> None:
        """Close all MCP sessions"""
        for session in self.sessions.values():
            await session.__aexit__(None, None, None)
        self.clients.clear()
        self.sessions.clear()
```

**Step 4: Run tests to verify**

Run: `pytest tests/test_mcp_client.py -v`
Expected: Tests may PASS or FAIL due to missing submodules - that's OK for now

**Step 5: Add skip decorators for missing submodules**

```python
# tests/test_mcp_client.py (add at top)
import os
from pathlib import Path

def skip_if_no_submodule(submodule_name: str):
    """Skip test if submodule not available"""
    path = Path(f"../{submodule_name}-mcp")
    return pytest.mark.skipif(
        not path.exists(),
        reason=f"{submodule_name}-mcp submodule not found"
    )

skip_feedder = skip_if_no_submodule("feedder")
skip_zotero = skip_if_no_submodule("zotero")
skip_logseq = skip_if_no_submodule("logseq")

# Add decorators to tests
@pytest.mark.asyncio
@skip_feedder
async def test_execute_feedder_tool():
    # ... existing test code
```

**Step 6: Commit**

```bash
git add src/orchestrator/mcp_client.py tests/test_mcp_client.py
git commit -m "feat: implement MCP client manager for server communication"
```

---

## Task 4: Intent Recognition and Workflow Planning

**Files:**
- Create: `src/orchestrator/planner.py`
- Test: `tests/test_planner.py`

**Step 1: Write planner tests**

```python
# tests/test_planner.py
import pytest
from src.orchestrator.planner import WorkflowPlanner
from src.models.intent import Intent
from src.models.workflow import Workflow

def test_plan_paper_discovery_workflow():
    planner = WorkflowPlanner()
    query = "帮我找最近一周关于transformer的论文"
    workflow = planner.plan_workflow(query)

    assert workflow.intent == Intent.PAPER_DISCOVERY
    assert len(workflow.steps) > 0
    assert workflow.steps[0].mcp_server == "feedder"
    assert workflow.steps[0].tool_name == "fetch_feeds"

def test_plan_paper_analysis_workflow():
    planner = WorkflowPlanner()
    query = "分析论文ABCD1234"
    workflow = planner.plan_workflow(query)

    assert workflow.intent == Intent.PAPER_ANALYSIS
    assert any(s.tool_name == "batch_analyze_pdfs" for s in workflow.steps)

def test_plan_literature_review_workflow():
    planner = WorkflowPlanner()
    query = "生成transformer的综述"
    workflow = planner.plan_workflow(query)

    assert workflow.intent == Intent.LITERATURE_REVIEW
```

**Step 2: Run tests (expected to fail)**

Run: `pytest tests/test_planner.py::test_plan_paper_discovery_workflow -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement workflow planner**

```python
# src/orchestrator/planner.py
from typing import List, Dict, Any, Optional
import re
from src.models.intent import Intent, detect_intent_from_query
from src.models.workflow import Workflow, WorkflowStep

class WorkflowPlanner:
    """Plans workflows based on user intent"""

    def __init__(self):
        self.context = None  # Will be set externally

    def set_context(self, context):
        """Set conversation context for planning"""
        self.context = context

    def plan_workflow(self, query: str) -> Workflow:
        """Create workflow from natural language query"""
        intent = detect_intent_from_query(query)

        if intent == Intent.PAPER_DISCOVERY:
            return self._plan_discovery(query)
        elif intent == Intent.PAPER_ANALYSIS:
            return self._plan_analysis(query)
        elif intent == Intent.LITERATURE_REVIEW:
            return self._plan_review(query)
        else:
            return self._plan_query(query)

    def _plan_discovery(self, query: str) -> Workflow:
        """Plan paper discovery workflow"""
        steps = [
            WorkflowStep(
                mcp_server="feedder",
                tool_name="fetch_feeds",
                parameters={"limit": 200, "since": 7}
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="generate_keywords",
                parameters={"topic": self._extract_topic(query)},
                depends_on=["step_0"]
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="filter_papers",
                parameters={"use_ai": True},
                depends_on=["step_1"]
            ),
            WorkflowStep(
                mcp_server="zotero",
                tool_name="get_metadata",
                parameters={"limit": 1000},
                depends_on=["step_2"]
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="enrich_papers",
                parameters={"api": "all"},
                depends_on=["step_3"]
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="export_papers",
                parameters={"format": "zotero"},
                depends_on=["step_4"]
            ),
            WorkflowStep(
                mcp_server="logseq",
                tool_name="create_page",
                parameters={},
                depends_on=["step_5"]
            ),
        ]

        return Workflow(
            intent=Intent.PAPER_DISCOVERY,
            description="Discover and import relevant papers from RSS feeds",
            steps=steps
        )

    def _plan_analysis(self, query: str) -> Workflow:
        """Plan paper analysis workflow"""
        item_key = self._extract_item_key(query)
        if not item_key:
            # Return minimal workflow that will ask for item_key
            return Workflow(
                intent=Intent.PAPER_ANALYSIS,
                description="Analyze a paper (requires item key)",
                steps=[
                    WorkflowStep(
                        mcp_server="system",
                        tool_name="ask_for_item_key",
                        parameters={}
                    )
                ]
            )

        steps = [
            WorkflowStep(
                mcp_server="zotero",
                tool_name="prepare_analysis",
                parameters={"item_keys": [item_key]},
            ),
            WorkflowStep(
                mcp_server="zotero",
                tool_name="batch_analyze_pdfs",
                parameters={"model": "deepseek-chat"},
                depends_on=["step_0"]
            ),
            WorkflowStep(
                mcp_server="logseq",
                tool_name="insert_block",
                parameters={"section": "AI分析"},
                depends_on=["step_1"]
            ),
        ]

        return Workflow(
            intent=Intent.PAPER_ANALYSIS,
            description="Deep analysis of paper content",
            steps=steps
        )

    def _plan_review(self, query: str) -> Workflow:
        """Plan literature review workflow"""
        topic = self._extract_topic(query)

        steps = [
            WorkflowStep(
                mcp_server="feedder",
                tool_name="generate_keywords",
                parameters={"topic": topic}
            ),
            WorkflowStep(
                mcp_server="zotero",
                tool_name="semantic_search",
                parameters={"query": topic, "limit": 20},
                depends_on=["step_0"]
            ),
            WorkflowStep(
                mcp_server="zotero",
                tool_name="batch_analyze_pdfs",
                parameters={},
                depends_on=["step_1"]
            ),
            WorkflowStep(
                mcp_server="logseq",
                tool_name="create_page",
                parameters={"template": "literature_review"},
                depends_on=["step_2"]
            ),
        ]

        return Workflow(
            intent=Intent.LITERATURE_REVIEW,
            description=f"Generate literature review on {topic}",
            steps=steps
        )

    def _plan_query(self, query: str) -> Workflow:
        """Plan knowledge query workflow"""
        steps = [
            WorkflowStep(
                mcp_server="zotero",
                tool_name="semantic_search",
                parameters={"query": query, "limit": 10}
            ),
            WorkflowStep(
                mcp_server="logseq",
                tool_name="simple_query",
                parameters={"query": query}
            ),
        ]

        return Workflow(
            intent=Intent.KNOWLEDGE_QUERY,
            description=f"Search knowledge base for: {query}",
            steps=steps
        )

    def _extract_topic(self, query: str) -> str:
        """Extract research topic from query"""
        # Simple extraction - can be enhanced with NLP
        # Remove common keywords
        for kw in ["生成", "综述", "找", "论文", "关于", "discover", "review", "papers"]:
            query = query.replace(kw, "")
        return query.strip()

    def _extract_item_key(self, query: str) -> Optional[str]:
        """Extract Zotero item key from query"""
        # Look for pattern like ABCD1234
        match = re.search(r'[A-Z]{4}\d{4}', query)
        return match.group(0) if match else None
```

**Step 4: Run tests to verify**

Run: `pytest tests/test_planner.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/orchestrator/planner.py tests/test_planner.py
git commit -m "feat: implement workflow planner with intent recognition"
```

---

## Task 5: Workflow Execution Engine

**Files:**
- Create: `src/orchestrator/executor.py`
- Test: `tests/test_executor.py`

**Step 1: Write executor tests**

```python
# tests/test_executor.py
import pytest
from src.orchestrator.executor import WorkflowExecutor
from src.models.workflow import Workflow, WorkflowStep

@pytest.mark.asyncio
async def test_execute_single_step():
    executor = WorkflowExecutor()
    step = WorkflowStep(
        mcp_server="feedder",
        tool_name="generate_keywords",
        parameters={"topic": "test"}
    )

    result = await executor.execute_step(step)
    assert "status" in result
    assert result["status"] in ["success", "error"]

@pytest.mark.asyncio
async def test_execute_workflow():
    executor = WorkflowExecutor()
    workflow = Workflow(
        intent=Intent.KNOWLEDGE_QUERY,
        description="Test query",
        steps=[
            WorkflowStep(
                mcp_server="zotero",
                tool_name="semantic_search",
                parameters={"query": "test", "limit": 5}
            )
        ]
    )

    results = await executor.execute_workflow(workflow)
    assert "steps_completed" in results
    assert "steps_failed" in results
```

**Step 2: Run tests (expected to fail)**

Run: `pytest tests/test_executor.py::test_execute_single_step -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement workflow executor**

```python
# src/orchestrator/executor.py
from typing import List, Dict, Any
from src.models.workflow import Workflow, WorkflowStep
from src.models.state import AgentState
from src.orchestrator.mcp_client import MCPClientManager

class WorkflowExecutor:
    """Executes workflows by coordinating MCP servers"""

    def __init__(self, client_manager: MCPClientManager):
        self.client_manager = client_manager

    async def execute_step(self, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a single workflow step"""
        try:
            result = await self.client_manager.execute_tool(
                server_name=step.mcp_server,
                tool_name=step.tool_name,
                arguments=step.parameters
            )

            # Add step metadata
            result["step_server"] = step.mcp_server
            result["step_tool"] = step.tool_name

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "step_server": step.mcp_server,
                "step_tool": = step.tool_name
            }

    async def execute_workflow(self, workflow: Workflow) -> Dict[str, Any]:
        """Execute complete workflow"""
        results = {
            "workflow": workflow.description,
            "steps_completed": [],
            "steps_failed": [],
            "final_result": None
        }

        completed_steps = []
        step_id = 0

        for step in workflow.steps:
            # Check dependencies
            if step.depends_on:
                if not all(dep in completed_steps for dep in step.depends_on):
                    continue

            # Execute step
            result = await self.execute_step(step)

            if result.get("status") == "success":
                completed_steps.append(f"step_{step_id}")
                results["steps_completed"].append({
                    "step_id": step_id,
                    "tool": f"{step.mcp_server}.{step.tool_name}",
                    "status": "success"
                })
            else:
                results["steps_failed"].append({
                    "step_id": step_id,
                    "tool": f"{step.mcp_server}.{step.tool_name}",
                    "error": result.get("error", "Unknown error")
                })

                # Decide whether to continue
                if self._is_critical_step(step):
                    break

            step_id += 1

        # Set final result
        if results["steps_failed"]:
            results["final_result"] = "completed_with_errors"
        else:
            results["final_result"] = "success"

        return results

    def _is_critical_step(self, step: WorkflowStep) -> bool:
        """Check if step is critical for workflow success"""
        critical_tools = {
            "fetch_feeds",
            "export_papers",
            "batch_analyze_pdfs"
        }
        return step.tool_name in critical_tools

    async def execute_workflow_with_context(
        self,
        workflow: Workflow,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute workflow with conversation context"""
        # Enhance workflow steps with context data
        enhanced_workflow = self._apply_context(workflow, context)

        results = await self.execute_workflow(enhanced_workflow)
        return results

    def _apply_context(self, workflow: Workflow, context: Dict[str, Any]) -> Workflow:
        """Apply conversation context to workflow"""
        # Can enhance parameters based on context
        # For example, use last discussed paper key
        return workflow
```

**Step 4: Run tests to verify**

Run: `pytest tests/test_executor.py -v`
Expected: All tests PASS (may skip if submodules missing)

**Step 5: Commit**

```bash
git add src/orchestrator/executor.py tests/test_executor.py
git commit -m "feat: implement workflow execution engine"
```

---

## Task 6: Zotero-Logseq Integration Layer

**Files:**
- Create: `src/integration/sync_adapter.py`
- Create: `src/integration/templates.py`
- Test: `tests/test_sync_adapter.py`

**Step 1: Write sync adapter tests**

```python
# tests/test_sync_adapter.py
import pytest
from src.integration.sync_adapter import ZoteroLogseqSyncAdapter
from src.integration.templates import TemplateManager

def test_generate_page_name():
    adapter = ZoteroLogseqSyncAdapter(None, None)
    item = {
        "title": "Test Paper",
        "year": 2024
    }

    page_name = adapter._generate_page_name(item)
    assert page_name == "Test Paper (2024)"

def test_apply_template():
    manager = TemplateManager()
    template = manager.get_template("academic_paper")

    content = template.format(
        title="Test",
        authors="[[Author]]",
        year="2024",
        doi="10.1234/test",
        item_key="KEY123",
        abstract="Test abstract"
    )

    assert "title:: [[Test]]" in content
    assert "zotero_key:: KEY123" in content
```

**Step 2: Run tests (expected to fail)**

Run: `pytest tests/test_sync_adapter.py::test_generate_page_name -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement template manager**

```python
# src/integration/templates.py
from typing import Dict
from pathlib import Path

class TemplateManager:
    """Manages academic templates for Logseq"""

    def __init__(self, templates_dir: str = "configs/templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._init_default_templates()

    def _init_default_templates(self):
        """Initialize default templates if not exist"""
        academic_paper_path = self.templates_dir / "academic_paper.md"

        if not academic_paper_path.exists():
            self._create_academic_paper_template(academic_paper_path)

    def _create_academic_paper_template(self, path: Path):
        """Create default academic paper template"""
        template = """---
title:: [[{title}]]
authors:: {authors}
year:: {year}
doi:: {doi}
zotero_select:: zotero://select/items/{item_key}
zotero_key:: {item_key}
publication:: {publication}
status:: to-read
tags:: {tags}
type:: paper
created:: {created_date}
---

## 摘要
{abstract}

## 研究问题
-
-
## 方法论
-
-
## 主要发现
-
-
## 局限性
-
-
## AI分析
🤖 *由academic-agent生成*
- 关键贡献：
- 方法创新点：
- 相关文献推荐：
## 个人思考
-
-
## 笔记
-
-
## 引用本文
"""
        path.write_text(template, encoding='utf-8')

    def get_template(self, template_name: str) -> str:
        """Get template content"""
        template_path = self.templates_dir / f"{template_name}.md"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_name}")

        return template_path.read_text(encoding='utf-8')

    def list_templates(self) -> Dict[str, str]:
        """List available templates"""
        templates = {}
        for template_file in self.templates_dir.glob("*.md"):
            name = template_file.stem
            templates[name] = template_file.read_text(encoding='utf-8')
        return templates
```

**Step 4: Implement sync adapter**

```python
# src/integration/sync_adapter.py
from typing import Dict, List, Any, Optional
from datetime import datetime
from src.integration.templates import TemplateManager
from src.orchestrator.mcp_client import MCPClientManager

class ZoteroLogseqSyncAdapter:
    """Synchronizes Zotero items with Logseq pages"""

    def __init__(self, client_manager: MCPClientManager):
        self.client_manager = client_manager
        self.template_manager = TemplateManager()

    async def sync_item_to_logseq(self, item: Dict) -> Dict[str, Any]:
        """Sync single Zotero item to Logseq"""
        # Check if page exists
        page_name = self._generate_page_name(item)

        # Try to get existing page
        existing = await self.client_manager.execute_tool(
            "logseq",
            "get_page",
            {"page_name": page_name}
        )

        if existing.get("status") == "success":
            return await self._update_page(page_name, item)
        else:
            return await self._create_page(item)

    def _generate_page_name(self, item: Dict) -> str:
        """Generate Logseq page name from item"""
        title = item.get("title", "Untitled")
        year = item.get("year", "n.d.")
        return f"{title} ({year})"

    async def _create_page(self, item: Dict) -> Dict[str, Any]:
        """Create new Logseq page"""
        page_name = self._generate_page_name(item)
        template = self.template_manager.get_template("academic_paper")

        # Format template variables
        authors_formatted = ", ".join([
            f"[[{a}]]" for a in item.get("authors", [])
        ])
        tags_formatted = ", ".join([
            f"[[{t}]]" for t in item.get("tags", [])
        ])

        content = template.format(
            title=item.get("title", ""),
            authors=authors_formatted,
            year=item.get("year", ""),
            doi=item.get("doi", ""),
            item_key=item.get("item_key", ""),
            publication=item.get("publication", ""),
            tags=tags_formatted,
            abstract=item.get("abstract", "")[:500] + "..."
            if item.get("abstract") else "",
            created_date=datetime.now().strftime("%Y-%m-%d")
        )

        # Create page via logseq-mcp
        result = await self.client_manager.execute_tool(
            "logseq",
            "create_page",
            {
                "page_name": page_name,
                "properties": {
                    "title": item.get("title", ""),
                    "authors": authors_formatted,
                    "year": item.get("year", ""),
                    "doi": item.get("doi", ""),
                    "zotero_key": item.get("item_key", "")
                }
            }
        )

        if result.get("status") == "success":
            # Add initial block with content
            await self.client_manager.execute_tool(
                "logseq",
                "insert_block",
                {
                    "content": content.strip(),
                    "parent_block": page_name
                }
            )

        return result

    async def _update_page(self, page_name: str, item: Dict) -> Dict[str, Any]:
        """Update existing Logseq page"""
        result = await self.client_manager.execute_tool(
            "logseq",
            "update_page_properties",
            {
                "page_name": page_name,
                "properties": {
                    "year": item.get("year", ""),
                    "doi": item.get("doi", ""),
                    "zotero_key": item.get("item_key", "")
                }
            }
        )
        return result

    async def sync_batch(self, items: List[Dict]) -> List[Dict]:
        """Sync multiple items to Logseq"""
        results = []
        for item in items:
            result = await self.sync_item_to_logseq(item)
            results.append(result)
        return results
```

**Step 5: Run tests to verify**

Run: `pytest tests/test_sync_adapter.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/integration/ tests/test_sync_adapter.py
git commit -m "feat: implement Zotero-Logseq sync adapter with templates"
```

---

## Task 7: LangGraph Master Agent

**Files:**
- Create: `src/orchestrator/graph.py`
- Create: `src/orchestrator/nodes.py`
- Test: `tests/test_graph.py`

**Step 1: Write graph tests**

```python
# tests/test_graph.py
import pytest
from src.orchestrator.graph import create_master_agent_graph
from src.models.state import AgentState

@pytest.mark.asyncio
async def test_graph_creation():
    graph = create_master_agent_graph()
    assert graph is not None

@pytest.mark.asyncio
async def test_graph_execution():
    graph = create_master_agent_graph()
    state = AgentState(user_query="找关于transformer的论文")

    result = await graph.ainvoke(state)
    assert result["intent"] is not None
    assert "final_response" in result or "error" in result
```

**Step 2: Run tests (expected to fail)**

Run: `pytest tests/test_graph.py::test_graph_creation -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement LangGraph nodes**

```python
# src/orchestrator/nodes.py
from typing import Dict, Any
from src.models.state import AgentState
from src.models.intent import detect_intent_from_query
from src.orchestrator.planner import WorkflowPlanner
from src.orchestrator.executor import WorkflowExecutor

async def understand_intent_node(state: AgentState) -> AgentState:
    """Understand user intent from query"""
    query = state["user_query"]
    intent = detect_intent_from_query(query)

    state["intent"] = intent.value
    return state

async def plan_workflow_node(state: AgentState) -> AgentState:
    """Plan workflow based on intent"""
    planner = WorkflowPlanner()
    workflow = planner.plan_workflow(state["user_query"])

    state["workflow"] = {
        "intent": workflow.intent.value,
        "description": workflow.description,
        "steps": [
            {
                "mcp_server": step.mcp_server,
                "tool_name": step.tool_name,
                "parameters": step.parameters,
                "depends_on": step.depends_on
            }
            for step in workflow.steps
        ]
    }
    return state

async def execute_tools_node(state: AgentState) -> AgentState:
    """Execute workflow tools"""
    from src.orchestrator.mcp_client import MCPClientManager

    client_manager = MCPClientManager()
    executor = WorkflowExecutor(client_manager)

    try:
        workflow_data = state["workflow"]
        from src.models.workflow import Workflow, WorkflowStep

        # Reconstruct workflow object
        steps = [
            WorkflowStep(
                mcp_server=s["mcp_server"],
                tool_name=s["tool_name"],
                parameters=s["parameters"],
                depends_on=s["depends_on"]
            )
            for s in workflow_data["steps"]
        ]
        workflow = Workflow(
            intent=state["intent"],
            description=workflow_data["description"],
            steps=steps
        )

        results = await executor.execute_workflow(workflow)
        state["step_results"].append(results)

        # Set final response
        if results.get("final_result") == "success":
            state["final_response"] = _format_success_response(results)
        else:
            state["final_response"] = _format_error_response(results)

    except Exception as e:
        state["error"] = str(e)
        state["final_response"] = f"Error executing workflow: {e}"

    finally:
        await client_manager.close_all()

    return state

def _format_success_response(results: Dict) -> str:
    """Format successful execution response"""
    completed = len(results.get("steps_completed", []))
    failed = len(results.get("steps_failed", []))

    if failed == 0:
        return f"✅ Workflow completed successfully. {completed} steps executed."
    else:
        return f"⚠️ Workflow completed with {failed} errors. {completed} steps successful."

def _format_error_response(results: Dict) -> str:
    """Format error response"""
    failed = results.get("steps_failed", [])
    errors = "\n".join([
        f"- {f.get('error', 'Unknown')}"
        for f in failed
    ])
    return f"❌ Workflow execution failed:\n{errors}"
```

**Step 4: Implement LangGraph**

```python
# src/orchestrator/graph.py
from langgraph.graph import StateGraph, END
from src.models.state import AgentState
from src.orchestrator.nodes import (
    understand_intent_node,
    plan_workflow_node,
    execute_tools_node
)

def create_master_agent_graph():
    """Create Master Agent state graph"""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("understand_intent", understand_intent_node)
    workflow.add_node("plan_workflow", plan_workflow_node)
    workflow.add_node("execute_tools", execute_tools_node)

    # Set entry point
    workflow.set_entry_point("understand_intent")

    # Add edges
    workflow.add_edge("understand_intent", "plan_workflow")
    workflow.add_edge("plan_workflow", "execute_tools")
    workflow.add_edge("execute_tools", END)

    return workflow.compile()
```

**Step 5: Run tests to verify**

Run: `pytest tests/test_graph.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/orchestrator/graph.py src/orchestrator/nodes.py tests/test_graph.py
git commit -m "feat: implement LangGraph-based master agent"
```

---

## Task 8: CLI Entry Point

**Files:**
- Create: `src/main.py`
- Create: `src/server.py`

**Step 1: Implement CLI**

```python
# src/main.py
import asyncio
import sys
from pathlib import Path
from src.orchestrator.graph import create_master_agent_graph
from src.models.state import AgentState
from src.models.context import ConversationContext

async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: academic-agent <your query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    # Load conversation context
    context_path = Path.home() / ".academic-agent" / "context.json"
    context = ConversationContext.load(str(context_path))

    # Create and execute graph
    graph = create_master_agent_graph()
    state = AgentState(
        user_query=query,
        context=context.to_dict()
    )

    result = await graph.ainvoke(state)

    # Print result
    print("\n" + "="*50)
    print(result.get("final_response", "No response generated"))
    print("="*50 + "\n")

    # Save updated context
    context.save(str(context_path))

if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Implement MCP server entry**

```python
# src/server.py
from mcp.server import Server
from src.orchestrator.graph import create_master_agent_graph
from src.models.state import AgentState
import asyncio
import json

app = Server("academic-agent")

@app.list_tools()
async def list_tools() -> list[dict]:
    """List available tools"""
    return [
        {
            "name": "execute_query",
            "description": "Execute academic workflow query",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query"
                    }
                },
                "required": ["query"]
            }
        }
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> str:
    """Handle tool call"""
    if name == "execute_query":
        query = arguments.get("query", "")
        graph = create_master_agent_graph()
        state = AgentState(user_query=query)
        result = await graph.ainvoke(state)
        return json.dumps({
            "response": result.get("final_response"),
            "intent": result.get("intent"),
            "workflow": result.get("workflow")
        }, ensure_ascii=False)

    return json.dumps({"error": "Unknown tool"})

def main():
    """MCP server entry point"""
    import mcp.server.stdio

    mcp.server.stdio.run(app)

if __name__ == "__main__":
    main()
```

**Step 3: Test CLI**

Run: `uv run academic-agent 帮我找关于transformer的论文`
Expected: Output showing workflow execution

**Step 4: Commit**

```bash
git add src/main.py src/server.py
git commit -m "feat: implement CLI and MCP server entry points"
```

---

## Task 9: Documentation and Configuration

**Files:**
- Update: `README.md`
- Update: `.env.example`
- Create: `docs/plans/README.md`

**Step 1: Create comprehensive README**

```markdown
# academic-agent

Academic research assistant with Master Agent orchestration, integrating feedder-mcp, logseq-mcp, and zotero-mcp.

## Features

- 🤖 **Natural Language Interface**: Chat with your research library in plain language
- 📚 **Paper Discovery**: Automatically fetch and filter papers from RSS/Gmail
- 🔍 **Semantic Search**: Find papers by meaning, not just keywords
- 📝 **Deep Analysis**: AI-powered paper analysis and summarization
- 🔄 **Auto-Sync**: Keep Zotero and Logseq in sync
- 📊 **Literature Reviews**: Generate comprehensive reviews automatically

## Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
┌──────▼────────────────┐
│  Master Agent (MCP)   │
│  - Intent recognition  │
│  - Workflow planning  │
│  - Tool orchestration│
└──────┬────────────────┘
       │
┌───────┴──────┬──────────────┬─────────────┐
│               │              │             │
▼               ▼              ▼             ▼
feedder-mcp   zotero-mcp   logseq-mcp
(RSS/Fetch)   (Library)     (Notes)
```

## Installation

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/your-org/academic-agent.git
cd academic-agent

# Install dependencies
uv sync

# Configure
cp .env.example ~/.academic-agent.env
# Edit with your API keys

# Run CLI
academic-agent "find papers on transformer architecture"

# Run MCP server
academic-agent-serve
```

## Configuration

See [.env.example](.env.example) for all configuration options.

## Usage

### CLI Mode

```bash
# Paper discovery
academic-agent "导入最近一周关于attention的论文"

# Paper analysis
academic-agent "分析论文ITEM_KEY"

# Literature review
academic-agent "生成深度学习综述"

# Knowledge query
academic-agent "什么是transformer架构"
```

### MCP Server Mode

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "academic-agent": {
      "command": "uv",
      "args": ["--directory", "/path/to/academic-agent", "run", "academic-agent", "serve"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "LOGSEQ_API_TOKEN": "your_token"
      }
    }
  }
}
```

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Type check
uv run mypy src
```

## License

MIT
```

**Step 2: Update .env.example**

```bash
# Copy existing submodule .env files and extend
cat ../feedder-mcp/.env.example >> .env.example
cat ../logseq-mcp/.env.example >> .env.example
cat ../zotero-mcp/.env.example >> .env.example

# Add academic-agent specific settings
cat >> .env.example << 'EOF'

# ====================
# academic-agent specific
# ====================
ACADEMIC_AGENT_AUTO_SYNC=true
ACADEMIC_AGENT_DEFAULT_TEMPLATE=configs/templates/academic_paper.md
ACADEMIC_AGENT_CONTEXT_PATH=~/.academic-agent/context.json
ACADEMIC_AGENT_MAX_PAPERS_PER_IMPORT=50
EOF
```

**Step 3: Create plans README**

```markdown
# Implementation Plans

This directory contains detailed implementation plans for academic-agent development.

## Plan Files

- [2026-02-11-master-agent-implementation.md](./2026-02-11-master-agent-implementation.md)
  - Master Agent orchestration layer
  - Integration with MCP submodules
  - Academic workflow definitions
  - Zotero-Logseq synchronization

## Plan Structure

Each plan follows this structure:
1. Task breakdown with file locations
2. Test-driven development steps
3. Exact commands and expected outputs
4. Commit messages for each task

## Execution

To execute a plan:
```bash
# Using executing-plans skill
claude-code --plan docs/plans/2026-02-11-master-agent-implementation.md
```
```

**Step 4: Commit documentation**

```bash
git add README.md .env.example docs/plans/README.md
git commit -m "docs: add comprehensive README and configuration"
```

---

## Task 10: End-to-End Integration Tests

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration tests**

```python
# tests/test_integration.py
import pytest
from src.orchestrator.graph import create_master_agent_graph
from src.models.state import AgentState

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_paper_discovery_workflow():
    """Test complete paper discovery workflow"""
    # This test requires actual MCP servers running
    graph = create_master_agent_graph()
    state = AgentState(
        user_query="帮我找最近一周关于transformer的论文并导入"
    )

    result = await graph.ainvoke(state)

    assert result["intent"] == "paper_discovery"
    assert result["final_response"] is not None or result["error"] is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_paper_analysis_workflow():
    """Test complete paper analysis workflow"""
    graph = create_master_agent_graph()
    state = AgentState(
        user_query="分析论文TEST_ITEM_KEY"
    )

    result = await graph.ainvoke(state)

    assert result["intent"] == "paper_analysis"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_context_persistence():
    """Test conversation context persistence"""
    from src.models.context import ConversationContext
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        context_path = Path(tmpdir) / "context.json"

        # Save context
        ctx = ConversationContext()
        ctx.remember("test_key", "test_value")
        ctx.save(str(context_path))

        # Load context
        loaded_ctx = ConversationContext.load(str(context_path))
        assert loaded_ctx.recall("test_key") == "test_value"
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v -m integration`
Expected: Tests may skip if servers not available

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add end-to-end integration tests"
```

---

## Task 11: CI/CD Pipeline Setup

**Files:**
- Create: `.github/workflows/test.yml`
- Create: `.github/workflows/lint.yml`

**Step 1: Create test workflow**

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
    - uses: actions/checkout@v4
      with:
        submodules: recursive

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.local/bin/env
        uv sync

    - name: Run tests
      run: |
        source $HOME/.local/bin/env
        uv run pytest -v

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
```

**Step 2: Create lint workflow**

```yaml
# .github/workflows/lint.yml
name: Lint

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Install uv
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.local/bin/env

    - name: Install ruff
      run: |
        source $HOME/.local/bin/env
        uv pip install ruff

    - name: Run ruff
      run: |
        source $HOME/.local/bin/env
        uv run ruff check .

    - name: Check formatting
      run: |
        source $HOME/.local/bin/env
        uv run ruff format --check .
```

**Step 3: Commit CI/CD**

```bash
git add .github/workflows/
git commit -m "ci: add test and lint workflows"
```

---

## Summary

This implementation plan covers:

1. **Foundation** (Tasks 1-3): Project structure, data models, MCP client communication
2. **Core Logic** (Tasks 4-5): Intent recognition, workflow planning, execution engine
3. **Integration** (Task 6): Zotero-Logseq sync adapter with templates
4. **Agent** (Task 7): LangGraph-based Master Agent
5. **Interface** (Task 8): CLI and MCP server entry points
6. **Polish** (Tasks 9-11): Documentation, integration tests, CI/CD

**Estimated Timeline**: 10 weeks total (Phase 0-4 from design doc)

**Key Success Metrics:**
- All tests passing (>80% coverage)
- Integration tests work with real MCP servers
- CLI responds to all 5 core intents
- MCP server provides `execute_query` tool

**Next Steps:**
1. Review and approve this plan
2. Choose execution method (subagent-driven or parallel session)
3. Begin implementation with Task 1
