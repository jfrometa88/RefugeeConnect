# RefugeeConnect AI — Notas Técnicas del Proyecto
> Documento de trabajo interno · Versión 0.1 · Abril 2025  
> Base para: Hackathon Writeup · GitHub README · Artículo LinkedIn/Medium

---

## 1. Contexto y Motivación

España es uno de los principales países de acogida de refugiados y solicitantes de asilo en Europa. Las personas que llegan se enfrentan a una barrera múltiple: idioma, burocracia desconocida, dispersión geográfica de los recursos, y la urgencia de necesidades básicas (alojamiento, comida, atención médica, asesoría legal).

**RefugeeConnect AI** nace como respuesta a esa brecha de información. Es un asistente de IA conversacional y geolocalizado que ayuda a refugiados y migrantes en España a encontrar los recursos que necesitan, en su propio idioma, con pasos accionables y referencias geolocalizadas en un mapa interactivo.

El proyecto se presenta al hackathon de Google centrado en el uso de **Gemma** (modelos de lenguaje abiertos de Google), con el requisito explícito de usar Gemma como motor de IA.

---

## 2. Arquitectura General

El sistema está compuesto por dos bloques desacoplados que se comunican por API REST:

```
┌─────────────────────────────────┐        ┌──────────────────────────────────────────┐
│   FRONTEND — Dashboard Dash     │        │   BACKEND — FastAPI + Google ADK         │
│                                 │        │                                          │
│  · Mapa interactivo (OSM)       │◄──────►│  · Orquestador (LlmAgent)               │
│  · Chat conversacional          │  REST  │  · Sub-agentes especializados            │
│  · Panel de configuración       │        │  · Herramientas (tools)                  │
│  · Visor de logs/trazas         │        │  · Ollama (local) / Google AI (cloud)    │
└─────────────────────────────────┘        └──────────────────────────────────────────┘
```

### Por qué esta separación

- El dashboard Dash puede actualizarse de forma independiente al backend de agentes.
- El backend puede escalar o desplegarse en un servidor separado sin afectar la UI.
- Permite testear los agentes directamente via API sin necesidad del dashboard.

---

## 3. Stack Tecnológico

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Modelo de IA (cloud) | Gemma 3 27B via Google AI Studio | Motor LLM en modo cloud |
| Modelo de IA (local) | Gemma 2 2B via Ollama | Motor LLM en modo local/offline |
| Framework de agentes | Google ADK (Agent Development Kit) | Orquestación multi-agente |
| Conector LLM local | LiteLLM | Puente entre ADK y Ollama |
| API Backend | FastAPI + Uvicorn | Exposición de endpoints REST |
| Frontend | Plotly Dash | Dashboard interactivo con mapa |
| Mapa | OpenStreetMap (via Dash Leaflet) | Geolocalización de recursos |
| Gestión de dependencias | uv | Resolución de conflictos de dependencias |
| Logging | Logger custom | Trazabilidad de agentes |

---

## 4. Sistema Multi-Agente con Google ADK

El corazón del proyecto es un sistema de **cuatro agentes** construido sobre Google ADK:

### 4.1 Orquestador (`refugee_connect_orchestrator`)

- Es el punto de entrada para todas las conversaciones.
- Detecta el idioma del usuario y responde **siempre en ese idioma**.
- Identifica la necesidad principal (Legal, Alojamiento, Comida, Salud, Empleo).
- Decide qué sub-agente(s) invocar y en qué orden.
- Por defecto asume la ciudad de Valencia si el usuario no especifica ubicación.

### 4.2 Sub-agentes Especializados (herramientas del orquestador)

Cada sub-agente se expone al orquestador como un `AgentTool` de ADK:

**`needs_specialist_agent`**
- Busca organizaciones en la base de datos por categoría de servicio.
- Categorías: Legal, Salud, Alojamiento, Comida, Empleo.
- Herramienta: `get_services_by_category`.
- Restricción crítica: no inventa organizaciones; si no hay datos, lo dice explícitamente.

**`geolocation_agent`**
- Obtiene coordenadas lat/long de sedes de organizaciones.
- Herramienta: `get_branch_coordinates`.
- Provee datos al orquestador para actualizar el mapa del dashboard.

**`guidance_specialist_agent`**
- Explica requisitos burocráticos en lenguaje sencillo (Empadronamiento, CITA OAR, Tarjeta Roja, NIE).
- Herramienta: `check_language_support` (verifica si un centro atiende en el idioma del usuario).
- Tono: empático, paciente, sin jerga legal.

### 4.3 Flujo de routing típico

```
Usuario: "Acabo de llegar a Valencia y no tengo donde dormir, hablo árabe"
    │
    ▼
Orquestador detecta: idioma=árabe, necesidad=alojamiento, ciudad=Valencia
    │
    ├──► needs_specialist_agent → busca recursos de alojamiento en Valencia
    │
    └──► guidance_specialist_agent → explica qué documentos necesita y si hay atención en árabe
    
Orquestador sintetiza → responde en árabe con lista de recursos + pasos concretos
```

