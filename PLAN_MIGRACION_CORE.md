# PLAN DE MIGRACION A CORE WEB/BACKEND

## Proyecto objetivo
Transformar el repositorio actual `F.I.C.C.T.-Proyecto-Final-Sw2-Web` en el CORE WEB/BACKEND del sistema:

`Sistema Inteligente de Atención de Emergencias Vehiculares en Tiempo Real`

## Restricciones de este plan

- No se modifica codigo en esta etapa.
- No se realizan commits.
- No se renombran archivos todavia.
- Este documento propone el camino de migracion por fases.

## Premisas de arquitectura objetivo

- El backend FastAPI actual se conservara como `Microservicio 1: Gestion Empresarial Core`.
- El frontend actual en `frontend/` se convertira en `Web Core empresarial`.
- La app movil React Native consumira este Core.
- La empresa trabajara con `sucursales propias`, no talleres afiliados.
- No existiran suscripciones, planes, pagos, comisiones ni marketplace.
- El Core manejara:
  - usuarios
  - roles
  - clientes
  - vehiculos
  - sucursales
  - tecnicos vehiculares
  - emergencias
  - asignaciones
  - eventos de seguimiento
  - evidencias
  - bitacora
- A futuro se integraran:
  - Microservicio de IA y procesamiento multimedia
  - Microservicio de tracking, automatizacion, FCM, DynamoDB y Blockchain

## Estrategia general

La migracion debe ser `incremental`, `compatible` y `por capas`.

Principios:

1. No romper el flujo actual mientras se ordena arquitectura.
2. Cambiar primero contratos, nombres y seguridad, no solo pantallas.
3. Introducir migraciones formales antes de cambios grandes de esquema.
4. Mantener compatibilidad temporal con mobile y frontend durante la transicion.
5. Reemplazar el concepto `workshop` por `sucursal` con una estrategia de backfill, no con un renombre brusco.

---

## FASE 1: Congelamiento Y Respaldo

### Objetivo
Congelar una linea base verificable del sistema actual antes de iniciar cualquier cambio funcional o estructural.

### Archivos afectados

- `README.md`
- `backend/API.md`
- `FLUJO_PROYECTO.md`
- `docker-compose.yml`
- `.env.example`
- `backend/.env.example`
- `AUDITORIA_MIGRACION_CORE.md`

### Cambios propuestos

- Crear rama de trabajo dedicada a migracion del Core.
- Levantar el sistema con Docker y validar estado real de arranque.
- Confirmar endpoints vigentes y documentar respuestas base.
- Capturar evidencia funcional minima:
  - healthcheck
  - login
  - listado de talleres
  - listado de tecnicos
  - listado de clientes
  - listado de emergencias
- Revisar que variables de entorno necesarias existan y esten documentadas.
- Crear un inventario de endpoints vigentes REST para usar como baseline.

### Riesgos

- Arrancar a migrar sin baseline verificable.
- Perder rastreo de contratos actuales usados por frontend/mobile.
- Suponer que un endpoint funciona cuando en realidad solo existe en codigo.

### Criterios de aceptacion

- Existe rama de trabajo de migracion.
- Docker levanta `db`, `backend` y `frontend`.
- `GET /api/health` responde correctamente.
- Endpoints principales quedan listados y confirmados.
- El estado actual queda documentado como baseline.

---

## FASE 2: Limpieza Conceptual

### Objetivo
Eliminar del lenguaje del sistema el arrastre de marketplace, afiliacion y monetizacion, y alinear el vocabulario hacia una empresa con sucursales propias.

### Archivos afectados

