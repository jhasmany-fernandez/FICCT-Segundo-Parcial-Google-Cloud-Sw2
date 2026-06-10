# BASELINE FUNCIONAL DEL PROYECTO

## Objetivo
Registrar el estado funcional actual del proyecto `F.I.C.C.T.-Proyecto-Final-Sw2-Web` despues de la validacion con Docker, antes de iniciar cambios de codigo para la migracion al Core de Emergencias Vehiculares.

## Rama actual

- `feature/migracion-core-emergencias`

## Estado de git

- Working tree antes de documentar: `clean`

## Comando usado para levantar Docker

```bash
docker compose up --build
```

## Servicios detectados

- `diagramador-db`
- `diagramador-backend`
- `diagramador-frontend`

## Puertos expuestos

- Base de datos: `5454 -> 5432`
- Backend: `80 -> 8000`
- Backend: `8787 -> 8000`
- Frontend: `5656 -> 5656`

## URLs validadas

- Frontend: `http://localhost:5656`
- Backend: `http://localhost:8787`
- Healthcheck: `http://localhost:8787/api/health`
- Swagger/OpenAPI: `http://localhost:8787/docs`

## Resultado de healthcheck

Respuesta interna validada desde el contenedor backend:

```json
{"status":"ok","environment":"development","database":"connected"}
```

Interpretacion:

- Backend operativo
- Entorno en `development`
- Base de datos conectada

## Resultado de Swagger

- `GET /docs` respondio `200`

Interpretacion:

- La documentacion Swagger/OpenAPI del backend esta disponible

## Resultado del frontend

- `GET /` del frontend respondio `200`

Interpretacion:

- El frontend levanta correctamente en su estado actual

## Advertencias no bloqueantes detectadas

Durante `docker compose up --build` se detecto la advertencia:

```text
Docker Compose requires buildx plugin to be installed
```

Evaluacion:

- No bloquea el build
- No impidio levantar backend, frontend ni base de datos

## Limitaciones del entorno de prueba

Desde el sandbox no se pudo abrir `localhost:8787` ni `localhost:5656` directamente desde el host.

Sin embargo:

- `docker compose ps` mostro los servicios levantados
- las verificaciones internas desde contenedores respondieron correctamente
- el backend devolvio healthcheck valido
- Swagger devolvio `200`
- frontend devolvio `200`

Conclusión:

- la limitacion pertenece al entorno de prueba del sandbox
- no corresponde a un fallo funcional del proyecto

## Resumen final

- Docker levanta: `Si`
- Backend levanta: `Si`
- Frontend levanta: `Si`
- Base de datos levanta: `Si`
- Errores bloqueantes: `No`

## Conclusión operativa

El proyecto queda registrado con baseline funcional valido antes de iniciar la migracion al Core de Emergencias Vehiculares.

En su estado actual:

- el stack Docker construye y arranca
- la base de datos responde
- el backend responde correctamente
- Swagger esta disponible
- el frontend responde correctamente

Por lo tanto, el repositorio se considera apto para iniciar la fase de cambios de codigo bajo una estrategia controlada de migracion.
