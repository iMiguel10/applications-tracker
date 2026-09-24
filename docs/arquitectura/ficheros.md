# Ficheros y generación de PDF

> Estado: **diseño, en construcción** (F9, F13, F14). Construidos en F9: el almacén (§1), la escritura y lectura en disco (§3), el volumen y el generador de PDF con su protección contra SSRF (§7) · Fecha: 2026-09-24 · Depende de la [arquitectura de la v2](v2.md) (A21–A27, A30) y de [servicios y estructura §8](servicios-y-estructura.md#8-ampliacion-de-la-v2)

## 1. Piezas

| Pieza | Qué es | Dónde |
|---|---|---|
| Almacén | `FileStorage` con una implementación de disco local (A21) | `infra/storage/` |
| Volumen | `files_data`, montado en `/data/files` en `api` y `worker` | `compose.yml` |
| Biblioteca | Tabla `documents` y `DocumentService` (RF-90…94) | `repositories/`, `services/` |
| Generación | WeasyPrint + plantillas Jinja2 (A24, A25) | `infra/pdf/` (construido en F9), `templates/cv/`, `templates/cover_letter/` |

`FileStorage` es deliberadamente pequeña: `put(key, chunks, max_bytes=None) -> size`, `open(key)`, `delete(key)`, `delete_prefix(prefix)` e `iter_keys()`. Construidas en F9 todas menos `iter_keys()`, que llega en F13 con su único consumidor, el barrido de huérfanos. `put` cuenta los bytes mientras escribe y corta con `FileTooLargeError` al pasar de `max_bytes`, sin dejar nada escrito: la subida (§2, paso 2) no necesita contar por su cuenta. Todo lo que sabe de documentos (propiedad, cuotas, estados) está en el service; el almacén solo sabe de claves y bytes.

## 2. Subir un documento

| Paso | Qué hace | Qué rechaza |
|---|---|---|
| 1 | `require_verified_email` y `rate_limit("upload")` | 403 `email_not_verified`, 429 `rate_limited` |
| 2 | Lee el cuerpo **contando bytes mientras lee**, y corta al pasar de 5 MB | 413 `file_too_large` |
| 3 | Comprueba la firma (`%PDF-` al principio) y que `pypdf` lo abre y cuenta sus páginas, con un límite de tiempo | 422 `invalid_file_type` |
| 4 | Con la fila del usuario bloqueada (A30): almacenamiento usado + tamaño **real** ≤ límite, y documentos ≤ límite | 409 `storage_limit_reached`, `documents_limit_reached` |
| 5 | Escribe el fichero en `users/{user_id}/documents/{document_id}.pdf` de forma atómica (§3) | — |
| 6 | Inserta la fila `ready` con tamaño, `sha256` y nombre saneado, y hace commit | — |

> **Trampa — fiarse de `Content-Length` o de la extensión.** `Content-Length` lo declara el cliente y puede mentir, y la extensión `.pdf` no dice nada del contenido. El tamaño que cuenta para la cuota es el de los bytes escritos de verdad, y el tipo es el que dice la firma del fichero.

> **Trampa — un PDF es una superficie de ataque.** Hay PDFs diseñados para colgar o agotar la memoria de quien los procesa (flujos comprimidos enormes, referencias circulares). Por eso el servidor **nunca renderiza ni extrae texto** de un PDF subido: solo lo abre para comprobar que es un PDF y contar páginas, con un límite de tiempo. El único que lo "ve" es el navegador del propio dueño.

## 3. Escribir y leer en disco

- **Escritura atómica.** Se escribe primero a `.tmp/<uuid>.part`, dentro del **mismo volumen**, se fuerza a disco (`fsync`: sin él, un corte de luz justo después del renombrado podría dejar el fichero con su nombre definitivo pero incompleto) y se renombra con `os.replace` al destino. Un lector nunca ve un PDF a medias, y un proceso que muere a mitad deja un `.part` que el barrido de huérfanos borra.
- **Rutas.** Las genera el servidor (A23). Aun así, `LocalFileStorage` rechaza con `InvalidStorageKeyError` dos cosas: una clave con algún segmento fuera de `[A-Za-z0-9._-]` o que empiece por punto (eso deja fuera `..`, las rutas absolutas, `//`, las barras invertidas y el directorio `.tmp`), y cualquier ruta que, resuelta, salga de `FILES_ROOT`, lo que cubre también un enlace simbólico dentro del almacén que apunte fuera. Una defensa más por si algún día una clave se construye mal.
- **Sin bloquear.** Todo el I/O de disco va a un hilo (`asyncio.to_thread`): leer o escribir un PDF no para el event loop de la API ni del `worker`.
- **Permisos.** El volumen pertenece a `appuser` (uid 1000), igual que el resto de ficheros de la imagen.

> **Trampa — el volumen nace con dueño `root`.** Un volumen con nombre que Docker crea vacío en un directorio que no existe en la imagen pertenece a `root`, y `appuser` no puede escribir en él: la primera subida falla con `PermissionError`. La imagen crea `/data/files` con dueño `appuser` **antes** de declararse el volumen, y Docker copia ese dueño la primera vez que lo crea.

> **Trampa — renombrar entre sistemas de ficheros no es atómico.** `os.replace` solo es atómico dentro del mismo sistema de ficheros. Si el temporal se escribiera en `/tmp` del contenedor y el destino estuviera en el volumen, sería una copia más un borrado, y un lector podría ver el fichero a medias. Por eso el temporal vive dentro de `FILES_ROOT`.

## 4. Descargar un documento

`GET /documents/{id}/file`: el service comprueba la propiedad (404 si es ajeno), el endpoint devuelve el fichero con:

| Cabecera | Valor | Por qué |
|---|---|---|
| `Content-Type` | `application/pdf`, siempre | Nunca el tipo que dijo el cliente al subirlo (RNF-05) |
| `X-Content-Type-Options` | `nosniff` | Que el navegador no intente adivinar otro tipo |
| `Content-Disposition` | `inline` o `attachment`, con `filename*=UTF-8''…` | Ver la trampa |
| `Cache-Control` | `private, no-store` | Un CV no debe quedarse en la caché de un proxy |

> **Trampa — los nombres con tildes rompen la cabecera.** Una cabecera HTTP solo admite ASCII. `filename="currículum.pdf"` llega mal o rompe la respuesta según el navegador. Se envía `filename` con una versión ASCII (`curriculum.pdf`) **y** `filename*=UTF-8''curr%C3%ADculum.pdf` (RFC 5987), que los navegadores modernos prefieren.

El visor del frontend descarga el fichero con `apiClient.getBlob()` y lo muestra en un `iframe` con una URL `blob:` que se libera al cerrar el visor.

## 5. Huérfanos

Postgres manda (invariante 9) y el orden de escritura garantiza que solo pueden sobrar **ficheros**, nunca faltar:

| Situación | Resultado |
|---|---|
| Se escribió el fichero y falló el commit de la fila | Fichero huérfano |
| Se borró la fila y falló el borrado del fichero | Fichero huérfano |
| Se borró la cuenta y falló el borrado de `users/{user_id}/` | Directorio huérfano |
| El proceso murió escribiendo un `.part` | Temporal huérfano |

El barrido diario recorre las claves del almacén, comprueba en lotes cuáles no tienen fila en `documents` y borra las que tienen **más de una hora**.

> **Trampa — el barrido borra una subida en curso.** Entre escribir el fichero y confirmar su fila pasan milisegundos, pero pasan. Un barrido que coincidiera justo en ese momento vería un fichero sin fila y lo borraría, y el commit posterior dejaría una fila apuntando a nada: justo lo que el orden de escritura debía impedir. El margen de una hora sobre la fecha de modificación lo evita.

## 6. Copias de seguridad y restauración

Una copia de una instalación son tres cosas: `pg_dump` de la base de la aplicación, `pg_dump` de la de SuperTokens y una copia de `files_data`. El orden importa:

1. Primero, los volcados de las bases de datos.
2. Después, la copia de los ficheros.

Así, los ficheros subidos entre ambos pasos quedan como huérfanos en la copia, que el barrido limpia al restaurar. En el orden contrario, una subida entre ambos pasos dejaría en la copia una fila sin su fichero. Es la misma regla de §5 aplicada a la copia, y el manual de despliegue la da como receta.

## 7. Generación de PDF (CVs y cartas)

### Plantillas

```
templates/cv/<diseño>/
├── manifest.json     nombre visible, idiomas, apto para ATS (sí/no), tamaño de página
├── template.html     Jinja2
├── style.css
└── fonts/            tipografías incluidas (@font-face con ficheros locales)
```

- El service prepara los datos (la **foto fija** de A27: perfil filtrado y, si hubo IA, la propuesta revisada) y la plantilla solo los presenta. Las etiquetas fijas ("Experiencia", "Experience") salen de ficheros de traducción de las plantillas, no de `es.json` del frontend.
- **Autoescape activado**: todo el contenido lo escribe el usuario o la IA.
- Tamaño A4 por defecto; el `manifest` puede declarar Carta (US Letter).
- Se renderiza en el `worker`, nunca en una petición (RNF-12).

> **Trampa — WeasyPrint descarga lo que le pidas.** Al renderizar, WeasyPrint sigue las URLs del HTML (imágenes, hojas de estilo, fuentes). Si una plantilla llegara a pintar como imagen una URL escrita por el usuario (el enlace a su web, un "logo"), el `worker` haría peticiones a donde el usuario quisiera, incluidos servicios internos de la red de Docker (`http://supertokens:3567`, `valkey:6379`). Es un SSRF de manual. `infra/pdf/weasyprint_renderer.py` usa un fetcher propio (`TemplateOnlyFetcher`, subclase del `URLFetcher` que WeasyPrint 70 pide heredar) que **solo** sirve ficheros de la carpeta de la plantilla y URLs `data:`, y rechaza todo lo demás sin abrir ninguna conexión; WeasyPrint sigue renderizando sin ese recurso. Los enlaces del usuario pueden aparecer como enlaces `<a>` del PDF, que WeasyPrint no descarga.

> **Trampa — un diseño bonito que ningún ATS lee.** Maquetar a dos columnas con posicionamiento absoluto o poner el nombre y los datos en una imagen se ve bien, pero un ATS extrae el texto en un orden absurdo o no lo extrae. Los diseños marcados como aptos para ATS (RF-105) usan flujo normal de texto, y una prueba extrae el texto del PDF generado y comprueba que aparece en orden.

### Fuentes

Las tipografías viajan con cada diseño. El PDF sale idéntico en desarrollo, en CI y en producción, y no depende de qué fuentes tenga instaladas la imagen.

**Lo que descubrió F9 (R9):**

- Sin sus librerías de sistema, `import weasyprint` falla al cargar `libgobject`. La imagen instala `libpango-1.0-0`, `libpangoft2-1.0-0` y `libharfbuzz-subset0`.
- La imagen **no** queda sin fuentes: `fontconfig`, que llega con Pango, depende de `fonts-dejavu-core`, y con él vienen DejaVu Sans, Serif y Mono. Es una ventaja: hacen de fuente de respaldo cuando la de un diseño no tiene un carácter, y el texto nunca sale vacío. Un diseño que pide `sans-serif` sin traer fuente propia sale en DejaVu Sans, incrustada solo con los caracteres usados.
- Tiempos con la plantilla de prueba de F9 (una página, texto simple), dentro de la imagen: ~130 ms por PDF de uno en uno y ~25 ms por PDF con 20 a la vez en un proceso de 6 núcleos. Buena parte del trabajo ocurre en código C (Pango, HarfBuzz) que no bloquea al resto de hilos. El proceso llega a unos 180 MB. Un CV real maqueta mucho más en Python, así que F14 vuelve a medir con sus plantillas.
- Se genera en un hilo (`asyncio.to_thread`) para que el `worker` siga atendiendo los demás trabajos mientras maqueta.
- Jinja2 con `StrictUndefined`: una variable mal escrita en la plantilla hace fallar el PDF en vez de dejar un hueco en blanco que nadie ve hasta que el CV ya se ha enviado.

## 8. Pruebas que demuestran el diseño

| # | Prueba | Qué demuestra |
|---|---|---|
| D1 | Un fichero con extensión `.pdf` que no es un PDF → 422 | Tipo por contenido |
| D2 | Un cuerpo de 6 MB con `Content-Length` falso de 1 KB → 413, y no se escribe nada | Tamaño real, cortado al leer |
| D3 | Dos subidas simultáneas que juntas pasan del almacenamiento restante: solo una entra | Cuota con bloqueo (A30) |
| D4 | La descarga de un documento de otro usuario → 404 | Aislamiento |
| D5 | Un documento asociado a una solicitud no se puede borrar (409 `document_in_use`); archivado, sigue asociado | RF-93 |
| D6 | Falla el commit tras escribir el fichero: queda un huérfano y ninguna fila rota; el barrido lo borra pasada la hora y no antes | Orden de escritura y margen del barrido |
| D7 | Una clave con `../` es rechazada por `LocalFileStorage`, y también una clave válida que atraviesa un enlace simbólico hacia fuera **[construida en F9]** | Rutas encerradas en la raíz |
| D8 | Un nombre `currículum.pdf` se descarga con `filename*` correcto, y el `filename` ASCII es `curriculum.pdf` (normalizado con NFKD: codificar a ASCII sin más quita la letra entera, `currculum`) **[probada en el esqueleto de F9, ya retirado; vuelve con la descarga de F13]** | Cabeceras |
| D9 | Una plantilla de prueba con `<img src="http://…">` no produce ninguna petición de red **[construida en F9]**: un servidor HTTP local cuenta cero peticiones con imágenes, hojas de estilo, fuentes y fondos externos | El `url_fetcher` contra SSRF |
| D10 | El texto extraído de un CV generado con un diseño apto para ATS sale en orden de lectura | RF-105 |
| D11 | Borrar la cuenta borra `users/{user_id}/`; si falla, el barrido lo limpia | RNF-41 |

## 9. Lo que no se hace todavía

| Funcionalidad | Estado | Costura que lo permitirá |
|---|---|---|
| S3 (gestionado o autoalojado) | Cuando haga falta más de un servidor | Otra implementación de `FileStorage` y copiar los ficheros una vez |
| Antivirus de los ficheros subidos | `[C]` | Un paso más en la subida, antes de escribir; hoy los PDF nunca se procesan en el servidor |
| Adjuntos que no sean PDF (Word) | No se hace | La validación por firma decide qué tipos entran |
| Editor visual de plantillas | No se hace | Las plantillas son carpetas: un diseño nuevo es código revisado |
