# RefugeeConnect AI — Notas Técnicas del Proyecto
> Documento de trabajo interno · Versión 0.2 · Abril 2025  
> Base para: Hackathon Writeup · GitHub README · Artículo LinkedIn/Medium  
> **Actualización sobre v0.1**: frontend construido y probado, tools implementadas, bugs de producción resueltos, limitaciones de hardware documentadas.

---

## RESUMEN DE CAMBIOS DESDE v0.1

Esta sección documenta todo lo desarrollado después de la versión anterior del documento. El resto de las secciones se actualiza en consecuencia.

### Lo que estaba pendiente en v0.1 y ahora está hecho
- ✅ Dashboard Dash construido con mapa interactivo, chat y panel de configuración
- ✅ Tools reales implementadas con consultas SQLite (`get_services_by_category`, `get_branch_coordinates`, `check_language_support`, `get_map_resources`)
- ✅ Endpoint `/map/resources` para alimentar el mapa directamente desde BD
- ✅ Endpoint `/config/toggle` para hot-swap del proveedor LLM en caliente
- ✅ Sistema probado end-to-end con Gemma 4 en Google AI Studio
- ✅ Marcadores del mapa funcionales con popup de información completa
- ✅ Aviso no bloqueante de disponibilidad de Gemma 4 en Ollama

### Nuevos problemas encontrados y resueltos
- 🐛 Iconos de mapa rotos (SVG inline rechazado por Leaflet) → resuelto con `dl.CircleMarker`
- 🐛 LLM exponiendo razonamiento interno al usuario → resuelto con instrucción explícita en prompt + filtro de postprocesado
- 🐛 `build_status_badge` llamado a nivel de módulo antes de que Dash esté inicializado → resuelto con callback dedicado
- 🐛 Error `_leaflet_events` e `iconUrl not set` en Leaflet → resuelto eliminando DivIcon y usando CircleMarker nativo
- 🐛 Código muerto en `build_marker` (bloque after `return`) → eliminado
- 🐛 `except` duplicado en `agent_manager.py` (segundo bloque nunca alcanzado) → eliminado

### Limitación de hardware documentada (crítica para el hackathon)
Gemma 4 (31B parámetros) no cabe en la máquina de desarrollo. Gemma 2 y versiones anteriores no soportan arquitecturas de agentes con tool-calling. El modelo local funcional para desarrollo es **Qwen 2.5** (base, no coder), pero presenta bugs de serialización con ADK+LiteLLM. La solución al bug de tool-calling local se documenta en la sección 5.

---

## 1. Contexto y Motivación

España es uno de los principales países de acogida de refugiados y solicitantes de asilo en Europa. Las personas que llegan se enfrentan a una barrera múltiple: idioma, burocracia desconocida, dispersión geográfica de los recursos, y la urgencia de necesidades básicas (alojamiento, comida, atención médica, asesoría legal).

**RefugeeConnect AI** nace como respuesta a esa brecha de información. Es un asistente de IA conversacional y geolocalizado que ayuda a refugiados y migrantes en España a encontrar los recursos que necesitan, en su propio idioma, con pasos accionables y referencias geolocalizadas en un mapa interactivo.

El proyecto se presenta al hackathon de Google centrado en el uso de **Gemma** (modelos de lenguaje abiertos de Google), con el requisito explícito de usar Gemma como motor de IA. El sistema usa **Gemma 4** via Google AI Studio en modo cloud (probado y funcional), y está diseñado para soportar también modelos locales via Ollama cuando el hardware lo permite.

---

## 2. Arquitectura General

```
┌─────────────────────────────────────────┐        ┌──────────────────────────────────────────┐
│   FRONTEND — Dashboard Plotly Dash      │        │   BACKEND — FastAPI + Google ADK         │
│                                         │        │                                          │
│  · Mapa interactivo (CartoDB/OSM)       │◄──────►│  · Orquestador (LlmAgent)               │
│  · Chat conversacional multilingüe      │  REST  │  · 3 Sub-agentes especializados          │
│  · Filtros por categoría de servicio    │        │  · 4 Tools SQLite                        │
│  · Panel configuración LLM (hot-swap)   │        │  · Gemma 4 cloud / Qwen local            │
│  · Badge de estado del sistema          │        │  · InMemorySessionService                │
│  · Aviso disponibilidad Gemma 4         │        │  · TracingPlugin                         │
│  · Mapa carga directo desde SQLite      │        │                                          │
└─────────────────────────────────────────┘        └──────────────────────────────────────────┘
         │                                                        │
         │ fetch directo (mapa)                                   │
         ▼                                                        ▼
  ┌─────────────┐                                     ┌─────────────────────┐
  │  SQLite     │◄────────────────────────────────────│  SQLite             │
  │  (mapa)     │                                     │  (agentes/tools)    │
  └─────────────┘                                     └─────────────────────┘
```

