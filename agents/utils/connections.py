"""Connection handling for MCP servers."""

from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from ..tools.mcp_tool import MCPTool


class MCPConnection(ABC):
    """Base class for MCP server connections."""

    def __init__(self):
        self.session = None
        self._rw_ctx = None
        self._session_ctx = None

    @abstractmethod
    async def _create_rw_context(self):
        """Create the read/write context based on connection type."""

    async def __aenter__(self):
        """Initialize MCP server connection."""
        self._rw_ctx = await self._create_rw_context()  #调用子类实现的抽象方法（MCPConnectionStdio 或 MCPConnectionSSE），返回一个异步上下文管理器对象。
        read_write = await self._rw_ctx.__aenter__()  #手动调用 __aenter__ 进入传输层上下文，真正建立底层连接（启动子进程/建立 SSE HTTP 连接）。
        read, write = read_write                      #两个异步流，read 用于接收服务器消息，write 用于向服务器发送消息。
        self._session_ctx = ClientSession(read, write)  #把底层的 read/write 流交给 MCP SDK 的 ClientSession，由它在流上实现完整的 MCP 协议（JSON-RPC 消息序列化/反序列化、请求-响应匹配等）。此时 ClientSession 还未启动。
        self.session = await self._session_ctx.__aenter__()  #同样手动调用 __aenter__，启动 ClientSession 内部的后台读取循环（开始监听 read 流上的服务器消息）。返回值就是 self.session，即激活状态的 ClientSession 实例，后续 call_tool / list_tools 都通过它发起。
        await self.session.initialize()  #按 MCP 规范发送 initialize 请求——客户端告知自己的协议版本和能力，服务器回复自己支持的能力。握手完成后连接才正式可用。
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up MCP server connection resources."""
        try:
            if self._session_ctx:
                await self._session_ctx.__aexit__(exc_type, exc_val, exc_tb)
            if self._rw_ctx:
                await self._rw_ctx.__aexit__(exc_type, exc_val, exc_tb)
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            self.session = None
            self._session_ctx = None
            self._rw_ctx = None

    async def list_tools(self) -> Any:
        """Retrieve available tools from the MCP server."""
        response = await self.session.list_tools()
        return response.tools

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """Call a tool on the MCP server with provided arguments."""
        return await self.session.call_tool(tool_name, arguments=arguments)


class MCPConnectionStdio(MCPConnection):
    """MCP connection using standard input/output."""

    def __init__(
        self, command: str, args: list[str] = [], env: dict[str, str] = None
    ):
        super().__init__()
        self.command = command
        self.args = args
        self.env = env

    async def _create_rw_context(self):
        return stdio_client(
            StdioServerParameters(
                command=self.command, args=self.args, env=self.env
            )
        )


class MCPConnectionSSE(MCPConnection):
    """MCP connection using Server-Sent Events."""

    def __init__(self, url: str, headers: dict[str, str] = None):
        super().__init__()
        self.url = url
        self.headers = headers or {}

    async def _create_rw_context(self):
        return sse_client(url=self.url, headers=self.headers)


def create_mcp_connection(config: dict[str, Any]) -> MCPConnection:
    """Factory function to create the appropriate MCP connection."""
    conn_type = config.get("type", "stdio").lower()

    if conn_type == "stdio":
        if not config.get("command"):
            raise ValueError("Command is required for STDIO connections")
        return MCPConnectionStdio(
            command=config["command"],
            args=config.get("args"),
            env=config.get("env"),
        )

    elif conn_type == "sse":
        if not config.get("url"):
            raise ValueError("URL is required for SSE connections")
        return MCPConnectionSSE(
            url=config["url"], headers=config.get("headers")
        )

    else:
        raise ValueError(f"Unsupported connection type: {conn_type}")


async def setup_mcp_connections(
    mcp_servers: list[dict[str, Any]] | None,
    stack: AsyncExitStack,
) -> list[MCPTool]:
    """Set up MCP server connections and create tool interfaces."""
    if not mcp_servers:
        return []          #mcp_servers为空，直接返回不启动任何子进程。比如WebSearchServerTool不是MCP Tool就不走

    mcp_tools = []

    for config in mcp_servers:
        try:
            connection = create_mcp_connection(config)
            await stack.enter_async_context(connection)
            tool_definitions = await connection.list_tools()  #这里的list_tools相当于激活后的ClientSesson.list_tools？

            for tool_info in tool_definitions:
                mcp_tools.append(
                    MCPTool(
                        name=tool_info.name,
                        description=tool_info.description
                        or f"MCP tool: {tool_info.name}",
                        input_schema=tool_info.inputSchema,
                        connection=connection,
                    )
                )

        except Exception as e:
            print(f"Error setting up MCP server {config}: {e}")

    print(
        f"Loaded {len(mcp_tools)} MCP tools from {len(mcp_servers)} servers."
    )
    return mcp_tools
