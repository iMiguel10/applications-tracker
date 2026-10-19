---
title: Despliegue continuo
sidebar_label: Despliegue continuo
---

Con el despliegue continuo, cada versión nueva que pasa las pruebas se despliega sola en Coolify, sin entrar al panel. Es opcional y solo sirve con [Coolify](coolify.md) y un repositorio en GitHub (la CI es GitHub Actions).

## Cómo funciona

Un push a `main` ejecuta la CI (estilo, pruebas, compilación, documentación e imágenes de producción). Si todo pasa, el último paso, el job `deploy`, hace esto:

1. **Comprueba que `main` sigue siendo ese commit.** Coolify despliega siempre lo último de la rama, no un commit concreto; si `main` ya avanzó, desplegar subiría un commit que esta CI no ha probado. En ese caso termina sin desplegar y sin fallar: lo despliega la CI del commit nuevo.
2. **Pide el despliegue** a la API de Coolify y espera, consultando su estado cada 10 segundos, hasta 30 minutos (una construcción suele tardar unos 7).
3. **Comprueba el resultado:** que Coolify desplegó ese commit y que `/api/v1/health` de tu dominio responde `ok`.

El job falla si el despliegue termina en `failed` o `cancelled`, si no acaba en 30 minutos, si Coolify rechaza el token, o si desplegó otro commit o la aplicación no responde. El motivo sale en el log del job.

## Configurarlo

1. **Crea un token en Coolify** (*Keys & Tokens › API tokens*, o el nombre equivalente en tu versión) con los permisos `read` y `deploy`, **y ningún otro**. Con solo `deploy` se lanza el despliegue pero no se puede seguirlo, y el job falla. Dedícalo a esto: no lo uses para nada más.
2. **Desactiva *Auto Deploy*** en el recurso de Coolify. Si no, Coolify despliega también en cada push sin esperar a la CI, aunque falle.
3. **Apunta el identificador del recurso**: el UUID de la aplicación que aparece en la URL de su página en Coolify.
4. **En GitHub** (*Settings › Secrets and variables › Actions*):

    | Dónde | Nombre | Valor |
    |---|---|---|
    | Secreto | `COOLIFY_URL` | La dirección de tu panel de Coolify |
    | Secreto | `COOLIFY_TOKEN` | El token del paso 1 |
    | Secreto | `COOLIFY_APP_UUID` | El UUID del paso 3 |
    | Variable | `PRODUCTION_URL` | La dirección pública de la aplicación (`APP_URL`) |

    La variable `PRODUCTION_URL` hace de interruptor: **sin ella el job no se ejecuta** (en un fork u otra instalación, nadie despliega por error). Para pausar el despliegue continuo, bórrala.

5. **El panel de Coolify tiene que ser alcanzable desde GitHub** (un runner normal de GitHub llama a su API): con el panel solo en tu red local, el job no llega. Hace falta que sea público (conviene con doble factor de autenticación) o un runner propio, que no cubre esta guía.

**Qué debe verse:** el siguiente push a `main` que pase la CI muestra un job *Producción · despliegue* verde, y su log acaba con `Desplegado <commit>` y `https://tracker.example.com responde`. Además, GitHub lo registra como un despliegue en el entorno `production`.

## Si falla

| Mensaje del job | Qué hacer |
|---|---|
| `Coolify rechazó el token (401/403)… necesita los permisos read y deploy` | Revisa el token: permisos `read` y `deploy`, y que sea el de `COOLIFY_TOKEN`. No se arregla repitiendo |
| `Coolify respondió 404` | `COOLIFY_APP_UUID` o `COOLIFY_URL` incorrectos |
| `El despliegue terminó en 'failed'` | Falló la construcción o el arranque. El log completo está en el panel de Coolify, en los despliegues del recurso. Lo habitual: falta una variable obligatoria |
| `Coolify desplegó X y no Y` | `main` avanzó mientras tanto. Esperar a la CI del commit nuevo |
| `…/api/v1/health no responde tras el despliegue` | Se desplegó pero la aplicación no contesta: mira los logs de `api` en Coolify |

Para desplegar a mano en cualquier momento, **Deploy** en el panel de Coolify sigue funcionando.
