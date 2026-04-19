RefugeeConnect — Registro de cambios y decisiones de arquitectura
Contexto del proyecto
Sistema multi-agente para ayudar a solicitantes de refugio internacional en España. Frontend en Dash, backend en FastAPI con Google ADK, base de datos SQLite, soporte para ejecución cloud (Gemini) y local (Gemma via Ollama).

Problemas identificados en el sistema original
El orquestador llamaba a múltiples agentes incluso ante saludos o consultas vagas. Los agentes entraban en bucle cuando no encontraban resultados en la base de datos. El sistema no tenía condiciones de parada explícitas entre estados. Los prompts mezclaban idiomas de forma inconsistente, reduciendo la fiabilidad en modelos pequeños.

Cambios en el orquestador
Se reescribió el instruction del orquestador como un árbol de decisión con estados terminales explícitos en lugar de pasos secuenciales.
Los estados definidos son cinco. STATE A cubre saludos y consultas vagas, responde sin llamar herramientas. STATE B cubre consultas con necesidad pero sin ciudad, pide solo el dato faltante. STATE C es la consulta completa, activa needs_specialist_agent. STATE D es el estado terminal de fallo, se activa cuando needs_specialist_agent devuelve NO_RECORDS o CATEGORY_NOT_SUPPORTED, informa al usuario y detiene la cadena sin llamar a los agentes restantes. STATE E es el estado de éxito, llama a geolocation_agent y guidance_specialist_agent solo si hay resultados válidos.
La regla más importante añadida es que STATE D es un nodo terminal explícito. Esta es la corrección principal para los bucles.

Cambios en needs_specialist_agent
Se estandarizó el formato de salida en caso de fallo para que sea parseable de forma determinista por el orquestador. El formato es NO_RECORDS:[Ciudad]:[Categoria] y CATEGORY_NOT_SUPPORTED:[input] en la primera línea, seguido de texto explicativo para el usuario. Esto elimina la ambigüedad que causaba que el orquestador no reconociera el fallo y continuara llamando agentes.

Incorporación del clasificador de intención
Se propuso añadir un clasificador de intención previo al orquestador, implementado como una llamada LLM pequeña y barata. Clasifica cada mensaje en GREETING, INCOMPLETE, COMPLETE o OUT_OF_SCOPE. Para GREETING y OUT_OF_SCOPE el mensaje no llega al orquestador con herramientas, reduciendo coste, latencia y comportamiento errático.

Nuevo componente: derechos y protección
Se añadió un módulo de derechos como función Python directa, no como agente adicional. La decisión de no implementarlo como agente se tomó por tres razones: no consume tokens de modelo adicional, no puede alucinar el contenido al ser datos estáticos, y funciona de forma idéntica en ejecución local y cloud.
La función get_rights_by_category recibe una categoría y devuelve los derechos relevantes junto con los contactos de emergencia. Se registra directamente en el parámetro tools del orquestador junto a los AgentTool existentes, lo cual es compatible con la API de Google ADK.
El contenido cubre cinco categorías: Legal, Salud, Alojamiento, Comida y Empleo. Cada categoría incluye derechos positivos garantizados independientemente del estatus migratorio, alertas específicas sobre estafas y abusos frecuentes contra recién llegados, y recursos de acción cuando se vulneran esos derechos. Existe además una clave especial de emergencia con números de teléfono críticos que se adjunta a todas las respuestas independientemente de la categoría.
Los derechos destacados por su importancia práctica son: el derecho a solicitar asilo independientemente de la forma de entrada, el acceso a urgencias sin documentación, el padrón municipal como derecho no condicionado a la propiedad, la prohibición de retención de documentos por empleadores, y la gratuidad de la solicitud de asilo como señal de alerta ante estafas.

Decisión sobre idiomas en el código
Se estableció una política de idioma única para todo el proyecto.
Inglés para todo lo técnico: docstrings, comentarios, nombres de funciones y variables, logs, system prompts de agentes, y mensajes de error internos entre componentes.
Español para todo el contenido visible al usuario: respuestas, contenido de RIGHTS_SNIPPETS, y mensajes de error que llegan al frontend.
La razón principal para los system prompts en inglés es que los modelos de lenguaje, especialmente los de menor tamaño como Gemma 7B, siguen lógica condicional con mayor fiabilidad cuando las instrucciones están en inglés debido a la distribución del corpus de entrenamiento. Para Google ADK específicamente, los docstrings en inglés mejoran la fiabilidad con la que el orquestador decide cuándo invocar cada herramienta, ya que el razonamiento interno ocurre en el mismo espacio semántico que las instrucciones.
La regla práctica para dudas es: si el texto lo ve el usuario final, español; si no lo ve, inglés.

Principio general adoptado para modelos pequeños
Los prompts deben diseñarse para el modelo más pequeño soportado, Gemma 7B en Ollama, y funcionarán correctamente en cloud. El diseño inverso no es válido. La complejidad del sistema debe residir en la arquitectura, no en la longitud o sofisticación de cada prompt individual. Un agente con una tarea acotada y una herramienta es significativamente más estable en modelos pequeños que un agente con múltiples herramientas y lógica condicional extensa en el prompt.