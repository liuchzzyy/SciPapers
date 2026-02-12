# 学术Agent系统设计文档

**日期**: 2025-02-08
**版本**: 2.0
**更新日期**: 2026-02-11
**状态**: 实现阶段

---

## 变更记录

### v2.0 (2026-02-11)
- **重大架构更新**: MCP服务器已作为成熟子模块存在
- **feedder-mcp** (v2.2.0): 完整的RSS/Gmail论文获取、过滤、增强、导出功能
- **logseq-mcp** (v2.1.1): 25个MCP工具，4层架构，158个测试
- **zotero-mcp** (v2.2.0): 语义搜索、PDF分析、批注提取、批量工作流
- **重新聚焦**: 主要开发工作转向Master Agent和集成层

### v1.0 (2025-02-08)
- 初始系统设计文档

---

## 目录

1. [系统架构概述](#1-系统架构概述)
2. [现有MCP服务器](#2-现有mcp服务器)
3. [Master Agent与工具编排](#3-master-agent与工具编排)
4. [数据流与核心工作流](#4-数据流与核心工作流)
5. [集成层设计](#5-集成层设计)
6. [错误处理与边界情况](#6-错误处理与边界情况)
7. [测试策略](#7-测试策略)
8. [部署与配置](#8-部署与配置)
9. [开发路线图](#9-开发路线图)
10. [关键技术与实现要点](#10-关键技术与实现要点)
11. [性能优化与成本控制](#11-性能优化与成本控制)

---

## 1. 系统架构概述

### 1.1 核心设计理念

这是一个基于MCP（Model Context Protocol）的学术研究助手系统，通过统一的Master Agent编排现有的成熟MCP服务器。

**核心设计理念：**
- **复用优先**: 三个核心MCP服务器已作为子模块存在，无需从头开发
- **单一入口**: 用户只与"学术助手"对话，不需要理解底层MCP架构
- **Zotero为中心**: Zotero是文献管理的唯一真相源，Logseq作为视图层
- **云AI驱动**: 所有AI功能使用商业API（OpenAI/Anthropic）确保效果
- **用户控制**: RSS源和Gmail标签完全由用户配置，Agent不自动推断

### 1.2 系统分层（更新）

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
│              服务层 (子模块)                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │feedder   │ │  zotero  │ │  logseq  │ │  master  │  │
│  │  -mcp    │ │   -mcp   │ │   -mcp   │ │  _agent  │  │
│  │(v2.2.0)  │ │ (v2.2.0) │ │ (v2.1.1) │ │  (NEW)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│       ↓            ↓            ↓            ↓          │
│  ┌──────────────────────────────────────────────────┐  │
│  │        集成层 (academic-agent核心)                │  │
│  │  - Zotero-Logseq同步                             │  │
│  │  - 学术工作流编排                                 │  │
│  │  - 模板管理                                       │  │
│  └──────────────────────────────────────────────────┘  │
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

### 1.3 子模块架构

```
academic-agent/
├── .gitmodules              # 子模块配置
├── feedder-mcp/             # 子模块: 论文获取与处理
│   ├── src/
│   │   ├── handlers/        # MCP工具处理器
│   │   ├── services/        # 核心业务逻辑
│   │   ├── sources/         # RSS/Gmail数据源
│   │   ├── filters/         # 关键词/AI过滤
│   │   └── adapters/        # JSON/Zotero导出
│   └── tests/               # 测试套件
├── logseq-mcp/              # 子模块: Logseq集成
│   ├── src/
│   │   ├── handlers/        # 25个MCP工具
│   │   ├── services/        # 业务逻辑
│   │   ├── models/          # 数据模型
│   │   └── client/          # Logseq API客户端
│   └── tests/
├── zotero-mcp/              # 子模块: Zotero集成
│   ├── src/
│   │   ├── handlers/        # MCP工具处理器
│   │   ├── services/        # 核心服务
│   │   ├── analyzer/        # PDF分析器
│   │   ├── clients/         # Zotero/外部API
│   │   └── models/          # 数据模型
│   └── tests/
└── src/                     # academic-agent核心
    ├── orchestrator/        # Master Agent编排层
    ├── workflows/           # 学术工作流定义
    ├── integration/         # MCP集成适配器
    └── models/              # 通用数据模型
```

### 1.4 典型工作流示例

**用户请求**: "帮我把最近一周arXiv上关于transformer的论文导入我的文献库"

```
1. Master Agent解析意图
   ├─ 识别: 文献发现任务
   ├─ 时间范围: 最近一周
   └─ 关键词: transformer

2. 调用feedder_mcp.fetch_feeds()
   ├─ 获取arXiv RSS源
   └─ 返回原始论文列表

3. 调用feedder_mcp.filter()
   ├─ 使用transformer关键词过滤
   └─ AI语义匹配（如果启用）

4. 调用zotero_mcp.get_metadata()
   ├─ 与现有库对比去重
   └─ 返回新论文列表

5. 调用feedder_mcp.enrich()
   ├─ CrossRef元数据增强
   └─ OpenAlex引用信息

6. 调用feedder_mcp.export()
   ├─ 导出到Zotero
   └─ 自动添加标签

7. 调用logseq_mcp.create_page()
   ├─ 为新论文创建笔记页面
   ├─ 应用学术模板
   └─ 建立Zotero链接

8. 返回结果给用户
   └─ "已导入15篇论文，已创建Logseq笔记"
```

---

## 2. 现有MCP服务器

### 2.1 feedder-mcp (v2.2.0)

**仓库位置**: `../feedder-mcp`

#### 2.1.1 功能概述

完整的论文获取、过滤、增强和导出系统，支持RSS源和Gmail集成。

**核心功能:**
- MCP服务器模式 (stdio) + CLI工具
- RSS订阅源管理 (OPML支持)
- Gmail论文邮件解析
- 双阶段过滤: 关键词 + AI语义匹配
- 元数据增强 (CrossRef + OpenAlex)
- 导出适配器 (JSON + Zotero)

#### 2.1.2 可用MCP工具

```python
# 获取工具
@mcp.tool
def fetch_feeds(source: str = "rss", limit: int = 200, since: int = 15) -> str:
    """从RSS源获取论文"""

@mcp.tool
def filter_papers(
    input_path: str,
    keywords: List[str],
    use_ai: bool = True
) -> str:
    """过滤论文（关键词 + AI语义）"""

@mcp.tool
def enrich_papers(
    input_path: str,
    api: str = "all",
    concurrency: int = 5
) -> str:
    """增强元数据（CrossRef + OpenAlex）"""

@mcp.tool
def export_papers(
    input_path: str,
    output_path: str,
    format: str = "json"
) -> str:
    """导出论文"""

@mcp.tool
def generate_keywords(topic: str) -> str:
    """AI生成搜索关键词"""
```

#### 2.1.3 CLI工具

```bash
# 1. 获取RSS论文
feedder-mcp fetch --source rss --limit 200 --output output/raw.json

# 2. 关键词过滤
feedder-mcp filter --input output/raw.json --output output/filtered.json \
    --keywords battery zinc electrolyte

# 3. AI语义过滤
feedder-mcp filter --input output/filtered.json --output output/ai_filtered.json \
    --keywords battery zinc

# 4. 元数据增强
feedder-mcp enrich --input output/ai_filtered.json --output output/enriched.json \
    --api all --concurrency 5

# 5. 导出到Zotero
feedder-mcp export --input output/enriched.json --format zotero
```

#### 2.1.4 配置环境变量

| 变量 | 说明 |
|------|------|
| `OPENAI_API_KEY` | AI过滤和关键词生成 |
| `RESEARCH_PROMPT` | 用户研究兴趣描述 |
| `FEEDDER_MCP_OPML` | OPML文件路径 |
| `GMAIL_TOKEN_JSON` | Gmail OAuth令牌 |
| `ZOTERO_MCP_PATH` | Zotero MCP路径（用于导出） |

---

### 2.2 logseq-mcp (v2.1.1)

**仓库位置**: `../logseq-mcp`

#### 2.2.1 功能概述

完整的Logseq知识图谱集成，提供25个MCP工具和6个Prompts。

**核心特性:**
- 25个MCP工具（块操作、页面操作、查询、Git操作）
- 4层架构（基础设施、域、应用、表现层）
- 完整类型安全（Pydantic v2）
- 158个测试，87%覆盖率
- 重试逻辑和指数退避

#### 2.2.2 可用MCP工具

**块操作（8个工具）:**
```python
@mcp.tool
def logseq_insert_block(
    content: str,
    parent_block: str = None,
    properties: dict = None
) -> str:
    """创建新块"""

@mcp.tool
def logseq_update_block(uuid: str, content: str) -> str:
    """更新块内容"""

@mcp.tool
def logseq_delete_block(uuid: str) -> str:
    """删除块"""

@mcp.tool
def logseq_get_block(uuid: str) -> str:
    """获取块详情"""

@mcp.tool
def logseq_move_block(uuid: str, target_uuid: str) -> str:
    """移动块"""

@mcp.tool
def logseq_insert_batch(parent: str, blocks: List[dict]) -> str:
    """批量插入块"""

@mcp.tool
def logseq_get_page_blocks(page_name: str) -> str:
    """获取页面所有块"""

@mcp.tool
def logseq_get_current_page_content() -> str:
    """获取当前页面内容"""
```

**页面操作（5个工具）:**
```python
@mcp.tool
def logseq_create_page(
    page_name: str,
    properties: dict = None,
    journal: bool = False
) -> str:
    """创建新页面"""

@mcp.tool
def logseq_get_page(page_name: str, include_children: bool = False) -> str:
    """获取页面详情"""

@mcp.tool
def logseq_delete_page(page_name: str) -> str:
    """删除页面"""

@mcp.tool
def logseq_rename_page(old_name: str, new_name: str) -> str:
    """重命名页面"""

@mcp.tool
def logseq_get_all_pages() -> str:
    """列出所有页面"""
```

**查询操作（3个工具）:**
```python
@mcp.tool
def logseq_simple_query(query: str) -> str:
    """简单查询"""

@mcp.tool
def logseq_advanced_query(query: str, inputs: List = None) -> str:
    """高级Datascript查询"""

@mcp.tool
def logseq_get_tasks(marker: str = None, priority: str = None) -> str:
    """获取任务列表"""
```

**编辑器操作（5个工具）:**
```python
@mcp.tool
def logseq_get_current_page() -> str:
    """获取当前页面"""

@mcp.tool
def logseq_get_current_block() -> str:
    """获取当前块"""

@mcp.tool
def logseq_edit_block(uuid: str, pos: int = 0) -> str:
    """编辑块"""

@mcp.tool
def logseq_exit_editing_mode(select_block: bool = False) -> str:
    """退出编辑模式"""

@mcp.tool
def logseq_get_editing_content() -> str:
    """获取编辑内容"""
```

**图操作（2个工具）:**
```python
@mcp.tool
def logseq_get_current_graph() -> str:
    """获取当前图信息"""

@mcp.tool
def logseq_get_user_configs() -> str:
    """获取用户配置"""
```

**Git操作（2个工具，需启用）:**
```python
@mcp.tool
def logseq_git_commit(message: str) -> str:
    """Git提交"""

@mcp.tool
def logseq_git_status() -> str:
    """Git状态"""
```

#### 2.2.3 配置环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LOGSEQ_API_TOKEN` | API授权令牌 | 必需 |
| `LOGSEQ_API_URL` | API端点 | `http://localhost:12315` |
| `LOGSEQ_ENABLE_ADVANCED_QUERIES` | 启用高级查询 | `true` |
| `LOGSEQ_ENABLE_GIT_OPERATIONS` | 启用Git操作 | `false` |
| `LOGSEQ_API_TIMEOUT` | API超时（秒） | `10` |
| `LOGSEQ_API_MAX_RETRIES` | 最大重试次数 | `3` |

---

### 2.3 zotero-mcp (v2.2.0)

**仓库位置**: `../zotero-mcp`

#### 2.3.1 功能概述

功能全面的Zotero集成，支持语义搜索、PDF分析、批注提取、批量工作流。

**核心特性:**
- 多模态PDF分析（OCR + 图像提取）
- 语义搜索（向量数据库）
- 元数据增强（CrossRef/OpenAlex）
- 批注和笔记提取
- 重复检测和删除
- 检查点/恢复机制
- 可配置输出模板

#### 2.3.2 可用MCP工具

**搜索与发现（5个工具）:**
```python
@mcp.tool
def zotero_semantic_search(query: str, limit: int = 10) -> str:
    """AI语义搜索"""

@mcp.tool
def zotero_search(query: str) -> str:
    """关键词搜索"""

@mcp.tool
def zotero_advanced_search(criteria: dict) -> str:
    """高级搜索"""

@mcp.tool
def zotero_search_by_tag(tag: str) -> str:
    """标签搜索"""

@mcp.tool
def zotero_get_recent(limit: int = 20) -> str:
    """最近添加"""
```

**内容访问（4个工具）:**
```python
@mcp.tool
def zotero_get_metadata(item_key: str) -> str:
    """获取元数据"""

@mcp.tool
def zotero_get_fulltext(item_key: str) -> str:
    """获取全文"""

@mcp.tool
def zotero_get_bundle(item_key: str) -> str:
    """获取完整数据包"""

@mcp.tool
def zotero_get_children(item_key: str) -> str:
    """获取附件和笔记"""
```

**批注和笔记（4个工具）:**
```python
@mcp.tool
def zotero_get_annotations(item_key: str) -> str:
    """获取PDF批注"""

@mcp.tool
def zotero_get_notes(item_key: str = None) -> str:
    """获取笔记"""

@mcp.tool
def zotero_search_notes(query: str) -> str:
    """搜索笔记/批注"""

@mcp.tool
def zotero_create_note(item_key: str, content: str) -> str:
    """创建笔记"""
```

**批量工作流（4个工具）:**
```python
@mcp.tool
def zotero_prepare_analysis(
    item_keys: List[str],
    analysis_type: str = "comprehensive"
) -> str:
    """准备PDF分析"""

@mcp.tool
def zotero_batch_analyze_pdfs(
    workflow_id: str,
    model: str = "deepseek-chat"
) -> str:
    """批量分析PDF"""

@mcp.tool
def zotero_resume_workflow(workflow_id: str) -> str:
    """恢复中断的工作流"""

@mcp.tool
def zotero_list_workflows() -> str:
    """列出工作流状态"""
```

**PDF发现（2个工具）:**
```python
@mcp.tool
def zotero_find_pdf_si(item_key: str) -> str:
    """查找PDF/SI（单个）"""

@mcp.tool
def zotero_find_pdf_si_batch(collection_name: str) -> str:
    """批量查找PDF/SI"""
```

**集合和标签（3个工具）:**
```python
@mcp.tool
def zotero_get_collections() -> str:
    """列出集合"""

@mcp.tool
def zotero_find_collection(name: str) -> str:
    """查找集合"""

@mcp.tool
def zotero_get_tags() -> str:
    """列出所有标签"""
```

#### 2.3.3 CLI工具

```bash
# 语义搜索数据库管理
zotero-mcp update-db                      # 更新数据库
zotero-mcp update-db --fulltext           # 全文更新
zotero-mcp db-status                      # 检查状态

# 研究工作流
zotero-mcp scan                            # 扫描未处理论文
zotero-mcp update-metadata                 # 增强元数据
zotero-mcp deduplicate                     # 去重
zotero-mcp pdf-find --item-key ABCD1234   # 查找PDF

# 更新和维护
zotero-mcp update                          # 更新版本
zotero-mcp version                         # 显示版本
```

#### 2.3.4 配置环境变量

**Zotero连接:**
```bash
ZOTERO_LOCAL=true                    # 本地API（默认）
ZOTERO_API_KEY=your_key             # Web API密钥
ZOTERO_LIBRARY_ID=your_id           # Web API库ID
```

**语义搜索:**
```bash
ZOTERO_EMBEDDING_MODEL=default      # default, openai, gemini
OPENAI_API_KEY=your_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

**批量分析:**
```bash
DEEPSEEK_API_KEY=your_key
DEEPSEEK_MODEL=deepseek-chat
```

**多模态分析:**
```bash
ZOTERO_MCP_CLI_LLM_PROVIDER=deepseek
ZOTERO_MCP_CLI_LLM_MODEL=deepseek-chat
ZOTERO_MCP_CLI_LLM_OCR_ENABLED=true
ZOTERO_MCP_CLI_LLM_MAX_PAGES=50
```

---

## 3. Master Agent与工具编排

### 3.1 Master Agent的职责

Master Agent是系统的协调者，负责：
1. **理解用户意图**: 将自然语言请求转换为工作流
2. **编排MCP工具**: 调用子模块中的工具完成复杂任务
3. **管理上下文**: 维护对话状态和用户研究兴趣
4. **处理错误**: 优雅降级和错误恢复
5. **提供学术工作流**: 预定义的常见研究任务流程

### 3.2 核心能力

#### 3.2.1 意图识别与任务分解

```python
from enum import Enum
from typing import List, Tuple
from dataclasses import dataclass

class Intent(Enum):
    PAPER_DISCOVERY = "paper_discovery"        # 论文发现
    PAPER_ANALYSIS = "paper_analysis"          # 论文分析
    LITERATURE_REVIEW = "literature_review"    # 文献综述
    KNOWLEDGE_QUERY = "knowledge_query"        # 知识查询
    WORKFLOW_AUTOMATION = "workflow_automation" # 工作流自动化

@dataclass
class WorkflowStep:
    mcp_server: str      # "feedder", "zotero", "logseq"
    tool_name: str       # 工具名称
    parameters: dict     # 工具参数
    depends_on: List[str] = None  # 依赖的步骤ID

@dataclass
class Workflow:
    intent: Intent
    steps: List[WorkflowStep]
    description: str

def decompose_user_query(query: str) -> Workflow:
    """将用户查询分解为MCP工具调用序列"""

    # 示例1: 文献发现
    if any(kw in query.lower() for kw in ["找论文", "新论文", "导入", "发现"]):
        return Workflow(
            intent=Intent.PAPER_DISCOVERY,
            description="从RSS源发现并导入相关论文",
            steps=[
                WorkflowStep(
                    mcp_server="feedder",
                    tool_name="fetch_feeds",
                    parameters={"limit": 200, "since": 7}
                ),
                WorkflowStep(
                    mcp_server="feedder",
                    tool_name="generate_keywords",
                    parameters={"topic": extract_topic(query)}
                ),
                WorkflowStep(
                    mcp_server="feedder",
                    tool_name="filter_papers",
                    parameters={"use_ai": True}
                ),
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="get_metadata",
                    parameters={"limit": 1000}
                ),
                WorkflowStep(
                    mcp_server="feedder",
                    tool_name="enrich_papers",
                    parameters={"api": "all"}
                ),
                WorkflowStep(
                    mcp_server="feedder",
                    tool_name="export_papers",
                    parameters={"format": "zotero"}
                ),
                WorkflowStep(
                    mcp_server="logseq",
                    tool_name="create_paper_pages",
                    parameters={}
                )
            ]
        )

    # 示例2: 文献分析
    elif any(kw in query.lower() for kw in ["分析", "理解", "总结"]):
        return Workflow(
            intent=Intent.PAPER_ANALYSIS,
            description="深度分析论文内容",
            steps=[
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="get_fulltext",
                    parameters={"item_key": extract_item_key(query)}
                ),
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="prepare_analysis",
                    parameters={"analysis_type": "comprehensive"}
                ),
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="batch_analyze_pdfs",
                    parameters={"model": "deepseek-chat"}
                ),
                WorkflowStep(
                    mcp_server="logseq",
                    tool_name="update_page_block",
                    parameters={"section": "AI分析"}
                ),
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="semantic_search",
                    parameters={"limit": 5}
                ),
                WorkflowStep(
                    mcp_server="logseq",
                    tool_name="add_related_papers",
                    parameters={}
                )
            ]
        )

    # 示例3: 文献综述
    elif any(kw in query.lower() for kw in ["综述", "回顾", "总结研究"]):
        return Workflow(
            intent=Intent.LITERATURE_REVIEW,
            description="生成主题文献综述",
            steps=[
                WorkflowStep(
                    mcp_server="feedder",
                    tool_name="generate_keywords",
                    parameters={"topic": extract_topic(query)}
                ),
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="semantic_search",
                    parameters={"limit": 20}
                ),
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="get_fulltext_batch",
                    parameters={}
                ),
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="batch_analyze_pdfs",
                    parameters={}
                ),
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="synthesize_review",
                    parameters={}
                ),
                WorkflowStep(
                    mcp_server="logseq",
                    tool_name="create_review_page",
                    parameters={}
                )
            ]
        )

    # 示例4: 知识查询
    else:
        return Workflow(
            intent=Intent.KNOWLEDGE_QUERY,
            description="查询文献库和笔记",
            steps=[
                WorkflowStep(
                    mcp_server="zotero",
                    tool_name="semantic_search",
                    parameters={"query": query, "limit": 10}
                ),
                WorkflowStep(
                    mcp_server="logseq",
                    tool_name="simple_query",
                    parameters={"query": query}
                )
            ]
        )
```

#### 3.2.2 上下文管理

```python
from typing import Dict, Any, Optional
from datetime import datetime
import json

class ConversationContext:
    """维护对话上下文"""

    def __init__(self):
        self.user_profile = {
            "research_interests": [],
            "recent_queries": [],
            "zotero_library_snapshot": None,
            "preferences": {
                "auto_sync_logseq": True,
                "default_analysis_type": "comprehensive",
                "max_papers_to_import": 50
            }
        }
        self.active_items = {}  # 当前讨论的文献
        self.workflow_history = []
        self.last_update = datetime.now()

    def remember(self, key: str, value: Any):
        """记住信息供后续使用"""
        self.user_profile[key] = value
        self.last_update = datetime.now()

    def recall(self, key: str, default: Any = None) -> Any:
        """召回之前的信息"""
        return self.user_profile.get(key, default)

    def add_active_item(self, item_key: str, metadata: dict):
        """添加当前讨论的文献"""
        self.active_items[item_key] = {
            "metadata": metadata,
            "added_at": datetime.now()
        }

    def get_active_item(self, item_key: str = None) -> Optional[dict]:
        """获取当前或最新的活跃文献"""
        if item_key:
            return self.active_items.get(item_key)
        if self.active_items:
            # 返回最近添加的
            return max(self.active_items.items(),
                      key=lambda x: x[1]["added_at"])[1]
        return None

    def add_workflow(self, workflow: Workflow):
        """记录工作流历史"""
        self.workflow_history.append({
            "workflow": workflow,
            "timestamp": datetime.now()
        })

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "user_profile": self.user_profile,
            "active_items": {
                k: {
                    "metadata": v["metadata"],
                    "added_at": v["added_at"].isoformat()
                }
                for k, v in self.active_items.items()
            },
            "workflow_history": [
                {
                    "intent": w["workflow"].intent.value,
                    "description": w["workflow"].description,
                    "timestamp": w["timestamp"].isoformat()
                }
                for w in self.workflow_history[-10:]  # 最近10条
            ],
            "last_update": self.last_update.isoformat()
        }

    def save(self, path: str):
        """保存到文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> 'ConversationContext':
        """从文件加载"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ctx = cls()
        ctx.user_profile = data.get("user_profile", {})
        # 恢复其他字段...
        return ctx

# 使用示例
ctx = ConversationContext()

# 用户提到研究兴趣
ctx.remember("research_interests", ["transformer", "attention", "NLP"])

# 导入论文后记录
ctx.add_active_item("ABCD1234", {
    "title": "Attention Is All You Need",
    "authors": ["Vaswani, A."],
    "year": 2017
})

# 用户问: "刚才那篇论文的作者还有什么其他工作？"
paper = ctx.get_active_item()
if paper:
    authors = paper["metadata"]["authors"]
    # 使用作者名进行搜索...
```

#### 3.2.3 工具选择策略

```python
from typing import List, Dict, Callable

# MCP工具映射
MCP_TOOLS = {
    "feedder": {
        "fetch_feeds": {
            "description": "从RSS源获取论文",
            "parameters": {"source": "rss", "limit": 200, "since": 15}
        },
        "filter_papers": {
            "description": "过滤论文（关键词+AI）",
            "parameters": {"input_path": "", "keywords": [], "use_ai": True}
        },
        "enrich_papers": {
            "description": "增强元数据",
            "parameters": {"input_path": "", "api": "all"}
        },
        "export_papers": {
            "description": "导出论文",
            "parameters": {"input_path": "", "format": "json"}
        },
        "generate_keywords": {
            "description": "AI生成关键词",
            "parameters": {"topic": ""}
        }
    },
    "zotero": {
        "semantic_search": {
            "description": "语义搜索",
            "parameters": {"query": "", "limit": 10}
        },
        "search": {
            "description": "关键词搜索",
            "parameters": {"query": ""}
        },
        "get_metadata": {
            "description": "获取元数据",
            "parameters": {"item_key": ""}
        },
        "get_fulltext": {
            "description": "获取全文",
            "parameters": {"item_key": ""}
        },
        "get_annotations": {
            "description": "获取批注",
            "parameters": {"item_key": ""}
        },
        "prepare_analysis": {
            "description": "准备PDF分析",
            "parameters": {"item_keys": [], "analysis_type": "comprehensive"}
        },
        "batch_analyze_pdfs": {
            "description": "批量分析PDF",
            "parameters": {"workflow_id": "", "model": "deepseek-chat"}
        },
        "get_recent": {
            "description": "最近添加",
            "parameters": {"limit": 20}
        }
    },
    "logseq": {
        "create_page": {
            "description": "创建页面",
            "parameters": {"page_name": "", "properties": {}}
        },
        "get_page": {
            "description": "获取页面",
            "parameters": {"page_name": "", "include_children": True}
        },
        "insert_block": {
            "description": "插入块",
            "parameters": {"content": "", "parent_block": ""}
        },
        "update_block": {
            "description": "更新块",
            "parameters": {"uuid": "", "content": ""}
        },
        "simple_query": {
            "description": "简单查询",
            "parameters": {"query": ""}
        },
        "get_all_pages": {
            "description": "列出所有页面",
            "parameters": {}
        }
    }
}

# 意图到工具的映射
INTENT_TOOL_MAPPING = {
    Intent.PAPER_DISCOVERY: [
        "feedder.fetch_feeds",
        "feedder.generate_keywords",
        "feedder.filter_papers",
        "zotero.get_metadata",
        "feedder.enrich_papers",
        "feedder.export_papers",
        "logseq.create_page"
    ],
    Intent.PAPER_ANALYSIS: [
        "zotero.get_fulltext",
        "zotero.prepare_analysis",
        "zotero.batch_analyze_pdfs",
        "logseq.insert_block",
        "zotero.semantic_search"
    ],
    Intent.LITERATURE_REVIEW: [
        "feedder.generate_keywords",
        "zotero.semantic_search",
        "zotero.get_fulltext",
        "zotero.batch_analyze_pdfs",
        "logseq.create_page"
    ],
    Intent.KNOWLEDGE_QUERY: [
        "zotero.semantic_search",
        "logseq.simple_query"
    ]
}

class ToolSelector:
    """工具选择器"""

    def __init__(self, context: ConversationContext):
        self.context = context

    def select_tools_for_intent(self, intent: Intent) -> List[str]:
        """根据意图选择工具"""
        return INTENT_TOOL_MAPPING.get(intent, [])

    def get_tool_definition(self, tool_path: str) -> Dict:
        """获取工具定义"""
        mcp, tool = tool_path.split('.')
        return MCP_TOOLS[mcp][tool]

    def adapt_parameters(self, tool_path: str, base_params: dict) -> dict:
        """根据上下文调整参数"""
        definition = self.get_tool_definition(tool_path)
        params = definition["parameters"].copy()
        params.update(base_params)

        # 根据用户偏好调整
        if tool_path == "feedder.filter_papers":
            params["use_ai"] = self.context.recall(
                "use_ai_filtering",
                default=True
            )

        return params
```

#### 3.2.4 执行引擎

```python
import asyncio
from typing import Any, Dict
import subprocess
import json

class MCPExecutor:
    """MCP工具执行器"""

    def __init__(self, context: ConversationContext):
        self.context = context
        self.selector = ToolSelector(context)

    async def execute_tool(self, mcp: str, tool: str, params: dict) -> Dict[str, Any]:
        """执行单个MCP工具"""

        # 根据MCP服务器类型选择执行方式
        if mcp == "feedder":
            return await self._execute_feedder(tool, params)
        elif mcp == "zotero":
            return await self._execute_zotero(tool, params)
        elif mcp == "logseq":
            return await self._execute_logseq(tool, params)
        else:
            raise ValueError(f"Unknown MCP server: {mcp}")

    async def _execute_feedder(self, tool: str, params: dict) -> Dict:
        """执行feedder-mcp工具"""

        # 使用CLI或MCP协议
        if tool == "fetch_feeds":
            cmd = [
                "feedder-mcp", "fetch",
                "--limit", str(params.get("limit", 200)),
                "--since", str(params.get("since", 15)),
                "--output", "output/raw.json"
            ]
        elif tool == "filter_papers":
            cmd = [
                "feedder-mcp", "filter",
                "--input", params["input_path"],
                "--output", "output/filtered.json"
            ]
            if params.get("keywords"):
                cmd.extend(["--keywords"] + params["keywords"])
            if params.get("use_ai"):
                cmd.append("--ai")
        elif tool == "generate_keywords":
            # 需要AI API调用
            return await self._generate_keywords_ai(params["topic"])
        else:
            raise ValueError(f"Unknown feedder tool: {tool}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr}

    async def _execute_zotero(self, tool: str, params: dict) -> Dict:
        """执行zotero-mcp工具"""

        if tool == "semantic_search":
            cmd = [
                "zotero-mcp", "query", params["query"],
                "--limit", str(params.get("limit", 10))
            ]
        elif tool == "get_fulltext":
            cmd = [
                "zotero-mcp", "export", params["item_key"],
                "--fulltext"
            ]
        elif tool == "batch_analyze_pdfs":
            cmd = [
                "zotero-mcp", "analyze",
                "--workflow-id", params["workflow_id"],
                "--model", params.get("model", "deepseek-chat")
            ]
        else:
            raise ValueError(f"Unknown zotero tool: {tool}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr}

    async def _execute_logseq(self, tool: str, params: dict) -> Dict:
        """执行logseq-mcp工具"""

        if tool == "create_page":
            cmd = [
                "logseq-mcp", "pages", "create",
                "--name", params["page_name"]
            ]
            if params.get("properties"):
                cmd.extend(["--properties", json.dumps(params["properties"])])
        elif tool == "insert_block":
            cmd = [
                "logseq-mcp", "blocks", "insert",
                "--parent", params.get("parent_block", ""),
                "--content", params["content"]
            ]
        elif tool == "simple_query":
            cmd = [
                "logseq-mcp", "queries", "simple",
                "--query", params["query"]
            ]
        else:
            raise ValueError(f"Unknown logseq tool: {tool}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr}

    async def _generate_keywords_ai(self, topic: str) -> Dict:
        """使用AI生成关键词"""
        # 这里可以调用OpenAI API或使用feedder-mcp的内置功能
        # 简化示例：
        return {
            "status": "success",
            "keywords": {
                "primary": [topic],
                "secondary": [],
                "related": []
            }
        }

    async def execute_workflow(self, workflow: Workflow) -> Dict[str, Any]:
        """执行完整工作流"""

        results = {
            "workflow": workflow.description,
            "steps_completed": [],
            "steps_failed": [],
            "final_result": None
        }

        for step in workflow.steps:
            try:
                # 检查依赖
                if step.depends_on:
                    if not all(d in results["steps_completed"] for d in step.depends_on):
                        continue

                # 执行工具
                result = await self.execute_tool(
                    step.mcp_server,
                    step.tool_name,
                    step.parameters
                )

                if result["status"] == "success":
                    results["steps_completed"].append(step.tool_name)
                else:
                    results["steps_failed"].append({
                        "tool": step.tool_name,
                        "error": result.get("error")
                    })

            except Exception as e:
                results["steps_failed"].append({
                    "tool": step.tool_name,
                    "error": str(e)
                })

        return results
```

### 3.3 实现框架

**推荐：基于MCP SDK + LangGraph**

```python
from mcp import ClientSession, StdioServerParameters
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    user_query: str
    intent: str
    workflow: Workflow
    step_results: Annotated[list, operator.add]
    context: ConversationContext
    final_response: str

async def create_mcp_client(server_name: str):
    """创建MCP客户端连接"""
    if server_name == "feedder":
        server_params = StdioServerParameters(
            command="feedder-mcp",
            args=["serve"]
        )
    elif server_name == "zotero":
        server_params = StdioServerParameters(
            command="zotero-mcp",
            args=["serve"]
        )
    elif server_name == "logseq":
        server_params = StdioServerParameters(
            command="logseq-mcp",
            args=["serve"]
        )

    client = ClientSession(server_params)
    await client.initialize()
    return client

async def understand_intent_node(state: AgentState) -> AgentState:
    """理解用户意图"""
    query = state["user_query"]
    workflow = decompose_user_query(query)
    state["intent"] = workflow.intent.value
    state["workflow"] = workflow
    return state

async def plan_workflow_node(state: AgentState) -> AgentState:
    """规划工作流"""
    # 已经在understand_intent_node中完成
    return state

async def execute_tools_node(state: AgentState) -> AgentState:
    """执行工具调用"""
    executor = MCPExecutor(state["context"])
    results = await executor.execute_workflow(state["workflow"])
    state["step_results"].append(results)
    return state

async def format_result_node(state: AgentState) -> AgentState:
    """格式化结果"""
    results = state["step_results"][-1]
    response = format_workflow_results(results)
    state["final_response"] = response
    return state

def should_execute(state: AgentState) -> str:
    """决定是否执行或需要澄清"""
    if state.get("workflow") and state["workflow"].steps:
        return "execute"
    else:
        return "clarify"

def build_master_agent():
    """构建Master Agent"""
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("understand_intent", understand_intent_node)
    workflow.add_node("plan_workflow", plan_workflow_node)
    workflow.add_node("execute_tools", execute_tools_node)
    workflow.add_node("format_result", format_result_node)

    # 设置入口
    workflow.set_entry_point("understand_intent")

    # 添加边
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
    workflow.add_edge("format_result", END)

    return workflow.compile()
```

---

## 4. 数据流与核心工作流

### 4.1 数据流向图

```
┌─────────────┐
│   RSS源     │  arXiv, Nature, Science等
│  Gmail      │  论文通知邮件
└──────┬──────┘
       │ feedder-mcp.fetch_feeds()
       ▼
┌──────────────────┐
│  feedder-mcp     │
│ - 原始数据获取   │
│ - 数据清洗       │
└──────┬───────────┘
       │ filtered_papers
       ▼
┌──────────────────┐
│  feedder-mcp     │
│ - 关键词过滤     │
│ - AI语义匹配     │
└──────┬───────────┘
       │ matched_papers
       ▼
┌──────────────────┐        ┌──────────────┐
│  feedder-mcp     │◄───────┤ zotero-mcp   │
│ - 元数据增强     │  去重  │ - 用户库     │
│ - 导出准备       │  检查  │ - 历史数据   │
└──────┬───────────┘        └──────────────┘
       │ enriched_papers
       ▼
┌──────────────────┐
│  zotero-mcp      │
│ - 导入文献       │
│ - 自动标签       │
│ - PDF附件        │
└──────┬───────────┘
       │ sync event
       ▼
┌──────────────────┐
│  logseq-mcp      │
│ - 创建页面       │
│ - 应用模板       │
│ - 建立链接       │
└──────────────────┘
```

### 4.2 核心工作流

#### 4.2.1 工作流1：每日论文自动发现

```yaml
触发: Cron (每天早上8点) 或 用户请求

步骤:
  1. feedder_mcp.fetch_feeds()
     - 获取所有RSS源的最新条目
     - 从Gmail获取论文通知邮件
     - 输出: output/raw.json

  2. feedder_mcp.generate_keywords()
     - 基于RESEARCH_PROMPT生成兴趣关键词
     - 使用AI生成相关术语

  3. zotero_mcp.get_metadata(limit=1000)
     - 获取用户现有文献库元数据
     - 用于去重检查

  4. feedder_mcp.filter_papers()
     - 关键词过滤（OR逻辑）
     - AI语义过滤（相似度>阈值）
     - 与Zotero库对比去重

  5. feedder_mcp.enrich_papers()
     - CrossRef元数据增强
     - OpenAlex引用信息
     - 并发请求优化

  6. feedder_mcp.export_papers(format="zotero")
     - 导入到Zotero
     - 自动应用AI生成的标签

  7. logseq_mcp.create_paper_page()
     - 为新论文创建笔记页面
     - 应用学术模板

  8. 通知用户
     - 发送摘要：导入N篇论文
     - 列出top 5推荐

降级策略:
  - 如果RSS失败，尝试Gmail
  - 如果AI过滤失败，使用关键词过滤
  - 如果Zotero导入失败，保存为JSON备份
```

#### 4.2.2 工作流2：文献深度分析

```yaml
触发: 用户请求"分析这篇论文"

步骤:
  1. zotero_mcp.get_fulltext(item_key)
     - 获取PDF全文内容

  2. zotero_mcp.prepare_analysis()
     - 准备分析工作流
     - 创建工作流ID

  3. zotero_mcp.batch_analyze_pdfs()
     - 使用LLM分析PDF
     - 提取结构化信息：
       - 研究问题
       - 核心贡献
       - 方法论
       - 主要发现
       - 局限性

  4. logseq_mcp.insert_block()
     - 将AI分析结果写入Logseq笔记
     - 在"AI分析"section添加内容

  5. zotero_mcp.semantic_search()
     - 基于分析结果搜索相关论文
     - 限制5篇最相关

  6. logseq_mcp.insert_batch()
     - 在笔记中添加相关论文链接
     - 构建知识网络

输出格式:
  - 在Logseq笔记页面添加AI分析section
  - 包含结构化的分析结果
  - 链接到相关论文
```

#### 4.2.3 工作流3：主题综述生成

```yaml
触发: 用户请求"生成X主题的综述"

步骤:
  1. feedder_mcp.generate_keywords(topic)
     - 生成主题相关关键词
     - 获取相关概念和术语

  2. zotero_mcp.semantic_search(query=topic, limit=20)
     - 语义搜索相关文献

  3. zotero_mcp.get_fulltext_batch()
     - 批量获取全文

  4. zotero_mcp.prepare_analysis()
     - 准备批量分析

  5. zotero_mcp.batch_analyze_pdfs()
     - 并行分析多篇论文
     - 提取关键信息

  6. zotero_mcp.synthesize_review()
     - 综合分析结果
     - 生成综述结构：
       - 引言
       - 主要方法分类
       - 关键发现总结
       - 研究gap
       - 未来方向

  7. logseq_mcp.create_review_page()
     - 创建综述页面
     - 引用所有相关论文
     - 生成可视化图谱链接

输出:
  - Logseq综述页面
  - 结构化的文献综述
  - 引用文献的链接网络
```

#### 4.2.4 工作流4：知识查询

```yaml
触发: 用户提出问题

步骤:
  1. zotero_mcp.semantic_search(query)
     - 在文献库中语义搜索
     - 返回最相关的10篇文献

  2. logseq_mcp.simple_query(query)
     - 在笔记图谱中查询
     - 返回相关页面和块

  3. 合并结果
     - 按相关性排序
     - 提供摘要和链接

  4. 格式化输出
     - 清晰展示来源（Zotero/Logseq）
     - 提供快速访问链接

特殊处理:
  - 如果用户提到"刚才那篇论文"，使用上下文中的active_item
  - 如果用户提到特定作者，优先搜索该作者的其他作品
```

### 4.3 状态管理

**Zotero作为状态源：**
- 已导入论文的DOI/标题
- 每篇论文的处理状态（新发现、已分析、已读）
- 标签和笔记的时间戳

**同步状态追踪：**

```python
@dataclass
class SyncState:
    last_sync: datetime
    last_rss_fetch: datetime
    zotero_last_update: datetime
    logseq_last_sync: datetime
    vector_db_version: int

    def to_dict(self) -> dict:
        return {
            "last_sync": self.last_sync.isoformat(),
            "last_rss_fetch": self.last_rss_fetch.isoformat(),
            "zotero_last_update": self.zotero_last_update.isoformat(),
            "logseq_last_sync": self.logseq_last_sync.isoformat(),
            "vector_db_version": self.vector_db_version
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SyncState':
        return cls(
            last_sync=datetime.fromisoformat(data["last_sync"]),
            last_rss_fetch=datetime.fromisoformat(data["last_rss_fetch"]),
            zotero_last_update=datetime.fromisoformat(data["zotero_last_update"]),
            logseq_last_sync=datetime.fromisoformat(data["logseq_last_sync"]),
            vector_db_version=data["vector_db_version"]
        )

    def save(self, path: str):
        """保存同步状态"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> 'SyncState':
        """加载同步状态"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
```

---

## 5. 集成层设计

### 5.1 Zotero-Logseq同步适配器

```python
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class ZoteroItem:
    item_key: str
    title: str
    authors: List[str]
    year: int
    doi: Optional[str]
    abstract: Optional[str]
    tags: List[str]
    date_added: str
    date_modified: str

@dataclass
class LogseqPage:
    page_name: str
    properties: Dict[str, Any]
    blocks: List[Dict]
    created_at: str
    updated_at: str

class ZoteroLogseqSyncAdapter:
    """Zotero和Logseq之间的同步适配器"""

    def __init__(self, zotero_client, logseq_client):
        self.zotero = zotero_client
        self.logseq = logseq_client
        self.template = self._load_academic_template()

    def _load_academic_template(self) -> str:
        """加载学术论文模板"""
        return """
title:: [[{title}]]
authors:: {authors}
year:: {year}
doi:: {doi}
zotero_select:: zotero://select/items/{item_key}
zotero_key:: {item_key}
status:: to-read
tags:: {tags}

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
## AI分析
🤖 *由academic-agent生成*
- 关键贡献：
- 方法创新点：
- 相关文献：
## 个人思考
-
-
## 相关文献
-
"""

    def sync_item_to_logseq(self, zotero_item: ZoteroItem) -> LogseqPage:
        """同步单个Zotero项目到Logseq"""

        # 检查页面是否已存在
        page_name = self._generate_page_name(zotero_item)
        existing_page = self.logseq.get_page(page_name)

        if existing_page:
            # 更新现有页面
            return self._update_page(existing_page, zotero_item)
        else:
            # 创建新页面
            return self._create_page(zotero_item)

    def _generate_page_name(self, item: ZoteroItem) -> str:
        """生成Logseq页面名"""
        # 格式: "Paper Title (Year)"
        return f"{item['title']} ({item['year']})"

    def _create_page(self, item: ZoteroItem) -> LogseqPage:
        """创建新的Logseq页面"""

        # 格式化作者
        authors_str = ", ".join([
            f"[[{a}]]" for a in item.get("authors", [])
        ])

        # 格式化标签
        tags_str = ", ".join([
            f"[[{t}]]" for t in item.get("tags", [])
        ])

        # 应用模板
        content = self.template.format(
            title=item["title"],
            authors=authors_str,
            year=item.get("year", "n.d."),
            doi=item.get("doi", ""),
            item_key=item["item_key"],
            tags=tags_str,
            abstract=item.get("abstract", "")[:500] + "..."
            if item.get("abstract") else ""
        )

        # 创建页面
        properties = {
            "title": item["title"],
            "authors": authors_str,
            "year": item.get("year", ""),
            "doi": item.get("doi", ""),
            "zotero_key": item["item_key"],
            "status": "to-read"
        }

        result = self.logseq.create_page(
            page_name=self._generate_page_name(item),
            properties=properties
        )

        # 添加初始块
        self.logseq.insert_block(
            content=content.strip(),
            parent_block=page_name
        )

        return LogseqPage(
            page_name=self._generate_page_name(item),
            properties=properties,
            blocks=[{"content": content}],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    def _update_page(self, existing_page: LogseqPage,
                     item: ZoteroItem) -> LogseqPage:
        """更新现有Logseq页面"""

        # 更新属性
        properties = existing_page.properties.copy()
        properties.update({
            "year": item.get("year", properties.get("year", "")),
            "doi": item.get("doi", properties.get("doi", "")),
            "zotero_key": item["item_key"]
        })

        # 更新页面
        self.logseq.update_page_properties(
            page_name=existing_page.page_name,
            properties=properties
        )

        return LogseqPage(
            page_name=existing_page.page_name,
            properties=properties,
            blocks=existing_page.blocks,
            created_at=existing_page.created_at,
            updated_at=datetime.now().isoformat()
        )

    def sync_batch(self, items: List[ZoteroItem]) -> List[LogseqPage]:
        """批量同步Zotero项目到Logseq"""
        return [self.sync_item_to_logseq(item) for item in items]

    def find_page_by_zotero_key(self, item_key: str) -> Optional[LogseqPage]:
        """通过Zotero key查找Logseq页面"""

        # 使用简单查询
        query = f"zotero_key::{item_key}"
        result = self.logseq.simple_query(query)

        if result and result.get("pages"):
            return result["pages"][0]
        return None
```

### 5.2 学术工作流编排器

```python
from enum import Enum
from typing import Callable, Awaitable

class AcademicWorkflow(Enum):
    DAILY_PAPER_DISCOVERY = "daily_paper_discovery"
    PAPER_DEEP_ANALYSIS = "paper_deep_analysis"
    LITERATURE_REVIEW = "literature_review"
    KNOWLEDGE_QUERY = "knowledge_query"
    REFERENCE_MANAGEMENT = "reference_management"

class WorkflowOrchestrator:
    """学术工作流编排器"""

    def __init__(self, executor: MCPExecutor, context: ConversationContext):
        self.executor = executor
        self.context = context
        self.sync_adapter = ZoteroLogseqSyncAdapter(
            zotero_client=self.executor._execute_zotero,
            logseq_client=self.executor._execute_logseq
        )

    async def execute_workflow(self,
                               workflow: AcademicWorkflow,
                               params: dict) -> dict:
        """执行指定工作流"""

        handlers = {
            AcademicWorkflow.DAILY_PAPER_DISCOVERY: self._daily_discovery,
            AcademicWorkflow.PAPER_DEEP_ANALYSIS: self._deep_analysis,
            AcademicWorkflow.LITERATURE_REVIEW: self._literature_review,
            AcademicWorkflow.KNOWLEDGE_QUERY: self._knowledge_query,
            AcademicWorkflow.REFERENCE_MANAGEMENT: self._reference_management
        }

        handler = handlers.get(workflow)
        if not handler:
            raise ValueError(f"Unknown workflow: {workflow}")

        return await handler(params)

    async def _daily_discovery(self, params: dict) -> dict:
        """每日论文发现工作流"""

        results = {
            "papers_fetched": 0,
            "papers_filtered": 0,
            "papers_imported": 0,
            "logseq_pages_created": 0,
            "errors": []
        }

        try:
            # 1. 获取RSS源
            fetch_result = await self.executor.execute_tool(
                "feedder", "fetch_feeds",
                {"limit": params.get("limit", 200)}
            )
            results["papers_fetched"] = self._count_papers(fetch_result)

            # 2. 过滤论文
            filter_result = await self.executor.execute_tool(
                "feedder", "filter_papers",
                {
                    "input_path": "output/raw.json",
                    "keywords": params.get("keywords", []),
                    "use_ai": True
                }
            )
            results["papers_filtered"] = self._count_papers(filter_result)

            # 3. 增强元数据
            enrich_result = await self.executor.execute_tool(
                "feedder", "enrich_papers",
                {
                    "input_path": "output/filtered.json",
                    "api": "all"
                }
            )

            # 4. 导出到Zotero
            export_result = await self.executor.execute_tool(
                "feedder", "export_papers",
                {
                    "input_path": "output/enriched.json",
                    "format": "zotero"
                }
            )
            results["papers_imported"] = self._count_imported(export_result)

            # 5. 同步到Logseq
            imported_items = self._extract_imported_items(export_result)
            for item in imported_items:
                try:
                    self.sync_adapter.sync_item_to_logseq(item)
                    results["logseq_pages_created"] += 1
                except Exception as e:
                    results["errors"].append(f"Logseq sync failed: {e}")

        except Exception as e:
            results["errors"].append(f"Workflow error: {e}")

        return results

    async def _deep_analysis(self, params: dict) -> dict:
        """深度分析工作流"""

        item_key = params.get("item_key")
        if not item_key:
            return {"error": "item_key is required"}

        results = {
            "analysis_complete": False,
            "logseq_updated": False,
            "related_papers_found": 0,
            "errors": []
        }

        try:
            # 1. 准备分析
            prep_result = await self.executor.execute_tool(
                "zotero", "prepare_analysis",
                {"item_keys": [item_key]}
            )

            workflow_id = prep_result.get("workflow_id")

            # 2. 执行分析
            analyze_result = await self.executor.execute_tool(
                "zotero", "batch_analyze_pdfs",
                {
                    "workflow_id": workflow_id,
                    "model": params.get("model", "deepseek-chat")
                }
            )
            results["analysis_complete"] = True

            # 3. 更新Logseq
            analysis = analyze_result.get("analysis", {})
            page = self.sync_adapter.find_page_by_zotero_key(item_key)
            if page:
                # 更新AI分析section
                self.logseq.update_block(
                    uuid=self._find_ai_analysis_block(page),
                    content=self._format_analysis(analysis)
                )
                results["logseq_updated"] = True

            # 4. 查找相关论文
            search_result = await self.executor.execute_tool(
                "zotero", "semantic_search",
                {"query": analysis.get("summary", ""), "limit": 5}
            )
            results["related_papers_found"] = len(search_result.get("results", []))

        except Exception as e:
            results["errors"].append(str(e))

        return results

    async def _literature_review(self, params: dict) -> dict:
        """文献综述工作流"""
        # 实现类似...
        pass

    async def _knowledge_query(self, params: dict) -> dict:
        """知识查询工作流"""
        # 实现类似...
        pass

    async def _reference_management(self, params: dict) -> dict:
        """文献管理工作流"""
        # 实现类似...
        pass

    def _count_papers(self, result: dict) -> int:
        """从结果中统计论文数量"""
        if result.get("status") == "success":
            return len(result.get("papers", []))
        return 0

    def _count_imported(self, result: dict) -> int:
        """统计成功导入的论文数量"""
        if result.get("status") == "success":
            return result.get("imported_count", 0)
        return 0

    def _extract_imported_items(self, result: dict) -> List[ZoteroItem]:
        """从导入结果中提取项目"""
        # 实现提取逻辑
        pass

    def _find_ai_analysis_block(self, page: LogseqPage) -> str:
        """查找AI分析块"""
        # 实现查找逻辑
        pass

    def _format_analysis(self, analysis: dict) -> str:
        """格式化分析结果"""
        return f"""
## AI分析
🤖 *由academic-agent生成*

### 关键贡献
{chr(10).join(f"- {c}" for c in analysis.get('contributions', []))}

### 方法创新点
{chr(10).join(f"- {p}" for p in analysis.get('methodology', []))}

### 相关文献推荐
{chr(10).join(f"- [[{r}]]" for r in analysis.get('related', []))}
"""
```

---

## 6. 错误处理与边界情况

### 6.1 MCP服务器级别的错误处理

#### feedder-mcp

```python
# RSS获取失败
if not feed_data:
    return {
        "status": "error",
        "error_type": "feed_not_found",
        "message": "RSS源无法访问",
        "suggestion": "请检查URL是否正确，或稍后重试",
        "fallback": "可以尝试使用Gmail作为备选数据源"
    }

# Gmail API限流
if rate_limit_exceeded:
    return {
        "status": "warning",
        "message": "Gmail API限流，部分邮件未获取",
        "retry_after": 3600,
        "partial_results": fetched_emails
    }

# AI过滤失败
if ai_filter_error:
    return {
        "status": "partial",
        "message": "AI过滤失败，使用关键词过滤",
        "fallback_results": keyword_filtered_results
    }
```

#### zotero-mcp

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
        "suggestion": "该文献可能已被删除",
        "action": "检查回收站或重新导入"
    }

# 语义搜索数据库未初始化
if vector_db_not_initialized:
    return {
        "status": "error",
        "error_type": "vector_db_not_ready",
        "message": "语义搜索数据库未初始化",
        "solution": "请运行 'zotero-mcp update-db' 初始化数据库"
    }
```

#### logseq-mcp

```python
# Logseq API未启动
if not logseq_api_responsive():
    return {
        "status": "error",
        "error_type": "logseq_not_running",
        "message": "Logseq未运行或本地API未启用",
        "solution": "请启动Logseq并在设置中启用API (端口12315)"
    }

# 页面已存在
if page_exists(page_title):
    return {
        "status": "conflict",
        "error_type": "page_already_exists",
        "page_id": existing_page_id,
        "options": [
            "update_existing",
            "create_new_with_suffix",
            "skip"
        ],
        "default_action": "update_existing"
    }
```

### 6.2 Agent编排级别的错误处理

```python
class WorkflowErrorHandler:
    """工作流错误处理器"""

    def __init__(self, context: ConversationContext):
        self.context = context

    async def handle_workflow_error(self,
                                     workflow: Workflow,
                                     step: WorkflowStep,
                                     error: Exception) -> dict:
        """处理工作流中的错误"""

        error_info = {
            "workflow": workflow.description,
            "step": step.tool_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "recovery_actions": []
        }

        # 根据错误类型决定恢复策略
        if isinstance(error, ConnectionError):
            # 连接错误 - 尝试降级
            return await self._handle_connection_error(step, error_info)

        elif isinstance(error, TimeoutError):
            # 超时错误 - 重试或降级
            return await self._handle_timeout_error(step, error_info)

        elif isinstance(error, ValueError):
            # 参数错误 - 请求用户输入
            return await self._handle_parameter_error(step, error_info)

        else:
            # 未知错误 - 记录并继续
            return await self._handle_unknown_error(step, error_info)

    async def _handle_connection_error(self,
                                        step: WorkflowStep,
                                        error_info: dict) -> dict:
        """处理连接错误"""

        # 尝试降级方案
        fallbacks = {
            "feedder.fetch_feeds": "feedder.fetch_from_gmail",
            "zotero.semantic_search": "zotero.search",
            "logseq.create_page": None  # 非关键，可以跳过
        }

        tool_path = f"{step.mcp_server}.{step.tool_name}"
        fallback_tool = fallbacks.get(tool_path)

        if fallback_tool:
            error_info["recovery_actions"].append({
                "action": "fallback",
                "to": fallback_tool,
                "reason": "连接失败，尝试降级方案"
            })
        else:
            error_info["recovery_actions"].append({
                "action": "skip",
                "reason": "无可用降级方案，跳过此步骤"
            })

        return error_info

    async def _handle_timeout_error(self,
                                     step: WorkflowStep,
                                     error_info: dict) -> dict:
        """处理超时错误"""

        error_info["recovery_actions"].append({
            "action": "retry",
            "max_retries": 3,
            "backoff": "exponential"
        })

        return error_info

    async def _handle_parameter_error(self,
                                       step: WorkflowStep,
                                       error_info: dict) -> dict:
        """处理参数错误"""

        error_info["recovery_actions"].append({
            "action": "ask_user",
            "prompt": f"参数错误，请提供正确的{step.tool_name}参数",
            "required_params": step.parameters
        })

        return error_info

    async def _handle_unknown_error(self,
                                     step: WorkflowStep,
                                     error_info: dict) -> dict:
        """处理未知错误"""

        error_info["recovery_actions"].append({
            "action": "log_and_continue",
            "log_level": "error",
            "message": f"未知错误: {error_info['error_message']}"
        })

        return error_info

    def should_continue_workflow(self, error_info: dict) -> bool:
        """判断工作流是否应该继续"""

        critical_steps = [
            "feedder.fetch_feeds",
            "zotero.get_metadata"
        ]

        tool_path = f"{error_info['step']}.{error_info['step']}"

        # 如果是关键步骤失败，不继续
        if tool_path in critical_steps:
            return False

        # 检查恢复动作
        for action in error_info.get("recovery_actions", []):
            if action.get("action") in ["fallback", "retry"]:
                return True

        return False
```

### 6.3 数据一致性保证

```python
class ConflictResolver:
    """冲突解决器"""

    def resolve_sync_conflict(self,
                               zotero_item: ZoteroItem,
                               logseq_page: LogseqPage) -> dict:
        """解决Zotero和Logseq之间的同步冲突"""

        zotero_ts = datetime.fromisoformat(zotero_item.date_modified)
        logseq_ts = datetime.fromisoformat(logseq_page.updated_at)

        if zotero_ts > logseq_ts:
            # Zotero更新，覆盖Logseq
            return {
                "action": "sync_zotero_to_logseq",
                "reason": "Zotero元数据更新",
                "timestamp": zotero_ts.isoformat()
            }

        elif logseq_ts > zotero_ts:
            # Logseq更新，保留副本
            return {
                "action": "create_conflict_copy",
                "reason": "Logseq笔记有用户修改",
                "timestamp": logseq_ts.isoformat(),
                "backup_page": f"{logseq_page.page_name}_backup"
            }

        else:
            # 同时更新，智能合并
            return {
                "action": "merge_changes",
                "reason": "同时更新",
                "strategy": "zotero_metadata_priority"
            }

    def merge_item_and_page(self,
                            zotero_item: ZoteroItem,
                            logseq_page: LogseqPage) -> LogseqPage:
        """智能合并Zotero项目和Logseq页面"""

        # Zotero元数据优先
        merged_properties = logseq_page.properties.copy()
        merged_properties.update({
            "title": zotero_item.title,
            "authors": zotero_item.authors,
            "year": zotero_item.year,
            "doi": zotero_item.doi,
            "zotero_key": zotero_item.item_key
        })

        # 保留Logseq的修改
        user_sections = ["个人思考", "相关文献", "笔记"]
        preserved_blocks = [
            block for block in logseq_page.blocks
            if any(section in block.get("content", "")
                   for section in user_sections)
        ]

        return LogseqPage(
            page_name=logseq_page.page_name,
            properties=merged_properties,
            blocks=preserved_blocks,
            created_at=logseq_page.created_at,
            updated_at=datetime.now().isoformat()
        )
```

---

## 7. 测试策略

### 7.1 单元测试

```python
# test_workflows.py
import pytest
from academic_agent.orchestrator import WorkflowOrchestrator
from academic_agent.models import Intent, Workflow

class TestWorkflowDecomposition:
    """测试工作流分解"""

    def test_paper_discovery_intent(self):
        """测试论文发现意图识别"""
        query = "帮我找最近一周关于transformer的论文"
        workflow = decompose_user_query(query)

        assert workflow.intent == Intent.PAPER_DISCOVERY
        assert len(workflow.steps) > 0
        assert workflow.steps[0].tool_name == "fetch_feeds"

    def test_paper_analysis_intent(self):
        """测试论文分析意图识别"""
        query = "分析这篇论文ABCD1234"
        workflow = decompose_user_query(query)

        assert workflow.intent == Intent.PAPER_ANALYSIS
        assert any(s.tool_name == "batch_analyze_pdfs"
                   for s in workflow.steps)

    def test_literature_review_intent(self):
        """测试文献综述意图识别"""
        query = "生成深度学习在NLP领域的综述"
        workflow = decompose_user_query(query)

        assert workflow.intent == Intent.LITERATURE_REVIEW

# test_context.py
class TestConversationContext:
    """测试对话上下文"""

    def test_remember_and_recall(self):
        """测试记忆和召回"""
        ctx = ConversationContext()
        ctx.remember("research_interests", ["AI", "NLP"])

        interests = ctx.recall("research_interests")
        assert interests == ["AI", "NLP"]

    def test_active_items(self):
        """测试活跃文献管理"""
        ctx = ConversationContext()
        ctx.add_active_item("KEY123", {"title": "Test Paper"})

        item = ctx.get_active_item("KEY123")
        assert item["metadata"]["title"] == "Test Paper"

    def test_workflow_history(self):
        """测试工作流历史"""
        ctx = ConversationContext()
        workflow = Workflow(
            intent=Intent.PAPER_DISCOVERY,
            description="Test",
            steps=[]
        )
        ctx.add_workflow(workflow)

        assert len(ctx.workflow_history) == 1

# test_sync_adapter.py
class TestSyncAdapter:
    """测试同步适配器"""

    def test_page_name_generation(self):
        """测试页面名生成"""
        adapter = ZoteroLogseqSyncAdapter(None, None)
        item = ZoteroItem(
            item_key="KEY123",
            title="Test Paper",
            authors=["Author One"],
            year=2024,
            doi="10.1234/test",
            abstract="Abstract",
            tags=["AI"],
            date_added="2024-01-01",
            date_modified="2024-01-01"
        )

        page_name = adapter._generate_page_name(item)
        assert page_name == "Test Paper (2024)"

    def test_template_application(self):
        """测试模板应用"""
        adapter = ZoteroLogseqSyncAdapter(None, None)
        template = adapter.template

        # 测试模板变量替换
        content = template.format(
            title="Test",
            authors="[[Author]]",
            year="2024",
            doi="10.1234/test",
            item_key="KEY123",
            tags="[[AI]]",
            abstract="Test abstract"
        )

        assert "title:: [[Test]]" in content
        assert "zotero_key:: KEY123" in content
```

### 7.2 集成测试

```python
# test_integration.py
import pytest
from academic_agent.orchestrator import WorkflowOrchestrator, AcademicWorkflow
from academic_agent.context import ConversationContext

@pytest.mark.integration
class TestEndToEndWorkflows:
    """端到端工作流测试"""

    @pytest.fixture
    def orchestrator(self):
        """创建编排器实例"""
        context = ConversationContext()
        executor = MCPExecutor(context)
        return WorkflowOrchestrator(executor, context)

    async def test_daily_discovery_workflow(self, orchestrator):
        """测试每日论文发现工作流"""
        # 注意：需要实际的MCP服务器运行

        params = {
            "limit": 50,
            "keywords": ["transformer", "attention"]
        }

        results = await orchestrator.execute_workflow(
            AcademicWorkflow.DAILY_PAPER_DISCOVERY,
            params
        )

        assert results["papers_fetched"] >= 0
        assert results["papers_filtered"] >= 0
        assert "errors" in results

    async def test_deep_analysis_workflow(self, orchestrator):
        """测试深度分析工作流"""
        # 需要一个测试用的item_key
        params = {
            "item_key": "TEST_ITEM_KEY",
            "model": "deepseek-chat"
        }

        results = await orchestrator.execute_workflow(
            AcademicWorkflow.PAPER_DEEP_ANALYSIS,
            params
        )

        # 根据是否有该文献，结果可能不同
        assert "analysis_complete" in results or "error" in results

    async def test_knowledge_query_workflow(self, orchestrator):
        """测试知识查询工作流"""
        params = {
            "query": "attention mechanism in neural networks"
        }

        results = await orchestrator.execute_workflow(
            AcademicWorkflow.KNOWLEDGE_QUERY,
            params
        )

        assert "zotero_results" in results or "logseq_results" in results
```

### 7.3 性能测试

```python
# test_performance.py
import pytest
import time
from academic_agent.orchestrator import WorkflowOrchestrator

@pytest.mark.performance
class TestPerformance:
    """性能测试"""

    async def test_large_scale_semantic_search(self):
        """测试大规模语义搜索性能"""
        # 假设有10000篇文献的库
        start_time = time.time()

        # 执行搜索
        result = await zotero_semantic_search("deep learning", limit=20)

        duration = time.time() - start_time

        # 断言：搜索应在2秒内完成
        assert duration < 2.0
        assert len(result.get("results", [])) <= 20

    async def test_batch_analysis_performance(self):
        """测试批量分析性能"""
        papers = ["ITEM_" + str(i) for i in range(10)]

        start_time = time.time()
        results = await batch_analyze_pdfs(papers)
        duration = time.time() - start_time

        # 批量分析10篇论文应在合理时间内完成
        assert duration < 300  # 5分钟
        assert len(results) == len(papers)

    def test_context_serialization_performance(self):
        """测试上下文序列化性能"""
        ctx = ConversationContext()
        # 添加大量数据
        for i in range(1000):
            ctx.add_active_item(f"KEY_{i}", {"title": f"Paper {i}"})

        start_time = time.time()
        data = ctx.to_dict()
        duration = time.time() - start_time

        # 序列化应在100ms内完成
        assert duration < 0.1
        assert len(data["active_items"]) == 1000
```

---

## 8. 部署与配置

### 8.1 项目结构

```
academic-agent/
├── .gitmodules              # Git子模块配置
├── .env.example             # 环境变量示例
├── README.md                # 项目说明
├── pyproject.toml           # Python项目配置
├── feedder-mcp/             # 子模块
├── logseq-mcp/              # 子模块
├── zotero-mcp/              # 子模块
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI入口
│   ├── server.py            # MCP服务器入口
│   ├── orchestrator/        # Master Agent编排层
│   │   ├── __init__.py
│   │   ├── intent.py        # 意图识别
│   │   ├── workflow.py      # 工作流定义
│   │   ├── executor.py      # MCP工具执行器
│   │   └── context.py       # 上下文管理
│   ├── integration/         # 集成层
│   │   ├── __init__.py
│   │   ├── sync_adapter.py  # Zotero-Logseq同步
│   │   └── templates.py     # 学术模板
│   ├── workflows/           # 预定义工作流
│   │   ├── __init__.py
│   │   ├── discovery.py     # 论文发现
│   │   ├── analysis.py      # 论文分析
│   │   └── review.py        # 文献综述
│   └── models/              # 数据模型
│       ├── __init__.py
│       ├── intent.py
│       ├── workflow.py
│       └── context.py
├── tests/
│   ├── __init__.py
│   ├── test_workflows.py
│   ├── test_context.py
│   ├── test_integration.py
│   └── test_performance.py
├── docs/
│   ├── design/
│   │   └── 2025-02-08-academic-agent-design.md
│   └── api/
│       └── mcp-tools.md
├── configs/
│   ├── academic_template.md  # Logseq学术模板
│   └── workflows.yaml        # 工作流配置
└── scripts/
    ├── setup.sh              # 初始化脚本
    ├── install.sh            # 安装脚本
    └── test.sh               # 测试脚本
```

### 8.2 环境配置

**.env.example:**

```bash
# ====================
# academic-agent配置
# ====================

# --------------------
# Zotero配置
# --------------------
ZOTERO_LOCAL=true
ZOTERO_API_KEY=your_zotero_api_key
ZOTERO_LIBRARY_ID=your_library_id
ZOTERO_LIBRARY_TYPE=user

# --------------------
# Logseq配置
# --------------------
LOGSEQ_GRAPH_PATH=~/Documents/Logseq/MyGraph
LOGSEQ_API_ENDPOINT=http://localhost:12315
LOGSEQ_API_TOKEN=your_logseq_api_token
LOGSEQ_ENABLE_ADVANCED_QUERIES=true
LOGSEQ_ENABLE_GIT_OPERATIONS=false

# --------------------
# AI服务配置
# --------------------
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_CHAT_MODEL=gpt-4o
DEFAULT_EMBEDDING_MODEL=default

# DeepSeek (用于PDF分析)
DEEPSEEK_API_KEY=your_deepseek_key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# --------------------
# 向量数据库
# --------------------
VECTOR_DB_PATH=~/.academic-agent/vectordb
ZOTERO_EMBEDDING_MODEL=default

# --------------------
# Gmail配置（可选）
# --------------------
GMAIL_ENABLED=false
GMAIL_LABELS=Arxiv,ScienceDirect,NatureAlerts
GMAIL_TOKEN_JSON=
GMAIL_CREDENTIALS_JSON=

# --------------------
# RSS配置
# --------------------
FEEDDER_MCP_OPML=configs/feeds/academic.opml
RESEARCH_PROMPT=My research interests include deep learning, natural language processing, and attention mechanisms.

# --------------------
# academic-agent特定配置
# --------------------
ACADEMIC_AGENT_AUTO_SYNC=true
ACADEMIC_AGENT_DEFAULT_TEMPLATE=configs/academic_template.md
ACADEMIC_AGENT_MAX_PAPERS_PER_IMPORT=50
ACADEMIC_AGENT_CONTEXT_PATH=~/.academic-agent/context.json
```

### 8.3 安装方式

**本地开发安装:**

```bash
# 1. 克隆仓库（包含子模块）
git clone --recurse-submodules https://github.com/your-org/academic-agent.git
cd academic-agent

# 如果已经克隆但没有子模块：
git submodule update --init --recursive

# 2. 安装依赖
# 使用uv
uv sync

# 或使用pip
pip install -e .

# 3. 安装子模块依赖
cd feedder-mcp && uv sync && cd ..
cd logseq-mcp && uv sync && cd ..
cd zotero-mcp && uv sync && cd ..

# 4. 配置环境
cp .env.example ~/.academic-agent.env
# 编辑 ~/.academic-agent.env 填入你的API密钥

# 5. 初始化
academic-agent init --interactive

# 6. 启动MCP服务器
academic-agent serve
```

**Docker部署:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  academic-agent:
    build: .
    container_name: academic-agent
    env_file:
      - .env
    volumes:
      - ~/.academic-agent:/app/data
      - ~/Documents/Logseq/MyGraph:/logseq-graph
    ports:
      - "8080:8080"
    depends_on:
      - chromadb

  chromadb:
    image: chromadb/chroma:latest
    container_name: chromadb
    volumes:
      - ~/.academic-agent/vectordb:/chroma/chroma
    ports:
      - "8000:8000"
```

**Claude Desktop配置:**

```json
{
  "mcpServers": {
    "academic-agent": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/academic-agent",
        "run",
        "academic-agent",
        "serve"
      ],
      "env": {
        "ZOTERO_LOCAL": "true",
        "LOGSEQ_API_TOKEN": "your_token",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

---

## 9. 开发路线图

### Phase 0: 准备阶段 - 1周

**Week 1: 环境搭建**
- [x] 确认子模块已配置（feedder-mcp, logseq-mcp, zotero-mcp）
- [ ] 设置开发环境和工具链
- [ ] 创建项目结构
- [ ] 编写基础配置文件

### Phase 1: Master Agent核心 - 3周

**Week 2: 意图识别与工作流定义**
- [ ] 实现`decompose_user_query`函数
- [ ] 定义核心工作流（发现、分析、综述、查询）
- [ ] 实现`ConversationContext`类
- [ ] 单元测试覆盖

**Week 3: MCP工具执行器**
- [ ] 实现`MCPExecutor`类
- [ ] 实现与三个子模块的通信
- [ ] 错误处理和降级策略
- [ ] 集成测试

**Week 4: 基础工作流实现**
- [ ] 实现每日论文发现工作流
- [ ] 实现知识查询工作流
- [ ] 端到端测试

### Phase 2: 集成层 - 2周

**Week 5: Zotero-Logseq同步**
- [ ] 实现`ZoteroLogseqSyncAdapter`
- [ ] 学术论文模板设计
- [ ] 批量同步功能
- [ ] 冲突解决机制

**Week 6: 高级工作流**
- [ ] 实现深度分析工作流
- [ ] 实现文献综述工作流
- [ ] 工作流编排器

### Phase 3: 增强功能 - 2周

**Week 7: CLI和用户界面**
- [ ] 实现CLI命令
- [ ] 交互式配置向导
- [ ] 上下文持久化

**Week 8: 性能优化**
- [ ] 并行处理优化
- [ ] 缓存机制
- [ ] 性能测试

### Phase 4: 生产化 - 2周

**Week 9: 稳定性**
- [ ] 完整错误处理
- [ ] 日志系统
- [ ] 测试覆盖率>80%

**Week 10: 部署与文档**
- [ ] Docker支持
- [ ] 用户文档
- [ ] API文档
- [ ] 发布准备

---

## 10. 关键技术与实现要点

### 10.1 MCP子模块集成

**子模块初始化:**

```bash
# 添加子模块
git submodule add https://github.com/your-org/feedder-mcp.git feedder-mcp
git submodule add https://github.com/dailydaniel/logseq-mcp.git logseq-mcp
git submodule add https://github.com/liuchzzyy/zotero-mcp.git zotero-mcp

# 更新子模块
git submodule update --remote --merge

# 克隆时包含子模块
git clone --recurse-submodules https://github.com/your-org/academic-agent.git
```

**子模块版本管理:**

```bash
# 锁定特定版本
cd feedder-mcp
git checkout v2.2.0
cd ..

cd logseq-mcp
git checkout v2.1.1
cd ..

cd zotero-mcp
git checkout v2.2.0
cd ..

# 提交子模块更新
git add feedder-mcp logseq-mcp zotero-mcp
git commit -m "Update submodules to specific versions"
```

### 10.2 Master Agent架构

**基于MCP SDK的通信:**

```python
from mcp import ClientSession, StdioServerParameters
import asyncio

async def create_mcp_session(server_name: str,
                              server_path: str) -> ClientSession:
    """创建MCP会话"""

    server_params = StdioServerParameters(
        command="uv",
        args=[
            "--directory", server_path,
            "run", f"{server_name}-mcp"
        ]
    )

    session = ClientSession(server_params)
    await session.__aenter__()
    await session.initialize()

    return session

# 使用示例
async def main():
    feedder_session = await create_mcp_session(
        "feedder",
        "../feedder-mcp"
    )

    # 调用工具
    result = await feedder_session.call_tool(
        "fetch_feeds",
        arguments={"limit": 100}
    )

    print(result)

    await feedder_session.__aexit__(None, None, None)

asyncio.run(main())
```

### 10.3 学术模板设计

**Logseq学术论文模板:**

```markdown
---
title:: [[{title}]]
authors:: {authors_formatted}
year:: {year}
doi:: {doi}
zotero_select:: zotero://select/items/{item_key}
zotero_key:: {item_key}
publication:: {publication}
volume:: {volume}
issue:: {issue}
pages:: {pages}
status:: to-read
tags:: {tags_formatted}
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
```

### 10.4 LangGraph工作流编排

**定义状态图:**

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    query: str
    intent: str
    context: ConversationContext
    workflow: Workflow
    step_index: int
    results: Annotated[list, operator.add]
    final_response: str

def create_master_agent_graph():
    """创建Master Agent状态图"""

    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("plan_steps", plan_steps_node)
    workflow.add_node("execute_step", execute_step_node)
    workflow.add_node("check_completion", check_completion_node)
    workflow.add_node("format_response", format_response_node)

    # 定义边
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "plan_steps")
    workflow.add_edge("plan_steps", "execute_step")
    workflow.add_edge("execute_step", "check_completion")

    # 条件边
    workflow.add_conditional_edges(
        "check_completion",
        should_continue,
        {
            "continue": "execute_step",
            "format": "format_response"
        }
    )
    workflow.add_edge("format_response", END)

    return workflow.compile()
```

---

## 11. 性能优化与成本控制

### 11.1 API调用优化

**批量处理策略:**

```python
class BatchProcessor:
    """批量处理器"""

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size

    async def batch_embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量embed文本"""
        embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            response = await openai.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            embeddings.extend([e.embedding for e in response.data])

        return embeddings

    async def batch_analyze_papers(self, item_keys: List[str]) -> List[dict]:
        """批量分析论文"""
        results = []

        for i in range(0, len(item_keys), self.batch_size):
            batch = item_keys[i:i + self.batch_size]
            # 并发处理
            tasks = [self._analyze_single(key) for key in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results
```

**缓存机制:**

```python
from functools import lru_cache
import hashlib
import pickle

class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: str = "~/.academic-agent/cache"):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, max_age: int = 86400) -> Any:
        """获取缓存"""
        cache_file = self.cache_dir / f"{key}.cache"

        if not cache_file.exists():
            return None

        # 检查年龄
        age = time.time() - cache_file.stat().st_mtime
        if age > max_age:
            return None

        with open(cache_file, 'rb') as f:
            return pickle.load(f)

    def set(self, key: str, value: Any):
        """设置缓存"""
        cache_file = self.cache_dir / f"{key}.cache"
        with open(cache_file, 'wb') as f:
            pickle.dump(value, f)

    def hash_content(self, content: str) -> str:
        """哈希内容"""
        return hashlib.md5(content.encode()).hexdigest()

# 使用示例
cache = CacheManager()

def get_embedding_with_cache(text: str) -> List[float]:
    """带缓存的embed"""
    cache_key = cache.hash_content(text)
    cached = cache.get(f"embedding_{cache_key}")

    if cached:
        return cached

    # 计算embed
    embedding = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

    # 缓存
    cache.set(f"embedding_{cache_key}", embedding)
    return embedding
```

### 11.2 成本估算

**每月成本估算（假设）:**

| 操作 | 次数 | 单次成本 | 月成本 |
|------|------|----------|--------|
| 语义搜索（1000篇索引） | 1次/月 | $0.0001/篇 | $0.10 |
| 日常语义查询 | 100次/月 | $0.0001/次 | $0.01 |
| PDF深度分析 | 20篇/月 | $0.05/篇 | $1.00 |
| 关键词生成 | 30次/月 | $0.001/次 | $0.03 |
| 批注提取 | 50次/月 | $0.0005/次 | $0.025 |
| **总计** | | | **约$1.20/月** |

**优化建议:**
- 使用本地embed模型（可选）
- 批量处理降低API调用
- 智能缓存减少重复计算
- 根据使用频率调整更新策略

### 11.3 性能指标

**目标性能:**
- 论文发现工作流: < 5分钟（200篇论文）
- 深度分析工作流: < 3分钟/篇
- 语义搜索: < 2秒（10,000篇库）
- 知识查询: < 1秒

**监控指标:**
```python
@dataclass
class PerformanceMetrics:
    workflow_name: str
    start_time: datetime
    end_time: datetime
    steps_completed: int
    steps_failed: int
    api_calls_made: int
    cache_hits: int
    cache_misses: int

    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        total = self.steps_completed + self.steps_failed
        return self.steps_completed / total if total > 0 else 0

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0
```

---

## 总结

### v2.0 主要更新

**架构变化:**
- ✅ 三个MCP服务器已作为子模块存在（feedder-mcp, logseq-mcp, zotero-mcp）
- ✅ 主要开发工作转向Master Agent和集成层
- ✅ 重新设计开发路线图，聚焦集成而非从零开发

**核心功能:**
- ✅ 论文发现与导入（基于feedder-mcp）
- ✅ 文献深度分析（基于zotero-mcp）
- ✅ Zotero-Logseq双向同步
- ✅ 语义搜索和知识查询
- ✅ 主题综述生成

**技术栈:**
- ✅ MCP协议和子模块架构
- ✅ 现有MCP服务器（无需重新开发）
- ✅ Master Agent（LangGraph + MCP SDK）
- ✅ 集成层和学术工作流

**实施计划:**
- Phase 0 (1周): 准备阶段
- Phase 1 (3周): Master Agent核心
- Phase 2 (2周): 集成层
- Phase 3 (2周): 增强功能
- Phase 4 (2周): 生产化

**总计: 约10周完成MVP**

---

**下一步行动:**
1. 初始化子模块
2. 搭建Master Agent基础框架
3. 实现第一个工作流（论文发现）
4. 编写集成测试
5. 迭代改进
