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
