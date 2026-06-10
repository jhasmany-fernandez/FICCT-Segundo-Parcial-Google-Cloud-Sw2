# AUDITORIA DE MODULARIZACION DEL BACKEND

## 1. Resumen ejecutivo

`backend/app/main.py` concentra hoy demasiadas responsabilidades para un Core FastAPI de produccion:

- configuracion de la aplicacion
- startup e inicializacion de base de datos
- modelos Pydantic
- helpers de seguridad
- helpers de uploads
- integracion OpenAI y Whisper
- integracion Firebase FCM
- autenticacion y login
- forgot-password legacy y seguro
- CRUDs de clientes, vehiculos, workshops, tecnicos y emergencias

El archivo tiene aproximadamente:

- `2566` lineas
- `27` modelos Pydantic definidos localmente
- `31` funciones auxiliares internas antes de los endpoints
- `33` rutas HTTP registradas directamente en `main.py`

La buena noticia es que el repositorio ya tiene una base parcial para modularizar:

- `backend/app/routes/`
- `backend/app/schemas.py`
- `backend/app/core/`
- `backend/app/security.py`

Sin embargo, esa estructura todavia no es la fuente real de verdad. Hoy la aplicacion sigue dependiendo principalmente de `main.py`, por lo que la modularizacion debe ser progresiva y con extracciones pequenas.

## 2. Mapa actual de responsabilidades de main.py

## Infraestructura y bootstrap

- crea `FastAPI`
- configura CORS
- monta archivos estaticos
- inicializa uploads locales
- inicializa BD en `startup`

## Integraciones externas

- OpenAI para clasificacion de fotos
- Whisper para transcripcion de audio
- Firebase Admin para FCM

## Seguridad y autenticacion

- login admin, workshop y client
- bloqueo de intentos fallidos
- `GET /api/auth/me`
- forgot-password legacy
- forgot-password seguro nuevo

## Dominio de negocio

- clientes
- vehiculos
- workshops o sucursales legacy
- tecnicos
- emergencias
- asignacion de tecnicos
- tokens FCM

## Archivos y multimedia

- guardado y borrado de fotos de vehiculos
- guardado y borrado de fotos y audio de emergencias
- transformacion de paths a URLs publicas

## 3. Imports principales

## Dependencias de FastAPI y framework

- `FastAPI`
- `File`, `Form`, `UploadFile`
- `HTTPException`, `Query`, `Security`
- `CORSMiddleware`
- `StaticFiles`
- `BaseModel`, `Field`, `EmailStr`, `AliasChoices`, `model_validator`

## Dependencias desde `app.db`

`main.py` importa una cantidad alta de operaciones DB:

- creacion: `create_client`, `create_vehicle`, `create_workshop_registration`, `create_technician`, `create_emergency_report`
- lectura: `get_client_by_email`, `get_client_by_id`, `get_vehicle_by_id`, `get_workshop_by_email`, `get_workshop_by_id`, `get_technician_by_workshop`, `list_clients`, `list_vehicles`, `list_workshop_registrations`, `list_technicians`, `list_technicians_by_workshop`, `list_emergency_reports`, `list_active_device_fcm_tokens`
- actualizacion: `update_client`, `update_client_password`, `update_client_status`, `update_vehicle`, `update_workshop_registration`, `update_workshop_password`, `update_workshop_approval_status_with_password`, `update_technician`, `update_technician_for_workshop`, `update_emergency_status`, `upsert_device_fcm_token`
- borrado: `delete_client`, `delete_vehicle`, `delete_workshop_registration`, `delete_technician`, `delete_technician_for_workshop`, `delete_emergency_report`
- otros: `assign_emergency_technician`, `check_database_connection`, `init_database`

Esto confirma un acoplamiento fuerte entre capa HTTP y capa de persistencia.

## Dependencias desde `app.security`

Hoy `main.py` importa solo helpers del forgot-password seguro:

- `create_password_reset_token as issue_password_reset_token`
- `verify_password_reset_token`
- `mark_password_reset_token_used`

Pero ademas define internamente otras funciones de seguridad que deberian salir:

- `hash_password`
- `verify_password`
- `login_attempt_key`
- `ensure_login_not_locked`
- `register_failed_login_attempt`
- `reset_login_attempts`

## Dependencias desde `app.core.dependencies`

- `AuthenticatedUser`
- `create_access_token`
- `get_current_active_user`
- `require_roles`

