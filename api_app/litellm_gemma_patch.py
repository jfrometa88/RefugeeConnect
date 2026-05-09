# api_app/patches/litellm_gemma_patch.py
"""
Monkey-patch para modelos que esperan 'tool_responses' en lugar de 'tool'.
Se parchea _get_completion_inputs, que es la función pública que ensambla
los mensajes finales — mucho más estable que parchear _content_to_message_param.
"""
from common.utils.logger import setup_logger

logger = setup_logger('api.litellm_gemma_patch')

TARGET_MODELS = {"gemma4"}

def apply():
    try:
        import google.adk.models.lite_llm as _mod

        _original = _mod._get_completion_inputs

        async def _patched_get_completion_inputs(llm_request, model: str):
            messages, tools, response_format, generation_params = \
                await _original(llm_request, model)

            model_lower = model.lower()
            if any(t in model_lower for t in TARGET_MODELS):
                for msg in messages:
                    if isinstance(msg, dict) and msg.get("role") == "tool":
                        msg["role"] = "tool_responses"
                        logger.debug(
                            "[patch] role 'tool' → 'tool_responses' "
                            "para modelo '%s'", model
                        )

            return messages, tools, response_format, generation_params

        _mod._get_completion_inputs = _patched_get_completion_inputs
        logger.info("[patch] litellm_gemma_patch aplicado sobre "
                    "_get_completion_inputs para modelos: %s", TARGET_MODELS)

    except AttributeError:
        logger.warning(
            "[patch] '_get_completion_inputs' no encontrada en "
            "google.adk.models.lite_llm — revisa la versión de ADK."
        )
    except Exception as e:
        logger.error("[patch] Error aplicando litellm_gemma_patch: %s",
                     e, exc_info=True)

apply()