from enum import Enum
from typing import Optional


class Intent(Enum):
    """User intent types"""

    PAPER_DISCOVERY = "paper_discovery"
    PAPER_ANALYSIS = "paper_analysis"
    LITERATURE_REVIEW = "literature_review"
    KNOWLEDGE_QUERY = "knowledge_query"
    WORKFLOW_AUTOMATION = "workflow_automation"


def detect_intent_from_query(query: str) -> Intent:
    """Detect user intent from natural language query"""
    query_lower = query.lower()

    # Check for paper discovery keywords
    discovery_keywords = ["找论文", "新论文", "导入", "发现", "fetch", "import", "discover", "找", "搜索"]
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
