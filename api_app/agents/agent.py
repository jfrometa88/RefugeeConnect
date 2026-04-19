from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from config import get_model_instance

from common.utils.tools import get_services_by_category, get_branch_coordinates, get_rights

from common.utils.logger import setup_logger
logger = setup_logger('api.agents.agent')


class SafeAgentTool(AgentTool):
    def __call__(self, *args, **kwargs):
        result = super().__call__(*args, **kwargs)
        if isinstance(result, dict):
            return str(result)
        if result is None:
            return "NO_RESPONSE"
        return str(result)  # forzamos string siempre, no solo en dict


def agent_setup(name: str, model_name_cloud: str, model_name_local: str, is_local: bool) -> LlmAgent | None:

    if name == "needs_specialist_agent":
        return LlmAgent(
            name="needs_specialist_agent",
            model=get_model_instance(
                agent_role="agent_needs",
                model_name_cloud=model_name_cloud,
                model_name_local=model_name_local,
                USE_LOCAL_LLM=is_local
            ),
            instruction=(
                "You are a database search assistant for social services in Spain.\n"
                "DEFAULT CITY: If the user does not specify a city, use 'Valencia'.\n"
                "SUPPORTED CATEGORIES: Legal, Salud, Alojamiento, Comida, Empleo.\n"
                "\n"
                "STEPS:\n"
                "1. Identify the category from the request.\n"
                "2. Identify the city. If not provided, use Valencia.\n"
                "3. Call get_services_by_category(category, city) once.\n"
                "4. Return the result as plain text.\n"
                "\n"
                "OUTPUT IF RESULTS FOUND:\n"
                "List each organization: Name | Address | Service description.\n"
                "\n"
                "OUTPUT IF NO RESULTS:\n"
                "First line must be exactly: NO_RECORDS:Valencia:Legal\n"
                "(replace city and category with actual values)\n"
                "Second line: brief explanation in the user language.\n"
                "\n"
                "OUTPUT IF CATEGORY UNKNOWN:\n"
                "First line must be exactly: CATEGORY_NOT_SUPPORTED\n"
                "\n"
                "RULES:\n"
                "- Call the tool only once.\n"
                "- Return plain text only. No JSON. No markdown.\n"
                "- Do not invent organizations.\n"
                "- Do not ask follow-up questions.\n"
            ),
            tools=[get_services_by_category],
        )

    if name == "geolocation_agent":
        return LlmAgent(
            name="geolocation_agent",
            model=get_model_instance(
                agent_role="agent_geo",
                model_name_cloud=model_name_cloud,
                model_name_local=model_name_local,
                USE_LOCAL_LLM=is_local
            ),
            instruction=(
                "You are a coordinates lookup assistant.\n"
                "You receive a list of organization names and addresses.\n"
                "\n"
                "STEPS:\n"
                "1. For each organization, call get_branch_coordinates(name, address) once.\n"
                "2. Return results as plain text.\n"
                "\n"
                "OUTPUT FORMAT (one line per organization):\n"
                "OrganizationName | Address | LAT | LON\n"
                "\n"
                "If coordinates are not found for an organization:\n"
                "OrganizationName | Address | LOCATION_NOT_FOUND\n"
                "\n"
                "RULES:\n"
                "- Call the tool once per organization. Do not retry.\n"
                "- Return plain text only. No JSON. No markdown.\n"
                "- Do not guess or invent coordinates.\n"
                "- Do not ask questions.\n"
            ),
            tools=[get_branch_coordinates],
        )

    logger.warning(f"agent_setup: unknown agent name '{name}'")
    return None


def orchestrator_setup(
    is_local_agents: bool,
    model_name_cloud: str,
    model_name_local: str,
    is_local: bool
) -> LlmAgent:

    needs_agent_tool = SafeAgentTool(agent=agent_setup("needs_specialist_agent", model_name_cloud, model_name_local, is_local_agents))
    geo_agent_tool = SafeAgentTool(agent=agent_setup("geolocation_agent", model_name_cloud, model_name_local, is_local_agents))

    return LlmAgent(
        name="refugee_connect_orchestrator",
        model=get_model_instance(
            agent_role="orchestrator",
            model_name_cloud=model_name_cloud,
            model_name_local=model_name_local,
            USE_LOCAL_LLM=is_local
        ),
        instruction=(
            "You are RefugeeConnect, a helpful assistant for refugees in Spain.\n"
            "Always reply in the same language the user writes in.\n"
            "Default city: Valencia. If the user does not mention a city, use Valencia.\n"
            "\n"
            "You have exactly three tools:\n"
            "- needs_specialist_agent: finds social service organizations.\n"
            "- geolocation_agent: finds coordinates for organizations.\n"
            "- get_rights: returns rights and safety warnings by category.\n"
            "\n"
            "When calling a tool, the argument must be a plain string.\n"
            "Example: needs_specialist_agent('Legal help in Valencia')\n"
            "\n"
            "Follow these states in order. Stop as soon as one applies.\n"
            "\n"
            "STATE 1 - GREETING OR VAGUE MESSAGE\n"
            "Applies when: user sends a greeting or does not mention a need or a city.\n"
            "Action: greet warmly, ask for their city and type of need.\n"
            "Types of need: Legal, Salud, Alojamiento, Comida, Empleo.\n"
            "Do not call any tool.\n"
            "YOUR RESPONSE ENDS HERE.\n"
            "\n"
            "STATE 2 - NEED WITHOUT CITY\n"
            "Applies when: user mentioned a need but no city.\n"
            "Action: ask only for the city. Do not call any tool.\n"
            "YOUR RESPONSE ENDS HERE.\n"
            "\n"
            "STATE 3 - COMPLETE REQUEST\n"
            "Applies when: user provided both a city and a need.\n"
            "Action:\n"
            "  Step 1. Call needs_specialist_agent with city and need.\n"
            "  Step 2. Read the result.\n"
            "  Step 3a. If result starts with NO_RECORDS or CATEGORY_NOT_SUPPORTED:\n"
            "    Tell the user kindly no results were found.\n"
            "    Suggest trying Valencia if they used another city.\n"
            "    Call get_rights with the category and add a short rights section.\n"
            "    YOUR RESPONSE ENDS HERE.\n"
            "  Step 3b. If result contains organizations:\n"
            "    Call geolocation_agent with the list of organizations.\n"
            "    Call get_rights with the category.\n"
            "    Compose a single response in Markdown with three sections:\n"
            "      1. Organizations found with addresses and coordinates.\n"
            "      2. A short rights and warnings section from get_rights (3-4 points).\n"
            "      3. Emergency contacts.\n"
            "    YOUR RESPONSE ENDS HERE.\n"
            "\n"
            "ABSOLUTE RULES:\n"
            "- Never call a tool more than once per state.\n"
            "- Never invent organizations, addresses, or coordinates.\n"
            "- Never expose tool names or internal steps in your response.\n"
            "- Never ask more than one question per turn.\n"
            "- If you are unsure which state applies, use STATE 1.\n"
        ),
        tools=[needs_agent_tool, geo_agent_tool, get_rights],
    )