import pytest
from src.orchestrator.planner import WorkflowPlanner
from src.models.intent import Intent


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


def test_plan_knowledge_query_workflow():
    planner = WorkflowPlanner()
    query = "attention mechanism是什么"
    workflow = planner.plan_workflow(query)

    assert workflow.intent == Intent.KNOWLEDGE_QUERY


def test_extract_topic():
    planner = WorkflowPlanner()
    assert "transformer" in planner._extract_topic("找关于transformer的论文")


def test_extract_item_key():
    planner = WorkflowPlanner()
    assert planner._extract_item_key("分析论文ABCD1234") == "ABCD1234"
    assert planner._extract_item_key("没有key的查询") is None
