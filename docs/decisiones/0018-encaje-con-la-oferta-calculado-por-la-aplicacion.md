# 0018 — Encaje con la oferta: la IA da los requisitos y la aplicación calcula el porcentaje

- **Fecha:** 2026-10-07
- **Estado:** aceptada

## Contexto

Con la revisión del CV adaptado ya construida (F15, paso 3), el usuario pidió que la revisión dijera **cuánto encajaba con la oferta el CV de antes y cuánto el adaptado**. La forma inmediata, pedirle a la IA un porcentaje, tiene tres problemas:

- **No es reproducible.** El mismo CV saldría con cifras distintas en cada llamada.
- **No sigue a la revisión.** El número llega con la propuesta y no cambia cuando el usuario edita, quita o reordena. Justo ahí es donde más útil sería.
- **Tiene un incentivo para inflarse.** El modelo que hizo la adaptación tiende a puntuar alto su propio "después".

## Decisión

- **La IA solo extrae los requisitos de la oferta**, en la misma llamada y sin gastar otro uso, con un prompt nuevo (`cv/v2`). Cada requisito trae:
    - su peso: imprescindible o valorable;
    - las palabras con que lo buscaría un ATS: como lo dice la oferta, más sinónimos, siglas y variantes, también en el idioma del CV;
    - los elementos del perfil que lo demuestran (la **evidencia**), por id corto. Esos ids se validan como cualquier otra referencia (A32): uno inventado invalida la propuesta.
- **El porcentaje lo calcula la interfaz** buscando esas palabras en el texto del CV: antes (el perfil tal cual) y después (el CV tal como queda en la revisión). Al comparar se ignoran mayúsculas, tildes, puntuación, plurales y versiones. Un imprescindible cuenta el doble. Es determinista y se recalcula con cada edición.
- **Cada requisito queda en uno de cuatro estados**:

    | Estado | Qué significa |
    |---|---|
    | Aparece | El CV lo nombra |
    | Lo tienes con otras palabras | La IA da evidencia, pero el texto no usa las palabras de la oferta |
    | En tu perfil, no en este CV | El perfil lo nombra y la revisión lo quitó |
    | No está en tu perfil | Es una carencia (RF-112) |

  **Solo suma el primero.** Los otros dos estados intermedios se enseñan con la evidencia y las palabras que contarían, para que decida la persona: la IA puede ser generosa con la evidencia.
- Las carencias dejan de ser una lista aparte en `cv/v2`: son los requisitos sin evidencia. Las propuestas de `cv/v1` siguen como estaban, sin encaje.
- Al probarlo con Groq, el modelo quitaba cifras al reformular ("para 40 clientes", "un 40%"). `cv/v2` pide además **conservarlas**: la regla de `cv/v1` solo prohibía añadirlas.

## Alternativas descartadas

- **Un porcentaje de la IA:** descartado por los tres problemas del contexto.
- **Contar también la evidencia** ("lo tienes con otras palabras" como medio punto): el número dependería del criterio de la IA, que es justo lo que se quería evitar. El estado se enseña aparte.
- **Un diccionario propio de sinónimos:** mantenerlo cuesta y nunca cubriría todos los sectores. Las variantes las da la IA para cada oferta, y la normalización (tildes, plurales, versiones) es código probado.
- **Comparación semántica (embeddings):** otra dependencia y otro proveedor para algo que un ATS tampoco hace. El valor está precisamente en señalar lo que un filtro literal no reconocería.
