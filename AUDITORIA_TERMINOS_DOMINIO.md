# AUDITORIA DE TERMINOS DE DOMINIO

## Objetivo
Detectar referencias del dominio anterior/comercial que deben migrarse para el nuevo Core de Emergencias Vehiculares con sucursales propias.

## Alcance
Se revisaron referencias en:

- `README.md`
- `FLUJO_PROYECTO.md`
- `backend/API.md`
- `backend/.env.example`
- `backend/app/`
- `frontend/src/`

## Nota de alcance
Los archivos de auditoría y planificación generados en esta rama (`AUDITORIA_*`, `PLAN_*`, `BASELINE_*`) también contienen estos términos, pero no se incluyen en la tabla principal porque son documentación de análisis y no forman parte del dominio ejecutable del sistema.

## Criterio de interpretación

- Referencias en `frontend/src/`:
  más candidatas a limpieza conceptual inmediata.
- Referencias en `backend/app/`:
  suelen estar atadas a contratos, tablas, endpoints y compatibilidad.
- Referencias en `backend/API.md` y `FLUJO_PROYECTO.md`:
  deben actualizarse, pero después de definir el modelo objetivo.

## Tabla de hallazgos

| Término encontrado | Archivo | Línea aprox. | Contexto breve | Acción recomendada |
|---|---|---:|---|---|
| `workshop`, `workshops` | [backend/app/db.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/db.py:17) | 17 | Tabla principal `workshop_registrations`, columnas `workshop_name`, `workshop_id`, `nearest_workshop_*` y múltiples SQL CRUD | conservar temporalmente por compatibilidad |
| `nearest_workshop_*` | [backend/app/db.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/db.py:107) | 107 | Campos de emergencia acoplados al concepto de taller cercano | revisar manualmente |
| `workshop_initial_password` | [backend/app/config.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/config.py:13) | 13 | Credencial inicial explícitamente asociada a taller | conservar temporalmente por compatibilidad |
| `WorkshopRegistrationCreate`, `WorkshopRegistrationResponse`, `WorkshopApprovalStatusUpdate` | [backend/app/schemas.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/schemas.py:6) | 6 | Schemas base del dominio taller/socio | conservar temporalmente por compatibilidad |
| `workshop_id` en técnicos | [backend/app/schemas.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/schemas.py:49) | 49 | El técnico sigue modelado como perteneciente a un taller | reemplazar por sucursal |
| `POST /api/workshops` | [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1327) | 1327 | Endpoint principal de registro de taller | conservar temporalmente por compatibilidad |
| `nearest_workshop_id`, `nearest_workshop_name`, etc. | [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1404) | 1404 | Contrato `multipart/form-data` de emergencias usa taller más cercano | conservar temporalmente por compatibilidad |
| `GET/PUT/DELETE /api/workshops` | [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1868) | 1868 | CRUD operativo completo de talleres | conservar temporalmente por compatibilidad |
| `approval-status` de taller | [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1953) | 1953 | Flujo de aprobación/rechazo de taller afiliado | reemplazar por sucursal |
| `role=workshop`, `get_workshop_by_email`, login de taller | [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2169) | 2169 | Login y auth todavía modelados en torno a cuenta de taller/socio | conservar temporalmente por compatibilidad |
| `forgot-password` de taller | [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1911) | 1911 | Recuperación vinculada a talleres; además es insegura | revisar manualmente |
| `WORKSHOP_ROLE`, `get_workshop_by_email`, `/workshops/change-password` | [backend/app/routes/auth.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/routes/auth.py:6) | 6 | Refactor parcial no conectada aún, pero muy acoplada a talleres | conservar temporalmente por compatibilidad |
| `router = APIRouter(... tags=["workshops"])` | [backend/app/routes/workshops.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/routes/workshops.py:44) | 44 | Módulo alterno de talleres con el mismo dominio viejo | revisar manualmente |
| `WORKSHOP_INITIAL_PASSWORD` | [backend/.env.example](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/.env.example:9) | 9 | Variable de entorno de contraseña inicial de taller | conservar temporalmente por compatibilidad |
| `POST /api/workshops/forgot-password` | [backend/API.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/API.md:585) | 585 | Documentación pública de recuperación de contraseña de taller | revisar manualmente |
| `POST /api/workshops`, `GET /api/workshops`, etc. | [backend/API.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/API.md:645) | 645 | Documentación completa del módulo de talleres | conservar temporalmente por compatibilidad |
| `nearest_workshop_*` | [backend/API.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/API.md:667) | 667 | Contrato documentado de emergencia con taller cercano | conservar temporalmente por compatibilidad |
| `taller`, `talleres`, `socio de taller` | [FLUJO_PROYECTO.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/FLUJO_PROYECTO.md:24) | 24 | Documento funcional todavía define roles y flujos en torno a talleres | reemplazar por sucursal |
| `Monto`: 90% del precio para el trabajo del taller | [FLUJO_PROYECTO.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/FLUJO_PROYECTO.md:206) | 206 | Regla operativa ligada a reparto/monetización | eliminar porque pertenece a monetización |
| `Talleres`/`Reportes` del dashboard | [FLUJO_PROYECTO.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/FLUJO_PROYECTO.md:250) | 250 | Documenta secciones aún con lenguaje de taller afiliado | reemplazar por sucursal |
| `Taller ACB Asistencia` | [frontend/src/index.html](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/index.html:5) | 5 | Título HTML de la aplicación | reemplazar por sucursal |
| `Planes`, `suscripciones`, `Taller ACB Asistencia` | [frontend/src/app/app.routes.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/app.routes.ts:21) | 21 | Rutas activas/redirecciones y títulos visibles ligados al dominio comercial | eliminar porque pertenece a monetización |
| `Taller ACB Asistencia`, `talleres aliados`, enlace `Planes` | [frontend/src/app/app.component.html](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/app.component.html:61) | 61 | Branding y footer comercial del sitio público | reemplazar por sucursal |
| `Planes` en navegación | [frontend/src/app/app.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/app.component.ts:19) | 19 | Menú principal todavía publica una vista comercial | eliminar porque pertenece a monetización |
| `role: 'admin' | 'workshop'` | [frontend/src/app/session.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/session.ts:8) | 8 | Sesión frontend todavía persiste el rol `workshop` | conservar temporalmente por compatibilidad |
| `Red nacional de talleres afiliados`, `Afiliación inmediata`, `Registra tu taller` | [frontend/src/app/pages/home-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/home-page.component.ts:30) | 30 | Landing principal completamente orientada a afiliación y captación de talleres | reemplazar por sucursal |
| `Únete a nuestra red y aumenta tus ingresos` | [frontend/src/app/pages/home-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/home-page.component.ts:37) | 37 | Copy explícito de monetización/marketplace | eliminar porque pertenece a monetización |
| `Nombre del Taller`, `Dirección del Taller`, `Registrar taller` | [frontend/src/app/pages/home-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/home-page.component.ts:42) | 42 | Formulario público de onboarding para talleres | reemplazar por sucursal |
| `Crecimiento para talleres aliados`, `unirte a nuestra red` | [frontend/src/app/pages/home-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/home-page.component.ts:192) | 192 | Beneficios comerciales de afiliación | eliminar porque pertenece a monetización |
| `Planes para talleres asociados`, `No pagas por estar`, `Comision por servicio` | [frontend/src/app/pages/planes-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/planes-page.component.ts:24) | 24 | Página 100% comercial: planes, visibilidad, comisiones, priorización | eliminar porque pertenece a monetización |
| `Suscripciones`, `Afiliación de talleres socios` | [frontend/src/app/pages/suscripciones-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/suscripciones-page.component.ts:14) | 14 | Flujo comercial legado de suscripción/afiliación | eliminar porque pertenece a monetización |
| `WorkshopMapItem`, `Talleres registrados en el mapa`, `API de talleres` | [frontend/src/app/pages/map-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/map-page.component.ts:9) | 9 | Tipos, labels y consumo API del mapa dependen del módulo `workshops` | reemplazar por sucursal |
| `Socio del Taller`, `placeholder ejemplo@talleracb.com`, `account_type: workshop` | [frontend/src/app/pages/login-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/login-page.component.ts:26) | 26 | Login del panel todavía se entiende como acceso de taller/socio | conservar temporalmente por compatibilidad |
| `workshopsApiUrl`, `workshops`, `WorkshopRegistration` | [frontend/src/app/pages/dashboard-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/dashboard-page.component.ts:1711) | 1711 | Estado central del dashboard y URL API atados a talleres | conservar temporalmente por compatibilidad |
| `Talleres registrados`, `Registros creados desde el formulario publico` | [frontend/src/app/pages/dashboard-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/dashboard-page.component.ts:1835) | 1835 | KPIs del dashboard todavía miden afiliación de talleres | reemplazar por sucursal |
| `isWorkshopSession`, `Todos los talleres`, `nearestWorkshopName` | [frontend/src/app/pages/dashboard-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/dashboard-page.component.ts:1936) | 1936 | Permisos, reportes y bitácora dependen del rol y nombre de taller | conservar temporalmente por compatibilidad |
| `approval-status`, `¿Deseas eliminar el taller...?`, `Completa Taller...` | [frontend/src/app/pages/dashboard-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/dashboard-page.component.ts:3167) | 3167 | CRUD del dashboard modelado para talleres aprobados/pendientes | revisar manualmente |
| `Solicitudes recibidas desde el formulario de afiliacion` | [frontend/src/app/pages/dashboard-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/dashboard-page.component.ts:3526) | 3526 | Métrica visual de afiliación comercial | eliminar porque pertenece a monetización |
| `plan-card`, `plans-*` | [frontend/src/app/pages/shared-pages.css](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/shared-pages.css:928) | 928 | CSS dedicada a páginas de planes y layout comercial | eliminar porque pertenece a monetización |
| `proyecto`, `proyectos` | [README.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/README.md:3) | 3 | Uso genérico como “proyecto”; no remite al dominio anterior de negocio | no aplica |
| `heatmapper`, `wireless`, `medicion`, `mediciones`, `plano`, `planos` | Repositorio auditado | N/A | No se encontraron referencias ejecutables al dominio Wireless HeatMapper; solo aparecen en documentos de auditoría | no aplica |

