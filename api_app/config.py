import os
import httpx
from common.utils.logger import setup_logger
from dotenv import load_dotenv
from google.genai import types
from google.adk.models import Gemini
from google.adk.models.lite_llm import LiteLlm 

# 1. Configurar Logger
logger = setup_logger('refugee_ai.config')
load_dotenv()

GEMMA_MODEL_NAME_local=os.getenv("GEMMA_MODEL_NAME_local", "qwen2.5-coder:3b")
GEMMA_MODEL_NAME_cloud=os.getenv("GEMMA_MODEL_NAME_cloud", "gemma-4-31b-it")

# 4. Configuración de reintentos (Políticas de resiliencia)
RETRY_CONFIG = types.HttpRetryOptions(
    attempts=4,
    exp_base=2,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)


def check_backend_availability(is_local: bool) -> bool:
    """
    Verifica si el backend de inferencia seleccionado está disponible.
    En local: Verifica que Ollama responda y tenga el modelo cargado.
    En cloud: Verifica que exista la API KEY.
    """
    if is_local:
        ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        try:
            # verificar que el servicio de Ollama está corriendo
            response = httpx.get(f"{ollama_host}/api/tags", timeout=2.0)
            if response.status_code != 200:
                logger.error(f"Ollama respondió con error: {response.status_code}")
                return False
            
            #Verificar si el modelo de Gemma 4 está en la lista, como advertencia que es el modelo meta del proyecto
            models = [m['name'] for m in response.json().get('models', [])]
            if not any(GEMMA_MODEL_NAME_local in m for m in models):
                logger.warning(f"Modelo {GEMMA_MODEL_NAME_local} no encontrado en Ollama.")
                # por ahora solo dejamos en el log
            return True
        except (httpx.ConnectError, httpx.TimeoutException):
            logger.error(f"No se pudo conectar a Ollama en {ollama_host}. ¿Está iniciado?")
            return False
    else:
        #validación simple para modo Cloud
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key or len(api_key) < 10:
            logger.error("GEMINI_API_KEY no configurada o inválida.")
            return False
        return True

def get_model_instance(agent_role: str = "general",
                       model_name_cloud: str = None,
                       model_name_local: str = None,
                       USE_LOCAL_LLM: bool = False
                       ):
    """Inicialización Dinámica del Modelo de LLM."""
    #asegurar valores por defecto
    model_name_cloud = model_name_cloud or GEMMA_MODEL_NAME_cloud
    model_name_local = model_name_local or GEMMA_MODEL_NAME_local
    
    try:
        if USE_LOCAL_LLM:
            ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
            os.environ['OLLAMA_API_BASE'] = ollama_host

            logger.info(
                f"[{agent_role}] Inicializando MODO LOCAL (Ollama) "
                f"→ modelo: {model_name_local}"
            )
            #limpiamos el modelo de prefijo ollama:
            model_clean = model_name_local.replace("ollama:", "")
            return LiteLlm(model=f"ollama_chat/{model_clean}")
        else:
            #intentamos obtener la api key 
            google_api_key = os.getenv('GEMINI_API_KEY')
            
            if not google_api_key:
                #si no es local y no hay api key, si es un error
                logger.error(f"[{agent_role}] ERROR: No hay API KEY para modo Cloud.")
                return None

            logger.info(f"[{agent_role}] Inicializando MODO CLOUD → {model_name_cloud}")
            return Gemini(
                model=model_name_cloud,
                api_key=google_api_key,
                retry_options=RETRY_CONFIG
            )
    except Exception as e:
        logger.error(f"Error fatal en get_model_instance: {e}")
        return None


