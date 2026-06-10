# AUDITORIA TECNICA DE MIGRACION A CORE WEB/BACKEND

## Alcance
Esta auditoria fue realizada sobre el repositorio actualmente cargado en:

`/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web`

No se modifico codigo de aplicacion. El unico artefacto nuevo generado es este informe.

## 1. Estado General Del Repositorio

### Estructura encontrada

- `backend/`: API FastAPI y acceso a PostgreSQL.
- `frontend/`: aplicacion Angular usada como sitio publico, login y dashboard operativo.
- `docker-compose.yml`: orquestacion local de `db`, `backend` y `frontend`.
- `.env` y `.env.example`: variables para PostgreSQL a nivel raiz.
- `backend/.env` y `backend/.env.example`: variables de backend.
- `backend/uploads/`: almacenamiento local de fotos y audio.

### Estructura no encontrada

- No existe carpeta `web/`; el frontend real vive en `frontend/`.
- No existe carpeta `mobile/`.
- No existe configuracion `nginx/` ni `nginx.conf`.
- No existe herramienta de migraciones formal tipo Alembic.
- No existe separacion por microservicios; todo el backend actual es un solo servicio.

### Conclusiones estructurales

- El repositorio actual ya no corresponde a un sistema tipo Wireless HeatMapper.
- El dominio actual ya esta orientado a asistencia vehicular, talleres, tecnicos, clientes y emergencias.
- Todavia conserva arrastre comercial/marketing del dominio anterior del propio proyecto actual:
  `planes`, `suscripciones`, `talleres afiliados`, aprobacion de talleres, etc.

## 2. Auditoria Del Backend FastAPI

### Stack y punto de entrada

- Framework: FastAPI.
- Validacion: Pydantic v2.
- Base de datos: PostgreSQL con SQLAlchemy Core y `psycopg`.
- Punto de entrada: [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1238).
- Configuracion: [backend/app/config.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/config.py:4).

### Organizacion real del backend

La arquitectura efectiva no esta separada por capas limpias.

- `main.py`: concentra app, modelos Pydantic, utilitarios, seguridad operativa, notificaciones, logica de negocio y endpoints.
- `db.py`: concentra definicion de tablas SQL, bootstrap del esquema y funciones CRUD.
- `security.py`: hashing, validaciones y normalizacion reusable.
- `uploads.py`: manejo de rutas de archivos.
- `routes/*.py`: existen, pero no se detecto `include_router`; parecen una refactorizacion parcial o estructura paralela no conectada.

### Rutas y endpoints existentes

Endpoints detectados en [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1281):

- `GET /`
- `GET /api/health`
- `POST /api/devices/fcm-token`
- `POST /api/workshops`
- `GET /api/workshops`
- `PUT /api/workshops/{workshop_id}`
- `PUT /api/workshops/{workshop_id}/approval-status`
- `DELETE /api/workshops/{workshop_id}`
- `POST /api/workshops/change-password`
- `POST|PUT /api/workshops/forgot-password`
- `POST /api/vehiculos`
- `GET /api/vehiculos`
- `PUT /api/vehiculos/{vehicle_id}`
- `DELETE /api/vehiculos/{vehicle_id}`
- `POST /api/emergencias`
- `GET /api/emergencias`
- `PUT /api/emergencias/{report_id}/status`
- `PUT /api/emergencias/{report_id}/technician-assignment`
- `DELETE /api/emergencias/{report_id}`
- `POST /api/clientes`
- `GET /api/clientes`
- `PUT /api/clientes/{client_id}`
- `PUT /api/clientes/{client_id}/status`
- `DELETE /api/clientes/{client_id}`
- `POST /api/clientes/change-password`
- `POST|PUT /api/clientes/forgot-password`
- `POST /api/auth/login`
- `POST /api/auth/account-type`
- `POST|PUT /api/auth/forgot-password`
- `POST /api/technicians`
- `GET /api/technicians`
- `PUT /api/technicians/{technician_id}`
- `DELETE /api/technicians/{technician_id}`