### Decisión de diseño clave: el mapa no pasa por los LLMs

El mapa lee SQLite directamente desde el frontend, sin pasar por la API ni por los agentes. Esto significa que el mapa carga aunque el backend esté caído o los agentes estén procesando una consulta larga. El chat sí pasa por los agentes, que es donde está la inteligencia conversacional.

---

## 3. Stack Tecnológico (actualizado)

| Capa | Tecnología | Rol |
|------|-----------|-----|
| Modelo IA cloud | Gemma 4 (31B) via Google AI Studio | Motor LLM principal — probado y funcional |
| Modelo IA local (objetivo) | Gemma 4 via Ollama | Requiere ≥16GB RAM — no disponible en dev |
| Modelo IA local (desarrollo) | Qwen 2.5:7B via Ollama | Workaround funcional con limitaciones |
| Framework de agentes | Google ADK | Orquestación multi-agente |
| Conector LLM local | LiteLLM (provider `openai/`) | Puente ADK↔Ollama, evita bug de serialización |
| API Backend | FastAPI + Uvicorn | Endpoints REST + lifespan |
| Frontend | Plotly Dash + dbc | Dashboard con mapa y chat |
| Mapa | Dash Leaflet + CartoDB Light | Visualización geoespacial |
| BD | SQLite | Recursos humanitarios por ciudad/categoría |
| Gestor dependencias | uv | SAT solver para conflictos protobuf |
| Logging | Logger custom | Trazabilidad de agentes |

---

## 4. Sistema Multi-Agente con Google ADK

Cuatro agentes, sin cambios estructurales respecto a v0.1. Las mejoras están en los prompts.

### 4.1 Prompt engineering — lecciones de producción

Durante las pruebas con Gemma 4 en cloud se detectó que el modelo exponía su razonamiento interno (chain-of-thought) en la respuesta al usuario. Ejemplo real observado:

```
The user is asking "can you speak french?". The system instructions explicitly state:
"**CRITICAL RULE: Always respond in the SAME LANGUAGE used by the user.**"
Plan: 1. Confirm in English that I can speak French. 2. Invite them to communicate in French.
```

**Solución aplicada en el prompt del orquestador:**
```
**OUTPUT FORMAT — CRITICAL:**
- Never expose your internal reasoning, plans, or intermediate steps to the user.
- Never write lines like "Plan:", "Step 1:", "I will now call...", or "The user is asking...".
- Your response to the user must be ONLY the final, helpful answer.
- Internal tool calls and reasoning happen silently.
```

**Solución adicional en `agent_manager.py`** — filtro de postprocesado como cinturón de seguridad:
```python
def _clean_response(self, text: str) -> str:
    patterns = [
        r"^(The user is asking|Plan:|Step \d+:|I will now|My plan).*?\n\n",
        r"^\*\*Plan:\*\*.*?\n\n",
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()
```

### 4.2 Reglas operacionales añadidas al orquestador

Para evitar bucles de razonamiento y llamadas redundantes a sub-agentes:

```
OPERATIONAL RULES (CRITICAL):
1. ONE-STEP RESOLUTION: Una vez que recibes info de un agente especialista, sintetiza inmediatamente.
2. NO REPETITION: No llames al mismo agente dos veces para el mismo request.
3. TERMINATION SIGNAL: Cuando tienes la info final, responde y PARA.
4. HANDLING ERRORS: Si un agente falla, informa al usuario en lugar de reintentar indefinidamente.
```

---

## 5. Integración Local: Limitaciones y Soluciones

Esta sección documenta los obstáculos reales encontrados con el modo local, que son relevantes tanto para el writeup técnico como para el artículo.

### 5.1 Gemma 4 no cabe en hardware de desarrollo

- Gemma 4 31B requiere aproximadamente 20GB de VRAM/RAM para inferencia.
- Gemma 2 2B y 3B no soportan arquitecturas de tool-calling (necesario para los agentes).
- **Solución para el hackathon**: presentar la demo en modo cloud (Gemma 4 via Google AI Studio), documentar el soporte local como característica de privacidad para producción.

