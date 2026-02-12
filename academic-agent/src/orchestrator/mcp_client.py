from typing import Dict, Any, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path


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
                "server": self.server_name,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "server": self.server_name,
                "tool": tool_name,
            }

    async def list_tools(self):
        """List available tools on this server"""
        result = await self.session.list_tools()
        return [t.name for t in result.tools]


class MCPClientManager:
    """Manages connections to MCP servers"""

    def __init__(self, base_path: Optional[str] = None):
        if base_path:
            self.base_path = Path(base_path).resolve()
        else:
            self.base_path = Path(__file__).parent.parent.parent.parent.resolve()
        self.clients: Dict[str, MCPClient] = {}
        self._exit_stack = AsyncExitStack()

    async def __aenter__(self):
        await self._exit_stack.__aenter__()
        return self

    async def __aexit__(self, *exc):
        await self.close_all()
        await self._exit_stack.__aexit__(*exc)

    async def get_client(self, server_name: str) -> MCPClient:
        """Get or create client for server"""
        if server_name in self.clients:
            return self.clients[server_name]

        server_path = self.base_path / f"{server_name}-mcp"

        if not server_path.exists():
            raise FileNotFoundError(f"MCP server not found: {server_path}")

        server_params = StdioServerParameters(
            command="uv",
            args=["--directory", str(server_path), "run", f"{server_name}-mcp"],
            env=None,
        )

        # Use stdio_client context manager via exit stack
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        session = ClientSession(read_stream, write_stream)
        await session.initialize()

        client = MCPClient(server_name, str(server_path), session)
        self.clients[server_name] = client

        return client

    async def execute_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute tool on specific MCP server"""
        client = await self.get_client(server_name)
        return await client.call_tool(tool_name, arguments)

    async def close_all(self) -> None:
        """Close all MCP sessions"""
        self.clients.clear()
