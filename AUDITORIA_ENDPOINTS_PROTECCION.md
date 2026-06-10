# AUDITORIA DE ENDPOINTS PARA PROTECCION JWT

## Objetivo
Identificar los endpoints actuales del backend FastAPI y definir cuales conviene proteger primero con autenticacion JWT y control de rol, sin romper de golpe el frontend web ni la app movil.

## Resumen ejecutivo
El backend ya cuenta con una base de autenticacion JWT y un endpoint protegido de validacion de sesion:

- `GET /api/auth/me`

Sin embargo, el resto de endpoints de negocio relevantes siguen publicos. Eso deja expuestos:

- clientes
- vehiculos
- sucursales o `workshops`
- tecnicos
- emergencias
- asignaciones
- tokens FCM

La recomendacion no es proteger todo al mismo tiempo. El primer lote pequeno y de mayor impacto deberia cubrir:

1. `GET /api/clientes`
2. `GET /api/workshops`
3. `GET /api/technicians`
4. `POST /api/devices/fcm-token`

Ese lote reduce exposicion de datos y abuso operativo sin tocar todavia flujos delicados de:

- login
- registro
- forgot-password
- creacion de emergencias
- CRUDs que hoy usan ownership implicito por query params o forms

## Archivos revisados

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1295)
- [backend/app/core/dependencies.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/core/dependencies.py:1)
- [backend/app/db.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/db.py:1)
- [backend/app/schemas.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/schemas.py:1)

## Estado actual de proteccion

### Protegido actualmente

- `GET /api/auth/me`

Usa `Security(get_current_active_user)` y valida JWT firmado.

### Publicos actualmente

Todos los demas endpoints listados en `main.py` siguen publicos desde el punto de vista de autorizacion de API.

## Clasificacion funcional de endpoints

### Publicos de infraestructura

- `GET /`
- `GET /api/health`
- `GET /docs`

### Autenticacion

- `POST /api/auth/login`
- `POST /api/auth/account-type`
- `GET /api/auth/me`
- `POST|PUT /api/auth/forgot-password`

### Clientes

- `POST /api/clientes`
- `GET /api/clientes`
- `POST /api/clientes/change-password`
- `POST|PUT /api/clientes/forgot-password`
- `PUT /api/clientes/{client_id}/status`
- `PUT /api/clientes/{client_id}`
- `DELETE /api/clientes/{client_id}`

### Vehiculos

- `POST /api/vehiculos`
- `GET /api/vehiculos`
- `PUT /api/vehiculos/{vehicle_id}`
- `DELETE /api/vehiculos/{vehicle_id}`

### Sucursales o workshops

- `POST /api/workshops`
- `GET /api/workshops`
- `POST /api/workshops/change-password`
- `POST|PUT /api/workshops/forgot-password`
- `PUT /api/workshops/{workshop_id}`
- `PUT /api/workshops/{workshop_id}/approval-status`
- `DELETE /api/workshops/{workshop_id}`

### Tecnicos

- `POST /api/technicians`
- `GET /api/technicians`
- `PUT /api/technicians/{technician_id}`
- `DELETE /api/technicians/{technician_id}`

### Emergencias

- `POST /api/emergencias`
- `GET /api/emergencias`
- `PUT /api/emergencias/{report_id}/status`
- `DELETE /api/emergencias/{report_id}`

### Asignaciones

- `PUT /api/emergencias/{report_id}/technician-assignment`

### Tokens FCM

- `POST /api/devices/fcm-token`

### Uploads y evidencias

No existen endpoints REST separados de uploads. Las evidencias viajan embebidas principalmente en:

- `POST /api/vehiculos`
- `PUT /api/vehiculos/{vehicle_id}`
- `POST /api/emergencias`

### Dashboard o reportes

No hay endpoints dedicados de dashboard. El frontend hoy arma gran parte de la operacion usando:

- `GET /api/workshops`
- `GET /api/clientes`
- `GET /api/technicians`
- `GET /api/emergencias`
- `GET /api/vehiculos`

### Administracion

Principalmente:

- `PUT /api/workshops/{workshop_id}/approval-status`
- `PUT /api/clientes/{client_id}/status`
- `DELETE /api/workshops/{workshop_id}`
- `DELETE /api/clientes/{client_id}`
- `DELETE /api/technicians/{technician_id}`
- `DELETE /api/emergencias/{report_id}`

## Modelo de proteccion recomendado

### Deben seguir publicos por ahora

- `GET /`
- `GET /api/health`
- `GET /docs`
- `POST /api/auth/login`
- `GET /api/auth/me` protegido, como ya esta
- `POST /api/clientes`
- `POST /api/workshops`
- `POST|PUT /api/auth/forgot-password`
- `POST|PUT /api/clientes/forgot-password`
- `POST|PUT /api/workshops/forgot-password`
- `POST /api/auth/account-type`

### Deben requerir cualquier usuario autenticado

- `POST /api/devices/fcm-token`

### Deben requerir ADMIN u OPERADOR