## Hallazgos consolidados

### 1. Dominio taller/comercial
Las referencias a `workshop`, `taller`, `talleres`, `socio de taller` y `approval_status` están embebidas en:

- tablas y columnas de base de datos
- endpoints REST
- login y recuperación de contraseña
- dashboard operativo
- mapa
- landing pública
- documentación API y funcional

Conclusión:

- no es solo un problema de textos
- el dominio de taller está incrustado en contratos, persistencia y permisos

### 2. Dominio de monetización
Las referencias a `planes`, `suscripciones`, `comision`, `pago` y lenguaje de visibilidad/ingresos están concentradas sobre todo en:

- `frontend/src/app/pages/planes-page.component.ts`
- `frontend/src/app/pages/suscripciones-page.component.ts`
- `frontend/src/app/pages/home-page.component.ts`
- `frontend/src/app/app.routes.ts`
- `frontend/src/app/app.component.html`
- `FLUJO_PROYECTO.md`

Conclusión:

- la monetización está mucho más en frontend y documentación que en el backend transaccional
- eso vuelve la limpieza conceptual relativamente segura si se hace sin tocar contratos primero

### 3. Dominio anterior tipo Wireless HeatMapper
No se detectaron referencias ejecutables relevantes a:

- `heatmapper`
- `wireless`
- `medicion`
- `mediciones`
- `plano`
- `planos`

