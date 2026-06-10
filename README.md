# F.I.C.C.T.-Primer-Parcial-Si2-Diagramador-Web

Estructura base del proyecto web para el primer parcial de SI2.

## Flujo Soportado

Este proyecto se ejecuta usando Docker Compose.

- Backend, frontend y PostgreSQL estan pensados para correr dentro de contenedores.
- No se requiere crear entornos virtuales locales ni instalar dependencias manualmente en la maquina host.
- Si existen carpetas locales como `.venv`, `node_modules` o `dist`, se consideran artefactos temporales y no forman parte del flujo oficial.

## Estructura

- `frontend`: aplicacion Angular para desarrollo web
- `backend`: API FastAPI y configuracion de acceso a PostgreSQL
- `docker-compose.yml`: entorno de desarrollo con frontend, backend y base de datos
- `backend/API.md`: documentacion de endpoints del backend
- `FLUJO_PROYECTO.md`: comentario general del flujo del sistema y sus modulos principales

## Desarrollo con Docker

1. Copiar `.env.example` a `.env`
2. Copiar `backend/.env.example` a `backend/.env`
3. Ejecutar `docker compose up --build`

## Puertos

- Frontend local: `http://localhost:5656`
- Frontend LAN: `http://192.168.0.50:5656`
- Frontend IP fija: `http://177.222.97.205:5656`
- Backend local: `http://localhost:8787`
- Backend LAN: `http://192.168.0.50:8787`
- Backend IP fija: `http://177.222.97.205:8787`
- API healthcheck local: `http://localhost:8787/api/health`
- PostgreSQL: `localhost:5454`

## Administrador Del Sistema

- Login web local: `http://localhost:5656/login`
- Login web LAN: `http://192.168.0.50:5656/login`
- Login web IP fija: `http://177.222.97.205:5656/login`

## Acceso por host

- El frontend resuelve el backend usando el mismo host con puerto `8787`.
- Esto permite abrir la app indistintamente por `localhost`, `192.168.0.50` o `177.222.97.205`.
- La geolocalizacion automatica del navegador sigue limitada a `HTTPS` o `localhost`; por HTTP con IP se debe usar seleccion manual en el mapa.
- Correo: `administrador@acb.com`
- Contrasena: `123ppp+++`

Notas:
- Este administrador es un usuario virtual del sistema.
- No se guarda en la tabla `clients` de PostgreSQL.
- Su autenticacion se resuelve directamente en `POST /api/auth/login`.
- El correo `administrador@acb.com` queda reservado y no debe usarse para registros normales de clientes.
