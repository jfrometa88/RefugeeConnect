RefugeeConnect — Registro de cambios sesión 2
Optimización de prompts para compatibilidad cloud/local
Se reescribieron todos los prompts del sistema eliminando markdown interno (headers ###, negritas **) dentro de los instruction de los agentes. Los modelos pequeños interpretan ese formato como contenido a generar en lugar de estructura a seguir, causando respuestas verbosas y comportamiento errático.
Se sustituyó el formato de estados con letras (STATE A, STATE B) por estados numerados (STATE 1, STATE 2) por mayor fiabilidad en modelos pequeños con lógica condicional.
Se añadió la marca explícita "YOUR RESPONSE ENDS HERE" al final de cada estado terminal. Es la señal de parada más efectiva documentada para modelos pequeños, evita que el modelo continúe generando y termine invocando herramientas innecesariamente.
Se convirtieron todos los instruction de string multilínea con triple comilla a concatenación con paréntesis y saltos de línea explícitos \n. Más predecible en el parsing interno de ADK.

Ciudad por defecto: Valencia
Se añadió Valencia como ciudad por defecto en dos niveles: en el instruction del orquestador como regla general, y en el instruction de needs_specialist_agent como comportamiento específico de la búsqueda. La duplicación es intencionada para que el modelo pequeño lo encuentre en el contexto más cercano a la tarea.

Corrección de bucles entre agentes
Se identificó que el bucle principal ocurría porque get_rights estaba definido como una regla separada al final del prompt del orquestador, y el modelo lo interpretaba como prerequisito antes de responder en lugar de como paso final. Se integró get_rights dentro de cada rama del STATE 3, tanto en el caso de fallo (3a) como en el de éxito (3b), como paso explícito con orden definido.
Se eliminó la lógica de proximidad de ramas del geolocation_agent. Era demasiado compleja para modelos pequeños y generaba llamadas adicionales a la herramienta intentando resolver la ambigüedad.
Se añadió la regla "Never call a tool more than once per state" en el orquestador para cortar reintentos silenciosos.

Corrección de SafeAgentTool
La implementación original solo convertía a string cuando el resultado era un dict. Se amplió para forzar str() en cualquier tipo de retorno y devolver la cadena "NO_RESPONSE" cuando el resultado es None. Los retornos None eran una fuente silenciosa de bucles porque ADK los propagaba al orquestador sin señal de error.

Diagnóstico de compatibilidad con modelos pequeños
Se confirmó que qwen2.5-coder:3b no es viable para esta arquitectura. El proceso se congela sin error al intentar procesar el contexto completo de una interacción multi-agente en CPU sin GPU dedicada. No es un bug del código sino un problema de recursos combinado con la ausencia de timeout por defecto en Ollama.
Se documentó la escala de modelos mínimos recomendados para ejecución local en orden de viabilidad: gemma3:4b como opción preferida para testing, phi4-mini:3.8b como alternativa, mistral:7b y qwen2.5:7b como mínimos reales para orquestación estable. El objetivo de producción es gemma4 en local.
Se recomendó añadir request_timeout=60 en la configuración de LiteLLM para ejecución local y limitar max_tokens a 512 en llamadas al modelo local para reducir el contexto procesado.

Indicador de estado en el frontend Dash
Se modificó el callback update_status_indicators para manejar tres estados en lugar de dos: API offline cuando fetch_system_health devuelve None o contiene clave error, mostrando badge en color danger con texto "API OFFLINE"; modo LOCAL con badge en success; modo CLOUD con badge en info. Se añadió un estado de fallback con badge en warning para modos desconocidos.
Se modificó fetch_system_health para capturar ConnectionError y Timeout de forma explícita y devolver un dict con clave error en lugar de propagar la excepción. Se añadió timeout=3 en la llamada requests.get para evitar que el callback de Dash se bloquee indefinidamente cuando la API no responde, problema análogo al identificado con Ollama.

Corrección del estado de modo local/cloud en el health endpoint
Se identificó que USE_LOCAL_LLM era una variable de módulo leída una vez al arrancar, por lo que el endpoint /health siempre devolvía el valor inicial ignorando los cambios en tiempo de ejecución.
Se introdujo un objeto RuntimeConfig como singleton en memoria usando dataclass de Python. Almacena el estado mutable del sistema, inicializado desde la variable de entorno pero modificable en tiempo de ejecución. El endpoint /health lee de runtime_config.use_local_llm en lugar de la variable de módulo. El endpoint de cambio de modo escribe en runtime_config.use_local_llm. Cualquier módulo que importe runtime_config ve el mismo estado mientras el proceso FastAPI esté activo. No requiere base de datos ni sistema externo de estado.