- `frontend/src/app/app.routes.ts`
- `frontend/src/app/app.component.ts`
- `frontend/src/app/app.component.html`
- `frontend/src/app/site-content.ts`
- `frontend/src/app/pages/home-page.component.ts`
- `frontend/src/app/pages/planes-page.component.ts`
- `frontend/src/app/pages/suscripciones-page.component.ts`
- `frontend/src/app/pages/servicios-page.component.ts`
- `frontend/src/app/pages/map-page.component.ts`
- `frontend/src/app/pages/dashboard-page.component.ts`
- `frontend/src/app/pages/shared-pages.css`
- `README.md`
- `FLUJO_PROYECTO.md`
- `backend/API.md`

### Cambios propuestos

- Identificar y catalogar todas las referencias a:
  - talleres afiliados
  - talleres aliados
  - marketplace
  - planes
  - suscripciones
  - comisiones
  - monetizacion
  - afiliacion
- Reemplazar lenguaje de:
  - `taller` por `sucursal` donde aplique al nuevo Core
  - `red de talleres` por `red operativa propia`
  - `aliado` por `unidad operativa` o `sucursal`
- Marcar como legado o retirar del flujo:
  - pagina `planes`
  - pagina `suscripciones`
  - copys comerciales de crecimiento/ingresos
- Reorientar el sitio publico hacia:
  - informacion institucional minima
  - acceso al panel
  - cobertura del servicio
  - contacto operativo

### Riesgos

- Cambiar demasiado temprano nombres visibles sin alinear backend.
- Mezclar conceptos: una cosa es “copy” de pantalla y otra el modelo real de datos.
- Eliminar vistas antes de definir si habra un sitio publico residual.

### Criterios de aceptacion

- Existe un inventario de textos/conceptos a sustituir.
- Queda definido el vocabulario oficial del nuevo Core.
- Se decide que pantallas publicas continúan y cuales pasan a legado.

---

## FASE 3: Modelo De Dominio Objetivo

### Objetivo
Definir de manera formal el modelo final del Core antes de refactorizar tablas, endpoints y pantallas.

### Archivos afectados

- `backend/app/db.py`
- `backend/app/schemas.py`
- `backend/app/main.py`
- `backend/API.md`
- `FLUJO_PROYECTO.md`

### Cambios propuestos

- Definir entidades objetivo:
  - `users`
  - `roles`
  - `clients`
  - `vehicles`
  - `branches`
  - `vehicle_technicians`
  - `emergencies`
  - `emergency_assignments`
  - `emergency_tracking_events`
  - `evidences`
  - `audit_logs`
- Definir relacion entre entidades:
  - un usuario pertenece a un rol
  - un tecnico pertenece a una sucursal
  - una emergencia pertenece a un cliente
  - una emergencia puede tener vehiculo asociado
  - una emergencia puede tener una asignacion vigente
  - una emergencia puede tener multiples eventos de seguimiento
  - una emergencia puede tener multiples evidencias
- Definir estados oficiales:
  - sucursal
  - tecnico
  - emergencia
  - asignacion
- Definir naming canónico:
  - `workshop` -> `branch`
  - `approval_status` -> `branch_status` o `operational_status`
  - `emergency_reports` -> `emergencies`
- Establecer decisiones de compatibilidad temporal:
  - que campos viejos se mantienen por un tiempo
  - que campos nuevos se agregan primero

### Riesgos

- Refactorizar sin modelo oficial y terminar con nombres mixtos.
- Acoplar demasiado el dominio al frontend actual.
- No definir eventos/evidencias desde el inicio y tener que rehacer tablas luego.

### Criterios de aceptacion

- Existe un modelo objetivo aprobado.
- Las entidades, relaciones y estados quedan documentados.
- Queda definido el mapeo viejo -> nuevo para tablas y endpoints.

---

## FASE 4: Seguridad Y Autenticacion

### Objetivo
Convertir la autenticacion actual en un sistema real para web y mobile, y cerrar el flujo inseguro de recuperacion de contraseña.

### Archivos afectados

- `backend/app/main.py`
- `backend/app/security.py`
- `backend/app/schemas.py`
- `backend/app/config.py`
- `frontend/src/app/session.ts`
- `frontend/src/app/auth.guard.ts`
- `frontend/src/app/pages/login-page.component.ts`
- `frontend/src/app/pages/forgot-password-page.component.ts`
- `backend/API.md`

