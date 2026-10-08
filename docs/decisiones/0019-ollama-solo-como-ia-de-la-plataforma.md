# 0019 — Ollama, solo como IA de la plataforma

- **Fecha:** 2026-10-08
- **Estado:** aceptada

## Contexto

Al detallar las claves propias (F15, paso 5), el usuario propuso añadir **Ollama** como proveedor. Ollama puede entrar de dos maneras distintas:

- **Un Ollama propio**, instalado por quien despliega. No tiene clave ni coste por uso, y en local impone el esquema JSON de la respuesta con decodificación restringida.
- **Ollama Cloud** (`ollama.com`), con una clave de API como los demás proveedores. Según su documentación y la de terceros, acepta el esquema **pero no lo impone**.

## Decisión

- **Ollama es un proveedor solo para la IA de la plataforma.** Quien despliega lo configura con `AI_PLATFORM_PROVIDER=ollama`, `AI_PLATFORM_MODEL` (un modelo ya descargado) y `AI_OLLAMA_BASE_URL`. No necesita `AI_PLATFORM_API_KEY`.
- **No es un proveedor de claves propias.** Las claves personales siguen siendo de Anthropic, OpenAI y Groq (0017).
- **La dirección de Ollama la fija siempre quien despliega**, nunca un usuario.
- **A petición del usuario:** al terminar el paso 5, Ollama pasa a ser la IA de plataforma **por defecto** en lugar de Groq. Hecho en [0020](0020-ollama-por-defecto-y-usos-gratuitos-sin-tope.md).

## Alternativas descartadas

- **Que cada usuario dé la dirección de su Ollama:** el servidor haría peticiones a cualquier dirección que le den, incluidas las de su red interna (SSRF). Un usuario que quiera su Ollama local tiene que ser quien despliega.
- **Ollama Cloud como clave propia:** sin el esquema impuesto saldrían más respuestas inválidas, y con clave propia las paga el usuario. Si su nube llega a imponerlo, se añade como un proveedor más sin tocar nada más.
- **Usar Ollama por su API compatible con OpenAI** (reutilizando el adaptador de OpenAI): la API nativa (`/api/chat` con `format`) es la que documenta la salida estructurada, y la comprobación del modelo (`/api/tags`) no existe en la compatible.