---

## 5. Configuración del Modelo (config.py)

Una de las decisiones de diseño clave es la **configurabilidad dual cloud/local** del modelo:

```python
def get_model_instance(agent_role, model_name_cloud, model_name_local, USE_LOCAL_LLM):
    if USE_LOCAL_LLM:
        os.environ.setdefault('OLLAMA_API_BASE', ollama_host)
        return LiteLlm(model=f"ollama_chat/{model_name_local}")
    else:
        return Gemini(model=model_name_cloud, retry_options=RETRY_CONFIG)
```

Esto permite:
- **Modo cloud**: Gemma 3 27B en Google AI Studio, con política de reintentos automática.
- **Modo local**: Gemma 2 2B corriendo en Ollama, sin coste y con privacidad total.
- Configurar el orquestador y los sub-agentes en modos distintos de forma independiente (ej: orquestador en cloud, sub-agentes en local).

### Lección aprendida — integración Ollama/ADK

El conector nativo `google.adk.models.ollama_llm` **no existe** en versiones actuales de ADK. La integración correcta es:
1. Usar `google.adk.models.lite_llm.LiteLlm` como wrapper.
2. Usar el prefijo `ollama_chat/` (no `ollama/`) — este último causa bucles infinitos de tool-calls.
3. Setear la variable de entorno `OLLAMA_API_BASE` además del parámetro `api_base` (LiteLLM la necesita internamente para llamadas no-generativas).

---

## 6. API Backend (FastAPI)

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Health check básico, modo activo |
| GET | `/health` | Estado real: Ollama, modelos, API key, AgentManager |
| GET | `/models/local` | Lista modelos instalados en Ollama (equivale a `ollama list`) |
| POST | `/query` | Envía mensaje al orquestador, retorna respuesta |
| GET | `/trajectory` | Trazas de razonamiento de los agentes |
| GET | `/logs` | Últimas N líneas del log del sistema |

### Decisión de diseño: configuración en servidor, no en cliente

La configuración del modelo (local vs cloud, nombre del modelo, host de Ollama) se lee de variables de entorno en el servidor. El dashboard **no envía** estos parámetros — solo envía el mensaje, el user_id y el session_id. Esto evita exponer detalles de infraestructura al cliente.

### Gestión del ciclo de vida con `lifespan`

El `RefugeeAgentManager` (que contiene todos los agentes y sesiones) se inicializa **una sola vez** al arrancar el servidor usando el patrón `lifespan` de FastAPI, no en cada request. Esto es crítico para mantener la memoria conversacional entre mensajes.

### Chequeo de Ollama en tiempo real

```python
async def check_ollama() -> dict:
    async with httpx.AsyncClient(timeout=3.0) as client:
        resp = await client.get(f"{OLLAMA_HOST}/api/tags")
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"available": True, "models": models}
```

El endpoint `/health` usa esto para reportar estado real del sistema. El endpoint `/models/local` lo expone al dashboard para mostrar un selector de modelos disponibles.

---

## 7. Gestión de Sesiones y Memoria

- Se usa `InMemorySessionService` de ADK para mantener el contexto conversacional.
- El `session_id` se deriva del `user_id` si no se provee explícitamente: `f"session_{user_id}"`.
- Esto evita el bug de privacidad de tener un `session_id` default compartido entre todos los usuarios.
- Limitación actual: `InMemorySessionService` no persiste entre reinicios del servidor — pendiente migrar a `DatabaseSessionService` para producción.

---

## 8. Gestión de Dependencias — Problema con protobuf

Durante el setup del entorno con Python 3.13 se encontró un conflicto entre `litellm` y `protobuf==5.29.x` (requerido por `google-adk` y `google-genai`).

**Solución adoptada**: migración a `uv` como gestor de dependencias.

```bash
rm -rf .venv
pip install uv
uv venv
uv add google-adk litellm python-dotenv
```

`uv` usa un SAT solver completo que resuelve el árbol de dependencias correctamente donde `pip` falla. A partir de este punto, el proyecto usa `pyproject.toml` + `uv.lock` en lugar de `requirements.txt` hardcodeado con versiones.

**Estructura de archivos de dependencias**:
- `pyproject.toml` — dependencias directas con rangos amplios.
- `uv.lock` — árbol completo resuelto y anclado (se commitea al repo).

---

## 9. Variables de Entorno (.env)

```env
# Modo de inferencia
USE_LOCAL_LLM=false          # true = Ollama local, false = Google AI Studio
USE_LOCAL_AGENTS=false       # puede diferir del orquestador

# Ollama (solo si USE_LOCAL_LLM=true)
OLLAMA_HOST=http://localhost:11434

# Google AI Studio (solo si USE_LOCAL_LLM=false)
GOOGLE_API_KEY=tu_clave_aqui
```

---

## 10. Estructura del Proyecto