### 5.2 Bug de serialización ADK + LiteLLM + Ollama con tool-calling

**El error**: al devolver el resultado de una tool al modelo local, el campo `content` del mensaje se convierte en array JSON en lugar de string. La API de Ollama espera estrictamente `content: string`.

```
litellm.APIConnectionError: Ollama_chatException - 
{"error":"json: cannot unmarshal array into Go struct field 
ChatRequest.messages.content of type string"}
```

**Causa raíz**: bug conocido en ADK/LiteLLM al formatear el historial de mensajes para el endpoint `/api/chat` de Ollama cuando hay herramientas invocadas.

**Solución implementada**: cambiar el provider de `ollama_chat/` a `openai/` en LiteLLM, usando el adaptador OpenAI que serializa el historial de forma diferente y compatible con Ollama:

```python
# Antes (bug):
return LiteLlm(model=f"ollama_chat/{model_name_local}")

# Después (solución):
os.environ.setdefault('OPENAI_API_BASE', f"{ollama_host}/v1")  # /v1 obligatorio
os.environ.setdefault('OPENAI_API_KEY', 'ollama-local')
return LiteLlm(model=f"openai/{model_name_local}")
```

### 5.3 Modelo local recomendado para desarrollo

`qwen2.5:7B` (base, no `coder`) es el mejor modelo local para tool-calling con ADK según evaluaciones en la comunidad. La variante `qwen2.5-coder` está especializada en generación de código y no tiene buen rendimiento en razonamiento conversacional ni coordinación de herramientas.

```bash
ollama pull qwen2.5:7b
ollama show qwen2.5:7b  # verificar que aparece "tools" en Capabilities
```

### 5.4 Tools: devolver siempre `str`, no `dict`

Algunos modelos locales no procesan bien los resultados de tools cuando son dicts serializados. Solución adicional: todas las tools devuelven `str` (JSON serializado):

```python
def get_services_by_category(category: str, city: str = "Valencia") -> str:
    results = _query_db(category, city)
    return json.dumps(results, ensure_ascii=False)  # siempre str, nunca dict
```

---

## 6. Tools Implementadas (common/utils/tools.py)

Las cuatro tools que conectan los agentes con la base de datos SQLite:

| Tool | Usada por | Descripción |
|------|-----------|-------------|
| `get_services_by_category(category, city)` | `needs_specialist_agent` | Devuelve organizaciones por categoría y ciudad |
| `get_branch_coordinates(org_name, city)` | `geolocation_agent` | Devuelve lat/lon de una sede |
| `check_language_support(branch_address)` | `guidance_specialist_agent` | Idiomas disponibles en una sede |
| `get_map_resources(city, category)` | Endpoint `/map/resources` | Todas las sedes con coords para el mapa |

**Detalles de implementación:**
- Conexión con `row_factory = sqlite3.Row` para acceso por nombre de columna.
- Ruta a BD dinámica con `Path(__file__).resolve().parents[N]`.
- `get_map_resources` resuelve el problema N+1 de idiomas en una segunda query con `IN (placeholders)`.
- Manejo de errores que devuelve lista vacía en lugar de propagar excepciones.

---

## 7. API Backend — Endpoints (actualizado)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Health check básico, modo activo |
| GET | `/health` | Estado real: Ollama, modelos, API key, AgentManager |
| GET | `/models/local` | Lista modelos instalados en Ollama |
| POST | `/query` | Envía mensaje al orquestador, retorna respuesta |
| POST | `/config/toggle` | Hot-swap del proveedor LLM sin reiniciar el servidor |
| GET | `/trajectory` | Trazas de razonamiento de los agentes |
| GET | `/logs` | Últimas N líneas del log del sistema |
| GET | `/map/resources` | Recursos con coordenadas para el mapa (directo a SQLite) |

### Hot-swap de proveedor LLM (`/config/toggle`)

Permite cambiar entre cloud y local en caliente, sin reiniciar el servidor y preservando las sesiones de conversación:

```python
def update_provider(self, is_local_agents, is_local, model_name_cloud, model_name_local):
    new_orchestrator = orchestrator_setup(...)
    self.orchestrator = new_orchestrator
    # Runner re-instanciado reutilizando self.session_service → memoria preservada
    self.runner = Runner(agent=self.orchestrator, ..., session_service=self.session_service)
```

---

