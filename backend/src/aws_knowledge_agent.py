import asyncio
from typing import Optional
from strands import Agent, tool
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from .stream_processor import StreamProcessor

class AWSKnowledgeAgentManager:
    """AWSナレッジエージェント管理クラス"""
    
    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.stream_processor = StreamProcessor("AWSナレッジ")
        self._initialize_mcp_client()
    
    def _initialize_mcp_client(self) -> None:
        """MCPクライアント初期化"""
        try:
            self.mcp_client = MCPClient(
                lambda: streamablehttp_client("https://knowledge-mcp.global.api.aws")
            )
        except Exception:
            self.mcp_client = None
    
    def set_parent_stream_queue(self, queue: Optional[asyncio.Queue]) -> None:
        self.stream_processor.set_parent_queue(queue)
    
    def create_agent(self) -> Agent:
        """AWSナレッジエージェント作成"""
        if not self.mcp_client:
            raise RuntimeError("AWS Knowledge MCP client is not available")
        return Agent(
            model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            tools=self.mcp_client.list_tools_sync()
        )
    
    async def process_query(self, query: str) -> str:
        """AWSナレッジクエリ処理"""
        if not self.mcp_client: return "処理に失敗しました"
        return await self.stream_processor.process_query_with_context(
            query, self.mcp_client, self.create_agent
        )

# グローバルインスタンス
_knowledge_manager = AWSKnowledgeAgentManager()

def set_parent_stream_queue(queue: Optional[asyncio.Queue]) -> None:
    _knowledge_manager.set_parent_stream_queue(queue)

@tool
async def aws_knowledge_agent(query: str) -> str:
    """AWS知識ベースエージェント"""
    return await _knowledge_manager.process_query(query)