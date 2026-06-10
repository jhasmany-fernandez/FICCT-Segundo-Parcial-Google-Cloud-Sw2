# ESTRATEGIA DOCKER Y MICROSERVICIOS

## Objetivo
Documentar la estrategia de contenedorizacion del sistema final y el camino de despliegue hacia una arquitectura distribuida en tres microservicios, con ejecucion local en Docker Compose y despliegue posterior en VMs separadas de Google Cloud, AWS y Azure.

## Alcance
Este documento no modifica la configuracion actual del repositorio. Solo define la estrategia objetivo para:

- desarrollo local
- integracion entre microservicios
- variables de entorno
- puertos
- responsabilidades
- despliegue futuro por nube

## 1. Arquitectura local con Docker Compose

### Estado actual del proyecto
El repositorio ya levanta localmente con:

- `db` -> PostgreSQL
- `backend` -> FastAPI
- `frontend` -> Angular

Puertos actuales validados:

- PostgreSQL: `5454 -> 5432`
- Backend: `80 -> 8000`
- Backend alterno: `8787 -> 8000`
- Frontend: `5656 -> 5656`

### Arquitectura local objetivo
Durante la evolucion a microservicios, localmente conviene operar con un `docker-compose` extendido, pero manteniendo el stack actual como base.

Arquitectura local recomendada:

- `frontend`
- `ms1-core-api`
- `ms1-core-db`
- `ms2-ia-api`
- `ms3-tracking-api`
- `ms3-n8n`
- servicios simulados o reales externos segun etapa:
  - `minio` o S3 real para pruebas
  - DynamoDB local opcional
  - mock de blockchain opcional

### Objetivo del entorno local

- desarrollar cada microservicio de forma aislada
- probar integracion end-to-end sin depender de la nube
- validar contratos HTTP/GraphQL entre servicios
- mantener reproducibilidad del entorno para frontend, mobile y backend

## 2. Arquitectura futura en cloud

### Distribucion objetivo por proveedor

- `MS1 Core FastAPI + GraphQL + PostgreSQL` en `Google Cloud`
- `MS2 IA y Multimedia NodeJS/TypeScript + S3 + OpenAI API` en `AWS`
- `MS3 Seguimiento Spring Boot + DynamoDB + FCM + n8n + Blockchain` en `Azure`

### Topologia objetivo

- Una VM principal por microservicio como minimo
- Red privada o tunel seguro entre VMs
- Exposicion publica controlada solo para endpoints necesarios
- Certificados TLS en cada entrada publica
- API Gateway o reverse proxy por servicio segun etapa

### Flujo general entre nubes

1. El `frontend web core` y la `app movil` consumen `MS1 Core`.
2. `MS1 Core` centraliza autenticacion, clientes, vehiculos, sucursales, tecnicos, emergencias y asignaciones.
3. `MS1 Core` invoca a `MS2 IA` para:
   - transcripcion
   - clasificacion
   - analisis multimedia
4. `MS1 Core` publica eventos o invoca a `MS3 Seguimiento` para:
   - tracking
   - notificaciones
   - automatizacion
   - auditoria extendida
   - blockchain

## 3. Contenedores necesarios

### Locales minimos

#### MS1 Core

- `frontend`
- `ms1-core-api`
- `ms1-core-db`

#### MS2 IA

- `ms2-ia-api`
- `minio` opcional en local si no se usa AWS S3 real

#### MS3 Seguimiento

- `ms3-tracking-api`
- `ms3-n8n`
- `dynamodb-local` opcional para desarrollo

### Futuros contenedores sugeridos por servicio

#### MS1 Core en Google Cloud

- `ms1-core-api`
- `ms1-core-worker` opcional
- PostgreSQL administrado o contenedor temporal solo en entornos no productivos
- reverse proxy opcional

#### MS2 IA en AWS

- `ms2-ia-api`
- `ms2-ia-worker` opcional para colas pesadas
- almacenamiento externo en S3

#### MS3 Seguimiento en Azure

- `ms3-tracking-api`
- `ms3-event-worker` opcional
- `n8n`
- integracion con DynamoDB externo

## 4. Puertos locales

### Puertos actuales validados

- `frontend`: `5656`
- `ms1-core-api` actual: `8787`
- `ms1-core-api` actual alterno: `80`
- `postgres`: `5454`

### Puertos locales recomendados a futuro