### Cambios propuestos

- Revisar el login actual y definir si se usara:
  - JWT con expiracion
  - refresh token
  - sesiones firmadas
- Proteger endpoints sensibles con autenticacion real:
  - clientes
  - tecnicos
  - sucursales
  - emergencias
  - asignaciones
  - bitacora
- Definir `RBAC` minimo:
  - `super_admin`
  - `operador_core`
  - `jefe_sucursal`
  - `tecnico_vehicular`
  - `cliente_movil`
- Rediseñar `forgot-password`:
  - token temporal o OTP
  - expiracion
  - invalidacion tras uso
- Definir politicas:
  - expiracion de sesion
  - lockout
  - rotacion de credenciales iniciales
  - no exponer tokens “cosmeticos”

### Riesgos

- Romper login del dashboard actual.
- Romper la futura app movil si cambia el contrato sin versionado.
- Introducir auth real sin adaptar `auth.guard` y almacenamiento de sesion.

### Criterios de aceptacion

- Los endpoints sensibles requieren auth real.
- El frontend usa token valido, no solo storage.
- `forgot-password` deja de depender solo del correo.
- Los roles y permisos quedan definidos y documentados.

---

## FASE 5: Modularizacion Backend

### Objetivo
Descomponer `backend/app/main.py` en una arquitectura mantenible sin romper el comportamiento vigente.

### Archivos afectados

- `backend/app/main.py`
- `backend/app/routes/`
- `backend/app/schemas.py`
- `backend/app/db.py`
- Nuevos directorios propuestos:
  - `backend/app/routers/`
  - `backend/app/services/`
  - `backend/app/repositories/`
  - `backend/app/models/`
  - `backend/app/schemas/`
  - `backend/app/core/`

### Cambios propuestos

- Mantener `main.py` solo como wiring:
  - crear `app`
  - registrar middlewares
  - registrar routers
  - startup/shutdown
- Separar routers por modulo:
  - `auth.py`
  - `branches.py`
  - `clients.py`
  - `vehicles.py`
  - `technicians.py`
  - `emergencies.py`
  - `assignments.py`
  - `tracking_events.py`
  - `evidences.py`
  - `dashboard.py`
  - `system.py`
- Crear services por dominio:
  - login/auth
  - emergencias
  - asignaciones
  - tracking
  - evidencias
  - sucursales
- Crear repositories o data access por modulo, extrayendo consultas desde `db.py`.
- Centralizar schemas por dominio.
- Mantener capa de compatibilidad temporal para no romper rutas actuales durante la transicion.

### Archivos nuevos propuestos

- `backend/app/routers/auth.py`
- `backend/app/routers/branches.py`
- `backend/app/routers/clients.py`
- `backend/app/routers/vehicles.py`
- `backend/app/routers/technicians.py`
- `backend/app/routers/emergencies.py`
- `backend/app/routers/assignments.py`
- `backend/app/routers/tracking_events.py`
- `backend/app/routers/evidences.py`
- `backend/app/routers/dashboard.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/emergency_service.py`
- `backend/app/services/assignment_service.py`
- `backend/app/services/tracking_service.py`
- `backend/app/services/evidence_service.py`
- `backend/app/services/branch_service.py`
- `backend/app/repositories/branch_repository.py`
- `backend/app/repositories/client_repository.py`
- `backend/app/repositories/vehicle_repository.py`
- `backend/app/repositories/technician_repository.py`
- `backend/app/repositories/emergency_repository.py`
- `backend/app/repositories/assignment_repository.py`
- `backend/app/repositories/tracking_repository.py`
- `backend/app/repositories/evidence_repository.py`

### Riesgos

- Duplicar logica en lugar de extraerla.
- Romper imports y startup.
- Reutilizar `routes/*.py` existentes sin revisar si su contrato coincide con el actual.