- `GET /api/clientes`
- `GET /api/workshops`
- `GET /api/technicians`
- `POST /api/technicians`
- `PUT /api/technicians/{technician_id}`
- `GET /api/emergencias`

### Deben requerir ADMIN

- `PUT /api/workshops/{workshop_id}/approval-status`
- `DELETE /api/workshops/{workshop_id}`
- `PUT /api/clientes/{client_id}/status`
- `DELETE /api/clientes/{client_id}`
- `DELETE /api/technicians/{technician_id}`
- `DELETE /api/emergencias/{report_id}`

### Deben requerir ADMIN u OPERADOR o propietario del recurso

- `GET /api/vehiculos`
- `PUT /api/vehiculos/{vehicle_id}`
- `DELETE /api/vehiculos/{vehicle_id}`
- `PUT /api/clientes/{client_id}`
- `PUT /api/workshops/{workshop_id}`

### Deben requerir CLIENTE, OPERADOR o ADMIN segun el caso

- `POST /api/vehiculos`
- `POST /api/emergencias`

### Deben requerir OPERADOR o sucursal propietaria

- `PUT /api/emergencias/{report_id}/status`
- `PUT /api/emergencias/{report_id}/technician-assignment`

### Deben requerir CLIENTE propietario o sesion autenticada propia

- `POST /api/clientes/change-password`
- `POST /api/workshops/change-password`

## Tabla de endpoints y prioridad de proteccion

| Metodo | Endpoint | Handler | Estado actual | Proteccion recomendada | Prioridad | Riesgo de cambio |
|---|---|---|---|---|---|---|
| `GET` | `/` | `read_root` | Publico | Publico | Baja | Bajo |
| `GET` | `/api/health` | `healthcheck` | Publico | Publico | Alta | Bajo |
| `POST` | `/api/devices/fcm-token` | `register_device_fcm_token` | Publico | Cualquier usuario autenticado | Alta | Media |
| `POST` | `/api/workshops` | `register_workshop` | Publico | Publico por compatibilidad temporal | Media | Media |
| `POST` | `/api/vehiculos` | `register_vehicle` | Publico | Cliente propietario o ADMIN/OPERADOR | Alta | Alta |
| `POST` | `/api/emergencias` | `register_emergency` | Publico | Cliente propietario o ADMIN/OPERADOR | Alta | Alta |
| `GET` | `/api/emergencias` | `get_emergency_reports` | Publico | ADMIN u OPERADOR, con filtro posterior por rol | Alta | Alta |
| `PUT` | `/api/emergencias/{report_id}/status` | `edit_emergency_status` | Publico | OPERADOR o sucursal propietaria | Alta | Alta |
| `PUT` | `/api/emergencias/{report_id}/technician-assignment` | `assign_technician_to_emergency` | Publico | OPERADOR o sucursal propietaria | Alta | Alta |
| `DELETE` | `/api/emergencias/{report_id}` | `remove_emergency_report` | Publico | ADMIN | Alta | Alta |
| `GET` | `/api/vehiculos` | `get_vehicles` | Publico | Propietario del recurso o ADMIN/OPERADOR | Alta | Alta |
| `PUT` | `/api/vehiculos/{vehicle_id}` | `edit_vehicle` | Publico | Propietario del recurso o ADMIN/OPERADOR | Alta | Alta |
| `DELETE` | `/api/vehiculos/{vehicle_id}` | `remove_vehicle` | Publico | Propietario del recurso o ADMIN/OPERADOR | Alta | Alta |
| `GET` | `/api/workshops` | `get_workshops` | Publico | ADMIN u OPERADOR | Alta | Baja |
| `POST` | `/api/workshops/change-password` | `change_workshop_password` | Publico | Sesion autenticada propia o rediseño posterior | Alta | Alta |
| `POST|PUT` | `/api/workshops/forgot-password` | `forgot_workshop_password` | Publico | Publico hasta rediseño | Alta | Alta |
| `PUT` | `/api/workshops/{workshop_id}` | `edit_workshop` | Publico | ADMIN u OPERADOR o sucursal propietaria | Alta | Media |
| `PUT` | `/api/workshops/{workshop_id}/approval-status` | `edit_workshop_approval_status` | Publico | ADMIN | Alta | Baja |
| `DELETE` | `/api/workshops/{workshop_id}` | `remove_workshop` | Publico | ADMIN | Alta | Baja |
| `POST` | `/api/clientes` | `register_client` | Publico | Publico por compatibilidad temporal | Media | Media |
| `GET` | `/api/clientes` | `get_clients` | Publico | ADMIN u OPERADOR | Alta | Baja |
| `POST` | `/api/clientes/change-password` | `change_client_password` | Publico | Sesion autenticada propia o rediseño posterior | Alta | Alta |
| `POST|PUT` | `/api/clientes/forgot-password` | `forgot_client_password` | Publico | Publico hasta rediseño | Alta | Alta |
| `PUT` | `/api/clientes/{client_id}/status` | `edit_client_status` | Publico | ADMIN | Alta | Baja |
| `PUT` | `/api/clientes/{client_id}` | `edit_client` | Publico | Propietario del recurso o ADMIN/OPERADOR | Alta | Media |
| `DELETE` | `/api/clientes/{client_id}` | `remove_client` | Publico | ADMIN | Alta | Baja |
| `POST` | `/api/auth/login` | `login` | Publico | Publico | Alta | Bajo |
| `POST` | `/api/auth/account-type` | `lookup_account_type` | Publico | Publico temporal o eliminar luego | Media | Media |
| `GET` | `/api/auth/me` | `get_authenticated_user_profile` | Protegido | Mantener protegido | Alta | Bajo |
| `POST|PUT` | `/api/auth/forgot-password` | `forgot_password` | Publico | Publico hasta rediseño | Alta | Alta |
| `POST` | `/api/technicians` | `register_technician` | Publico | ADMIN u OPERADOR | Alta | Baja |
| `GET` | `/api/technicians` | `get_technicians` | Publico | ADMIN u OPERADOR | Alta | Baja |
| `PUT` | `/api/technicians/{technician_id}` | `edit_technician` | Publico | ADMIN u OPERADOR | Alta | Baja |
| `DELETE` | `/api/technicians/{technician_id}` | `remove_technician` | Publico | ADMIN | Alta | Baja |