- `frontend`: `5656`
- `ms1-core-api`: `8787`
- `ms1-graphql`: mismo contenedor MS1 por `/graphql`
- `ms1-postgres`: `5454`
- `ms2-ia-api`: `8790`
- `ms3-tracking-api`: `8795`
- `ms3-n8n`: `5678`
- `dynamodb-local` opcional: `8001`
- `minio` opcional:
  - API `9000`
  - consola `9001`

### Regla recomendada
Evitar superponer puertos entre microservicios. Mantener numeracion consistente por dominio para facilitar debug local.

## 5. Variables de entorno por servicio

## MS1 Core FastAPI + GraphQL

Variables base derivadas del proyecto actual:

- `APP_NAME`
- `APP_ENV`
- `APP_DEBUG`
- `API_PREFIX`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_CONNECT_TIMEOUT`
- `UPLOADS_DIR`
- `PROTECTED_ADMIN_EMAIL`
- `PROTECTED_ADMIN_PASSWORD`
- `PROTECTED_ADMIN_FULL_NAME`
- `PROTECTED_ADMIN_PHONE`
- `WORKSHOP_INITIAL_PASSWORD`
- `FCM_ENABLED`
- `FIREBASE_CREDENTIALS_PATH`

Variables nuevas recomendadas:

- `JWT_SECRET`
- `JWT_ACCESS_EXPIRES_MINUTES`
- `JWT_REFRESH_EXPIRES_DAYS`
- `GRAPHQL_ENABLED`
- `GRAPHQL_PATH`
- `MS2_IA_BASE_URL`
- `MS3_TRACKING_BASE_URL`
- `CORS_ALLOWED_ORIGINS`
- `PUBLIC_BASE_URL`

## MS2 IA y Multimedia NodeJS/TypeScript

- `NODE_ENV`
- `PORT`
- `OPENAI_API_KEY`
- `OPENAI_MODEL_TRANSCRIPTION`
- `OPENAI_MODEL_VISION`
- `AWS_REGION`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_UPLOADS`
- `S3_BUCKET_PROCESSED`
- `MS1_CALLBACK_URL` opcional
- `MS1_SHARED_TOKEN` o firma entre servicios
- `MAX_UPLOAD_SIZE_MB`

## MS3 Seguimiento Spring Boot

- `SPRING_PROFILES_ACTIVE`
- `SERVER_PORT`
- `MS1_CORE_BASE_URL`
- `MS1_SHARED_TOKEN`
- `AWS_REGION` si consume DynamoDB real
- `DYNAMODB_ENDPOINT` para local o testing
- `FCM_ENABLED`
- `FIREBASE_CREDENTIALS_PATH`
- `N8N_BASE_URL`
- `BLOCKCHAIN_ENABLED`
- `BLOCKCHAIN_RPC_URL`
- `BLOCKCHAIN_PRIVATE_KEY` o mecanismo equivalente seguro

## n8n

- `N8N_HOST`
- `N8N_PORT`
- `N8N_PROTOCOL`
- `N8N_BASIC_AUTH_ACTIVE`
- `N8N_BASIC_AUTH_USER`
- `N8N_BASIC_AUTH_PASSWORD`
- `WEBHOOK_URL`

## 6. Comunicacion local entre contenedores

### Regla de red local
Todos los contenedores deben vivir en la misma red Docker local o en redes conectadas explicitamente.

### Comunicacion recomendada

- `frontend` -> `ms1-core-api`
- `ms1-core-api` -> `ms1-core-db`
- `ms1-core-api` -> `ms2-ia-api`
- `ms1-core-api` -> `ms3-tracking-api`
- `ms3-tracking-api` -> `n8n`
- `ms2-ia-api` -> `minio` o S3 real

### Forma recomendada
Usar nombres de servicio Docker como hostnames:

- `db`
- `backend` o futuro `ms1-core-api`
- `ms2-ia-api`
- `ms3-tracking-api`
- `n8n`

### Contratos recomendados

- HTTP/REST para comandos simples
- GraphQL en MS1 para agregacion de lecturas
- Webhooks firmados para callbacks
- Tokens internos o firmas HMAC entre microservicios

## 7. Comunicacion futura entre VMs

### Recomendacion principal
La comunicacion entre nubes no debe depender de IPs abiertas sin control. Debe existir:

