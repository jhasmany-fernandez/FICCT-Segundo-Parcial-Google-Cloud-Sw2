# Arquitectura Final del Proyecto

## Resumen

Este proyecto consolida una arquitectura distribuida para gestión de emergencias vehiculares. La solución integra un Core en FastAPI, un frontend web, microservicios dockerizados, un API Gateway, mensajería asíncrona con RabbitMQ, almacenamiento de evidencias con MinIO/S3, capacidades de IA multimedia, observabilidad con Prometheus y Grafana, manifests base para Kubernetes y validaciones automáticas con GitHub Actions.

## Componentes principales

- Frontend
  Interfaz web principal del sistema. Expone la experiencia de usuario y consume los endpoints del backend.

- Core FastAPI
  Servicio central con lógica principal del dominio, autenticación JWT, forgot-password seguro, endpoints de integración y comunicación con otros componentes.

- MS IA Multimedia
  Microservicio para análisis de texto, imagen y audio. También expone métricas, consume RabbitMQ y sube evidencias a MinIO.

- MS Seguimiento Automatización
  Microservicio base para flujos complementarios de seguimiento y automatización.

- API Gateway
  Gateway Nginx para centralizar acceso local a Core y microservicios.

- PostgreSQL
  Base de datos principal usada por el Core.

- RabbitMQ
  Broker de mensajería para desacoplar publicación y consumo de eventos.

- MinIO/S3
  Almacenamiento compatible con S3 para evidencias multimedia.

- Prometheus
  Recolección de métricas técnicas del sistema, incluyendo `ms-ia-multimedia`.

- Grafana
  Visualización de métricas a partir de Prometheus.

- Kubernetes manifests
  Carpeta `k8s/` con manifests básicos para ejecución local en entornos tipo kind, minikube o Docker Desktop Kubernetes.

- GitHub Actions
  Workflows de CI/CD básico para validar sintaxis, YAML y configuraciones Docker Compose.

## Arquitectura general

```text
Usuario
  ↓
Frontend
  ↓
API Gateway
  ↓
Core FastAPI
  ├── PostgreSQL
  ├── RabbitMQ
  └── MS IA Multimedia
        ├── OpenAI/fallback
        ├── MinIO/S3
        └── /metrics

Prometheus → Grafana
```

## Flujos principales

1. Login y seguridad JWT
   El usuario autentica contra el Core FastAPI. El Core valida credenciales y emite token JWT para endpoints protegidos.

2. Forgot-password seguro
   El Core expone endpoints de solicitud y reseteo de contraseña con flujo seguro y compatibilidad con endpoint legacy.

3. Core hacia MS IA por HTTP
   El Core puede invocar directamente al MS IA Multimedia mediante `POST /api/integrations/ia/analyze-test`.

4. Core hacia RabbitMQ
   El Core publica eventos en la cola `emergency.analysis.requested` con `POST /api/integrations/ia/queue-test`.

5. MS IA consume mensajes
   El MS IA Multimedia se conecta a RabbitMQ, consume mensajes y registra el consumo por logs.

6. Upload de evidencias a MinIO
   El MS IA Multimedia recibe archivos multipart y los sube al bucket `emergencias-evidencias`.

7. Análisis de texto
   `POST /analyze/emergency` devuelve análisis estructurado. Si no existe `OPENAI_API_KEY`, usa fallback controlado.

8. Análisis de imagen
   `POST /analyze/image-test` valida imagen, acepta `jpeg`, `png` y `webp`, e intenta análisis visual o fallback.

9. Análisis de audio
   `POST /analyze/audio-test` valida audio, acepta `mpeg`, `mp3`, `wav`, `webm` y `ogg`, y devuelve transcripción/análisis o fallback.

10. Observabilidad con Prometheus/Grafana
    `ms-ia-multimedia` expone `/metrics`, Prometheus scrapea métricas y Grafana consume Prometheus como datasource.

## Comandos de ejecución

```bash
docker compose -f docker-compose.integracion.yml up --build -d
docker compose -f docker-compose.gateway.yml up --build -d
docker compose -f docker-compose.observabilidad.yml up --build -d
```

## Puertos principales

- Frontend: http://localhost:5656
- Core FastAPI: http://localhost:8787
- MS IA Multimedia: http://localhost:8090
- MinIO Console: http://localhost:9001
- RabbitMQ Management: http://localhost:15672
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3006
- Gateway: http://localhost:8088

## Endpoints de prueba

- `GET /api/health`
- `GET /health`
- `GET /metrics`
- `POST /api/integrations/ia/analyze-test`
- `POST /api/integrations/ia/queue-test`
- `POST /analyze/emergency`
- `POST /analyze/image-test`
- `POST /analyze/audio-test`
- `POST /evidence/upload-test`

## Validaciones finales realizadas

- `py_compile OK`
- `docker compose config OK`
- `K8S_YAML_OK`
- `WORKFLOWS_YAML_OK`
- `Backend health OK`
- `Frontend OK`
- `RabbitMQ consumer OK`
- `MinIO upload OK`
- `Prometheus targets UP`

## Kubernetes

La carpeta `k8s/` contiene manifests básicos para ejecución local. Incluye namespace, configmaps, secrets de ejemplo, deployments y services mínimos para los componentes principales.

Las imágenes propias definidas en esos manifests son placeholders como:

- `ficct-backend:local`
- `ficct-frontend:local`
- `ficct-ms-ia-multimedia:local`
- `ficct-gateway:local`

Antes de ejecutar en un cluster local, esas imágenes deben construirse y cargarse en el cluster o reemplazarse por imágenes reales publicadas.

## CI/CD

Workflows disponibles en `.github/workflows/`:

- `ci.yml`
  Valida backend Python, frontend, `ms-ia-multimedia`, YAML del repositorio y manifests de Kubernetes.

- `docker-config.yml`
  Ejecuta `docker compose config` sobre los archivos Compose existentes y prepara placeholders temporales para archivos locales requeridos por la validación.

## Alcance y limitaciones

- No hay despliegue cloud real.
- No hay Helm.
- No hay Terraform.
- No hay TLS ni cert-manager.
- La IA funciona con fallback si no existe `OPENAI_API_KEY`.
- Los secretos incluidos en documentación y manifests son placeholders.

## Guía rápida de exposición

1. Presentar la arquitectura general y explicar el rol del Core, frontend y microservicios.
2. Mostrar los `docker-compose` principales y qué levanta cada uno.
3. Mostrar el health del backend en `GET /api/health`.
4. Mostrar el MS IA Multimedia con `GET /health` y `POST /analyze/emergency`.
5. Mostrar RabbitMQ publicando y consumiendo mensajes.
6. Mostrar MinIO recibiendo evidencias multimedia.
7. Mostrar Prometheus y Grafana con métricas del MS IA.
8. Explicar que Kubernetes y CI/CD ya tienen base mínima preparada para evolución futura.
