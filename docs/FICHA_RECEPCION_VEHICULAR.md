# Ficha De Recepcion Vehicular

## Objetivo

Agregar un modulo minimo de ficha de recepcion vehicular para conectar el dashboard web con la app movil del mecanico.

El modulo permite:

- registrar una ficha desde el dashboard web
- listar fichas para operacion administrativa
- consultar el detalle por ficha
- consultar la ficha asociada a una emergencia
- exponer la ficha al mecanico movil cuando la emergencia le pertenece

## Tabla Utilizada

El proyecto ya contaba con la tabla `fichas_recepcion`, por lo que no se creo una tabla paralela nueva.

Se reutilizo esa base y se amplió con:

- `emergencia_id BIGINT NULL REFERENCES reportes_emergencia(id) ON DELETE SET NULL`

La tabla sigue conservando el esquema existente del modulo previo:

- `cliente_id`
- `vehiculo_id`
- `recepcionado_por_user_id`
- `assigned_mechanic_id`
- `status`
- `fecha_recepcion`
- `observaciones_generales`
- `created_at`
- `updated_at`

Tambien siguen activas las tablas relacionadas:

- `clientes_recepcion`
- `vehiculos_recepcion`
- `problemas_recepcion`
- `accesorios_recepcion`
- `diagnosticos_recepcion`
- `observaciones_recepcion`

## Endpoints

### Web / Operacion

- `POST /api/fichas-recepcion`
- `GET /api/fichas-recepcion`
- `GET /api/fichas-recepcion/{id}`
- `GET /api/emergencias/{emergencia_id}/ficha-recepcion`

### Mobile mecanico

- `GET /api/mobile/emergencias/{emergencia_id}/ficha-recepcion`

## Permisos

- `admin`: puede crear, listar y ver detalle
- `secretaria`: puede crear, listar y ver detalle
- `mecanico`: no crea ficha desde web; solo consulta desde endpoint mobile si la emergencia le corresponde
- `client`: no crea ficha y no consume este modulo

## Reglas De Negocio Implementadas

- al menos uno entre `cliente_id` o `emergencia_id` debe existir
- si `emergencia_id` existe, la emergencia debe existir
- si `cliente_id` existe, el cliente debe existir y estar activo
- si la emergencia ya tiene una ficha activa, no se crea otra
- la placa se normaliza con trim y uppercase si fue enviada
- `problema_reportado` es obligatorio
- el estado inicial se adapta al dominio existente y se guarda como `registrada`

## Flujo Web -> Backend -> Movil

1. Secretaria o admin crea una ficha desde `/fichas-recepcion/nueva`.
2. El frontend envía la ficha a `POST /api/fichas-recepcion`.
3. El backend reutiliza la estructura existente de recepcion y guarda la relacion opcional con `emergencia_id`.
4. Si la ficha tiene mecanico asignado y la emergencia pertenece a ese flujo operativo, el mecanico puede consultar `GET /api/mobile/emergencias/{emergencia_id}/ficha-recepcion`.

## Fuera De Alcance

Queda explicitamente fuera de esta iteracion:

- PDF
- fotos
- firma
- edicion avanzada
- eliminacion fisica
- autocompletado complejo
- normalizacion completa entre `clientes(role=mecanico)` y la tabla operativa `mecanicos`