### Modelos de datos reales

No hay ORM declarativo con entidades. El modelo real se deduce desde SQL en [backend/app/db.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/db.py:17).

Tablas actuales:

- `workshop_registrations`
- `technicians`
- `clients`
- `vehicles`
- `emergency_reports`
- `emergency_assignments`
- `device_fcm_tokens`

### Schemas Pydantic

Hay schemas en [backend/app/schemas.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/schemas.py:1), pero no representan todo el backend actual.

Schemas encontrados:

- `WorkshopRegistrationCreate/Response`
- `WorkshopApprovalStatusUpdate`
- `TechnicianCreate/Response`
- `ClientRegistrationCreate/Response`
- `LoginRequest/LoginResponse`
- `WorkshopPasswordChangeRequest`
- `ClientStatusUpdate`
- `ClientUpdate`
- `VehicleResponse`
- `EmergencyReportResponse`

Observacion:

- `main.py` redefine y amplia varios schemas internamente.
- El modulo `schemas.py` no es la fuente unica de contratos.

### Services y repositories

No existe esta separacion de manera formal.

- `services/`: no existe.
- `repositories/`: no existe.
- `db.py` actua como repositorio procedural.
- `main.py` actua como capa de servicios/controladores mezclados.

### Autenticacion

Hallazgos principales:

- Hay login de `admin`, `workshop` y `client`.
- Se generan `access_token` aleatorios en login.
- No se encontro validacion real de token en endpoints protegidos.
- No se detecto JWT, OAuth2, middleware de autorizacion ni dependencia `Bearer`.
- El backend hoy no protege sus CRUDs mediante autenticacion efectiva.

Referencias:

- Login: [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2169)
- Hashing: [backend/app/security.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/security.py:14)

### Recuperacion de contraseña

Riesgo alto:

- Existen endpoints de cambio/reset de contraseña para talleres y clientes.
- El flujo `forgot-password` actual permite resetear contraseña solo con correo y nueva clave.
- No se detecto OTP, email token, challenge temporal ni verificacion secundaria.

Referencias:

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1911)
- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2079)
- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2297)

### Conexion a base de datos

- Motor: SQLAlchemy `create_engine`.
- URL construida desde `Settings.database_url`.
- Bootstrap en startup con `init_database()`.

Referencias:

- [backend/app/config.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/config.py:36)
- [backend/app/db.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/db.py:8)
- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1273)

### Migraciones

No existe sistema formal de migraciones.

En su lugar:

