from typing import Optional
import re
from src.models.intent import Intent, detect_intent_from_query
from src.models.workflow import Workflow, WorkflowStep


class WorkflowPlanner:
    """Plans workflows based on user intent"""

    def __init__(self):
        self.context = None

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
                parameters={"limit": 200, "since": 7},
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="generate_keywords",
                parameters={"topic": self._extract_topic(query)},
                depends_on=["step_0"],
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="filter_papers",
                parameters={"use_ai": True},
                depends_on=["step_1"],
            ),
            WorkflowStep(
                mcp_server="zotero",
                tool_name="get_metadata",
                parameters={"limit": 1000},
                depends_on=["step_2"],
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="enrich_papers",
                parameters={"api": "all"},
                depends_on=["step_3"],
            ),
            WorkflowStep(
                mcp_server="feedder",
                tool_name="export_papers",
                parameters={"format": "zotero"},
                depends_on=["step_4"],
            ),
            WorkflowStep(
                mcp_server="logseq",
                tool_name="create_page",
                parameters={},
                depends_on=["step_5"],
            ),
        ]

        return Workflow(
            intent=Intent.PAPER_DISCOVERY,
            description="Discover and import relevant papers from RSS feeds",
            steps=steps,
        )

    def _plan_analysis(self, query: str) -> Workflow:
        """Plan paper analysis workflow"""
        item_key = self._extract_item_key(query)
        if not item_key:
            return Workflow(
                intent=Intent.PAPER_ANALYSIS,
                description="Analyze a paper (requires item key)",
                steps=[
                    WorkflowStep(
                        mcp_server="system",
                        tool_name="ask_for_item_key",
                        parameters={},
                    )
                ],
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
                depends_on=["step_0"],
            ),
            WorkflowStep(
                mcp_server="logseq",
                tool_name="insert_block",
                parameters={"section": "AI分析"},
                depends_on=["step_1"],
            ),
        ]

        return Workflow(
            intent=Intent.PAPER_ANALYSIS,
            description="Deep analysis of paper content",
            steps=steps,
        )

    def _plan_review(self, query: str) -> Workflow:
        """Plan literature review workflow"""
        topic = self._extract_topic(query)

        steps = [
            WorkflowStep(
                mcp_server="feedder",
                tool_name="generate_keywords",
                parameters={"topic": topic},
            ),
            WorkflowStep(
                mcp_server="zotero",
                tool_name="semantic_search",
                parameters={"query": topic, "limit": 20},
                depends_on=["step_0"],
            ),
            WorkflowStep(
                mcp_server="zotero",
                tool_name="batch_analyze_pdfs",
                parameters={},
                depends_on=["step_1"],
            ),
            WorkflowStep(
                mcp_server="logseq",
                tool_name="create_page",
                parameters={"template": "literature_review"},
                depends_on=["step_2"],
            ),
        ]

        return Workflow(
            intent=Intent.LITERATURE_REVIEW,
            description=f"Generate literature review on {topic}",
            steps=steps,
        )

    def _plan_query(self, query: str) -> Workflow:
        """Plan knowledge query workflow"""
        steps = [
            WorkflowStep(
                mcp_server="zotero",
                tool_name="semantic_search",
                parameters={"query": query, "limit": 10},
            ),
            WorkflowStep(
                mcp_server="logseq",
                tool_name="simple_query",
                parameters={"query": query},
            ),
        ]

        return Workflow(
            intent=Intent.KNOWLEDGE_QUERY,
            description=f"Search knowledge base for: {query}",
            steps=steps,
        )

    def _extract_topic(self, query: str) -> str:
        """Extract research topic from query"""
        for kw in ["生成", "综述", "找", "论文", "关于", "discover", "review", "papers"]:
            query = query.replace(kw, "")
        return query.strip()

    def _extract_item_key(self, query: str) -> Optional[str]:
        """Extract Zotero item key from query"""
        match = re.search(r"[A-Z]{4}\d{4}", query)
        return match.group(0) if match else None
