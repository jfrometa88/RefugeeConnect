Resumen de Decisiones Técnicas y Evolución: Proyecto RefugeeConnect
1. Problema Inicial: Falta de Visibilidad (Caja Negra)

    Contexto: Se utilizaba una arquitectura multi-agente donde un orquestador delegaba tareas a agentes especialistas (ej. needs_specialist_agent).

    Problema: Al ocurrir errores (como no encontrar registros en la base de datos), el desarrollador no podía determinar si el fallo estaba en el orquestador, en el especialista, o en la herramienta (tool) de consulta SQL. Los logs estándar no mostraban el intercambio de mensajes interno.

2. Implementación de Trazabilidad con Google ADK

    Funcionalidad clave: Uso de outputKey (u output_key según versión).

    Decisión Técnica: Se refactorizó el bucle de eventos async for event in runner.run_async(...) para inspeccionar la identidad del evento (event.author) y el contenido de las respuestas de herramientas (function_response).

    Resultado: Se logró "abrir la caja negra", permitiendo ver en tiempo real:

        Qué argumentos exactos enviaba el orquestador.

        Qué datos crudos devolvía la base de datos antes de ser procesados por el modelo.

3. Diagnóstico de Fallos Estructurales

Gracias a la trazabilidad, se detectaron tres puntos críticos de fallo:

    Inconsistencia de Idioma: El orquestador razonaba en inglés pero la base de datos estaba en español. El modelo traducía categorías (ej. de "Salud" a "Health"), rompiendo las consultas SQL.

    Ambigüedad en Docstrings: Las descripciones de las funciones (herramientas) indicaban valores válidos en inglés, confundiendo al LLM.

    Paso de Argumentos Incorrecto: El orquestador enviaba frases completas (ej. "Salud en Valencia") a campos que esperaban valores atómicos, debido a una falta de estructura en la comunicación entre agentes.

4. Cambio de Arquitectura: De Multi-Agente a Centralizada

    Decisión: Se decidió prescindir del needs_specialist_agent para las consultas de base de datos.

    Razón: En tareas de consulta directa a BD, una capa adicional de agente LLM añadía latencia (3-5 segundos extra) y aumentaba la probabilidad de error en el formateo de datos.

    Nueva Estructura: El orquestador ahora consume directamente la herramienta get_services_by_category.

    Optimización de Interfaz: Se actualizaron los Docstrings de las funciones a español y se añadieron instrucciones de tipado y valores permitidos (Health -> Salud).

5. Lecciones Aprendidas para la Memoria

    Observabilidad: La trazabilidad en sistemas de IA generativa no es opcional; es la única forma de depurar flujos lógicos complejos.

    Principio de Parsimonia: No usar un agente si una herramienta directa (tool) puede resolver la tarea. El orquestador es suficiente para estructurar llamadas a funciones si los docstrings son claros.

    Alineación de Lenguaje: En aplicaciones multi-idioma, la interfaz de las herramientas (docstrings) debe coincidir estrictamente con el idioma de los datos en la persistencia (DB).

Estado Final de la Solución

El sistema actual es más robusto, rápido y fácil de auditar. El orquestador identifica la necesidad, llama a la base de datos con parámetros limpios en español y, gracias al código de inspección implementado, cada paso queda registrado para futura supervisión o mejora del modelo.