### Criterios de aceptacion

- `main.py` queda reducido a configuracion e integracion.
- Cada dominio tiene router, service y repository.
- No se pierde ningun endpoint vigente durante la fase de transicion.

---

## FASE 6: Migraciones Y Base De Datos

### Objetivo
Pasar de bootstrap manual en `db.py` a migraciones formales y preparar la evolucion del esquema al dominio nuevo.

### Archivos afectados

- `backend/app/db.py`
- `backend/app/config.py`
- `backend/requirements.txt`
- Nuevo directorio:
  - `backend/alembic/`
  - `backend/alembic.ini`

### Cambios propuestos

- Incorporar Alembic.
- Definir baseline inicial desde el estado actual.
- Diseñar migraciones por etapas:
  - crear tablas nuevas del dominio objetivo
  - backfill desde tablas antiguas
  - exponer compatibilidad temporal
  - desactivar gradualmente nomenclatura anterior
- Migracion clave:
  - `workshop_registrations` -> `branches`
- Opciones de estrategia:
  - Opcion A: renombrar tabla y columnas
  - Opcion B: crear tabla nueva `branches`, migrar datos y deprecatear la anterior
- Recomendacion:
  - usar Opcion B si se quiere menor riesgo y mejor trazabilidad
- Crear tablas nuevas:
  - `roles`
  - `users`
  - `branch_staff` si se requiere
  - `emergency_tracking_events`
  - `evidences`
  - `audit_logs`
- Eliminar o desactivar del dominio:
  - planes
  - suscripciones
  - comisiones
  - marketplace
  Estas hoy estan mas en frontend/copy que en DB, pero debe confirmarse que no haya nuevas tablas futuras relacionadas.

### Riesgos

- Tocar `db.py` antes de tener migraciones.
- Perder datos de talleres al pasarlos a sucursales.
- Dejar el sistema en estado mixto entre tablas viejas y nuevas.

### Criterios de aceptacion

- Alembic queda integrado.
- Existe estrategia aprobada para `workshops` -> `branches`.
- El esquema objetivo puede reproducirse por migraciones.

---

## FASE 7: Adaptacion Funcional Backend

### Objetivo
Redefinir la superficie API del Core para soportar el nuevo dominio operativo y preparar clientes web/mobile.

### Archivos afectados

- `backend/app/main.py`
- `backend/app/schemas.py`
- `backend/API.md`
- `backend/app/routes/` o futuros `routers/`
- futuros `services/` y `repositories/`

### Cambios propuestos

#### Endpoints de sucursales

- `GET /api/branches`
- `POST /api/branches`
- `GET /api/branches/{branch_id}`
- `PUT /api/branches/{branch_id}`
- `PATCH /api/branches/{branch_id}/status`
- `GET /api/branches/{branch_id}/technicians`
- `GET /api/branches/map`

#### Endpoints de tecnicos vehiculares

- `GET /api/technicians`
- `POST /api/technicians`
- `GET /api/technicians/{technician_id}`
- `PUT /api/technicians/{technician_id}`
- `PATCH /api/technicians/{technician_id}/status`
- `GET /api/technicians/{technician_id}/assignments`

#### Endpoints de vehiculos

- `GET /api/vehicles`
- `POST /api/vehicles`
- `GET /api/vehicles/{vehicle_id}`
- `PUT /api/vehicles/{vehicle_id}`
- `DELETE /api/vehicles/{vehicle_id}`

#### Endpoints de emergencias

- `GET /api/emergencies`
- `POST /api/emergencies`
- `GET /api/emergencies/{emergency_id}`
- `PATCH /api/emergencies/{emergency_id}/status`
- `GET /api/emergencies/{emergency_id}/timeline`

#### Endpoints de asignaciones