Estas ya son buenas candidatas a quedarse en `core/`.

## 4. Tabla de endpoints por modulo

| Modulo | Metodo | Endpoint | Handler |
|---|---|---|---|
| `health` | `GET` | `/` | `read_root` |
| `health` | `GET` | `/api/health` | `healthcheck` |
| `fcm` | `POST` | `/api/devices/fcm-token` | `register_device_fcm_token` |
| `workshops` | `POST` | `/api/workshops` | `register_workshop` |
| `workshops` | `GET` | `/api/workshops` | `get_workshops` |
| `workshops` | `POST` | `/api/workshops/change-password` | `change_workshop_password` |
| `workshops` | `POST|PUT` | `/api/workshops/forgot-password` | `forgot_workshop_password` |
| `workshops` | `PUT` | `/api/workshops/{workshop_id}` | `edit_workshop` |
| `workshops` | `PUT` | `/api/workshops/{workshop_id}/approval-status` | `edit_workshop_approval_status` |
| `workshops` | `DELETE` | `/api/workshops/{workshop_id}` | `remove_workshop` |
| `clientes` | `POST` | `/api/clientes` | `register_client` |
| `clientes` | `GET` | `/api/clientes` | `get_clients` |
| `clientes` | `POST` | `/api/clientes/change-password` | `change_client_password` |
| `clientes` | `POST|PUT` | `/api/clientes/forgot-password` | `forgot_client_password` |
| `clientes` | `PUT` | `/api/clientes/{client_id}/status` | `edit_client_status` |
| `clientes` | `PUT` | `/api/clientes/{client_id}` | `edit_client` |
| `clientes` | `DELETE` | `/api/clientes/{client_id}` | `remove_client` |
| `vehiculos` | `POST` | `/api/vehiculos` | `register_vehicle` |
| `vehiculos` | `GET` | `/api/vehiculos` | `get_vehicles` |
| `vehiculos` | `PUT` | `/api/vehiculos/{vehicle_id}` | `edit_vehicle` |
| `vehiculos` | `DELETE` | `/api/vehiculos/{vehicle_id}` | `remove_vehicle` |
| `emergencias` | `POST` | `/api/emergencias` | `register_emergency` |
| `emergencias` | `GET` | `/api/emergencias` | `get_emergency_reports` |
| `emergencias` | `PUT` | `/api/emergencias/{report_id}/status` | `edit_emergency_status` |
| `asignaciones` | `PUT` | `/api/emergencias/{report_id}/technician-assignment` | `assign_technician_to_emergency` |
| `emergencias` | `DELETE` | `/api/emergencias/{report_id}` | `remove_emergency_report` |
| `auth` | `POST` | `/api/auth/login` | `login` |
| `auth` | `POST` | `/api/auth/account-type` | `lookup_account_type` |
| `auth` | `GET` | `/api/auth/me` | `get_authenticated_user_profile` |
| `forgot-password` | `POST` | `/api/auth/forgot-password/request` | `request_password_reset` |
| `forgot-password` | `POST` | `/api/auth/forgot-password/reset` | `reset_password_with_token` |
| `forgot-password` | `POST|PUT` | `/api/auth/forgot-password` | `forgot_password` |
| `tecnicos` | `POST` | `/api/technicians` | `register_technician` |
| `tecnicos` | `GET` | `/api/technicians` | `get_technicians` |
| `tecnicos` | `PUT` | `/api/technicians/{technician_id}` | `edit_technician` |
| `tecnicos` | `DELETE` | `/api/technicians/{technician_id}` | `remove_technician` |

## 5. Tabla de modelos Pydantic por modulo

| Modulo | Modelos actuales en `main.py` |
|---|---|
| `workshops` | `WorkshopRegistrationCreate`, `WorkshopRegistrationResponse`, `WorkshopApprovalStatusUpdate`, `WorkshopPasswordChangeRequest`, `WorkshopForgotPasswordRequest` |
| `tecnicos` | `TechnicianBase`, `TechnicianCreate` |
| `clientes` | `ClientRegistrationCreate`, `ClientRegistrationResponse`, `ClientPasswordChangeRequest`, `ClientForgotPasswordRequest`, `ClientStatusUpdate`, `ClientUpdate` |
| `auth` | `LoginRequest`, `AccountTypeLookupRequest`, `AccountTypeLookupResponse`, `LoginResponse`, `AuthMeResponse` |
| `forgot-password` | `UnifiedForgotPasswordRequest`, `PasswordResetRequestCreate`, `PasswordResetRequestResponse`, `PasswordResetConfirmRequest`, `PasswordResetConfirmResponse` |
| `vehiculos` | `VehicleResponse` |
| `emergencias` | `EmergencyReportResponse`, `EmergencyStatusUpdate`, `EmergencyTechnicianAssignmentRequest` |
| `fcm` | `DeviceFcmTokenCreate`, `DeviceFcmTokenResponse` |