Conclusión:

- el repositorio actual ya está efectivamente migrado a asistencia vehicular
- el arrastre principal no es HeatMapper, sino marketplace/talleres/comercial

## Lista de cambios seguros para el siguiente paso

- Actualizar documentación funcional y técnica:
  - `README.md`
  - `FLUJO_PROYECTO.md`
  - `backend/API.md`
- Limpiar vistas puramente comerciales:
  - `frontend/src/app/pages/planes-page.component.ts`
  - `frontend/src/app/pages/suscripciones-page.component.ts`
- Ajustar branding público:
  - `frontend/src/app/app.component.html`
  - `frontend/src/index.html`
- Limpiar títulos/rutas visibles del frontend sin romper backend:
  - `frontend/src/app/app.routes.ts`
  - `frontend/src/app/app.component.ts`

## Lista de cambios riesgosos que NO deben tocarse todavía

- Renombrar tablas o columnas físicas con `workshop_*`
- Cambiar endpoints `/api/workshops`
- Cambiar campos `nearest_workshop_*`
- Cambiar `role=workshop` en login/sesión sin estrategia de compatibilidad
- Reescribir `backend/app/db.py` sin Alembic
- Reescribir `backend/app/main.py` antes de definir modelo y auth final
- Tocar de golpe `frontend/src/app/pages/dashboard-page.component.ts` sin dividir responsabilidades

## Recomendación del primer archivo o módulo que conviene modificar

### Recomendación principal

`frontend/src/app/pages/planes-page.component.ts`

### Por qué

- concentra referencias puramente comerciales
- no sostiene contratos backend
- no afecta autenticación
- no impacta base de datos
- permite empezar la limpieza conceptual con riesgo bajo

### Recomendación técnica inmediata después de eso

Si el siguiente paso ya debe atacar funcionalidad real del Core, entonces el mejor primer módulo no visual es:

`backend/app/main.py` en el flujo de autenticación y recuperación de contraseña`

pero solo para:

- endurecer auth
- preparar compatibilidad futura
- sin renombrar aún el dominio `workshop`

## Cierre

La auditoría confirma que el arrastre dominante del sistema no es el dominio Wireless HeatMapper, sino el modelo de:

- talleres afiliados
- marketplace/red
- páginas comerciales
- comisiones/planes/suscripciones

La migración segura debe separar dos capas:

1. limpieza visual/comercial de bajo riesgo
2. migración profunda del dominio técnico `workshop -> branch/sucursal`

Hacer ambas al mismo tiempo aumentaría innecesariamente el riesgo sobre login, dashboard, base de datos y compatibilidad con mobile.