- `POST /api/emergencies/{emergency_id}/assignments`
- `PUT /api/emergencies/{emergency_id}/assignments/{assignment_id}`
- `PATCH /api/assignments/{assignment_id}/status`
- `GET /api/assignments`

#### Endpoints de eventos de seguimiento

- `GET /api/emergencies/{emergency_id}/tracking-events`
- `POST /api/emergencies/{emergency_id}/tracking-events`
- `PATCH /api/tracking-events/{event_id}`

#### Endpoints de evidencias

- `GET /api/emergencies/{emergency_id}/evidences`
- `POST /api/emergencies/{emergency_id}/evidences`
- `DELETE /api/evidences/{evidence_id}`

#### Endpoints de dashboard

- `GET /api/dashboard/summary`
- `GET /api/dashboard/active-emergencies`
- `GET /api/dashboard/branch-load`
- `GET /api/dashboard/technician-availability`
- `GET /api/dashboard/audit-feed`

### Compatibilidad transitoria recomendada

- Mantener temporalmente:
  - `/api/workshops`
  - `/api/emergencias`
  - `/api/clientes`
  - `/api/vehiculos`
- Exponer paralelamente endpoints nuevos o alias.

### Riesgos

- Romper consumo del dashboard al renombrar rutas demasiado temprano.
- Romper app movil por cambios bruscos de payload.
- Duplicar semanticamente endpoints nuevos y viejos por demasiado tiempo.

### Criterios de aceptacion

- El contrato futuro del Core queda definido.
- Existe estrategia de compatibilidad REST durante la migracion.
- Frontend y mobile pueden migrar gradualmente.

---

## FASE 8: Frontend Core

### Objetivo
Convertir `frontend/` en el panel empresarial del Core y reducir el arrastre de sitio publico comercial.

### Archivos afectados

- `frontend/src/app/app.routes.ts`
- `frontend/src/app/app.component.ts`
- `frontend/src/app/app.component.html`
- `frontend/src/app/api-base.ts`
- `frontend/src/app/session.ts`
- `frontend/src/app/auth.guard.ts`
- `frontend/src/app/pages/dashboard-page.component.ts`
- `frontend/src/app/pages/home-page.component.ts`
- `frontend/src/app/pages/login-page.component.ts`
- `frontend/src/app/pages/forgot-password-page.component.ts`
- `frontend/src/app/pages/map-page.component.ts`
- `frontend/src/app/pages/planes-page.component.ts`
- `frontend/src/app/pages/suscripciones-page.component.ts`
- `frontend/src/app/pages/servicios-page.component.ts`
- `frontend/src/app/site-content.ts`

### Cambios propuestos

- Replantear `frontend/` como Web Core empresarial.
- Renombrar pantallas de `talleres` a `sucursales`.
- Ajustar menu principal.
- Eliminar del flujo activo:
  - planes
  - suscripciones
  - monetizacion
- Dividir `dashboard-page.component.ts` en subcomponentes:
  - resumen
  - sucursales
  - tecnicos
  - clientes
  - emergencias
  - seguimiento
  - bitacora
  - reportes
- Introducir capa `services/` para API:
  - `auth.service.ts`
  - `branches.service.ts`
  - `technicians.service.ts`
  - `clients.service.ts`
  - `vehicles.service.ts`
  - `emergencies.service.ts`
  - `tracking.service.ts`
  - `dashboard.service.ts`
- Separar, si aplica:
  - sitio institucional minimo
  - panel operativo autenticado

### Decision recomendada

Mantener un sitio publico minimo, pero priorizar que `frontend/` sea ante todo el panel empresarial. Si la parte institucional crece mucho, moverla luego a otro frontend separado.

### Riesgos

- Querer rediseñar todo el frontend antes de estabilizar API y auth.
- Seguir usando `dashboard-page.component.ts` como megacomponente demasiado tiempo.
- Eliminar rutas publicas sin decidir si hay necesidades institucionales reales.

### Criterios de aceptacion