Nota importante:

- ya existe `backend/app/schemas.py`
- una parte de estos modelos ya existe duplicada o parcialmente migrada ahi

Eso vuelve prioritaria una consolidacion de `schemas/` antes de mover rutas mas complejas.

## 6. Tabla de funciones auxiliares por modulo

| Modulo | Helpers actuales en `main.py` |
|---|---|
| `auth` | `hash_password`, `verify_password`, `login_attempt_key`, `get_login_attempt_state`, `ensure_login_not_locked`, `register_failed_login_attempt`, `reset_login_attempts`, `is_protected_admin_email`, `is_protected_admin_role`, `workshop_login_status` |
| `forgot-password` | `_resolve_password_reset_account_by_email` |
| `vehiculos` | `normalize_plate`, `save_vehicle_photo`, `remove_vehicle_photo` |
| `emergencias` | `normalize_optional_text`, `normalize_problem_type`, `normalize_text_for_matching`, `standardize_problem_type`, `extract_response_text`, `classify_emergency_photos`, `determine_standardized_problem_type`, `resolve_emergency_price`, `transcribe_emergency_audio`, `save_emergency_photo`, `save_emergency_audio`, `parse_json_string_list`, `normalize_emergency_media_fields`, `existing_upload_urls_from_media_lists` |
| `uploads` | `build_public_upload_url`, `remove_file_if_exists`, `save_upload_with_limit`, `cleanup_uploaded_files`, `remove_uploaded_file`, `relative_upload_path_from_url` |
| `fcm` | `ensure_firebase_app`, `send_push_to_client`, `compact_push_text` |
| `asignaciones` | `emergency_incident_label`, `push_coordinate`, `add_coordinate_pair` |
| `clientes` | `ensure_client_exists` |
| `system` | `on_startup` |

## 7. Dependencias por capa

## Dependencias con `app.db`

Muy altas. `main.py` mezcla:

- validacion de request
- decisiones de negocio
- persistencia directa
- transformacion de respuesta

La extraccion segura debe mover primero controladores y dejar la logica DB intacta, para no cambiar demasiadas capas a la vez.

## Dependencias con `app.security`

Hoy estan subutilizadas desde `main.py`. La presencia de `backend/app/security.py` es una oportunidad para mover ahi:

- hashing de contraseñas
- normalizacion de email y texto
- control de intentos de login
- resolucion de cuentas protegidas

## Dependencias con `app.core.dependencies`

Este modulo ya tiene forma correcta para crecer y deberia mantenerse como punto unico de:

- autenticacion JWT
- usuario autenticado
- control de roles

## 8. Modulos propuestos

Clasificacion recomendada del backend:

- `health`
- `auth`
- `clientes`
- `vehiculos`
- `workshops` o `sucursales`
- `tecnicos`
- `emergencias`
- `asignaciones`
- `fcm`
- `uploads`
- `dashboard`
- `forgot-password`
- `utilidades internas`

## 9. Propuesta de estructura final

```text
backend/app/
├── main.py
├── api/
│   └── v1/
│       ├── health.py
│       ├── auth.py
│       ├── clientes.py
│       ├── vehiculos.py
│       ├── sucursales.py
│       ├── tecnicos.py
│       ├── emergencias.py
│       ├── fcm.py
│       └── dashboard.py
├── schemas/
├── services/
└── core/
```

## Nota sobre la migracion real

Como ya existe `backend/app/routes/`, hay dos caminos:

1. reutilizar `routes/` como etapa intermedia y luego renombrar a `api/v1/`
2. migrar directamente a `api/v1/`

La opcion mas segura es:

- etapa intermedia usando lo que ya existe en `routes/`
- consolidacion de contratos en `schemas/`
- extraccion de logica reusable a `services/`
- renombre estructural despues

## 10. Orden recomendado de extraccion

## 1. Health

Mover primero:

- `read_root`
- `healthcheck`
- `on_startup`

