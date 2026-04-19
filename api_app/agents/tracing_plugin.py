from common.utils.logger import setup_logger
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.plugins.base_plugin import BasePlugin

class MinimalTracingPlugin(BasePlugin):
    """
    Minimal tracing plugin for RefugeeConnect AI.
    Logs agent and Gemma 4 invocations to ensure observability in the 
    multi-agent architecture.
    """

    def __init__(self) -> None:
        super().__init__(name="minimal_tracing_plugin")
        self.agent_count = 0
        self.llm_count = 0
        self.logger = setup_logger("minimal_tracing")

    async def before_agent_run(
        self, agent: BaseAgent, context: CallbackContext
    ) -> None:
        """
        Triggered before an agent starts processing.
        Standardizes 'before_agent_run' instead of 'callback' nomenclature.
        """
        self.agent_count += 1
        # In ADK, metadata is often inside context.metadata
        session_id = context.metadata.get('session_id', 'unknown') if context.metadata else 'unknown'
        
        self.logger.info(
            f"🔍 [TRACE] Agent '{agent.name}' started | "
            f"Invocations: {self.agent_count} | Session: {session_id}"
        )

    async def before_llm_run(
        self, llm_request: LlmRequest, context: CallbackContext
    ) -> None:
        """
        Triggered before a request is sent to Gemma 4 (via Ollama or API).
        Standardizes 'before_llm_run' nomenclature.
        """
        self.llm_count += 1
        model_name = getattr(llm_request, 'model', 'Gemma-4')
        
        # Log the first prompt message for better debugging of the Orchestrator's plan
        last_msg = ""
        if llm_request.messages:
            last_msg = llm_request.messages[-1].content[:50] + "..."
            
        self.logger.info(
            f"🧠 [TRACE] LLM Request #{self.llm_count} | "
            f"Model: {model_name} | Prompt: {last_msg}"
        )

    def get_stats(self) -> dict:
        """Returns session statistics for the Dashboard."""
        return {
            "agent_invocations": self.agent_count,
            "llm_requests": self.llm_count,
            "status": "active"
        }

# Global instance for the FastAPI app
tracing_plugin = MinimalTracingPlugin()