- El frontend representa sucursales propias, no talleres afiliados.
- No existen flujos activos de planes/suscripciones.
- El dashboard queda orientado a operacion real del Core.

---

## FASE 9: Preparacion GraphQL

### Objetivo
Diseñar una capa GraphQL complementaria dentro del backend FastAPI sin reemplazar abruptamente REST.

### Archivos afectados

- `backend/app/main.py`
- futuros `backend/app/graphql/`
- `backend/API.md`

### Cambios propuestos

- Incorporar GraphQL como capa adicional sobre servicios ya estabilizados.
- Mantener REST para:
  - login/auth
  - uploads de evidencias
  - webhooks/eventos
  - healthchecks
- Exponer por GraphQL consultas agregadas y lecturas complejas de dashboard.

### Queries recomendadas

- `me`
- `branches`
- `branch(id)`
- `technicians`
- `clients`
- `vehicles(clientId)`
- `emergencies(filters)`
- `emergency(id)`
- `emergencyTimeline(emergencyId)`
- `dashboardSummary`
- `auditFeed`

### Mutations recomendadas

- `login`
- `createBranch`
- `updateBranch`
- `createTechnician`
- `updateTechnicianStatus`
- `createClient`
- `createVehicle`
- `createEmergency`
- `updateEmergencyStatus`
- `assignTechnician`
- `createTrackingEvent`

### Que se mantiene REST

- `POST /api/auth/login`
- `POST /api/auth/forgot-password`
- `POST multipart` para evidencias/audio/fotos
- `GET /api/health`
- endpoints de integracion con otros microservicios

### Riesgos

- Agregar GraphQL antes de modularizar servicios.
- Duplicar logica de negocio entre REST y GraphQL.
- Querer migrar frontend entero a GraphQL demasiado pronto.

### Criterios de aceptacion

- Existe estrategia clara de convivencia REST + GraphQL.
- GraphQL se monta sobre services existentes, no sobre consultas ad hoc dispersas.

---

## FASE 10: Integracion Futura Con Microservicios Externos

### Objetivo
Preparar el Core para hablar con microservicios externos sin implementarlos todavia.

### Archivos afectados

- `backend/app/config.py`
- futuros `backend/app/clients/`
- futuros `backend/app/services/`
- `backend/API.md`

### Cambios propuestos

#### Cliente para microservicio de IA y multimedia

Preparar interfaz para:

- transcripcion de audio
- clasificacion de imagenes
- extraccion de entidades
- enriquecimiento de incidentes

Cliente propuesto:

- `backend/app/clients/ai_client.py`

#### Cliente para microservicio de seguimiento y automatizacion

Preparar interfaz para:

- tracking
- automatizacion de eventos
- FCM
- integracion con DynamoDB
- registro hash/Blockchain

Cliente propuesto:

- `backend/app/clients/tracking_client.py`

### Reglas de desacople

- El Core no debe conocer detalles internos de DynamoDB ni Blockchain.
- El Core solo debe emitir comandos/eventos de negocio.
- La integracion debe ser configurable por feature flag o endpoint externo.

### Riesgos

- Acoplar desde ya el Core a implementaciones no disponibles.
- Mezclar logica de IA dentro de `main.py`.
- Construir integracion sin contratos definidos.

### Criterios de aceptacion

- Existe interfaz clara de clientes externos.
- El Core queda preparado para integrar sin bloquear el avance actual.

---

## FASE 11: Validacion

### Objetivo
Definir como validar que la migracion del Core no rompa lo existente y cumpla el dominio nuevo.

### Archivos afectados

- `README.md`
- `backend/API.md`
- `docker-compose.yml`
- futuros tests backend/frontend

### Cambios propuestos

#### Comandos de levantamiento

- `docker compose up --build`
- `curl http://localhost:8787/api/health`
- `http://localhost:5656`

#### Pruebas minimas recomendadas

