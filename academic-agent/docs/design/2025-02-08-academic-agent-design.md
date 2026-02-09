# 学术Agent系统设计文档

**日期**: 2025-02-08
**版本**: 1.0
**状态**: 设计阶段

---

## 目录

1. [系统架构概述](#1-系统架构概述)
2. [Master Agent与工具编排](#2-master-agent与工具编排)
3. [MCP服务器详细设计](#3-mcp服务器详细设计)
4. [数据流与核心工作流](#4-数据流与核心工作流)
5. [错误处理与边界情况](#5-错误处理与边界情况)
6. [测试策略](#6-测试策略)
7. [部署与配置](#7-部署与配置)
8. [开发路线图](#8-开发路线图)
9. [关键技术与实现要点](#9-关键技术与实现要点)
10. [性能优化与成本控制](#10-性能优化与成本控制)

---

## 1. 系统架构概述

### 1.1 核心设计理念

这是一个基于MCP（Model Context Protocol）的学术研究助手系统，通过统一的Master Agent编排四个专门的MCP服务器。

**核心设计理念：**
- **单一入口**：用户只与"学术助手"对话，不需要理解底层MCP架构
- **Zotero为中心**：Zotero是文献管理的唯一真相源，Logseq作为视图层
- **云AI驱动**：所有AI功能使用商业API（OpenAI/Anthropic）确保效果
- **用户控制**：RSS源和Gmail标签完全由用户配置，Agent不自动推断

### 1.2 系统分层

```
┌─────────────────────────────────────────────────────────┐
│                    交互层                                │
│              Master Agent (用户对话)                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                    编排层                                │
│          意图识别 → 任务分解 → 工具调用                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                    服务层                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │paper_feeder│ │  zotero  │ │  logseq  │ │    ai    │  │
│  │   _mcp   │ │   _mcp   │ │   _mcp   │ │   _mcp   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                    数据层                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│  │  Zotero  │ │  Logseq  │ │ChromaDB  │                │
│  │ (文献库) │ │ (笔记)   │ │(向量索引)│                │
│  └──────────┘ └──────────┘ └──────────┘                │
└─────────────────────────────────────────────────────────┘
```

### 1.3 典型工作流示例

**用户请求**: "帮我把最近一周arXiv上关于transformer的论文导入我的文献库"

```
1. Master Agent解析意图
   ├─ 识别: 文献发现任务
   ├─ 时间范围: 最近一周
   └─ 关键词: transformer

2. 调用paper_feeder_mcp.get_rss_feeds()
   ├─ 获取arXiv RSS源
   └─ 返回原始论文列表

3. 调用ai_mcp.semantic_match()
   ├─ 使用transformer的embedding
   ├─ 匹配相关论文
   └─ 计算相似度分数

4. 调用zotero_mcp.batch_import()
   ├─ 导入高相关度论文
   ├─ 自动添加标签
   └─ 下载PDF附件

5. 调用logseq_mcp.sync_from_zotero()
   ├─ 为新论文创建笔记页面
   ├─ 应用模板结构
   └─ 建立Zotero链接

6. 返回结果给用户
   └─ "已导入15篇论文，已创建Logseq笔记"
```

---

## 2. Master Agent与工具编排

### 2.1 Master Agent的职责

Master Agent是系统的协调者，负责理解用户意图并调用合适的MCP工具组合。它不是简单的工具路由器，而是需要理解学术工作流的知识。

### 2.2 核心能力

#### 2.2.1 意图识别与任务分解

```python
def decompose_user_query(query: str) -> Workflow:
    """将用户查询分解为MCP工具调用序列"""

    # 示例1: 文献发现
    if "找论文" in query or "新论文" in query:
        return Workflow([
            ("paper_feeder_mcp", "fetch_feeds"),
            ("ai_mcp", "generate_keywords"),
            ("ai_mcp", "semantic_match"),
            ("zotero_mcp", "batch_import"),
            ("logseq_mcp", "sync_from_zotero")
        ])

    # 示例2: 文献分析
    elif "分析论文" in query or "理解这篇" in query:
        return Workflow([
            ("zotero_mcp", "get_item_fulltext"),
            ("ai_mcp", "analyze_pdf"),
            ("logseq_mcp", "update_page_block"),
            ("ai_mcp", "find_similar_papers"),
            ("logseq_mcp", "add_linked_pages")
        ])
```

#### 2.2.2 上下文管理

```python
class ConversationContext:
    """维护对话上下文"""

    def __init__(self):
        self.user_profile = {
            "research_interests": [],
            "recent_queries": [],
            "zotero_library_snapshot": None
        }
        self.active_items = {}  # 当前讨论的文献
        self.workflow_history = []

    def remember(self, key, value):
        """记住信息供后续使用"""
        self.user_profile[key] = value

    def recall(self, key):
        """召回之前的信息"""
        return self.user_profile.get(key)

# 使用示例
ctx.remember("last_discussed_paper", "ABCD1234")
# 用户问: "刚才那篇论文的作者还有什么其他工作？"
paper_key = ctx.recall("last_discussed_paper")
```

#### 2.2.3 工具选择策略

```python
TOOL_MAPPING = {
    "文献发现": {
        "tools": [
            "paper_feeder_mcp.fetch_feeds",
            "ai_mcp.generate_keywords",
            "ai_mcp.semantic_match"
        ]
    },
    "文献管理": {
        "tools": [
            "zotero_mcp.search_items",
            "zotero_mcp.get_annotations",
            "logseq_mcp.sync_from_zotero"
        ]
    },
    "内容分析": {
        "tools": [
            "zotero_mcp.get_fulltext",
            "ai_mcp.analyze_pdf",
            "ai_mcp.semantic_search"
        ]
    }
}

def select_tools(intent: str) -> list[str]:
    """根据意图选择工具"""
    return TOOL_MAPPING.get(intent, {}).get("tools", [])
```

### 2.3 实现框架选择

**推荐：LangGraph**

```python
from langgraph.graph import StateGraph
from typing import TypedDict

class AgentState(TypedDict):
    user_query: str
    intent: str
    tools_to_call: list
    context: dict
    final_result: str

def build_master_agent():
    workflow = StateGraph(AgentState)

    # 定义节点
    workflow.add_node("understand_intent", understand_intent_node)
    workflow.add_node("plan_workflow", plan_workflow_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("format_result", format_result_node)

    # 定义执行流程
    workflow.set_entry_point("understand_intent")
    workflow.add_edge("understand_intent", "plan_workflow")
    workflow.add_conditional_edges(
        "plan_workflow",
        should_execute,
        {
            "execute": "execute_tools",
            "clarify": "understand_intent"
        }
    )
    workflow.add_edge("execute_tools", "format_result")
    workflow.set_finish_point("format_result")

    return workflow.compile()
```

---

## 3. MCP服务器详细设计

### 3.1 paper_feeder_mcp：论文数据获取与清洗

#### 3.1.1 核心职责

从RSS源和Gmail获取论文元数据，清洗标准化后供其他组件使用。

#### 3.1.2 主要工具

```python
@mcp.tool
def list_feeds() -> str:
    """列出所有配置的RSS源"""

@mcp.tool
def fetch_feed(feed_url: str, limit: int = 50) -> str:
    """获取指定RSS的最新条目"""

@mcp.tool
def add_feed(feed_url: str, category: str) -> str:
    """添加新的RSS源到配置"""

@mcp.tool
def fetch_papers_from_gmail(label: str, days: int = 7) -> str:
    """从Gmail指定标签获取学术邮件"""

@mcp.tool
def normalize_paper_metadata(raw_data: List[Dict]) -> str:
    """标准化论文元数据"""

@mcp.tool
def deduplicate_papers(papers: List[Dict], zotero_library: str) -> str:
    """与Zotero库对比，去除已存在的论文"""
```

#### 3.1.3 数据流

```
RSS/Gmail → 原始数据 → normalize_paper_metadata()
→ deduplicate_papers(对比Zotero) → 清洗后的论文列表
→ 传递给AI_mcp进行智能过滤
```

#### 3.1.4 配置文件

```json
{
  "rss_feeds": [
    {
      "url": "http://export.arxiv.org/rss/cs.AI",
      "category": "AI",
      "enabled": true
    },
    {
      "url": "http://export.arxiv.org/rss/cs.CV",
      "category": "CV",
      "enabled": true
    },
    {
      "url": "https://www.nature.com/nrsa.rss",
      "category": "Robotics",
      "enabled": false
    }
  ],
  "gmail": {
    "enabled": true,
    "labels": ["Arxiv", "ScienceDirect", "NatureAlerts"],
    "poll_interval_hours": 6
  }
}
```

---

### 3.2 zotero_mcp：文献管理核心

#### 3.2.1 核心职责

作为系统的文献管理真相源，提供文献的CRUD操作、标签管理、全文检索等核心能力。

#### 3.2.2 设计策略

基于现有的 [zotero-mcp](https://github.com/54yyyu/zotero-mcp) 项目进行扩展，复用其成熟功能，重点增强与Logseq和AI_mcp的集成。

#### 3.2.3 核心工具（复用zotero-mcp）

```python
@mcp.tool
def search_items(query: str, tag: List[str] = None, limit: int = 10) -> str:
    """关键词搜索文献"""

@mcp.tool
def semantic_search(query: str, limit: int = 10) -> str:
    """AI语义搜索（基于向量数据库）"""

@mcp.tool
def get_recent_items(limit: int = 20) -> str:
    """获取最近添加的文献"""

@mcp.tool
def get_item_fulltext(item_key: str) -> str:
    """获取文献全文内容"""

@mcp.tool
def get_annotations(item_key: str, use_pdf_extraction: bool = True) -> str:
    """获取PDF批注"""

@mcp.tool
def get_notes(item_key: str = None, limit: int = 20) -> str:
    """获取文献笔记"""
```

#### 3.2.4 需要扩展的工具

```python
@mcp.tool
def export_items_for_logseq(item_keys: List[str], format: str = "markdown") -> str:
    """导出文献元数据为Logseq格式

    返回格式：
    - title:: 论文标题
    - authors:: 作者列表
    - year:: 年份
    - doi:: DOI
    - abstract:: 摘要
    - zotero_select:: zotero://select/items/KEY
    """

@mcp.tool
def get_items_updated_since(timestamp: str) -> str:
    """获取指定时间后更新的文献（用于Logseq增量同步）"""

@mcp.tool
def batch_update_tags_from_logseq(tag_updates: List[Dict]) -> str:
    """批量更新标签（从Logseq同步回来）

    格式：[{"item_key": "xxx", "add_tags": ["tag1"], "remove_tags": ["tag2"]}]
    """
```

#### 3.2.5 配置文件

```json
{
  "zotero": {
    "local": true,
    "library_type": "user",
    "api_key": "${ZOTERO_API_KEY}",
    "library_id": "${ZOTERO_LIBRARY_ID}"
  },
  "semantic_search": {
    "embedding_model": "openai",
    "openai_api_key": "${OPENAI_API_KEY}",
    "embedding_model_name": "text-embedding-3-small",
    "auto_update": true,
    "update_frequency": "daily"
  }
}
```

---

### 3.3 logseq_mcp：知识图谱与笔记管理

#### 3.3.1 核心职责

作为系统的知识管理视图层，从Zotero同步文献数据，提供笔记的CRUD、标签管理、图谱查询等功能。

#### 3.3.2 主要工具

```python
@mcp.tool
def create_paper_page(item_key: str, zotero_data: Dict) -> str:
    """为Zotero文献创建Logseq页面"""

@mcp.tool
def get_page(page_id: str) -> str:
    """获取页面内容和属性"""

@mcp.tool
def update_page_block(block_id: str, content: str) -> str:
    """更新页面块内容"""

@mcp.tool
def query_graph(query: str, query_type: str = "page") -> str:
    """查询图谱：按标签、属性、链接关系"""

@mcp.tool
def get_linked_pages(page_id: str) -> str:
    """获取链接到的其他页面（知识网络）"""

@mcp.tool
def add_tag_to_block(block_id: str, tag: str) -> str:
    """为块添加标签"""

@mcp.tool
def sync_from_zotero(items: List[Dict], sync_mode: str = "incremental") -> str:
    """从Zotero同步文献到Logseq"""

@mcp.tool
def get_zotero_backlinks(item_key: str) -> str:
    """获取引用该文献的Logseq笔记页面"""
```

#### 3.3.3 Logseq页面模板

```markdown
title:: [[Deep Learning for NLP]]
authors:: [[Bengio, Y.]], [[Goodfellow, I.]]
year:: 2016
doi:: 10.1234/example
zotero_select:: zotero://select/items/ABCD1234
zotero_key:: ABCD1234
status:: reading
tags:: [[NLP]], [[Deep Learning]], [[Survey]]

## 摘要
本文综述了深度学习在NLP领域的应用...

## 研究问题
- 如何用神经网络表示语言？
- 哪些架构最适合序列建模？

## 方法论
- Word2Vec embeddings
- RNN/LSTM架构
- Attention机制

## 主要发现
- Embeddings捕获语义关系
- LSTM解决长距离依赖
- Attention显著提升性能

## 个人思考
- 这篇论文的局限是什么？
- 与其他研究的联系：[[Transformer Architecture]]
- 未来研究方向：预训练模型

## AI分析
🤖 *由AI_mcp生成*
- 关键贡献：xxx
- 方法创新点：xxx
- 相关文献推荐：[[Attention Is All You Need]], [[BERT]]
```

#### 3.3.4 配置文件

```json
{
  "logseq": {
    "graph_path": "~/Documents/Logseq/MyGraph",
    "api_endpoint": "http://localhost:12315",
    "sync": {
      "auto_sync": true,
      "sync_interval_minutes": 30,
      "default_template": "academic_paper"
    }
  }
}
```

---

### 3.4 ai_mcp：智能分析与语义理解

#### 3.4.1 核心职责

提供所有AI驱动的智能功能，包括语义搜索、关键字生成、PDF深度分析。

#### 3.4.2 技术栈

- **Embedding**: OpenAI text-embedding-3-small
- **生成/分析**: GPT-4o / Claude 3.5 Sonnet
- **向量数据库**: ChromaDB（本地持久化）

#### 3.4.3 主要工具

**语义搜索工具**

```python
@mcp.tool
def semantic_search(
    query: str,
    search_scope: str = "all",
    limit: int = 10,
    filters: Dict = None
) -> str:
    """基于语义相似度搜索文献和笔记"""

@mcp.tool
def find_similar_papers(item_key: str, limit: int = 5) -> str:
    """查找与指定论文语义相似的其他论文"""

@mcp.tool
def build_semantic_index(force_rebuild: bool = False) -> str:
    """为Zotero库构建语义索引"""
```

**关键字生成工具**

```python
@mcp.tool
def generate_search_keywords(
    topic: str,
    context: str = "",
    num_keywords: int = 10
) -> str:
    """为研究主题生成搜索关键字

    返回：
    {
      "primary_keywords": ["transformer", "attention"],
      "secondary_keywords": ["self-attention", "multi-head"],
      "related_topics": ["BERT", "GPT", "seq2seq"],
      "search_queries": ["transformer architecture", "attention mechanism"]
    }
    """

@mcp.tool
def classify_paper_categories(paper_text: str, categories: List[str]) -> str:
    """将论文分类到指定类别（用于RSS过滤）"""
```

**PDF深度分析工具**

```python
@mcp.tool
def analyze_pdf(
    item_key: str,
    analysis_type: str = "comprehensive",
    focus_areas: List[str] = None
) -> str:
    """深度分析PDF内容

    analysis_type选项：
    - comprehensive: 全文分析
    - methodology: 仅分析方法论
    - findings: 仅分析主要发现
    - critique: 批判性分析（局限、漏洞）

    返回结构化分析：
    {
      "summary": "论文总结",
      "key_contributions": ["贡献1", "贡献2"],
      "methodology": "方法论分析",
      "main_findings": ["发现1", "发现2"],
      "limitations": "局限性与批评",
      "future_work": "未来方向",
      "related_work": "相关工作",
      "suggested_tags": ["标签1", "标签2"]
    }
    """

@mcp.tool
def extract_paper_structure(pdf_content: str) -> str:
    """提取论文结构化内容"""

@mcp.tool
def compare_papers(item_keys: List[str]) -> str:
    """对比多篇论文的方法、发现、贡献"""
```

#### 3.4.4 向量数据库设计

```python
# Collection结构
Collection: "academic_papers"

Document结构:
{
    "item_key": "ABCD1234",
    "title": "Attention Is All You Need",
    "abstract": "全文...",
    "authors": ["Vaswani, A."],
    "year": 2017,
    "tags": ["NLP", "Transformer"],
    "pdf_text": "完整PDF文本...",
    "zotero_created": "2024-01-01",
    "embedding": [0.1, 0.2, ...]  # text-embedding-3-small (1536维)
}

# Metadata Filter示例
filters = {
    "year": {"$gte": 2020},
    "tags": {"$in": ["Deep Learning", "NLP"]},
    "authors": "Hinton"
}
```

#### 3.4.5 Prompt设计

**PDF分析Prompt**

```python
PDF_ANALYSIS_PROMPT = """
你是一个学术研究助手。请分析以下论文内容，提供结构化的学术分析。

论文标题：{title}
作者：{authors}
摘要：{abstract}
全文：{content}

请提供：
1. **研究问题**（1-2句话）
2. **核心贡献**（3-5点bullet）
3. **方法论**（详细说明方法设计）
4. **主要发现**（关键实验结果）
5. **局限性与批评**（至少2点）
6. **相关研究方向**（建议的标签和相关主题）

以JSON格式返回。
"""
```

**关键字生成Prompt**

```python
KEYWORD_GENERATION_PROMPT = """
用户的研究主题：{topic}
上下文：{context}

请生成：
1. 10-15个核心搜索关键词（英文和中文）
2. 5-10个相关概念/术语
3. 5个优化的搜索查询字符串
4. 3-5个相关的学术数据库/期刊建议

返回JSON格式。
"""
```

#### 3.4.6 配置文件

```json
{
  "ai": {
    "openai_api_key": "${OPENAI_API_KEY}",
    "anthropic_api_key": "${ANTHROPIC_API_KEY}",
    "default_model": "gpt-4o",
    "embedding": {
      "model": "text-embedding-3-small",
      "dimensions": 1536
    },
    "vector_db": {
      "type": "chromadb",
      "persist_directory": "~/.academic-agent/vectordb",
      "collection_name": "academic_papers"
    },
    "analysis": {
      "max_pdf_tokens": 128000,
      "chunk_size": 50000,
      "overlap": 1000
    }
  }
}
```

---

## 4. 数据流与核心工作流

### 4.1 数据流向图

```
┌─────────────┐
│   RSS源     │  arXiv, Nature, Science等
│  Gmail      │  论文通知邮件
└──────┬──────┘
       │ fetch_feeds()
       ▼
┌──────────────────┐
│ paper_feeder_mcp │
│ - 原始数据获取   │
│ - 数据清洗       │
│ - 去重检查       │
└──────┬───────────┘
       │ filtered_papers
       ▼
┌─────────────┐        ┌──────────────┐
│  ai_mcp     │◄───────┤ zotero_mcp  │
│ - 关键词生成│  用户  │ - 用户库     │
│ - 语义匹配  │ 兴趣  │ - 历史数据   │
└──────┬──────┘        └──────────────┘
       │ matched_papers
       ▼
┌──────────────────┐
│ zotero_mcp       │
│ - 导入文献       │
│ - 自动标签       │
│ - PDF附件        │
└──────┬───────────┘
       │ sync event
       ▼
┌──────────────────┐
│ logseq_mcp       │
│ - 创建页面       │
│ - 提取元数据     │
│ - 建立链接       │
└──────────────────┘
```

### 4.2 核心工作流

#### 4.2.1 工作流1：每日论文自动发现

```yaml
触发: Cron (每天早上8点)

步骤:
  1. paper_feeder_mcp.fetch_all_feeds()
     - 获取所有RSS源的最新条目
     - 从Gmail获取论文通知邮件

  2. paper_feeder_mcp.normalize_and_dedupe()
     - 标准化元数据
     - 与Zotero库对比去重

  3. ai_mcp.generate_search_keywords()
     - 基于用户Zotero库生成兴趣关键词

  4. ai_mcp.semantic_match()
     - 将新论文与用户研究兴趣匹配
     - 计算相似度分数

  5. zotero_mcp.batch_import()
     - 导入相似度>阈值的论文
     - 自动应用AI生成的标签

  6. logseq_mcp.sync_from_zotero()
     - 为新导入论文创建笔记页面
     - 预填充模板结构

  7. 通知用户
     - 发送摘要：导入N篇论文
     - 列出top 5推荐
```

#### 4.2.2 工作流2：文献深度分析

```yaml
触发: 用户请求"分析这篇论文"

步骤:
  1. zotero_mcp.get_item_fulltext(item_key)
     - 获取PDF全文

  2. ai_mcp.analyze_pdf(
       item_key,
       analysis_type="comprehensive"
     )
     - 提取研究问题、方法、发现
     - 批判性分析局限性
     - 推荐相关工作和标签

  3. logseq_mcp.update_page_block()
     - 将AI分析结果写入Logseq笔记
     - 在"AI分析"section添加内容

  4. ai_mcp.find_similar_papers()
     - 基于分析结果搜索库中相关论文

  5. logseq_mcp.add_linked_pages()
     - 在笔记中添加相关论文链接
     - 构建知识网络
```

#### 4.2.3 工作流3：主题综述生成

```yaml
触发: 用户请求"生成X主题的综述"

步骤:
  1. ai_mcp.generate_search_keywords(topic)
     - 生成主题相关关键词

  2. zotero_mcp.semantic_search(query=topic)
     - 语义搜索相关文献

  3. zotero_mcp.get_items_fulltext(item_keys)
     - 批量获取全文

  4. ai_mcp.analyze_papers(papers)
     - 并行分析多篇论文

  5. ai_mcp.synthesize_literature_review()
     - 综合分析结果
     - 生成综述结构：
       - 引言
       - 主要方法分类
       - 关键发现总结
       - 研究gap
       - 未来方向

  6. logseq_mcp.create_review_page()
     - 创建综述页面
     - 引用所有相关论文
     - 生成可视化图谱
```

### 4.3 状态管理

**Zotero作为状态源：**
- 已导入论文的record ID
- 每篇论文的处理状态（新发现、已分析、已读）
- 标签和笔记的时间戳

**同步状态追踪：**

```json
{
  "last_sync": "2025-01-15T10:30:00Z",
  "last_rss_fetch": "2025-01-15T08:00:00Z",
  "zotero_last_update": "2025-01-15T09:15:00Z",
  "logseq_last_sync": "2025-01-15T10:30:00Z",
  "vector_db_version": 3
}
```

---

## 5. 错误处理与边界情况

### 5.1 MCP服务器级别的错误处理

#### paper_feeder_mcp

```python
# RSS获取失败
try:
    feed_data = fetch_feed(url)
except FeedNotFoundError:
    return {
        "status": "error",
        "error_type": "feed_not_found",
        "message": f"RSS源 {url} 无法访问",
        "suggestion": "请检查URL是否正确，或稍后重试"
    }

# Gmail API限流
if rate_limit_exceeded:
    return {
        "status": "warning",
        "message": "Gmail API限流，部分邮件未获取",
        "retry_after": 3600,
        "partial_results": fetched_emails
    }
```

#### zotero_mcp

```python
# Zotero未运行
if not zotero_running():
    return {
        "status": "error",
        "error_type": "zotero_not_running",
        "message": "Zotero未运行或本地API未启用",
        "solution": "请在Zotero偏好设置中启用HTTP服务器"
    }

# 文献不存在
if item_not_found:
    return {
        "status": "error",
        "error_type": "item_not_found",
        "item_key": item_key,
        "suggestion": "该文献可能已被删除"
    }
```

#### logseq_mcp

```python
# Logseq API未启动
if not logseq_api_responsive():
    return {
        "status": "error",
        "error_type": "logseq_not_running",
        "message": "Logseq未运行或本地API未启用",
        "solution": "请启动Logseq并在设置中启用API"
    }

# 页面已存在
if page_exists(page_title):
    return {
        "status": "conflict",
        "error_type": "page_already_exists",
        "page_id": existing_page_id,
        "options": ["update_existing", "create_new_with_suffix", "skip"]
    }
```

#### ai_mcp

```python
# API限流/配额用尽
if openai_rate_limited():
    return {
        "status": "error",
        "error_type": "api_rate_limit",
        "message": "OpenAI API配额已用尽或触发限流",
        "retry_after": get_retry_after_time(),
        "suggestion": "请检查API配额或稍后重试"
    }

# Token超限
if exceeds_token_limit(content):
    return {
        "status": "partial",
        "message": "文档过长，已分段处理",
        "chunks_processed": f"{current}/{total}",
        "warning": "结果可能不完整，建议手动合并"
    }
```

### 5.2 Agent编排级别的错误处理

```python
def workflow_import_papers(topic):
    try:
        # Step 1: 获取RSS
        feeds = paper_feeder.fetch_all()
        if feeds["status"] == "error":
            # 降级：使用Gmail作为备选
            feeds = paper_feeder.fetch_from_gmail()

        # Step 2: AI过滤
        filtered = ai.semantic_match(feeds)
        if filtered["status"] == "error":
            # 降级：使用关键词匹配
            filtered = paper_feeder.keyword_filter(feeds, topic)

        # Step 3: 导入Zotero
        imported = zotero.batch_import(filtered)
        if not imported:
            logger.error("Zotero导入失败")
            return {"status": "partial", "papers_imported": 0}

        # Step 4: 同步Logseq
        synced = logseq.sync_from_zotero(imported)
        if synced["status"] == "error":
            # 非关键失败：不影响主流程
            logger.warning(f"Logseq同步失败: {synced['message']}")

        return {
            "status": "success",
            "papers_imported": len(imported),
            "logseq_synced": synced.get("status") == "success"
        }

    except Exception as e:
        return {
            "status": "critical",
            "error": str(e),
            "recovery_suggestion": "请检查系统配置和日志"
        }
```

### 5.3 数据一致性保证

```python
def resolve_sync_conflict(zotero_item, logseq_page):
    zotero_ts = zotero_item["data"]["dateModified"]
    logseq_ts = logseq_page["updated_at"]

    if zotero_ts > logseq_ts:
        # Zotero更新，覆盖Logseq
        return sync_zotero_to_logseq(zotero_item)
    elif logseq_ts > zotero_ts:
        # Logseq更新，询问用户或保留副本
        return create_conflict_copy(logseq_page)
    else:
        # 同时更新，智能合并
        return merge_changes(zotero_item, logseq_page)
```

---

## 6. 测试策略

### 6.1 单元测试

```python
# paper_feeder_mcp测试
def test_feed_parsing():
    """测试RSS解析"""
    mock_rss = load_fixture("arxiv_cs_ai.xml")
    result = paper_feeder.fetch_feed("mock_url")
    assert len(result["items"]) > 0
    assert "title" in result["items"][0]

def test_deduplication():
    """测试去重逻辑"""
    existing_zotero = [{"title": "Paper A", "doi": "10.123/xyz"}]
    new_papers = [
        {"title": "Paper A", "doi": "10.123/xyz"},
        {"title": "Paper B"}
    ]
    result = paper_feeder.dedupe(new_papers, existing_zotero)
    assert len(result) == 1

# ai_mcp测试
def test_keyword_generation():
    """测试关键词生成"""
    result = ai.generate_keywords(topic="transformer")
    assert "primary_keywords" in result
    assert len(result["primary_keywords"]) >= 5
```

### 6.2 集成测试

```python
def test_daily_paper_discovery_workflow():
    """测试完整论文发现流程"""
    # Setup
    mock_rss_server.add_paper("AI paper 1")
    zotero_test_library.clear()

    # Execute
    agent.handle("帮我导入今天关于AI的新论文")

    # Assert
    imported = zotero_test_library.get_items()
    assert len(imported) > 0
    logseq_pages = logseq_test_graph.get_pages()
    assert any(p["properties"]["zotero_key"] in [i["key"] for i in imported]
               for p in logseq_pages)
```

### 6.3 性能测试

```python
def test_large_library_semantic_search():
    """测试大规模语义搜索性能"""
    create_test_library(size=10000)
    build_semantic_index()

    start_time = time.time()
    result = ai.semantic_search("deep learning", limit=20)
    duration = time.time() - start_time

    assert duration < 2.0
    assert len(result["results"]) == 20
```

---

## 7. 部署与配置

### 7.1 项目结构

```
academic-agent/
├── mcp-servers/
│   ├── paper_feeder_mcp/
│   ├── zotero_mcp/
│   ├── logseq_mcp/
│   ├── ai_mcp/
│   └── master_agent/
├── shared/
│   ├── utils/
│   └── models/
├── docs/
├── tests/
├── .env.example
├── docker-compose.yml
└── README.md
```

### 7.2 环境配置

**.env.example:**

```bash
# Zotero配置
ZOTERO_LOCAL=true
ZOTERO_API_KEY=your_zotero_api_key
ZOTERO_LIBRARY_ID=your_library_id

# Logseq配置
LOGSEQ_GRAPH_PATH=~/Documents/Logseq/MyGraph
LOGSEQ_API_ENDPOINT=http://localhost:12315

# AI服务配置
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
DEFAULT_CHAT_MODEL=gpt-4o

# 向量数据库
VECTOR_DB_PATH=~/.academic-agent/vectordb

# Gmail配置（可选）
GMAIL_ENABLED=false
GMAIL_LABELS=Arxiv,ScienceDirect

# RSS配置
RSS_FEEDS_CONFIG_PATH=~/.academic-agent/feeds.json
RSS_FETCH_INTERVAL_HOURS=6
```

### 7.3 安装方式

**本地开发安装:**

```bash
git clone https://github.com/your-org/academic-agent.git
cd academic-agent

pip install -e ./mcp-servers/*  # 安装所有MCP服务器
cp .env.example ~/.env
academic-agent init --interactive
academic-agent start
```

**Docker部署:**

```yaml
# docker-compose.yml
services:
  master-agent:
    build: .
    env_file: .env
    depends_on:
      - chromadb
    ports:
      - "8080:8080"

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - ${VECTOR_DB_PATH}:/chroma/chroma
```

**Claude Desktop配置:**

```json
{
  "mcpServers": {
    "academic-agent": {
      "command": "academic-agent",
      "env": {
        "ZOTERO_LOCAL": "true",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

---

## 8. 开发路线图

### Phase 1: 核心功能（MVP）- 4周

**Week 1-2: 基础MCP服务器**
- [ ] paper_feeder_mcp: RSS获取、Gmail解析、数据清洗
- [ ] zotero_mcp: 基于现有项目扩展
- [ ] 基础测试覆盖

**Week 3: AI功能**
- [ ] ai_mcp: 语义搜索
- [ ] ai_mcp: 关键字生成
- [ ] 向量索引构建工具

**Week 4: 集成与测试**
- [ ] logseq_mcp: 基础CRUD和同步
- [ ] Master Agent: 简单工具编排
- [ ] 端到端工作流

### Phase 2: 智能分析 - 3周

**Week 5-6: PDF分析**
- [ ] ai_mcp: PDF深度分析工具
- [ ] 批量分析和并行处理

**Week 7: 高级工作流**
- [ ] Master Agent: 多步骤工作流编排
- [ ] 主题综述生成

### Phase 3: 增强功能 - 3周

**Week 8-9: RAG能力**
- [ ] ai_mcp: 基于笔记的RAG检索
- [ ] 智能推荐系统

**Week 10: 用户体验**
- [ ] CLI工具完善
- [ ] 配置向导

### Phase 4: 生产化 - 2周

**Week 11-12: 稳定性与部署**
- [ ] 性能优化
- [ ] 完整测试套件
- [ ] Docker部署
- [ ] 文档完善

---

## 9. 关键技术与实现要点

### 9.1 语义搜索实现

**ChromaDB集成:**

```python
import chromadb

client = chromadb.PersistentClient(path="~/.academic-agent/vectordb")
collection = client.get_or_create_collection("academic_papers")

# 添加文档
collection.add(
    documents=[paper["abstract"]],
    embeddings=[embeddings],
    metadatas=[{
        "item_key": paper["key"],
        "title": paper["title"],
        "year": paper["year"]
    }],
    ids=[paper["key"]]
)

# 查询
results = collection.query(
    query_texts=[user_query],
    n_results=10,
    where={"year": {"$gte": 2020}}
)
```

### 9.2 PDF分析实现

**分块策略:**

```python
def chunk_pdf(pdf_text, max_tokens=100000):
    """将长PDF分块"""
    sections = split_by_sections(pdf_text)
    chunks = []

    for section in sections:
        if section["token_count"] > max_tokens:
            subchunks = split_by_paragraphs(section, max_tokens)
            chunks.extend(subchunks)
        else:
            chunks.append(section)

    return chunks

# 并行分析
results = parallel_map(analyze_chunk, chunks, max_workers=4)
final_analysis = merge_analysis_results(results)
```

### 9.3 Zotero-Logseq双向同步

```python
class ZoteroLogseqSync:
    def sync(self, mode="incremental"):
        if mode == "incremental":
            zotero_changes = self.get_zotero_changes(
                since=self.last_sync_timestamp
            )
            for item in zotero_changes:
                self.sync_item_to_logseq(item)

    def sync_item_to_logseq(self, item):
        page = self.logseq.find_page_by_zotero_key(item["key"])

        if page:
            self.logseq.update_page_properties(
                page["id"],
                self.extract_properties(item)
            )
        else:
            self.logseq.create_page_from_template(
                item,
                template="academic_paper"
            )
```

### 9.4 Master Agent工具编排

**基于LangGraph:**

```python
from langgraph.graph import StateGraph

def build_master_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("understand_intent", understand_intent_node)
    workflow.add_node("plan_workflow", plan_workflow_node)
    workflow.add_node("execute_tools", execute_tools_node)

    workflow.set_entry_point("understand_intent")
    workflow.add_edge("understand_intent", "plan_workflow")
    workflow.add_edge("plan_workflow", "execute_tools")
    workflow.set_finish_point("execute_tools")

    return workflow.compile()
```

---

## 10. 性能优化与成本控制

### 10.1 API调用优化

**批量处理:**

```python
def batch_embed_texts(texts, batch_size=100):
    """批量embed降低成本"""
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )
        embeddings.extend([e.embedding for e in response.data])
    return embeddings
```

**缓存机制:**

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding_cached(text_hash):
    return openai.embeddings.create(...)
```

### 10.2 成本估算

**每月成本（假设）：**
- 语义搜索索引1000篇：$0.02
- 每日查询100次：$0.06
- PDF分析10篇：$1.00
- 关键字生成30次：$0.03

**总计：约 $1.11/月**

### 10.3 性能优化

```python
import asyncio
from asyncio import Semaphore

semaphore = Semaphore(5)  # 限流

async def rate_limited_api_call(func, *args):
    async with semaphore:
        return await func(*args)

# 批量搜索
@mcp.tool
async def batch_search_items(queries: list[str]) -> str:
    """并发搜索多个查询"""
    tasks = [search_item(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return format_results(results)
```

---

## 总结

这个学术Agent系统设计包含：

**核心特性:**
- 单一Master Agent统一编排
- 四个专门MCP服务器
- Zotero为数据真相源
- 云AI驱动确保效果

**关键功能:**
- 自动化论文发现与导入
- 语义搜索和智能匹配
- PDF深度分析
- Zotero-Logseq双向同步
- 主题综述生成

**技术选型:**
- MCP协议标准化
- OpenAI/Anthropic API
- ChromaDB向量数据库
- LangGraph Agent编排
- 复用zotero-mcp

**实施计划:**
- Phase 1 (4周): MVP
- Phase 2 (3周): PDF分析
- Phase 3 (3周): RAG功能
- Phase 4 (2周): 生产化

**成本:**
- 月均约$1-2
- 性能优化降低API调用

---

**下一步行动:**
1. 审阅并批准设计文档
2. 创建详细的实现计划
3. 搭建开发环境和项目结构
4. 开始Phase 1开发
