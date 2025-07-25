import asyncio
from typing import Optional

class StreamProcessor:
    """サブエージェント用シンプルストリーム処理"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.parent_stream_queue: Optional[asyncio.Queue] = None
        self.response = ""
    
    def set_parent_queue(self, queue: Optional[asyncio.Queue]) -> None:
        self.parent_stream_queue = queue
    
    async def _notify(self, message: str, stage: str, tool_name: Optional[str] = None) -> None:
        """サブエージェント状態を通知"""
        if not self.parent_stream_queue: return
        event = {
            "event": {
                "subAgentProgress": {
                    "message": message,
                    "stage": stage
                }
            }
        }
        if tool_name:
            event["event"]["subAgentProgress"]["tool_name"] = tool_name
        await self.parent_stream_queue.put(event)
    
    async def notify_start(self) -> None:
        await self._notify(f"サブエージェント「{self.agent_name}」が呼び出されました", "start")
    
    async def notify_complete(self) -> None:
        await self._notify(f"サブエージェント「{self.agent_name}」が調査を完了しました", "complete")
    
    async def notify_tool_use(self, tool_name: str) -> None:
        await self._notify(f"サブエージェント「{self.agent_name}」がツール「{tool_name}」を実行中", "tool_use", tool_name)
    
    async def process_agent_stream(self, agent_stream) -> str:
        """エージェントストリームを処理"""
        await self.notify_start()
        
        try:
            async for event in agent_stream:
                if isinstance(event, str):
                    self.response += event
                    if self.parent_stream_queue:
                        await self.parent_stream_queue.put({
                            "event": {
                                "contentBlockDelta": {
                                    "delta": {"text": event}
                                }
                            }
                        })
                elif isinstance(event, dict) and "event" in event:
                    event_data = event["event"]
                    
                    # ツール使用の検出と通知
                    if "contentBlockStart" in event_data:
                        start_data = event_data["contentBlockStart"].get("start", {})
                        if "toolUse" in start_data:
                            tool_info = start_data["toolUse"]
                            tool_name = tool_info.get("name", "unknown")
                            await self.notify_tool_use(tool_name)
                    
                    if "contentBlockDelta" in event_data:
                        delta = event_data["contentBlockDelta"].get("delta", {})
                        if "text" in delta:
                            self.response += delta["text"]
                    if self.parent_stream_queue:
                        await self.parent_stream_queue.put(event)

            await self.notify_complete()
            return self.response
        
        except Exception:
            return f"{self.agent_name}エージェントの処理に失敗しました"
    
    async def process_query_with_context(self, query: str, context_manager, agent_factory):
        """コンテキスト管理でクエリ処理"""
        with context_manager:
            agent = agent_factory()
            agent_stream = agent.stream_async(query)
            return await self.process_agent_stream(agent_stream)