- Healthcheck backend
- Login admin
- Login operador/sucursal
- CRUD sucursales
- CRUD tecnicos
- CRUD clientes
- CRUD vehiculos
- Creacion de emergencia
- Cambio de estado de emergencia
- Asignacion de tecnico
- Registro de evento de seguimiento
- Subida de evidencia

#### Validaciones manuales

- Navegacion en login y dashboard
- Control de acceso por rol
- Sesion persistente valida
- Mapa de sucursales
- Dashboard con datos reales
- Timeline de emergencia
- Bitacora visible

#### Criterios de aceptacion globales

- Docker sigue levantando el sistema.
- El backend responde con auth real.
- El frontend refleja sucursales propias y no marketplace.
- No hay planes/suscripciones activos.
- Emergencias, asignaciones, eventos y evidencias funcionan de extremo a extremo.
- La API queda documentada para Web Core y app movil.

### Riesgos

- Validar solo por UI y no por contrato API.
- No tener pruebas de regresion sobre endpoints antiguos.
- Romper integraciones futuras por falta de documentacion.

### Criterios de aceptacion

- Existe checklist de validacion tecnica y funcional.
- El sistema puede probarse de manera repetible por entorno local.

---

## Orden Recomendado De Implementacion

1. Fase 1: Congelamiento y baseline.
2. Fase 3: Modelo de dominio objetivo.
3. Fase 4: Seguridad y autenticacion.
4. Fase 6: Migraciones y estrategia de base de datos.
5. Fase 5: Modularizacion backend.
6. Fase 7: Adaptacion funcional backend.
7. Fase 8: Frontend Core.
8. Fase 2: Limpieza conceptual visual completa.
9. Fase 9: GraphQL.
10. Fase 10: Preparacion para microservicios externos.
11. Fase 11: Validacion integral.

### Nota de orden

Aunque enunciado original separa Fase 2 antes de Fase 3, para implementacion real conviene definir primero el modelo objetivo y auth antes de terminar la limpieza visual completa. El lenguaje puede empezar a limpiarse temprano, pero los cambios de nombres profundos deben responder al dominio ya aprobado.

## Que NO Se Debe Tocar Todavia

- No renombrar tablas fisicas en base de datos sin Alembic.
- No eliminar endpoints actuales usados por frontend o mobile.
- No dividir `main.py` sin definir primero la arquitectura objetivo.
- No migrar a GraphQL antes de estabilizar REST.
- No eliminar paginas publicas hasta decidir el alcance institucional residual.
- No introducir integraciones reales con microservicios externos todavia.
- No cambiar masivamente `workshop` a `branch` en codigo sin estrategia de compatibilidad.

## Recomendacion Para El Primer Cambio De Codigo Seguro

El primer cambio de codigo seguro recomendado es:

`introducir autenticacion real y cerrar forgot-password, sin cambiar todavia el dominio de datos`

Por que:

- reduce el riesgo mas serio actual
- mejora inmediatamente la base del Core
- afecta web y futuro mobile de forma positiva
- no obliga todavia a renombrar tablas ni pantallas
- permite seguir migrando sobre una plataforma mas segura

### Secuencia del primer cambio seguro

1. Definir estrategia de token real.
2. Proteger endpoints sensibles.
3. Adaptar `session.ts` y `auth.guard.ts`.
4. Rehacer `forgot-password` con token temporal.
5. Documentar el nuevo contrato de auth.

## Cierre

La migracion no parte de un sistema equivocado; parte de una base ya bastante cercana al dominio final. El principal desafio no es “crear emergencias desde cero”, sino convertir una solucion operativa con semantica de talleres/afiliacion en un Core empresarial seguro, modular y preparado para crecer por microservicios.

La clave del exito sera migrar en este orden:

- baseline
- dominio objetivo
- seguridad
- migraciones
- modularizacion
- adaptacion funcional
- frontend

Sin ese orden, el riesgo de romper login, dashboard, contratos de mobile y base de datos es alto.
