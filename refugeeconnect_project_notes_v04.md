# 🧠 Debug y diseño de agentes con Google ADK + Ollama (Resumen técnico)

## 📌 Contexto
Proyecto de agentes de IA usando:
- Google ADK (`LlmAgent`, `AgentTool`)
- LiteLLM + Ollama (modelos locales como qwen2.5:3b)
- Máquina limitada (8GB RAM)

Problemas encontrados al implementar un orquestador con múltiples agentes y tools.

---

# 🧨 1. Error inicial: `Part.text` esperaba string

## ❌ Error

Input should be a valid string
input_value={'type': 'string'}


## 🔍 Causa
- Se estaban devolviendo `dict` o `list` desde:
  - tools
  - sub-agentes
- ADK intenta hacer:
```python
Part(text=<dict>)

→ falla porque solo acepta str

✅ Solución
Forzar que TODAS las tools devuelvan str
✔️ Ejemplo incorrecto
return df.to_dict(orient="records")
✔️ Ejemplo correcto
return "\n".join([
    f"{r['name']} | {r['address']} | {r['description']}"
    for r in results
])
🧨 2. Error: invalid model name (Ollama)
🔍 Causa
Se estaba pasando:
ollama_chat/ollama:qwen2.5-coder:3b

→ doble prefijo ollama

✅ Solución
Normalizar nombre del modelo:
model_clean = model_name_local.replace("ollama:", "")
model = f"ollama_chat/{model_clean}"
🧨 3. Error: Tool inexistente (greeting)
🔍 Causa
El modelo “alucinaba” tools a partir del prompt:
STATE A — GREETING

→ interpretado como tool

✅ Solución
Cambiar naming:
STATE → CASE / SCENARIO
Añadir regla estricta:
You can ONLY call:
- needs_specialist_agent
- geolocation_agent
- get_rigths
🧨 4. Error: args mal formados en tool call
❌ Error
args['request'] = {'type': 'string'}
🔍 Causa
El modelo genera JSON incorrecto al llamar tools
Problema típico en modelos pequeños
✅ Solución
✔️ Wrapper para AgentTool
class SafeAgentTool(AgentTool):
    async def run_async(self, args, tool_context=None):
        for k, v in args.items():
            if not isinstance(v, str):
                args[k] = str(v)
        return await super().run_async(args=args, tool_context=tool_context)
🧨 5. Loop infinito del agente
🔍 Síntoma
Múltiples llamadas seguidas al modelo
Nunca se emite final_response
🔍 Causa
El modelo no entiende cuándo terminar
No interpreta correctamente estados como:
NO_RECORDS
LOCATION_NOT_FOUND
✅ Soluciones
✔️ 1. Regla de terminación en prompt
If you have enough information:
- Respond to the user
- DO NOT call any tool
- END the conversation
✔️ 2. Límite de iteraciones
max_events = 10
if event_count > max_events:
    return "Error: demasiadas iteraciones"
✔️ 3. Control en código (recomendado)
if "NO_RECORDS" in tool_result:
    return respuesta_directa
🧠 Lecciones clave
❗ 1. Google ADK NO soporta outputs estructurados automáticamente
Tools deben devolver str
No usar dict ni list
❗ 2. Modelos pequeños (3B) tienen limitaciones

Problemas típicos:

tool calling incorrecto
JSON mal formado
loops
confusión entre instrucciones y tools
❗ 3. No confiar en el LLM para controlar lógica

Evitar:

LLM = controlador del flujo

Preferir:

Código = lógica
LLM = generación de texto
🏗️ Arquitectura recomendada (para local)
❌ No recomendado
Orchestrator LLM → decide todo
✅ Recomendado
Código controla flujo
↓
LLM se usa para:
- interpretar input
- generar respuesta
🛠️ Buenas prácticas aplicadas
Normalizar SIEMPRE outputs de tools → str
Validar inputs a tools
Limitar iteraciones
Evitar nombres ambiguos en prompts
Diseñar outputs “LLM-friendly” (texto simple)
🏁 Conclusión

El sistema pasó por 3 fases típicas:

❌ Errores de tipo (dict vs string)
❌ Errores de tool calling (inputs mal formados)
❌ Problemas de control de flujo (loops)

👉 Solución final:

normalización de datos
control en código
prompts más estrictos
🚀 Insight final

En entornos con recursos limitados:

Un buen diseño de arquitectura importa más que el modelo.