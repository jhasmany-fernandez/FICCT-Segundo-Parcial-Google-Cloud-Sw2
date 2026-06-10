# Guía de Exposición del Proyecto

## 1. Presentación inicial

Texto sugerido para decir:

"Este proyecto es una arquitectura distribuida para gestión de emergencias vehiculares. Integra un frontend, un backend Core, microservicios, mensajería asíncrona, almacenamiento de evidencias, análisis con IA, observabilidad, Kubernetes y CI/CD."

## 2. Problema que resuelve

Este sistema busca resolver un flujo moderno de gestión de emergencias vehiculares:

- recepción de solicitudes de emergencia
- procesamiento centralizado desde el Core
- manejo de evidencias multimedia
- análisis automático de texto, imagen y audio
- monitoreo del estado técnico del sistema

Texto sugerido para decir:

"La idea del proyecto es no quedarse solo en registrar una emergencia, sino también preparar la plataforma para analizar evidencias, desacoplar procesos, monitorear servicios y dejar una base lista para crecer."

## 3. Arquitectura general

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
        ├── OpenAI / fallback
        ├── MinIO/S3
        └── /metrics
Prometheus → Grafana
```

Texto sugerido para decir:

"La arquitectura separa responsabilidades. El frontend atiende al usuario, el Core concentra la lógica principal, los microservicios resuelven tareas especializadas, RabbitMQ desacopla procesos, MinIO guarda evidencias y Prometheus con Grafana permiten observar el comportamiento del sistema."

## 4. Componentes principales y qué decir

### Frontend

Qué decir:

- Es la interfaz de usuario.
- Permite interactuar con el sistema.
- Se ejecuta en el puerto `5656`.

Frase sugerida:

"El frontend representa la capa visible del sistema y sirve como punto de entrada para el usuario."

### Core FastAPI

Qué decir:

- Es el núcleo del negocio.
- Gestiona autenticación, usuarios, rutas principales e integración con servicios externos.
- Expone `/api/health`.
- Se ejecuta en el puerto `8787`.

Frase sugerida:

"El Core FastAPI centraliza la lógica funcional y coordina tanto persistencia como integración con otros servicios."

### MS IA Multimedia

Qué decir:

- Es un microservicio especializado en análisis multimedia.
- Procesa texto, imágenes, audio y evidencias.
- Tiene fallback si no existe `OPENAI_API_KEY`.
- Se ejecuta en el puerto `8090`.

Frase sugerida:

"Este microservicio concentra las funciones avanzadas de IA y multimedia, pero mantiene un fallback controlado para funcionar incluso sin proveedor externo."

### RabbitMQ

Qué decir:

- Permite comunicación asíncrona.
- Core publica mensajes.
- MS IA consume mensajes de la cola `emergency.analysis.requested`.

Frase sugerida:

"RabbitMQ nos permite desacoplar al Core del procesamiento posterior, evitando que todo dependa de llamadas síncronas."

### MinIO/S3

Qué decir:

- Almacena evidencias multimedia.
- Simula almacenamiento tipo S3 local.
- Usa bucket `emergencias-evidencias`.

Frase sugerida:

"MinIO nos da una capa de almacenamiento compatible con S3 para trabajar localmente con archivos y evidencias."

### Prometheus y Grafana

Qué decir:

- Prometheus recolecta métricas.
- Grafana permite visualizar esas métricas.
- MS IA expone `/metrics`.

Frase sugerida:

"Con observabilidad básica podemos demostrar que la arquitectura no solo funciona, sino que además puede medirse y monitorearse."

### Kubernetes

Qué decir:

- Se prepararon manifests básicos para una futura ejecución en Kubernetes local.
- No es despliegue cloud real todavía.

Frase sugerida:

"La carpeta Kubernetes no representa un despliegue productivo final, pero sí una base concreta para evolucionar hacia orquestación real."

### GitHub Actions

Qué decir:

- Automatiza validaciones.
- Revisa Python, Node, YAML, Kubernetes y Docker Compose.

Frase sugerida:

"GitHub Actions refuerza la calidad técnica del proyecto validando automáticamente la consistencia de varias capas."

## 5. Comandos para levantar el sistema

```bash
docker compose -f docker-compose.integracion.yml up --build -d

