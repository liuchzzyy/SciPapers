import pytest
from unittest.mock import AsyncMock, MagicMock
from src.orchestrator.executor import WorkflowExecutor
from src.models.workflow import Workflow, WorkflowStep
from src.models.intent import Intent


@pytest.fixture
def mock_client_manager():
    """Create a mock MCPClientManager"""
    manager = AsyncMock()
    manager.execute_tool = AsyncMock(
        return_value={"status": "success", "data": {"result": "test"}, "server": "feedder"}
    )
    return manager


@pytest.mark.asyncio
async def test_execute_single_step(mock_client_manager):
    executor = WorkflowExecutor(mock_client_manager)
    step = WorkflowStep(
        mcp_server="feedder",
        tool_name="generate_keywords",
        parameters={"topic": "test"},
    )

    result = await executor.execute_step(step)
    assert "status" in result
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_execute_workflow(mock_client_manager):
    executor = WorkflowExecutor(mock_client_manager)
    workflow = Workflow(
        intent=Intent.KNOWLEDGE_QUERY,
        description="Test query",
        steps=[
            WorkflowStep(
                mcp_server="zotero",
                tool_name="semantic_search",
                parameters={"query": "test", "limit": 5},
            )
        ],
    )

    results = await executor.execute_workflow(workflow)
    assert "steps_completed" in results
    assert "steps_failed" in results
    assert results["final_result"] == "success"


@pytest.mark.asyncio
async def test_execute_workflow_with_failure(mock_client_manager):
    mock_client_manager.execute_tool = AsyncMock(
        return_value={"status": "error", "error": "test error", "server": "feedder"}
    )
    executor = WorkflowExecutor(mock_client_manager)
    workflow = Workflow(
        intent=Intent.KNOWLEDGE_QUERY,
        description="Test query",
        steps=[
            WorkflowStep(
                mcp_server="zotero",
                tool_name="semantic_search",
                parameters={"query": "test"},
            )
        ],
    )

    results = await executor.execute_workflow(workflow)
    assert len(results["steps_failed"]) > 0
    assert results["final_result"] == "completed_with_errors"


@pytest.mark.asyncio
async def test_execute_workflow_dependency_ordering(mock_client_manager):
    executor = WorkflowExecutor(mock_client_manager)
    workflow = Workflow(
        intent=Intent.PAPER_DISCOVERY,
        description="Test dependencies",
        steps=[
            WorkflowStep(
                mcp_server="feedder",
                tool_name="fetch_feeds",
                parameters={},
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="filter_papers",
                parameters={},
                depends_on=["step_0"],
            ),
        ],
    )

    results = await executor.execute_workflow(workflow)
    assert len(results["steps_completed"]) == 2


@pytest.mark.asyncio
async def test_critical_step_stops_workflow(mock_client_manager):
    call_count = 0

    async def fail_on_critical(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"status": "error", "error": "critical fail", "server": "feedder"}
        return {"status": "success", "data": {}, "server": "feedder"}

    mock_client_manager.execute_tool = AsyncMock(side_effect=fail_on_critical)

    executor = WorkflowExecutor(mock_client_manager)
    workflow = Workflow(
        intent=Intent.PAPER_DISCOVERY,
        description="Test critical failure",
        steps=[
            WorkflowStep(
                mcp_server="feedder",
                tool_name="fetch_feeds",
                parameters={},
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="filter_papers",
                parameters={},
            ),
        ],
    )

    results = await executor.execute_workflow(workflow)
    # fetch_feeds is critical, so workflow should stop after it fails
    assert len(results["steps_failed"]) == 1
    assert len(results["steps_completed"]) == 0