## 8. Dashboard Dash (app_new.py)

### Componentes principales

**Mapa (columna derecha, 8/12)**
- Tile layer: CartoDB Light (más limpio que OSM por defecto)
- Marcadores: `dl.CircleMarker` con radio fijo en píxeles (visible en todos los niveles de zoom)
- Popup por marcador: organización, servicio, dirección, teléfono, idiomas, requisitos
- Leyenda flotante con colores por categoría
- Filtros de categoría con feedback visual (botón activo destacado)
- Carga de datos: **SQLite directo**, independiente del backend

**Chat (columna izquierda, 4/12)**
- Burbujas diferenciadas por rol (usuario/bot)
- Indicador de carga durante respuesta del agente
- Manejo explícito de timeout (30s) y error de conexión con mensajes al usuario
- Mensaje de bienvenida en español con invitación multilingüe

**Panel de configuración (header del chat)**
- Dropdown de modelos Ollama disponibles (cargado del `/health`)
- Switch local/cloud que dispara el `/config/toggle`
- Toast de confirmación al cambiar configuración

**Header**
- Badge de estado del sistema (healthy/degraded/unavailable) actualizado dinámicamente
- Indicador del modelo activo
- Botón "Estado sistema" que abre modal con tabla completa del `/health`
- Botón "Actualizar mapa"

**Aviso de Gemma 4**
- Alert amarillo dismissable si Gemma 4 no está instalada en Ollama
- No bloqueante: el sistema sigue funcionando con cloud o con el modelo local alternativo
- Se actualiza al cargar, al pulsar "Estado sistema", y al cambiar el switch

---

## 9. Variables de Entorno (.env) — actualizado

```env
# Modo de inferencia
USE_LOCAL_LLM=false              # true = Ollama local, false = Google AI Studio
USE_LOCAL_AGENTS=false           # puede diferir del orquestador

# Modelos
GEMMA_MODEL_NAME_cloud=gemma-4-31b-it
GEMMA_MODEL_NAME_local=qwen2.5:7b    # qwen2.5:3b si RAM limitada

# Ollama
OLLAMA_HOST=http://localhost:11434
OPENAI_API_BASE=http://localhost:11434/v1  # para el provider openai/ de LiteLLM
OPENAI_API_KEY=ollama-local               # cualquier valor no vacío

# Google AI Studio
GEMINI_API_KEY=tu_clave_aqui
```

---

## 10. Bugs Encontrados y Resueltos — tabla completa (v0.1 + v0.2)

| Bug | Archivo | Descripción | Corrección |
|-----|---------|-------------|------------|
| Import inexistente | `config.py` | `ollama_llm.Ollama` no existe en ADK | Cambiado a `LiteLlm` |
| Prefijo Ollama incorrecto | `config.py` | `ollama/` causa bucles infinitos | Cambiado a `ollama_chat/` → luego a `openai/` |
| Variable entorno Ollama | `config.py` | `api_base` param insuficiente para LiteLLM | `os.environ.setdefault('OLLAMA_API_BASE', ...)` |
| Serialización tool-calling | `config.py` | Arrays en `content` rompen API Ollama | Provider `openai/` + `OPENAI_API_BASE` con `/v1` |
| Tools devuelven dict | `tools.py` | Modelos locales no procesan dict de tools | Todas las tools devuelven `json.dumps(...)` |
| Args insuficientes | `agent.py` | `get_model_instance` llamado con 2 args | Añadidos los 4 argumentos |
| SyntaxError | `agent.py` | Coma faltante tras `model=...` | Añadidas |
| Return faltante | `agent.py` | `orchestrator_setup` no retornaba | `return LlmAgent(...)` |
| Parámetro sin uso | `agent.py` | `name` en `orchestrator_setup` ignorado | Eliminado de firma |
| Except duplicado | `agent_manager.py` | Segundo `except` nunca alcanzado | Eliminado |
| Extracción de respuesta | `agent_manager.py` | Sobreescribía con cualquier evento | `event.is_final_response()` + iteración de parts |
| Razonamiento expuesto | `agent_manager.py` | Gemma 4 filtraba chain-of-thought | Instrucción en prompt + `_clean_response()` |
| Manager por request | `IA_api.py` | `RefugeeAgentManager` instanciado en cada POST | Movido a `lifespan` |
| Config expuesta al cliente | `IA_api.py` | Parámetros LLM como query params | Variables de entorno en servidor |
| Health check falso | `IA_api.py` | `/health` siempre "healthy" | Chequeo real Ollama + API key |
| CORS abierto | `IA_api.py` | `allow_origins=["*"]` | Limitado a `localhost:8050` |
| Session ID compartido | `agent_manager.py` | Default compartido entre usuarios | Derivado de `user_id` |
| `build_status_badge` en módulo | `app_new.py` | Llamada antes de inicializar Dash | Convertido a callback con Output en placeholder |
| Iconos mapa rotos | `app_new.py` | SVG inline / DivIcon rechazado por Leaflet | Reemplazado por `dl.CircleMarker` nativo |
| Error `_leaflet_events` | `app_new.py` | `dl.Marker` con dict icon mal formado | `dl.CircleMarker` elimina necesidad de icon dict |
| Código muerto en `build_marker` | `app_new.py` | Bloque `dl.Marker` after `return` | Eliminado |