Riesgo bajo:

- sin payload complejo
- sin contratos de frontend delicados
- ya existe `backend/app/routes/system.py`

## 2. Auth/me

Mover despues:

- `get_authenticated_user_profile`

Riesgo bajo:

- depende de `get_current_active_user`
- contrato simple
- no toca login todavia

## 3. Forgot-password

Mover luego:

- `request_password_reset`
- `reset_password_with_token`
- `forgot_password`
- `forgot_client_password`
- `forgot_workshop_password`

Riesgo medio:

- conviven flujo nuevo y legacy
- importante mantener exactamente los contratos

## 4. Clientes

Mover:

- `register_client`
- `get_clients`
- `edit_client_status`
- `edit_client`
- `remove_client`
- `change_client_password`

Riesgo medio:

- payloads Pydantic reutilizables
- varias validaciones de negocio

## 5. Vehiculos

Mover:

- CRUD de vehiculos
- helpers de foto a modulo de uploads o services

Riesgo medio:

- usa multipart
- depende de archivos locales

## 6. Tecnicos

Mover:

- CRUD de tecnicos

Riesgo medio-bajo:

- relativamente aislado
- ya existe `backend/app/routes/technicians.py`

## 7. Workshops o sucursales

Mover:

- CRUD de workshops
- aprobacion
- cambio de contraseña inicial

Riesgo medio:

- mezcla dominio legacy y autenticacion inicial

## 8. Emergencias

Mover al final de la primera gran fase:

- registro de emergencia
- listado
- cambio de estado
- asignacion de tecnico
- borrado

Riesgo alto:

- integra uploads
- integra Whisper
- integra OpenAI
- integra FCM
- mezcla reglas de negocio y efectos laterales

## 11. Riesgos de modularizacion

## Imports circulares

Riesgo alto si:

- routers importan helpers desde `main.py`
- servicios importan routers

Mitigacion:

- mover helpers reutilizables primero a `security.py`, `uploads.py`, `services/`

## Modelos Pydantic compartidos

Riesgo alto porque:

- hay modelos definidos en `main.py`
- ya existe `schemas.py`
- puede aparecer duplicacion o desalineacion

Mitigacion:

- crear `schemas/` por modulo y migrar uno por uno

## Rutas duplicadas

Riesgo real porque:

- ya existen archivos en `backend/app/routes/`
- si se incluyen routers sin retirar rutas equivalentes de `main.py`, FastAPI puede registrar rutas duplicadas

Mitigacion:

- mover modulo por modulo
- validar `/openapi.json` y `/docs` despues de cada extraccion

## Perdida de OpenAPI

Riesgo medio:

- cambios de `response_model`
- imports cruzados
- alias Pydantic inconsistentes

Mitigacion:

- snapshot funcional de `/docs`
- pruebas smoke por endpoint movido

## Errores de CORS o startup

Riesgo bajo-medio:

- si se mueve `on_startup`
- si `main.py` deja de incluir middlewares o routers correctamente

Mitigacion:

- mantener `main.py` como ensamblador minimo
- no mover configuracion global hasta el final

## Ruptura del frontend o mobile

Riesgo alto en:

- login
- forgot-password legacy
- endpoints multipart

Mitigacion:

- mover primero endpoints de riesgo bajo
- no alterar contratos ni mensajes todavia

## 12. Primer cambio de codigo seguro recomendado

El primer cambio seguro recomendado es:

1. conectar `main.py` a routers ya existentes para `health`
2. mover `get_authenticated_user_profile` a un router de `auth`
3. dejar `main.py` como ensamblador de app, middlewares y `include_router`

### Por que este orden

- aprovecha estructura ya presente en `backend/app/routes/`
- evita tocar primero modulos con uploads, IA o flujos legacy sensibles
- reduce tamano de `main.py` sin afectar contratos de negocio
- valida la estrategia de extraccion con endpoints simples

## 13. Recomendacion final

La modularizacion no debe empezar reescribiendo `main.py` completo, sino extrayendo capas y modulos con riesgo acotado.

Orden mas seguro:

1. `health`
2. `auth/me`
3. `forgot-password`
4. `clientes`
5. `vehiculos`
6. `tecnicos`
7. `workshops/sucursales`
8. `emergencias`

Con esa secuencia, el backend puede pasar de archivo monolitico a composicion por routers sin romper Docker, frontend ni mobile en un solo salto.