```
refugee-ai/
├── pyproject.toml              # dependencias del proyecto
├── uv.lock                     # lockfile generado por uv
├── .env                        # variables de entorno (no se commitea)
├── src/
│   └── refugee_ai/
│       ├── config.py           # configuración del modelo, get_model_instance()
│       ├── IA_api.py           # FastAPI: endpoints, lifespan, chequeo Ollama
│       ├── agents/
│       │   ├── agent.py        # definición de agentes y orquestador
│       │   ├── agent_manager.py # RefugeeAgentManager, gestión de sesiones
│       │   └── tracing_plugin.py # plugin de trazas para auditoría
│       └── common/
│           ├── utils/
│           │   ├── logger.py   # setup de logging
│           │   └── tools.py    # herramientas de los agentes (funciones Python)
│           └── data/
│               └── logs/       # logs del sistema
```

---

## 11. Bugs Encontrados y Corregidos Durante el Desarrollo

| Bug | Archivo | Descripción | Corrección |
|-----|---------|-------------|------------|
| Import inexistente | `config.py` | `from google.adk.models.ollama_llm import Ollama` no existe | Cambiado a `LiteLlm` de `lite_llm` |
| Prefijo Ollama incorrecto | `config.py` | `ollama/` causa bucles infinitos de tool-calls | Cambiado a `ollama_chat/` |
| Variable de entorno Ollama | `config.py` | `api_base` como parámetro no es suficiente para LiteLLM | Añadido `os.environ.setdefault('OLLAMA_API_BASE', ...)` |
| Args insuficientes | `agent.py` | `needs_specialist_agent` llamaba `get_model_instance` con 2 args en lugar de 4 | Añadidos los 4 argumentos |
| SyntaxError | `agent.py` | Coma faltante tras `model=...` en dos `LlmAgent` | Añadidas |
| Return faltante | `agent.py` | `orchestrator_setup` no hacía return del agente | Añadido `return LlmAgent(...)` |
| Parámetro sin uso | `agent.py` | `name` en `orchestrator_setup` recibido pero ignorado | Eliminado de la firma |
| Manager por request | `IA_api.py` | `RefugeeAgentManager` se instanciaba en cada POST /query | Movido a `lifespan` |
| Config expuesta al cliente | `IA_api.py` | Parámetros LLM como query params del endpoint | Leídos de variables de entorno |
| Nombre de parámetro | `IA_api.py` | Llamada con `USER_ID=` tras renombrar a `user_id=` | Corregido |
| Health check falso | `IA_api.py` | `/health` siempre retornaba "healthy" | Chequeo real de Ollama y API key |
| Session ID compartido | `agent_manager.py` | Default `"default_refugee"` compartido entre usuarios | Derivado de `user_id` |
| Extracción de respuesta | `agent_manager.py` | Sobreescribía con cualquier evento, no solo el final | Cambiado a `event.is_final_response()` |
| CORS abierto | `IA_api.py` | `allow_origins=["*"]` | Limitado a `localhost:8050` |

---

## 12. Pendientes y Próximos Pasos

### Para el hackathon
- [ ] Implementar las herramientas reales (`get_services_by_category`, `get_branch_coordinates`, `check_language_support`) con base de datos de recursos en España.
- [ ] Construir el dashboard Dash con mapa OSM y chat integrado.
- [ ] Conectar el dashboard al endpoint `/query` y `/health`.
- [ ] Poblar la base de datos con ONGs, centros de acogida y servicios reales en Valencia y otras ciudades.
- [ ] Implementar el `tracing_plugin` para auditoría del razonamiento.

### Para producción (post-hackathon)
- [ ] Migrar `InMemorySessionService` a `DatabaseSessionService` (SQLite o PostgreSQL).
- [ ] Añadir autenticación básica a la API (al menos API key para el dashboard).
- [ ] Desplegar en Cloud Run o similar.
- [ ] Tests de integración para los agentes.
- [ ] Gestión de rate limits para el modo cloud.

---

## 13. Notas para los Textos Definitivos

### Para el Hackathon Writeup
- Enfatizar el uso de Gemma como requisito cumplido: Gemma 3 27B (cloud) y Gemma 2 2B (local via Ollama).
- Destacar el impacto social: refugiados en España, barrera idiomática, acceso a servicios.
- Resaltar la arquitectura multi-agente como solución a la complejidad del dominio.
- Mencionar la configurabilidad local/cloud como característica de privacidad (datos sensibles de personas vulnerables).

### Para el GitHub README
- Incluir diagrama de arquitectura ASCII (ya disponible en sección 2).
- Instrucciones de instalación con `uv`.
- Tabla de variables de entorno (sección 9).
- Instrucciones para arrancar en modo local (Ollama) y modo cloud.
- Capturas del dashboard (pendiente).

### Para LinkedIn/Medium
- Ángulo narrativo: "Cómo construí un asistente de IA para refugiados con Google ADK y Gemma".
- Punto técnico de interés para la audiencia: la integración ADK + Ollama + LiteLLM y los bugs no documentados que encontré.
- Punto humano: el problema real que resuelve y por qué importa.
- Sección de lecciones aprendidas (bugs de la tabla anterior son oro para esto).

---

*Documento generado como punto de partida — actualizar con cada iteración del proyecto.*
