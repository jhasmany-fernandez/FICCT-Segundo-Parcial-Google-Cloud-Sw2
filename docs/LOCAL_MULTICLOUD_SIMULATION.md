# Simulacion Local Multi-Cloud

## Objetivo

Este entorno agrega una simulacion local tipo multi-cloud sin modificar el `docker-compose.yml` principal ni tocar sus volumenes. AWS y Azure no son reales: se representan con contenedores locales aislados y un gateway local que puede reenviar trafico hacia:

- simuladores locales dentro de Docker
- el backend publicado en Google Cloud mediante `CLOUD_BACKEND_URL`
- un backend local expuesto en la maquina host mediante `LOCAL_BACKEND_URL`

## Servicios incluidos

Archivo principal: `docker-compose.local-multicloud.yml`

- `local-aws-simulator`
  - Imagen: `traefik/whoami:v1.10`
  - Puerto publicado: ninguno
  - Uso: simulador local para rutas `/gateway/aws/`

- `local-azure-simulator`
  - Imagen: `traefik/whoami:v1.10`
  - Puerto publicado: ninguno
  - Uso: simulador local para rutas `/gateway/azure/`

- `local-integration-gateway`
  - Imagen: `nginx:1.27-alpine`
  - Puerto publicado por defecto: `8089`
  - Uso: punto de entrada local para la simulacion

- `local-observability`
  - Imagen: `prom/prometheus:v2.54.1`
  - Perfil: `observability`
  - Puerto publicado por defecto: `9091`
  - Uso: observabilidad basica opcional del stack de simulacion

## Rutas del gateway

Con el gateway arriba en `http://localhost:8089`:

- `GET /healthz`
  - Healthcheck del gateway

- `GET /health`
  - Health local del gateway

- `GET /api/health`
  - Proxy al health del backend cloud definido en `CLOUD_BACKEND_URL`

- `GET /gateway/aws/`
  - Reenvia a `local-aws-simulator`

- `GET /gateway/azure/`
  - Reenvia a `local-azure-simulator`

- `GET /gateway/core/`
  - Reenvia al backend definido en `CLOUD_BACKEND_URL`

- `GET /gateway/core-local/`
  - Reenvia al backend local definido en `LOCAL_BACKEND_URL`

## Variables de entorno

Archivo de ejemplo: `local-multicloud.env.example`

Variables:

- `CLOUD_BACKEND_URL`
  - URL base del backend publicado en Google Cloud
  - Ejemplo: `http://34.122.37.25`

- `LOCAL_BACKEND_URL`
  - URL base para un backend local ya expuesto en tu host
  - Ejemplo recomendado con el compose principal actual: `http://host.docker.internal:8787`

- `LOCAL_GATEWAY_PORT`
  - Puerto host del gateway local
  - Valor por defecto: `8089`

- `LOCAL_PROMETHEUS_PORT`
  - Puerto host de Prometheus cuando actives el perfil `observability`
  - Valor por defecto: `9091`

Importante:

- No pongas barra final en `CLOUD_BACKEND_URL` ni en `LOCAL_BACKEND_URL`.
- No copies secretos reales a este archivo.
- Si usas `host.docker.internal`, el compose ya incluye `host-gateway` para Linux Docker moderno.

## Comandos seguros

Preparar variables desde el ejemplo:

```bash
cp local-multicloud.env.example .env.local-multicloud
```

Validacion de YAML:

```bash
docker compose --env-file .env.local-multicloud -f docker-compose.local-multicloud.yml config
```

Arranque del stack base:

```bash
docker compose --env-file .env.local-multicloud -f docker-compose.local-multicloud.yml up -d --build
```

Arranque con observabilidad:

```bash
docker compose --env-file .env.local-multicloud --profile observability -f docker-compose.local-multicloud.yml up -d --build
```

Estado:

```bash
docker compose --env-file .env.local-multicloud -f docker-compose.local-multicloud.yml ps
```

Logs:

```bash
docker compose --env-file .env.local-multicloud -f docker-compose.local-multicloud.yml logs -f
```

Parada segura:

```bash
docker compose --env-file .env.local-multicloud -f docker-compose.local-multicloud.yml down
```

No usar:

```bash
docker compose --env-file .env.local-multicloud -f docker-compose.local-multicloud.yml down -v
```

## Verificaciones recomendadas

Ver puertos ocupados antes de levantar el stack:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}'
ss -ltnp
```

Verificar el gateway:

```bash
curl -i http://127.0.0.1:8089/healthz
curl -i http://127.0.0.1:8089/gateway/aws/
curl -i http://127.0.0.1:8089/gateway/azure/
```

Verificar salida hacia Google Cloud:

```bash
curl -i http://127.0.0.1:8089/gateway/core/
```

Verificar salida hacia backend local:

```bash
curl -i http://127.0.0.1:8089/gateway/core-local/
```

## Decisiones de seguridad

- No se modifica `docker-compose.yml` principal.
- No se cambian puertos del stack principal.
- No se eliminan contenedores, imagenes ni volumenes.
- No se usa `down -v`.
- No se copia ningun secreto real del repo.

## Limitaciones conocidas

- Este stack no comparte automaticamente la red Docker del compose principal. Para evitar acoplar el sistema actual, la integracion con un backend/gateway local se hace por puertos publicados del host.
- Si en el futuro quieres trafico contenedor a contenedor sin pasar por puertos del host, conviene crear una red Docker externa comun y conectar ambos stacks de forma controlada.
