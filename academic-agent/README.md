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
│  Master Agent (MCP)  │
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

Create a copy of `.env.example` and configure with your API keys:

```bash
cp .env.example ~/.academic-agent.env
# Edit with your settings
```

Required configuration:
- **Zotero**: API key, library ID (or local=true)
- **Logseq**: API token, graph path
- **AI Services**: OpenAI API key (for embeddings and chat)
- **Feedder**: OPML file path for RSS feeds
- **Research Prompt**: Your research interests for AI filtering

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
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Type check
uv run mypy src
```

## Project Structure

```
academic-agent/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── server.py            # MCP server entry
│   ├── orchestrator/        # Master Agent logic
│   │   ├── mcp_client.py
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── graph.py
│   │   └── nodes.py
│   ├── integration/          # Zotero-Logseq sync
│   │   ├── sync_adapter.py
│   │   └── templates.py
│   ├── workflows/            # Workflow definitions
│   └── models/             # Data models
├── tests/
├── docs/
│   ├── design/
│   └── plans/
├── .prompts/               # Subagent prompts
├── pyproject.toml
└── README.md
```

## License

MIT