- `init_database()` ejecuta `CREATE TABLE IF NOT EXISTS`.
- Luego ejecuta una larga serie de `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
- Tambien crea constraints e indices manualmente.

Referencia:

- [backend/app/db.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/db.py:1152)

Diagnostico:

- Funciona para desarrollo y evoluciones pequeñas.
- Es fragil para produccion, versionado de esquema y multiples ambientes.

## 3. Auditoria Del Frontend Web

### Tecnologia usada

- Angular 20 standalone.
- Angular Material en formularios/dialogos puntuales.
- HttpClient para consumo API.
- Router standalone.
- CSS global grande y componentes con template inline.

Referencias:

- [frontend/package.json](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/package.json:1)
- [frontend/src/main.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/main.ts:1)
- [frontend/angular.json](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/angular.json:1)

### Organizacion real del frontend

- No existe carpeta `web/`; la app vive en `frontend/`.
- No existen `hooks` porque no es React.
- No existen `services` API formales por feature.
- No existen `layouts` dedicados; `AppComponent` actua como shell global.
- Gran parte de la logica del panel esta concentrada en un solo componente.

### Rutas

Rutas detectadas en [frontend/src/app/app.routes.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/app.routes.ts:14):

- `/` → `HomePageComponent`
- `/suscripciones` → redirect a `planes`
- `/nosotros` → redirect a `planes`
- `/planes`
- `/novedades` → redirect a `planes`
- `/servicios`
- `/mapa`
- `/login`
- `/forgot-password`
- `/dashboard`
- `/escuela` → redirect a `mapa`
- `/contacto`
- `**`

### Paginas y componentes principales

- `HomePageComponent`: landing publica y formulario de registro de taller.
- `ServiciosPageComponent`: marketing de servicios.
- `PlanesPageComponent`: marketing/comercial de planes.
- `MapPageComponent`: mapa Leaflet de talleres registrados.
- `LoginPageComponent`: login admin/socio.
- `ForgotPasswordPageComponent`: cambio/reset de contraseñas.
- `DashboardPageComponent`: panel administrativo y operativo.
- `SectionPageComponent`: seccion generica de contenido.
- `NotFoundPageComponent`
- `AlertSuccessComponent`
- `ValidationDialogComponent`
- `SuscripcionesPageComponent`: existe archivo, pero no aparece en rutas.

### Servicios API

No existe capa `services/` separada. El consumo HTTP esta embebido en componentes:

- `home-page.component.ts` → `POST /api/workshops`
- `map-page.component.ts` → `GET /api/workshops`
- `login-page.component.ts` → `POST /api/auth/login`
- `forgot-password-page.component.ts` → endpoints de recovery
- `dashboard-page.component.ts` → talleres, tecnicos, clientes y emergencias

Base URL:

- [frontend/src/app/api-base.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/api-base.ts:1)

### Estado de sesion y proteccion de rutas

- La sesion se guarda en `localStorage` o `sessionStorage`.
- El `auth.guard` solo valida que exista una sesion parseable.
- No valida token real ni expiracion.

Referencias:

- [frontend/src/app/session.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/session.ts:1)
- [frontend/src/app/auth.guard.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/auth.guard.ts:1)

### Layouts

No hay sistema de layouts separado.

- `AppComponent` funciona como layout publico.
- Oculta header/footer en login, forgot-password y dashboard.
- El dashboard renderiza su propia estructura interna.

Referencias:

- [frontend/src/app/app.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/app.component.ts:1)
- [frontend/src/app/app.component.html](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/app.component.html:1)

## 4. Modulos Del Dominio Anterior Detectados

### Modulos o conceptos NO detectados

No se encontraron en el codigo actual:

- `projects`
- `project`
- `planes` en sentido tecnico de planos de levantamiento
- `measurements`
- `Wireless HeatMapper`
- `organizations`
- estructura tipica de analitica WiFi o mediciones de calor de señal

### Modulos o conceptos SI detectados del dominio actual/previo inmediato

Se detectaron conceptos que no encajan con el nuevo CORE final:

- `workshops` o talleres afiliados
- `approval_status` de talleres
- `planes` comerciales
- `suscripciones`
- `comision`
- `red de talleres`
- `afiliacion`
- `mapa de talleres`
- `clientes`
- `tecnicos`
- `emergencias`

### Interpretacion

El repositorio actual ya esta mucho mas cerca del nuevo dominio de emergencias vehiculares que de Wireless HeatMapper. La migracion no parte de cero ni desde un dominio totalmente ajeno; parte desde una base intermedia de asistencia vehicular con sesgo de marketplace/red de talleres.

## 5. Que Se Puede Reutilizar

### Reutilizacion alta

- Docker base (`docker-compose`, `Dockerfile.dev` de frontend y backend).
- Conexion PostgreSQL y estructura de arranque del backend.
- Manejo de uploads para fotos/audio.
- CRUD de clientes, con renombre y endurecimiento.
- CRUD de tecnicos, con renombre de rol/entidad.
- Flujo de emergencias, porque ya existe una estructura cercana al nuevo dominio.
- Dashboard como base visual y operativa.
- Integracion futura con mobile via HTTP JSON/multipart.
- FCM token registry y notificaciones push, si la app React Native lo necesitara.

### Reutilizacion media

- Login y hashing de contraseñas.
- Proteccion de correo admin reservado.
- Bloqueo de intentos de login.
- Mapa Leaflet para ubicaciones de sucursales o eventos.
- Secciones de reportes y bitacora del dashboard.

### Reutilizacion baja o cuestionable

- Modulo `workshops` tal como esta.
- Aprobacion de talleres por administrador.
- Pagina `planes`.
- Pagina `suscripciones`.
- Narrativa de landing basada en afiliacion y red comercial.
- Nombre de variables y tablas muy atados a `workshop`.

## 6. Que Debe Cambiar Para El Nuevo Dominio

### Mapeo conceptual recomendado

- `workshops` / `workshop_registrations` → `branches` / `branches` o `company_branches`
- `approval_status` → `branch_status` o `operational_status`
- `technicians` → `vehicle_technicians`
- `vehicle` se puede conservar como `vehicles`
- `emergency_reports` → `emergencies`
- `emergency_assignments` → `emergency_dispatches` o `emergency_assignments`
- `photo_paths`, `audio_path` → `evidences`, `attachments` o `incident_media`
- `maintenance` usado en dashboard → `seguimiento`, `atencion`, `operacion`

### Adaptacion a tus reglas nuevas

#### Empresa con sucursales propias

Cambios:

- Eliminar nocion de taller afiliado.
- Eliminar aprobacion externa de taller.
- Reemplazar formulario de registro publico por gestion interna de sucursales.
- Convertir `workshops` en sucursales administradas por la empresa.

#### Sin planes de suscripcion

Cambios:

- Eliminar o archivar `/planes`, `/suscripciones`, copys comerciales y referencias de comision.
- Limpiar el menu principal y el sitio publico.

#### Sin pagos, comisiones ni marketplace

Cambios:

- Eliminar lenguaje de red de talleres, visibilidad, mas ingresos y comisiones.
- Eliminar cualquier futuro acoplamiento de reportes con monetizacion.

#### App movil React Native conectada al core

Cambios:

- Formalizar autenticacion API real.
- Congelar y documentar contratos para cliente movil.
- Separar endpoints publicos, web admin y mobile.
- Definir versionado de API si el backend sera el Microservicio 1 Core.

### Traduccion de tu mapeo propuesto

- `proyectos` → no aplica directamente; usar `emergencias`.
- `planos` → evidencias, documentos, fotos, audios, PDF, actas.
- `mediciones` → eventos de seguimiento, historial, bitacora, trazabilidad.
- `organizaciones/talleres` → sucursales.
- `tecnico de campo` → tecnico vehicular.

## 7. Riesgos Tecnicos

### Riesgos que pueden romper login

- Cambiar nombres de rol `admin` / `workshop` sin adaptar frontend y backend a la vez.
- Renombrar tablas de talleres sin migrar `get_workshop_by_email`, `login` y el dashboard.
- Sustituir recovery sin revisar `forgot-password-page.component.ts`.
- Mantener tokens cosmeticos mientras se cree que el sistema esta autenticado.

### Riesgos que pueden romper la conexion movil

- Cambiar payloads de `clientes`, `vehiculos`, `emergencias` sin versionar contratos.
- Renombrar campos `nearest_workshop_*` sin capa de compatibilidad.
- Cambiar `multipart/form-data` de emergencias sin coordinar con React Native.
- Cambiar rutas `/api/clientes`, `/api/vehiculos`, `/api/emergencias` sin documentacion de transicion.

### Riesgos que pueden romper Docker

- Renombrar carpetas `frontend` o `backend` sin actualizar `docker-compose.yml`.
- Cambiar el path de `firebase-service-account.json`.
- Mover directorios de `uploads` sin actualizar montajes y `StaticFiles`.
- Cambiar puertos base sin revisar `frontend/src/app/api-base.ts`.

### Riesgos que pueden romper base de datos

- Renombrar tablas o columnas sin tener migraciones formales.
- Mezclar cambios en `db.py` y datos existentes en `postgres_data`.
- Cambiar `workshop_registrations` a sucursales sin estrategia de backfill.
- Reescribir `init_database()` sin pruebas sobre una BD ya poblada.

### Riesgos que pueden romper frontend

- `dashboard-page.component.ts` esta muy acoplado a nombres actuales de API y dominio.
- `api-base.ts` asume backend en puerto `8787`.
- El dashboard asume `workshops`, `technicians`, `clientes`, `emergencias`.
- El menu y las paginas publicas todavia contienen lenguaje comercial anterior.

## 8. Tabla De Archivos Clave Y Accion Recomendada

| Archivo actual | Responsabilidad actual | Accion recomendada | Nuevo nombre o nuevo proposito |
|---|---|---|---|
| `docker-compose.yml` | Levanta `db`, `backend`, `frontend` | Conservar y ajustar nombres de servicio mas adelante | Base del entorno Core |
| `.env.example` | Variables raiz de PostgreSQL | Conservar y ampliar | Variables de infraestructura |
| `backend/.env.example` | Variables del backend, admin, DB, uploads, FCM | Conservar pero limpiar defaults inseguros | Config del Microservicio 1 Core |
| `backend/Dockerfile.dev` | Imagen dev de FastAPI | Conservar | Imagen dev del Core Backend |
| `frontend/Dockerfile.dev` | Imagen dev de Angular | Conservar | Imagen dev del Core Web |
| `backend/app/main.py` | App FastAPI, endpoints, logica, schemas, seguridad operativa | Refactorizar fuerte | Punto de entrada del Core, solo wiring |
| `backend/app/db.py` | SQL, tablas, CRUD, bootstrap de esquema | Dividir por dominio y migraciones | Capa de persistencia/refactor a repositories |
| `backend/app/config.py` | Settings del backend | Conservar | Configuracion del Core |
| `backend/app/security.py` | Hash, verify, normalizaciones | Conservar y ampliar con auth real | Seguridad transversal |
| `backend/app/uploads.py` | Manejo de archivos y URLs publicas | Conservar | Evidencias y adjuntos de emergencias |
| `backend/app/constants.py` | Constantes de uploads, roles y limites | Conservar con renombre | Constantes del dominio nuevo |
| `backend/app/schemas.py` | Parte de los contratos Pydantic | Reordenar y completar | Schemas del Core por modulo |
| `backend/app/routes/*.py` | Rutas modulares no conectadas del todo | Revisar y reutilizar parcialmente | Base para modularizar routers reales |
| `frontend/src/main.ts` | Bootstrap Angular | Conservar | Bootstrap del Core Web |
| `frontend/src/app/app.routes.ts` | Rutas de la web | Refactorizar | Rutas del panel Core y sitio institucional minimo |
| `frontend/src/app/app.component.ts` | Shell principal | Conservar con ajustes | Layout raiz del Core Web |
| `frontend/src/app/api-base.ts` | Base URL del backend | Conservar y endurecer por entorno | Config de API por environment |
| `frontend/src/app/session.ts` | Persistencia de sesion en storage | Refactorizar | Session/auth client con token real |
| `frontend/src/app/auth.guard.ts` | Guard basico por storage | Refactorizar fuerte | Guard de auth real |
| `frontend/src/app/pages/dashboard-page.component.ts` | Dashboard, CRUD y operacion principal | Dividir por modulos | Panel Core empresarial |
| `frontend/src/app/pages/home-page.component.ts` | Landing y registro publico de talleres | Rediseñar | Landing institucional o acceso operativo |
| `frontend/src/app/pages/login-page.component.ts` | Login admin/socio | Conservar con cambios de rol | Login del Core |
| `frontend/src/app/pages/forgot-password-page.component.ts` | Recovery/cambio de clave | Rehacer flujo seguro | Recuperacion de acceso segura |
| `frontend/src/app/pages/map-page.component.ts` | Mapa de talleres | Conservar adaptando entidad | Mapa de sucursales/unidades/eventos |
| `frontend/src/app/pages/planes-page.component.ts` | Planes y comercial | Retirar del flujo activo | Archivo legado o futura pagina institucional |
| `frontend/src/app/pages/suscripciones-page.component.ts` | Formulario comercial no enrutado | Archivar logicamente | Legado no prioritario |
| `frontend/src/app/pages/servicios-page.component.ts` | Marketing de servicios | Ajustar copy o reducir | Servicios de asistencia del sistema |
| `README.md` | Guia de uso actual | Reescribir | Documentacion del nuevo Core |
| `FLUJO_PROYECTO.md` | Flujo funcional actual | Reescribir | Documento de arquitectura y dominio nuevo |
| `backend/API.md` | Documentacion API actual | Reescribir y versionar | Contrato API del Core |

## 9. Evaluacion De Reutilizacion Por Objetivo

### Como Microservicio 1: Gestion Empresarial Core

El backend actual sirve como punto de partida, pero no todavia como microservicio robusto.

Sirve porque ya tiene:

- clientes
- tecnicos
- vehiculos
- emergencias
- asignaciones
- notificaciones
- dashboard acoplado

No sirve aun como Core final porque:

- no tiene autenticacion real de API
- no tiene arquitectura modular limpia
- no tiene migraciones formales
- mantiene semantica de marketplace/talleres afiliados
- mezcla mucho dominio con presentacion operativa

## 10. Resumen Del Estado Actual

El repositorio actual es una base funcional de asistencia vehicular con frontend Angular y backend FastAPI/PostgreSQL. Ya existe un flujo de emergencias, clientes, vehiculos, tecnicos y operadores, lo cual reduce mucho el esfuerzo de migracion hacia el nuevo sistema.

Sin embargo, no esta listo para ser el CORE definitivo sin una refactorizacion importante. La autenticacion es incompleta, la recuperacion de contraseña es insegura, la arquitectura del backend esta concentrada en `main.py`, y el frontend mezcla sitio publico comercial con panel operativo.

## 11. Que Partes Conviene Conservar

- `docker-compose.yml`
- `backend/app/config.py`
- `backend/app/security.py`
- `backend/app/uploads.py`
- estructura base PostgreSQL
- CRUD de clientes
- CRUD de tecnicos
- flujo general de emergencias
- dashboard como referencia funcional
- mapa y gestion de ubicaciones
- manejo de FCM tokens, si se usara mobile push

## 12. Que Partes Deben Cambiarse

- semantica completa de `workshops` hacia `sucursales`
- flujo publico de afiliacion y aprobacion
- paginas de planes/suscripciones
- autenticacion y autorizacion reales
- recovery de contraseña
- modularizacion backend
- contratos API consolidados para mobile
- guard y sesion del frontend
- naming general ligado a marketplace/talleres aliados

## 13. Primera Recomendacion Para El Siguiente Paso

La primera recomendacion es hacer una fase de **diseno de migracion de dominio y arquitectura**, antes de tocar codigo:

1. Congelar el modelo objetivo del Core:
   `usuarios`, `roles`, `sucursales`, `tecnicos vehiculares`, `vehiculos`, `emergencias`, `eventos de seguimiento`, `evidencias`.
2. Definir el mapa exacto de renombre tabla por tabla y endpoint por endpoint.
3. Decidir la nueva arquitectura backend:
   `routers + services + repositories + schemas`.
4. Definir autenticacion real para web y mobile.
5. Recién despues iniciar la refactorizacion incremental con migraciones formales.

La mejor estrategia no es “renombrar todo de una vez”, sino convertir este repo en el Core nuevo por capas, empezando por contratos, auth y modelo de datos.