## Endpoints criticos a proteger primero

### Lote 1 recomendado

- `GET /api/clientes`
- `GET /api/workshops`
- `GET /api/technicians`
- `POST /api/devices/fcm-token`

### Por que este lote primero

- son endpoints de alto impacto y bajo acoplamiento con formularios complejos
- no dependen de uploads multipart masivos
- no fuerzan todavia ownership fino por `client_id`
- reducen de inmediato exposicion de datos y suplantacion de dispositivo
- son mas faciles de adaptar en frontend y mobile que los CRUDs completos

### Proteccion sugerida para ese lote

- `GET /api/clientes` -> `ADMIN u OPERADOR`
- `GET /api/workshops` -> `ADMIN u OPERADOR`
- `GET /api/technicians` -> `ADMIN u OPERADOR`
- `POST /api/devices/fcm-token` -> `cualquier usuario autenticado`, pero atando el token al `current_user`

## Endpoints que no conviene proteger todavia

### Por compatibilidad con login y onboarding

- `POST /api/auth/login`
- `POST /api/clientes`
- `POST /api/workshops`
- `POST /api/auth/account-type`

### Porque requieren rediseño de seguridad antes de protegerlos

- `POST /api/clientes/change-password`
- `POST /api/workshops/change-password`
- `POST|PUT /api/clientes/forgot-password`
- `POST|PUT /api/workshops/forgot-password`
- `POST|PUT /api/auth/forgot-password`

### Porque requieren ownership claro o reglas de rol mas maduras

- `POST /api/vehiculos`
- `GET /api/vehiculos`
- `PUT /api/vehiculos/{vehicle_id}`
- `DELETE /api/vehiculos/{vehicle_id}`
- `POST /api/emergencias`
- `GET /api/emergencias`
- `PUT /api/emergencias/{report_id}/status`
- `PUT /api/emergencias/{report_id}/technician-assignment`
- `DELETE /api/emergencias/{report_id}`
- `PUT /api/clientes/{client_id}`
- `PUT /api/workshops/{workshop_id}`

## Endpoints que deben seguir publicos por ahora

- `GET /`
- `GET /api/health`
- `GET /docs`
- `POST /api/auth/login`
- `POST /api/clientes`
- `POST /api/workshops`
- `POST|PUT /api/auth/forgot-password`
- `POST|PUT /api/clientes/forgot-password`
- `POST|PUT /api/workshops/forgot-password`
- `POST /api/auth/account-type`

## Recomendacion operativa

El primer lote pequeno de proteccion deberia implementarse en este orden:

1. `POST /api/devices/fcm-token`
2. `GET /api/clientes`
3. `GET /api/workshops`
4. `GET /api/technicians`

### Justificacion del orden

- `devices/fcm-token` es el abuso mas directo y facil de cerrar con `current_user`
- los tres `GET` siguientes son lecturas de alto valor para dashboard y administracion
- ese orden permite validar JWT, rechazo `401`, rechazo `403` por rol y propagacion de headers desde frontend/mobile sin tocar aun formularios pesados

## Cierre

La auditoria confirma que el backend todavia expone demasiados endpoints sensibles como publicos. La estrategia segura no es proteger todo de golpe, sino comenzar por:

- identidad autenticada reutilizable
- cierre de abuso en FCM
- cierre de listados operativos sensibles

Despues de ese lote, el siguiente paso natural seria proteger:

- `POST /api/technicians`
- `PUT /api/technicians/{technician_id}`
- `PUT /api/workshops/{workshop_id}/approval-status`
- `PUT /api/clientes/{client_id}/status`

Eso ya abriria la siguiente fase de RBAC real para el Core empresarial.
