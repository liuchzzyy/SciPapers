import pytest
from pathlib import Path
from src.orchestrator.mcp_client import MCPClientManager


def skip_if_no_submodule(submodule_name: str):
    """Skip test if submodule not available"""
    path = Path(__file__).parent.parent.parent / f"{submodule_name}-mcp"
    return pytest.mark.skipif(
        not path.exists(),
        reason=f"{submodule_name}-mcp submodule not found",
    )


skip_feedder = skip_if_no_submodule("feedder")
skip_zotero = skip_if_no_submodule("zotero")
skip_logseq = skip_if_no_submodule("logseq")


def test_manager_creation():
    """Test MCPClientManager can be instantiated"""
    manager = MCPClientManager()
    assert manager.base_path.exists()
    assert len(manager.clients) == 0


def test_manager_resolves_submodule_paths():
    """Test that manager correctly resolves MCP server paths"""
    manager = MCPClientManager()
    feedder_path = manager.base_path / "feedder-mcp"
    assert feedder_path.exists()


@pytest.mark.integration
@pytest.mark.asyncio
@skip_feedder
async def test_create_feedder_client():
    async with MCPClientManager() as manager:
        client = await manager.get_client("feedder")
        assert client is not None
        assert client.server_name == "feedder"


@pytest.mark.integration
@pytest.mark.asyncio
@skip_zotero
async def test_create_zotero_client():
    async with MCPClientManager() as manager:
        client = await manager.get_client("zotero")
        assert client is not None


@pytest.mark.integration
@pytest.mark.asyncio
@skip_logseq
async def test_create_logseq_client():
    async with MCPClientManager() as manager:
        client = await manager.get_client("logseq")
        assert client is not None


@pytest.mark.integration
@pytest.mark.asyncio
@skip_feedder
async def test_execute_feedder_tool():
    async with MCPClientManager() as manager:
        result = await manager.execute_tool(
            "feedder", "generate_keywords", {"topic": "transformer"}
        )
        assert "status" in result
        assert result["status"] in ["success", "error"]