---

## 11. Esquema de BD SQLite

```sql
organizations     id, name, description, website
branches          id, organization_id, city, address, latitude, longitude, local_phone
services          id, name, category  -- categorías: Legal/Salud/Alojamiento/Comida/Empleo
branch_services   branch_id, service_id, requirements
languages_served  branch_id, language_code
```

---

## 12. Pendientes para el hackathon

- [ ] Poblar BD con más recursos reales en Valencia y otras ciudades españolas
- [ ] Implementar `tracing_plugin.get_stats()` con métricas reales de los agentes
- [ ] Capturas de pantalla del dashboard para el README
- [ ] Probar flujo completo en hardware con Gemma 4 local (≥16GB RAM)
- [ ] Añadir ciudad como parámetro en el chat (actualmente hardcoded a Valencia)

### Para producción (post-hackathon)
- [ ] Migrar `InMemorySessionService` a `DatabaseSessionService`
- [ ] Autenticación básica en la API
- [ ] Despliegue en Cloud Run
- [ ] Tests de integración para los agentes
- [ ] Rate limiting para modo cloud

---

## 13. Notas para los Textos Definitivos (actualizado)

### Para el Hackathon Writeup
- **Uso de Gemma**: Gemma 4 31B via Google AI Studio — probado y funcional en producción. Arquitectura diseñada para soportar Gemma local cuando el hardware lo permite.
- **Impacto social**: barrera idiomática + dispersión de recursos + urgencia = problema real que AI puede resolver de forma concreta.
- **Decisión técnica destacable**: separación mapa/chat. El mapa lee SQLite directo; el chat va por los agentes. Cada canal usa el medio más apropiado.
- **Honestidad sobre limitaciones**: documentar la limitación de hardware como parte del proceso, no como fracaso. Forma parte de la realidad de modelos open-weight grandes.

### Para el GitHub README
- Diagrama ASCII de arquitectura (sección 2).
- Instrucciones de instalación con `uv` (única forma de resolver conflicto protobuf).
- Tabla de variables de entorno (sección 9) — incluyendo las nuevas de `OPENAI_API_BASE`.
- Sección "Modo local" con advertencia de requisitos de hardware.
- Tabla de endpoints API (sección 7).

### Para LinkedIn/Medium — ángulos narrativos

**Ángulo técnico** (más adecuado para Medium):
*"Cómo construí un sistema multi-agente con Google ADK, Gemma 4 y Dash — y los bugs no documentados que encontré en el camino"*
- La tabla de bugs es el núcleo del artículo técnico. Cada bug es una historia.
- El bug de serialización ADK+LiteLLM+Ollama merece su propia sección: es un problema real que afecta a cualquier persona que intente usar modelos locales con ADK y no está documentado claramente.
- El razonamiento interno de Gemma 4 filtrándose al usuario es un ejemplo concreto de por qué el prompt engineering importa incluso con modelos muy buenos.

**Ángulo de impacto** (más adecuado para LinkedIn):
*"Construí un asistente de IA para refugiados en España — lo que aprendí sobre tecnología con propósito"*
- Por qué este problema específico: datos reales sobre solicitudes de asilo en España.
- Por qué IA conversacional multilingüe: la barrera idiomática como primera barrera.
- Por qué open-source (Gemma): privacidad de datos de personas vulnerables, sin vendor lock-in, posibilidad de despliegue local en ONGs con recursos limitados.
- El hackathon como catalizador, no como destino.

---

*Versión 0.2 — continuar actualizando con cada iteración significativa del proyecto.*