docker compose -f docker-compose.gateway.yml up --build -d

docker compose -f docker-compose.observabilidad.yml up --build -d
```

Texto sugerido para decir:

"Con estos tres comandos levantamos la capa de integración, el gateway y la observabilidad."

## 6. Puertos importantes

| Componente | URL |
|---|---|
| Frontend | http://localhost:5656 |
| Core FastAPI | http://localhost:8787 |
| MS IA Multimedia | http://localhost:8090 |
| RabbitMQ Management | http://localhost:15672 |
| MinIO Console | http://localhost:9001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3006 |
| Gateway | http://localhost:8088 |

## 7. Demo paso a paso

### Paso 1: Mostrar frontend

Abrir:

`http://localhost:5656`

Qué decir:

"Esta es la interfaz principal del sistema."

### Paso 2: Verificar backend

Endpoint:

`GET http://localhost:8787/api/health`

Respuesta esperada:

```json
{"status":"ok","environment":"development","database":"connected"}
```

Qué decir:

"Esto demuestra que el Core FastAPI está activo y conectado a la base de datos."

### Paso 3: Verificar MS IA

Endpoint:

`GET http://localhost:8090/health`

Respuesta esperada:

```json
{"status":"ok","service":"ms-ia-multimedia"}
```

Qué decir:

"Esto demuestra que el microservicio multimedia está activo."

### Paso 4: Probar análisis de texto

Endpoint:

`POST http://localhost:8090/analyze/emergency`

Qué decir:

"Este endpoint analiza una descripción de emergencia. Si no hay clave externa de IA, responde con fallback controlado."

### Paso 5: Probar Core hacia IA

Endpoint:

`POST http://localhost:8787/api/integrations/ia/analyze-test`

Qué decir:

"Este endpoint demuestra comunicación HTTP entre el Core y el microservicio IA."

### Paso 6: Probar RabbitMQ

Endpoint:

`POST http://localhost:8787/api/integrations/ia/queue-test`

Qué decir:

"Core publica un mensaje en RabbitMQ y el microservicio IA lo consume de forma asíncrona."

### Paso 7: Probar MinIO

Endpoint:

`POST http://localhost:8090/evidence/upload-test`

Qué decir:

"Este endpoint sube una evidencia al bucket emergencias-evidencias en MinIO."

### Paso 8: Probar análisis de imagen

Endpoint:

`POST http://localhost:8090/analyze/image-test`

Qué decir:

"Este endpoint recibe una imagen y devuelve un análisis visual estructurado."

### Paso 9: Probar análisis de audio

Endpoint:

`POST http://localhost:8090/analyze/audio-test`

Qué decir:

"Este endpoint recibe audio y devuelve una transcripción y análisis estructurado usando fallback si no hay IA externa."

### Paso 10: Mostrar Prometheus

Abrir:

`http://localhost:9090`

Mostrar targets:

`http://localhost:9090/api/v1/targets`

Qué decir:

"Prometheus monitorea sus propios servicios y el microservicio IA."

### Paso 11: Mostrar Grafana

Abrir:

`http://localhost:3006`

Qué decir:

"Grafana se usa para visualizar métricas."

## 8. Qué validaciones finales se hicieron

- `py_compile OK`
- `docker compose config OK`
- `K8S_YAML_OK`
- `WORKFLOWS_YAML_OK`
- `Backend health OK`
- `Frontend OK`
- `RabbitMQ consumer OK`
- `MinIO upload OK`
- `Prometheus targets UP`

## 9. Qué no incluye todavía

- No hay despliegue cloud real.
- No hay Helm.
- No hay Terraform.
- No hay TLS/cert-manager.
- No hay secretos reales.
- La IA real depende de configurar `OPENAI_API_KEY`.

Texto sugerido para decir:

"La arquitectura ya está preparada para escalar, pero todavía no se llevó a un despliegue cloud real ni a una configuración de secretos productivos."

## 10. Cierre de exposición

Texto sugerido para decir:

"En conclusión, este proyecto no solo implementa una aplicación funcional, sino una base arquitectónica distribuida lista para evolucionar hacia un entorno cloud-native. Integra backend, frontend, microservicios, mensajería, almacenamiento, IA, observabilidad, Kubernetes y CI/CD."