- TLS
- autenticacion de servicio a servicio
- allowlists
- secretos rotados
- logs centralizados

### Esquema recomendado

- `MS1` expone API publica para web/mobile
- `MS2` y `MS3` exponen solo endpoints necesarios y preferiblemente privados
- `MS1` actua como orquestador principal
- `MS2` y `MS3` responden por contratos controlados

### Opciones de conexion

#### Opcion A
APIs publicas protegidas por:

- HTTPS
- API keys internas
- JWT de servicio
- firewall por IP

#### Opcion B
Red privada entre VMs usando:

- VPN site-to-site
- WireGuard
- VPC peering si la estrategia multicloud lo permite

### Recomendacion de implementacion
Comenzar con `HTTPS + auth de servicio + firewall restrictivo` y evolucionar luego a una red privada entre VMs si el volumen y la criticidad aumentan.

## 8. Responsabilidad de cada microservicio

## MS1 Core en Google Cloud

Responsabilidad:

- autenticacion web/mobile
- usuarios y roles
- clientes
- vehiculos
- sucursales
- tecnicos vehiculares
- emergencias
- asignaciones
- eventos basicos de seguimiento
- evidencias y bitacora base
- API REST principal
- GraphQL para lecturas agregadas

No debe asumir:

- procesamiento pesado de IA
- automatizaciones complejas
- logica de blockchain

## MS2 IA y Multimedia en AWS

Responsabilidad:

- recepcion y analisis de audio, imagen y multimedia
- transcripcion
- clasificacion de incidentes
- enriquecimiento de datos
- persistencia de archivos procesados en S3
- devolucion de resultados a MS1

No debe asumir:

- autenticacion principal de usuarios
- gestion empresarial core

## MS3 Seguimiento en Azure

Responsabilidad:

- tracking y eventos operativos avanzados
- automatizacion de procesos
- integracion con FCM
- orquestacion via n8n
- almacenamiento de eventos en DynamoDB
- anclaje o registro hash en blockchain

No debe asumir:

- administracion principal de clientes, sucursales o vehiculos
- procesamiento multimedia pesado

## 9. Orden recomendado de implementacion

1. Consolidar `MS1 Core` con la arquitectura actual.
2. Mantener `frontend + MS1 + PostgreSQL` como stack estable en Docker Compose.
3. Introducir GraphQL dentro de MS1 sin romper REST.
4. Extraer clientes HTTP internos para `MS2` y `MS3`.
5. Levantar `MS2 IA` localmente como servicio aislado.
6. Levantar `MS3 Seguimiento` localmente con API minima.
7. Definir contratos de integracion y autenticacion entre servicios.
8. Probar integracion end-to-end local.
9. Desplegar `MS1` primero en Google Cloud.
10. Desplegar `MS2` despues en AWS.
11. Desplegar `MS3` despues en Azure.
12. Activar automatizaciones, FCM y blockchain al final, no al principio.

## 10. Riesgos y precauciones

### Riesgos tecnicos

- acoplar demasiado temprano el frontend a multiples microservicios
- romper el backend actual antes de consolidar MS1
- mezclar autenticacion de usuario final con autenticacion entre servicios
- depender de recursos cloud no disponibles en desarrollo local
- exponer secretos en contenedores o repositorio
- usar puertos inconsistentes entre local y cloud
- duplicar logica de negocio entre MS1, MS2 y MS3

### Riesgos operativos

- latencia entre nubes
- costos por trafico entre proveedores
- dificultad de observabilidad distribuida
- troubleshooting mas complejo entre tres clouds
- diferencias de politicas IAM entre Google Cloud, AWS y Azure

### Precauciones recomendadas

- centralizar el dominio core en MS1
- versionar contratos entre microservicios
- definir timeouts y retries controlados
- usar correlation IDs para trazabilidad
- implementar logs estructurados
- separar secretos por entorno
- no desplegar blockchain ni automatizaciones pesadas antes de estabilizar el Core
- preferir feature flags para integraciones nuevas

## Recomendacion final

La mejor estrategia es evolucionar el proyecto actual de forma progresiva:

- primero `MS1 Core` estable
- luego integraciones desacopladas
- despues despliegue multicloud controlado

El repositorio actual ya sirve como base del `MS1 Core`. La contenedorizacion futura debe preservar ese rol central y evitar que la complejidad de `MS2` y `MS3` contamine demasiado pronto el backend actual.
