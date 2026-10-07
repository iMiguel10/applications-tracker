# 0017 — IA: plataforma configurable (Groq), cuota por tipo, sin tope global y modelo a elegir

- **Fecha:** 2026-10-07
- **Estado:** aceptada

## Contexto

La especificación dejó para el inicio de F15 fijar con precios reales la cuota gratuita y el tope de gasto (R7), y el diseño suponía una plataforma con un proveedor concreto, 10 usos gratuitos que valían para CV o carta (RF-150), un tope de gasto mensual global (RF-155) y que el usuario con clave propia eligiera proveedor pero no modelo (RF-151). Al empezar la fase, el usuario decidió otra cosa en casi todos esos puntos.

Con los precios de octubre de 2026, una propuesta (unos 5 000 tokens de entrada y 2 500 de salida, más el razonamiento) cuesta unos 0,13 $ con Claude Opus 5.5, 0,06 $ con Claude Sonnet 5.5 y unos 0,004 $ con `openai/gpt-oss-120b` en Groq, que además tiene salida estructurada estricta.

## Decisión

- **La IA de la plataforma se configura por entorno**: proveedor, modelo y clave (`AI_PLATFORM_PROVIDER`, `AI_PLATFORM_MODEL`, `AI_PLATFORM_API_KEY`) y su precio por millón de tokens, solo para estimar el coste de cada propuesta. Cambiar de proveedor o de modelo es cambiar el `.env`. Sin proveedor, la instalación no tiene uso gratuito. Se empieza con **Groq y `openai/gpt-oss-120b`**.
- **Cuota gratuita por tipo**: **1 propuesta de CV y 1 de carta** por cuenta, sin renovación y ajustables por cuenta con `set_user_limit` (RF-143). Sustituye a los 10 usos comunes de RF-150. Como decía el diseño, una respuesta que no pasa la validación o una oferta rechazada por insuficiente **consumen el uso** (ia.md §6).
- **Sin tope de gasto global**: RF-155 se descarta. La plataforma se limita solo por uso: la cuota de cada cuenta, el email verificado (A38) y el rate limit de la IA. El coste estimado de cada propuesta se sigue guardando, para saber cuánto se gasta.
- **Claves propias de Anthropic, OpenAI y Groq**, cada una con su adaptador sobre su SDK oficial (A31). El usuario elige proveedor, añade su clave **y elige el modelo** de una lista que quien despliega fija por proveedor (`AI_ANTHROPIC_MODELS`, `AI_OPENAI_MODELS`, `AI_GROQ_MODELS`; el primero es el de por defecto). Cambia RF-151, que decía que el usuario no elegía modelo. Un proveedor con la lista vacía no se ofrece.
- **Sin límites del usuario sobre sus propias claves**: cada proveedor ya permite poner un tope de gasto en su consola, y ese se aplica a la factura real.
- Cambiar las listas de modelos o los proveedores habilitados **no pierde datos**: las claves guardadas siguen ahí aunque su proveedor se deshabilite; un usuario cuyo modelo se retira de la lista pasa al primero de su proveedor; y cada propuesta guarda como texto el proveedor, el modelo y la versión del prompt con que se hizo (RF-115).
- La carta de presentación tiene una plantilla **por cada diseño de CV**.

## Alternativas descartadas

- **Claude como modelo de la plataforma**: mejor calidad de redacción, pero de 15 a 30 veces más caro por propuesta para un uso gratuito y abierto a cualquiera. Sigue disponible con clave propia.
- **`openai/gpt-oss-20b` o `qwen/qwen3.8-27b` en Groq**: el primero es la mitad de barato pero más flojo y más propenso a fallar la validación; el segundo está en vista previa (puede retirarse sin aviso) y cuesta unas seis veces más.
- **Que una respuesta inválida no consumiera el uso**: con un solo uso gratuito, un fallo del modelo deja al usuario sin probar la función. El usuario prefirió la regla del diseño, más estricta contra el abuso.
- **Tope de gasto mensual global** (RF-155): el usuario prefirió limitar solo por uso; con el coste por propuesta de Groq, el riesgo es pequeño.
- **Límites del usuario sobre su clave** (por usos o por gasto, al mes): duplicarían el tope de su proveedor con peores datos, porque los precios configurados envejecen.
- **Que el usuario escriba cualquier modelo**: un modelo sin evaluar puede no saber responder con el esquema. La lista la fija quien despliega, y el script de evaluación manual recorre todos sus modelos.

## Consecuencias

- **Riesgo nuevo, aceptado:** sin tope global, muchas cuentas falsas consumirían su cuota gratuita (unos 0,008 $ cada una con la configuración inicial). Lo frenan el email verificado y el rate limit; si pasara, se baja la cuota o se quita `AI_PLATFORM_PROVIDER`.
- La cuota gratuita se cuenta por separado para CV y carta (dos claves de límite).
- El usuario elige proveedor y modelo, así que `users` guarda los dos, y la evaluación manual (RNF-23) se ejecuta con cada modelo de las listas antes de ofrecerlo.
- RF-150, RF-151 y RF-155 cambian en la especificación, y `ia.md` §6 deja de tener tope global.
