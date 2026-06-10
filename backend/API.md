# Backend API

Documentacion breve de los endpoints disponibles en el backend FastAPI.

## Base URL

- Desarrollo con Docker Compose: `http://localhost:8787`
- Alternativa equivalente en la misma maquina: `http://127.0.0.1:8787`

Nota:

- El backend de este proyecto corre dentro de Docker.
- El host `db` de PostgreSQL esta pensado para resolverse desde la red interna de Docker Compose.

## Endpoints

### `GET /`

Endpoint basico para comprobar que el backend esta levantado.

Respuesta esperada:

```json
{
  "message": "Backend running"
}
```

Ejemplo:

```bash
curl http://localhost:8787/
```

### `GET /api/health`

Verifica el estado general del backend y la conexion con PostgreSQL.

Respuesta esperada:

```json
{
  "status": "ok",
  "environment": "development",
  "database": "connected"
}
```

Campo `database`:

- `connected`: la base de datos responde correctamente
- `unavailable`: el backend esta arriba, pero PostgreSQL no responde

Ejemplo:

```bash
curl http://localhost:8787/api/health
```

### `POST /api/devices/fcm-token`

Registra o actualiza el token FCM de un dispositivo movil.

#### Autenticacion

- Requiere `Authorization: Bearer <token>`.
- Un usuario autenticado solo puede registrar su propio `user_id`.
- El administrador puede registrar tokens para otros usuarios.
- Las cuentas `workshop` no pueden usar este endpoint.

#### Body JSON

```json
{
  "user_id": 3,
  "fcm_token": "token_del_dispositivo",
  "platform": "android"
}
```

Valores permitidos para `platform`:

- `android`
- `ios`
- `web`

#### Comportamiento

- Crea el token si no existe.
- Si el mismo token ya existe, actualiza `user_id`, `platform`, `updated_at` y lo marca como activo.
- Permite mas de un dispositivo por usuario porque la unicidad esta en `fcm_token`.
- Requiere que `user_id` exista en clientes.

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "user_id": 3,
  "fcm_token": "token_del_dispositivo",
  "platform": "android",
  "is_active": true,
  "created_at": "2026-04-25T01:25:00.000000Z",
  "updated_at": "2026-04-25T01:25:00.000000Z"
}
```

#### Push enviados por backend

El backend envia notificaciones FCM si `FCM_ENABLED=true` y `FIREBASE_CREDENTIALS_PATH` apunta al JSON de service account de Firebase.

Eventos implementados:

- `emergency_accepted`: cuando un taller acepta una emergencia.
- `mechanic_assigned`: cuando un taller asigna o cambia el mecanico de una emergencia.

Payload para emergencia aceptada:

```json
{
  "notification": {
    "title": "Emergencia aceptada",
    "body": "DiegoRepair acepto tu emergencia: Bateria descargada"
  },
  "data": {
    "type": "emergency_accepted",
    "emergency_id": "45",
    "workshop_id": "11",
    "workshop_name": "DiegoRepair",
    "incident_description": "Bateria descargada"
  }
}
```

Payload para mecanico asignado:

```json
{
  "notification": {
    "title": "Mecánico asignado",
    "body": "Lucia Cuellar de DiegoRepair atendera: Bateria descargada"
  },
  "data": {
    "type": "mechanic_assigned",
    "emergency_id": "45",
    "workshop_id": "11",
    "mecanico_id": "40",
    "workshop_name": "DiegoRepair",
    "mecanico_name": "Lucia Cuellar",
    "incident_description": "Bateria descargada",
    "mechanic_latitude": "-17.7700",
    "mechanic_longitude": "-63.1700"
  }
}

```

Nota: el backend ya maneja tracking operativo real para emergencias aceptadas y asignadas. Cuando todavia no existen eventos persistidos, algunos contratos legacy pueden seguir mostrando coordenadas derivadas de la sucursal o taller asociado.

### `POST /api/clientes`

Registra un cliente desde la app movil despues de la validacion OTP.

#### Body JSON

```json
{
  "identityCard": "12345678",
  "fullName": "Juan Perez Gomez",
  "email": "juan@example.com",
  "phone": "71234567",
  "password": "ClaveSegura123",
  "confirmPassword": "ClaveSegura123",
  "acceptedTerms": true,
  "role": "client"
}
```

#### Claves aceptadas

El backend acepta tanto nombres en camelCase como en snake_case para facilitar compatibilidad con el telefono:

- `identityCard`, `identity_card`, `ci`
- `fullName`, `full_name`, `name`
- `phone`, `telefono`
- `confirmPassword`, `confirm_password`
- `acceptedTerms`, `accepted_terms`, `termsAccepted`

#### Validaciones

- `identity_card`: entre 5 y 40 caracteres
- `full_name`: entre 3 y 160 caracteres
- `email`: debe ser un correo valido
- `phone`: entre 7 y 40 caracteres
- `password`: minimo 6 caracteres
- `confirm_password`: si se envia, debe coincidir con `password`
- `accepted_terms`: debe ser `true`

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "identity_card": "12345678",
  "full_name": "Juan Perez Gomez",
  "email": "juan@example.com",
  "phone": "71234567",
  "role": "client",
  "accepted_terms": true,
  "created_at": "2026-04-11T20:45:00.000000Z",
  "updated_at": "2026-04-11T20:45:00.000000Z"
}
```

#### Campos canónicos y compatibilidad

Para asignación de mecánicos, el contrato preferido del backend es:

- `assigned_mecanico_id`
- `assigned_mecanico_name`
- `assigned_mecanico_phone`
- `assigned_mecanico_email`
- `assigned_mecanico_specialty`

Aliases legacy mantenidos temporalmente por compatibilidad:

- `assigned_mechanic_id`
- `assigned_mechanic_name`
- `assigned_mechanic_phone`
- `assigned_mechanic_email`
- `assigned_mechanic_specialty`
- `assigned_technician_id`
- `assigned_technician_name`
- `assigned_technician_phone`
- `assigned_technician_email`
- `assigned_technician_specialty`

Recomendación:

- Clientes nuevos deben preferir siempre `assigned_mecanico_*`.
- Los aliases `assigned_mechanic_*` y `assigned_technician_*` deben considerarse `legacy/deprecated` y se mantienen solo para no romper integraciones existentes.
- Los clientes nuevos deben consumir `assigned_mecanico_*`. Los aliases `assigned_mechanic_*` y `assigned_technician_*` se mantienen temporalmente por compatibilidad.

#### Errores posibles

- `409 Conflict`: ya existe un cliente con ese carnet o correo
- `422 Unprocessable Entity`: datos invalidos o terminos no aceptados

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/clientes \
  -H "Content-Type: application/json" \
  -d '{
    "identityCard": "12345678",
    "fullName": "Juan Perez Gomez",
    "email": "juan@example.com",
    "phone": "71234567",
    "password": "ClaveSegura123",
    "confirmPassword": "ClaveSegura123",
    "acceptedTerms": true,
    "role": "client"
  }'
```

### `GET /api/clientes`

Lista los clientes registrados.

Ejemplo:

```bash
curl http://localhost:8787/api/clientes
```

### `PUT /api/clientes/{client_id}/status`

Actualiza el estado de un cliente desde el panel administrativo.

#### Body JSON

```json
{
  "status": "suspended"
}
```

Valores permitidos:

- `active`
- `suspended`

Ejemplo:

```bash
curl -X PUT http://localhost:8787/api/clientes/4/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active"
  }'
```

### `PUT /api/clientes/{client_id}`

Actualiza los datos administrativos de un cliente.

#### Body JSON

```json
{
  "identity_card": "7700476",
  "full_name": "Jhasmany Fernandez",
  "email": "jhasmany@gmail.com",
  "phone": "72992000",
  "password": "NuevaClave123",
  "role": "client",
  "status": "active",
  "accepted_terms": true
}
```

El campo `password` es opcional en esta edición. Si se envía, el backend actualiza la contraseña del cliente; si se omite o va vacío, conserva la actual.

### `DELETE /api/clientes/{client_id}`

Elimina un cliente por su identificador.

Ejemplo:

```bash
curl -X DELETE http://localhost:8787/api/clientes/4
```

### `POST /api/auth/login`

Autentica un cliente registrado desde la app movil.

Tambien autentica al administrador web del sistema con estas credenciales:

- `email`: `administrador@acb.com`
- `password`: `123ppp+++`

Importante:

- El administrador es un usuario virtual del sistema.
- No se guarda en la tabla `clients`.
- Si el correo es `administrador@acb.com`, el backend valida ese acceso fuera del CRUD normal de clientes.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com",
  "password": "claveSegura123"
}
```

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "id": 4,
  "email": "jhasmany@gmail.com",
  "full_name": "Jhasmany Fernandez",
  "phone": "72992000",
  "role": "client",
  "status": "active",
  "access_token": "token_generado_por_el_backend",
  "token_type": "bearer"
}
```

#### Errores posibles

- `401 Unauthorized`: `{"detail":"Correo o contraseña incorrectos"}`
- `403 Forbidden`: `{"detail":"Cuenta suspendida"}`

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com",
    "password": "claveSegura123"
  }'
```

### `POST /api/auth/account-type`

Permite consultar si un correo pertenece a una cuenta registrada y de qué tipo es.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com"
}
```

#### Respuesta cuando existe

```json
{
  "exists": true,
  "role": "workshop"
}
```

o

```json
{
  "exists": true,
  "role": "client"
}
```

#### Respuesta cuando no existe

```json
{
  "exists": false,
  "role": null
}
```

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/auth/account-type \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com"
  }'
```

### `POST /api/auth/forgot-password`

Permite restablecer la contraseña con una sola ruta para clientes y talleres.

El backend decide internamente si el correo pertenece a un cliente o a un taller.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

#### Claves aceptadas

- `newPassword`, `new_password`, `password`
- `confirmPassword`, `confirm_password`

#### Respuesta exitosa

Cliente:

```json
{
  "message": "La contraseña del cliente fue restablecida correctamente"
}
```

Taller:

```json
{
  "message": "La contraseña del taller fue restablecida correctamente"
}
```

#### Errores posibles

- `403 Forbidden`: cuenta suspendida o taller no habilitado
- `404 Not Found`: `{"detail":"No existe una cuenta con ese correo"}`
- `422 Unprocessable Entity`: datos invalidos o contraseñas que no coinciden

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com",
    "newPassword": "NuevaClave123",
    "confirmPassword": "NuevaClave123"
  }'
```

### `POST /api/clientes/change-password`

Permite que un cliente cambie su propia contraseña usando su correo y su contraseña actual.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com",
  "currentPassword": "claveActual123",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

#### Claves aceptadas

- `currentPassword`, `current_password`
- `newPassword`, `new_password`, `password`
- `confirmPassword`, `confirm_password`

#### Validaciones

- `email`: debe pertenecer a un cliente registrado
- `current_password`: debe coincidir con la contraseña actual del cliente
- `new_password`: minimo 6 caracteres
- `confirm_password`: debe coincidir con `new_password`
- La nueva contraseña debe ser distinta a la actual
- La cuenta del cliente debe estar en estado `active`

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "message": "La contraseña del cliente fue actualizada correctamente"
}
```

#### Errores posibles

- `401 Unauthorized`: `{"detail":"La contraseña actual es incorrecta"}`
- `403 Forbidden`: `{"detail":"Cuenta suspendida"}`
- `404 Not Found`: `{"detail":"Cliente no encontrado"}`
- `422 Unprocessable Entity`: datos invalidos o contraseñas que no coinciden

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/clientes/change-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com",
    "currentPassword": "claveActual123",
    "newPassword": "NuevaClave123",
    "confirmPassword": "NuevaClave123"
  }'
```

### `POST /api/clientes/forgot-password`

Permite restablecer la contraseña de un cliente usando solamente su correo y una nueva contraseña.

Importante:

- Este es un flujo simple de recuperacion.
- No pide la contraseña actual.
- No usa token de recuperacion ni envio de correo.

#### Body JSON

```json
{
  "email": "jhasmany@gmail.com",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

#### Claves aceptadas

- `newPassword`, `new_password`, `password`
- `confirmPassword`, `confirm_password`

#### Validaciones

- `email`: debe pertenecer a un cliente registrado
- `new_password`: minimo 6 caracteres
- `confirm_password`: debe coincidir con `new_password`
- La cuenta del cliente debe estar en estado `active`

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "message": "La contraseña del cliente fue restablecida correctamente"
}
```

#### Errores posibles

- `403 Forbidden`: `{"detail":"Cuenta suspendida"}`
- `404 Not Found`: `{"detail":"Cliente no encontrado"}`
- `422 Unprocessable Entity`: datos invalidos o contraseñas que no coinciden

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/clientes/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jhasmany@gmail.com",
    "newPassword": "NuevaClave123",
    "confirmPassword": "NuevaClave123"
  }'
```

### `POST /api/workshops/forgot-password`

Permite restablecer la contraseña de un taller usando solamente su correo y una nueva contraseña.

Importante:

- Este es un flujo simple de recuperacion.
- No pide la contraseña actual.
- No usa token de recuperacion ni envio de correo.

#### Body JSON

```json
{
  "email": "taller@correo.com",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

#### Claves aceptadas

- `newPassword`, `new_password`, `password`
- `confirmPassword`, `confirm_password`

#### Validaciones

- `email`: debe pertenecer a un taller registrado
- `new_password`: minimo 6 caracteres
- `confirm_password`: debe coincidir con `new_password`
- El taller debe estar en estado `activo`

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "message": "La contraseña del taller fue restablecida correctamente"
}
```

#### Errores posibles

- `403 Forbidden`: `{"detail":"El taller todavía no fue habilitado por el administrador"}`
- `404 Not Found`: `{"detail":"Taller no encontrado"}`
- `422 Unprocessable Entity`: datos invalidos o contraseñas que no coinciden

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/workshops/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "taller@correo.com",
    "newPassword": "NuevaClave123",
    "confirmPassword": "NuevaClave123"
  }'
```

### `POST /api/workshops`

### `POST /api/emergencias`

Registra una solicitud de emergencia enviada desde la app movil usando `multipart/form-data`.

#### Campos `form-data`

- `client_id`: opcional, entero mayor a 0
- `vehicle_name`: nombre mostrado del vehiculo
- `vehicle_plate`: placa del vehiculo
- `problem_type`: tipo de problema o emergencia
- `price`: opcional, precio estimado del servicio. Si no llega y el backend puede clasificar el problema, se completa con el precio base
- `problem_type_standardized`: calculado por backend a partir de `problem_type` y `description`; no es necesario enviarlo
- `photo_problem_type_standardized`: calculado por backend desde las fotos cuando la clasificacion visual esta activada
- `photo_classification_confidence`: confianza numerica de la clasificacion visual, entre `0.0` y `1.0`
- `photo_classification_error`: detalle del error si la clasificacion visual falla o no esta configurada
- `description`: opcional, descripcion detallada
- `latitude`: opcional
- `longitude`: opcional
- `address`: opcional
- `zone`: opcional
- `nearest_workshop_id`: opcional, entero mayor a 0
- `nearest_workshop_name`: opcional
- `nearest_workshop_specialty`: opcional
- `nearest_workshop_zone`: opcional
- `nearest_workshop_distance_meters`: opcional
- `audio_duration_seconds`: opcional
- `photos`: opcional, archivo repetido 0..n veces
- `audio`: opcional, archivo unico

#### Valores permitidos para `problem_type`

- `Batería`
- `Neumático`
- `Combustible`
- `Motor`
- `Sistema eléctrico`
- `Accidente`
- `Cerrajería / llaves`
- `Otro`

Si `problem_type` es `Otro`, el cliente movil puede complementar el detalle en `description`.
En ese caso, el backend intenta clasificarlo automaticamente a una de las 7 categorias estandarizadas y la guarda en `problem_type_standardized`.
Si hay fotos y la clasificacion visual esta activada, el backend tambien intenta inferir `photo_problem_type_standardized` y usa esa sugerencia como apoyo cuando el texto no alcanza para decidir.

#### Precios estimados enviados por movil

- `Batería`: `50`
- `Neumático`: `50`
- `Combustible`: `60`
- `Motor`: `100`
- `Sistema eléctrico`: `90`
- `Accidente`: `150`
- `Cerrajería / llaves`: `80`

Para `Otro`, `price` puede no enviarse. Si el backend logra clasificarlo en `problem_type_standardized`, guardara el precio base de esa categoria; si no logra clasificarlo, devolvera `price: null` y queda como servicio a cotizar.

#### Nombres de campos aceptados para archivos

- Fotos: `photos`
- Audio: `audio`

#### Tipos de archivo aceptados

- Fotos: `jpg`, `jpeg`, `png`, `webp`
- Audio: `aac`, `m4a`, `mp3`, `wav`, `ogg`, `webm`

#### Limites actuales

- Fotos: maximo `6` archivos por solicitud
- Tamano maximo por foto: `20 MB`
- Audio: maximo `1` archivo
- Tamano maximo del audio: `40 MB`

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "client_id": 4,
  "vehicle_name": "Toyota Corolla",
  "vehicle_plate": "1234ABC",
  "problem_type": "Neumático",
  "price": 50,
  "problem_type_standardized": "Neumático",
  "photo_problem_type_standardized": "Neumático",
  "photo_classification_confidence": 0.93,
  "photo_classification_error": null,
  "description": "La llanta delantera se vacio en plena avenida",
  "latitude": -17.7833,
  "longitude": -63.1821,
  "address": "Av. Banzer y 4to anillo",
  "zone": "Norte",
  "nearest_workshop_id": 14,
  "nearest_workshop_name": "MecaApp",
  "nearest_workshop_specialty": "Electricidad automotriz",
  "nearest_workshop_zone": "Centro",
  "nearest_workshop_distance_meters": 482.37,
  "audio_duration_seconds": 12.4,
  "audio_transcript": "se me pinchó la llanta en el camino",
  "audio_transcript_status": "completed",
  "audio_transcript_error": null,
  "photo_paths": [
    "emergencias/photos/archivo1.jpg"
  ],
  "photo_urls": [
    "/uploads/emergencias/photos/archivo1.jpg"
  ],
  "audio_path": "emergencias/audio/audio1.m4a",
  "audio_url": "/uploads/emergencias/audio/audio1.m4a",
  "created_at": "2026-04-12T12:00:00.000000Z"
}
```

#### Errores posibles

- `400 Bad Request`: archivo de foto o audio invalido
- `404 Not Found`: `client_id` no existe
- `422 Unprocessable Entity`: `problem_type` invalido
- `503 Service Unavailable`: base de datos no disponible

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/emergencias \
  -F "client_id=4" \
  -F "vehicle_name=Toyota Corolla" \
  -F "vehicle_plate=1234ABC" \
  -F "problem_type=Sistema eléctrico" \
  -F "price=90" \
  -F "description=El auto no enciende y las luces del tablero parpadean" \
  -F "latitude=-17.7833" \
  -F "longitude=-63.1821" \
  -F "address=Av. Banzer y 4to anillo" \
  -F "zone=Norte" \
  -F "nearest_workshop_id=14" \
  -F "nearest_workshop_name=MecaApp" \
  -F "nearest_workshop_specialty=Electricidad automotriz" \
  -F "nearest_workshop_zone=Centro" \
  -F "nearest_workshop_distance_meters=482.37" \
  -F "audio_duration_seconds=12.4" \
  -F "photos=@foto1.jpg" \
  -F "photos=@foto2.jpg" \
  -F "audio=@nota.m4a"
```

Ejemplo con clasificacion automatica desde `Otro`:

```bash
curl -X POST http://localhost:8787/api/emergencias \
  -F "client_id=4" \
  -F "vehicle_name=Suzuki Swift" \
  -F "vehicle_plate=5678XYZ" \
  -F "problem_type=Otro" \
  -F "description=Las llaves quedaron dentro del vehiculo" \
  -F "address=Av. Banzer" \
  -F "zone=Norte"
```

En ese caso, el backend conserva `problem_type=Otro` y normalmente guarda `problem_type_standardized=Cerrajería / llaves`.

Activacion de clasificacion visual:

- `PHOTO_CLASSIFICATION_ENABLED=true`
- `PHOTO_CLASSIFICATION_MODEL=gpt-5-mini`
- `OPENAI_API_KEY=<tu_api_key>`

Si `PHOTO_CLASSIFICATION_ENABLED=false` o no existe `OPENAI_API_KEY`, la emergencia igual se registra y `photo_problem_type_standardized` queda vacio.

### `GET /api/emergencias`

Lista reportes de emergencia en orden descendente.

#### Query params opcionales

- `nearest_workshop_id`: filtra por sucursal o taller cercano
- `secretaria_sucursal_id`: filtra por sucursal de secretaria
- `emergency_status`: filtra por estado (`pendiente`, `activo`, `rechazado`)

#### Respuesta exitosa

Codigo: `200 OK`

```json
[
  {
    "id": 13,
    "client_id": 3,
    "client_name": "Juan Perez",
    "vehicle_name": "Toyota Corolla",
    "vehicle_plate": "1234ABC",
    "problem_type": "Motor",
    "price": 100,
    "emergency_status": "pendiente",
    "problem_type_standardized": "Motor",
    "description": "El vehiculo no arranca",
    "nearest_workshop_id": 1,
    "nearest_workshop_name": "Taller Central",
    "created_at": "2026-05-30T03:10:36.340584Z"
  }
]
```

### `PUT /api/emergencias/{report_id}/status`

Actualiza el estado operativo de una emergencia existente.

#### Roles permitidos

- `admin`
- `secretaria`

#### Reglas

- Solo acepta `emergency_status = "activo"` desde este endpoint.
- Para rechazar con motivo se debe usar `POST /api/emergencias/{report_id}/rechazar`.
- `workshop_id` es obligatorio para aceptar la emergencia.
- Si la emergencia ya estaba `activo`, el endpoint responde `200 OK` sin duplicar notificaciones ni push.
- Al aceptar correctamente:
  - actualiza `estado_emergencia` a `activo`
  - crea una notificación móvil `emergency_accepted` para el cliente
  - envía push FCM al cliente usando el mecanismo existente

#### Query params

- `workshop_id`: entero mayor a `0`, obligatorio para aceptación

#### Body JSON

```json
{
  "emergency_status": "activo"
}
```

#### Notificación creada al aceptar

Tipo: `emergency_accepted`

```json
{
  "tipo": "emergency_accepted",
  "titulo": "Emergencia aceptada",
  "mensaje": "Tu emergencia fue aceptada. Estamos buscando un mecánico disponible.",
  "metadata": {
    "status": "accepted",
    "open_screen": "notifications",
    "emergency_id": 13
  }
}
```

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "id": 13,
  "client_id": 3,
  "client_name": "Juan Perez",
  "vehicle_name": "Toyota Corolla",
  "vehicle_plate": "1234ABC",
  "problem_type": "Motor",
  "price": 100,
  "emergency_status": "activo",
  "description": "El vehiculo no arranca",
  "nearest_workshop_id": 1,
  "nearest_workshop_name": "Taller Central",
  "created_at": "2026-05-30T03:10:36.340584Z"
}
```

#### Errores posibles

- `400 Bad Request`: falta `workshop_id` o se intenta rechazar por este endpoint
- `404 Not Found`: emergencia inexistente o no asociada al `workshop_id` indicado
- `503 Service Unavailable`: base de datos no disponible

Ejemplo:

```bash
curl -X PUT "http://localhost:8787/api/emergencias/13/status?workshop_id=1" \
  -H "Authorization: Bearer <token_admin_o_secretaria>" \
  -H "Content-Type: application/json" \
  -d '{
    "emergency_status": "activo"
  }'
```

### `POST /api/emergencias/{report_id}/rechazar`

Rechaza una emergencia con motivo obligatorio y mantiene el flujo de notificación `emergency_rejected`.

#### Roles permitidos

- `admin`
- `secretaria`

#### Body JSON

```json
{
  "motivo": "No contamos con cobertura operativa inmediata para esta zona."
}
```

### `PUT /api/emergencias/{report_id}/mechanic-assignment`

Asigna o reasigna un mecánico a una emergencia ya aceptada.

#### Roles permitidos

- `admin`
- `secretaria`

#### Reglas

- La emergencia debe estar en estado `activo`.
- `workshop_id` es obligatorio.
- El mecánico debe pertenecer al `workshop_id` indicado.
- El mecánico debe estar `disponible`, salvo que sea exactamente el mismo ya asignado.
- El mecánico debe tener `sucursal_id`.
- La sucursal afiliada del mecánico debe estar `ACTIVO`.
- Si se reasigna el mismo mecánico a la misma emergencia, la asignación se mantiene pero no se duplica la notificación `mechanic_assigned`.
- Si cambia el mecánico, se genera una nueva notificación.

#### Body JSON

```json
{
  "mecanico_id": 5
}
```

#### Notificación creada al asignar

Tipo: `mechanic_assigned`

Título: `Mecánico asignado`

Mensaje:

```text
Carlos Ramírez fue asignado para auxiliarte.
```

Metadata ejemplo:

```json
{
  "open_screen": "emergency_tracking",
  "emergencia_id": 11,
  "mechanic_id": 4,
  "mechanic_name": "Carlos Ramírez",
  "mechanic_phone": "79910530",
  "mechanic_specialty": "Motor",
  "sucursal_id": 3,
  "sucursal_nombre": "Service Norte",
  "tracking_available": true,
  "origin_latitude": -17.784023352445807,
  "origin_longitude": -63.18855724850921,
  "destination_latitude": -17.7895,
  "destination_longitude": -63.1812
}
```

Si faltan coordenadas de origen o destino:

```json
{
  "open_screen": "emergency_tracking",
  "emergencia_id": 11,
  "mechanic_id": 4,
  "mechanic_name": "Carlos Ramírez",
  "mechanic_phone": "79910530",
  "mechanic_specialty": "Motor",
  "sucursal_id": 3,
  "sucursal_nombre": "Service Norte",
  "tracking_available": false,
  "tracking_reason": "Faltan coordenadas de origen o destino"
}
```

#### Push FCM enviado

El backend envía `data.type = mechanic_assigned` y `data.open_screen = emergency_tracking`.

#### Respuesta exitosa

Codigo: `200 OK`

La respuesta sigue usando el contrato canónico de emergencia con campos `assigned_mecanico_*`.

#### Errores posibles

- `404 Not Found`: emergencia o mecánico no encontrado
- `409 Conflict`: la emergencia no fue aceptada o el mecánico no está disponible
- `400 Bad Request`: falta `sucursal_id` afiliada del mecánico
- `503 Service Unavailable`: base de datos no disponible

Ejemplo:

```bash
curl -X PUT "http://localhost:8787/api/emergencias/20/mechanic-assignment?workshop_id=1" \
  -H "Authorization: Bearer <token_admin_o_secretaria>" \
  -H "Content-Type: application/json" \
  -d '{
    "mecanico_id": 5
  }'
```

### `GET /api/mobile/emergencias/{emergencia_id}/tracking`

Devuelve el tracking operativo de una emergencia asignada para el cliente dueño de esa emergencia.

#### Roles permitidos

- `client`

#### Reglas

- Solo puede consultarse para emergencias propias del cliente autenticado.
- La emergencia debe estar `activo`.
- La emergencia debe tener mecánico asignado.
- El origen del tracking es la sucursal del mecánico asignado.
- El destino es la ubicación de la emergencia.
- Si faltan coordenadas de sucursal o de emergencia, responde `409 Conflict`.

#### Respuesta exitosa

Codigo: `200 OK`

```json
{
  "emergencia_id": 15,
  "emergency_id": 15,
  "client_id": 7,
  "estado_tracking": "moving",
  "estado_emergencia": "activo",
  "mecanico": {
    "id": 4,
    "nombre": "Carlos Ramirez",
    "telefono": "76324511",
    "email": "carlos@acb.com",
    "especialidad": "Motor"
  },
  "origen": {
    "sucursal_id": 3,
    "nombre": "Service Norte",
    "latitud": -17.784,
    "longitud": -63.188
  },
  "destino": {
    "latitud": -17.789,
    "longitud": -63.180,
    "direccion": "Av. Banzer",
    "zona": "Norte"
  },
  "eventos": [
    {
      "id": 1,
      "emergencia_id": 15,
      "mecanico_id": 4,
      "latitud": -17.785,
      "longitud": -63.187,
      "heading": 120.0,
      "speed": 28.5,
      "event_type": "moving",
      "created_at": "2026-06-01T12:00:00Z"
    }
  ]
}
```

### `POST /api/mobile/emergencias/{emergencia_id}/tracking/events`

Registra un punto de tracking persistido para una emergencia ya aceptada y asignada.

#### Roles permitidos

- `admin`
- `secretaria`
- `mecanico`

#### Reglas

- `mecanico` solo puede registrar eventos para emergencias asignadas a su propio correo/login.
- `secretaria` solo puede registrar eventos de emergencias dentro de su alcance por sucursal.
- La emergencia debe estar `activo` y con mecánico asignado.

#### Body JSON

```json
{
  "latitud": -17.785,
  "longitud": -63.187,
  "heading": 120.0,
  "speed": 28.5,
  "event_type": "moving"
}
```

### `GET /api/emergencias/{emergencia_id}/tracking`

Lectura operativa del tracking para dashboard web.

#### Roles permitidos

- `admin`
- `secretaria`
- `mecanico` asignado

#### Reglas

- `secretaria` solo puede consultar emergencias dentro de su alcance por sucursal.
- `mecanico` solo puede consultar emergencias asignadas a su propia cuenta.
- Mantiene la misma respuesta de `GET /api/mobile/emergencias/{emergencia_id}/tracking`.

Registra un taller mecanico desde el formulario principal del frontend.

#### Body JSON

```json
{
  "workshop_name": "Taller Demo",
  "contact_name": "Noelia Demo",
  "phone": "77712345",
  "email": "demo@example.com",
  "zone": "Centro",
  "specialty": "Auxilio mecánico",
  "latitude": -17.7833,
  "longitude": -63.1821,
  "timezone": "America/La_Paz",
  "utc_offset_minutes": -240
}
```

#### Campos

- `workshop_name`: nombre del taller
- `contact_name`: nombre del responsable
- `phone`: telefono de contacto
- `email`: correo valido
- `zone`: zona o direccion referencial del taller
- `specialty`: especialidad principal
- `latitude`: latitud del punto en el mapa, opcional
- `longitude`: longitud del punto en el mapa, opcional
- `timezone`: zona horaria IANA, opcional
- `utc_offset_minutes`: diferencia respecto a UTC en minutos, opcional

#### Validaciones

- `workshop_name`: entre 3 y 160 caracteres
- `contact_name`: entre 3 y 160 caracteres
- `phone`: entre 7 y 40 caracteres
- `email`: debe ser un correo valido
- `zone`: entre 2 y 120 caracteres
- `specialty`: entre 2 y 120 caracteres
- `latitude`: entre `-90` y `90`
- `longitude`: entre `-180` y `180`
- `timezone`: entre 2 y 120 caracteres
- `utc_offset_minutes`: entre `-840` y `840`

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "workshop_name": "Taller Demo",
  "contact_name": "Noelia Demo",
  "phone": "77712345",
  "email": "demo@example.com",
  "zone": "Centro",
  "specialty": "Auxilio mecánico",
  "latitude": -17.7833,
  "longitude": -63.1821,
  "timezone": "America/La_Paz",
  "utc_offset_minutes": -240,
  "created_at": "2026-04-09T05:35:45.417342Z"
}
```

Ejemplo:

```bash
curl -X POST http://localhost:8787/api/workshops \
  -H "Content-Type: application/json" \
  -d '{
    "workshop_name": "Taller Demo",
    "contact_name": "Noelia Demo",
    "phone": "77712345",
    "email": "demo@example.com",
    "zone": "Centro",
    "specialty": "Auxilio mecánico",
    "latitude": -17.7833,
    "longitude": -63.1821,
    "timezone": "America/La_Paz",
    "utc_offset_minutes": -240
  }'
```

### `GET /api/workshops`

Lista todos los talleres registrados en orden descendente de creacion.

Ejemplo:

```bash
curl http://localhost:8787/api/workshops
```

### `PUT /api/workshops/{workshop_id}`

Actualiza el registro de un taller existente usando la misma estructura JSON de creacion.

Opcionalmente tambien puede recibir `password` para reemplazar la contraseña actual del taller.

Ejemplo:

```bash
curl -X PUT http://localhost:8787/api/workshops/1 \
  -H "Content-Type: application/json" \
  -d '{
    "workshop_name": "Taller Demo Actualizado",
    "contact_name": "Noelia Demo",
    "phone": "77712345",
    "email": "demo@example.com",
    "zone": "Centro",
    "specialty": "Auxilio mecánico",
    "password": "NuevaClave123",
    "latitude": -17.7833,
    "longitude": -63.1821,
    "timezone": "America/La_Paz",
    "utc_offset_minutes": -240
  }'
```

### `DELETE /api/workshops/{workshop_id}`

Elimina un taller por su identificador.

Ejemplo:

```bash
curl -X DELETE http://localhost:8787/api/workshops/1
```

### `POST /api/vehiculos`

Registra un vehiculo desde la app movil usando `multipart/form-data`.

#### Campos enviados

- `client_id`: identificador del cliente propietario del vehiculo
- `brand`: marca del vehiculo
- `model`: modelo del vehiculo
- `year`: anio del vehiculo
- `plate`: placa
- `color`: color
- `is_primary`: `true` o `false`
- `photo`: archivo opcional en formato `jpg`, `jpeg`, `png` o `webp`

#### Ejemplo con curl

```bash
curl -X POST http://localhost:8787/api/vehiculos \
  -F "client_id=15" \
  -F "brand=Toyota" \
  -F "model=Corolla" \
  -F "year=2018" \
  -F "plate=1023HHNNI" \
  -F "color=gris" \
  -F "is_primary=true" \
  -F "photo=@/ruta/opcional/vehiculo.jpg"
```

#### Respuesta exitosa

Codigo: `201 Created`

```json
{
  "id": 1,
  "client_id": 15,
  "brand": "Toyota",
  "model": "Corolla",
  "year": 2018,
  "plate": "1023HHNNI",
  "color": "gris",
  "is_primary": true,
  "photo_path": "vehicles/archivo_generado.jpg",
  "photo_url": "/uploads/vehicles/archivo_generado.jpg",
  "created_at": "2026-04-11T21:10:00.000000Z"
}
```

#### Errores posibles

- `400 Bad Request`: foto con formato no permitido
- `404 Not Found`: cliente no encontrado
- `409 Conflict`: ya existe un vehiculo con esa placa
- `422 Unprocessable Entity`: datos faltantes o invalidos

### `GET /api/vehiculos`

Lista los vehiculos registrados de un cliente en orden descendente de creacion.

#### Ejemplo

```bash
curl "http://localhost:8787/api/vehiculos?client_id=15"
```

#### Respuesta exitosa

Codigo: `200 OK`

```json
[
  {
    "id": 2,
    "client_id": 15,
    "brand": "Suzuki",
    "model": "Vitara",
    "year": 2021,
    "plate": "REMOTE20260411",
    "color": "negro",
    "is_primary": false,
    "photo_path": null,
    "photo_url": null,
    "created_at": "2026-04-11T06:12:01.102533Z"
  },
  {
    "id": 1,
    "client_id": 15,
    "brand": "Suzuki",
    "model": "Vitara",
    "year": 2021,
    "plate": "PRUEBA20260411",
    "color": "negro",
    "is_primary": false,
    "photo_path": null,
    "photo_url": null,
    "created_at": "2026-04-11T06:07:52.203747Z"
  }
]
```

#### Reglas

- `client_id` es obligatorio como query param
- el backend filtra por `client_id`
- si el cliente no existe, responde `404 Not Found`

### `DELETE /api/vehiculos/{vehicle_id}`

Elimina un vehiculo por su identificador. Si el vehiculo tenia foto guardada, tambien elimina el archivo asociado.
La eliminacion valida pertenencia usando `client_id`.

#### Ejemplo

```bash
curl -X DELETE "http://localhost:8787/api/vehiculos/1?client_id=15"
```

#### Respuestas

- `204 No Content`: vehiculo eliminado
- `404 Not Found`: vehiculo no encontrado
- `503 Service Unavailable`: base de datos no disponible

### `PUT /api/vehiculos/{vehicle_id}`

Actualiza un vehiculo existente usando `multipart/form-data`. La foto es opcional; si no se envia una nueva, se conserva la actual.

#### Campos enviados

- `client_id`
- `brand`
- `model`
- `year`
- `plate`
- `color`
- `is_primary`
- `photo` opcional

#### Ejemplo

```bash
curl -X PUT http://localhost:8787/api/vehiculos/3 \
  -F "client_id=15" \
  -F "brand=Suzuki" \
  -F "model=Vitara GLX" \
  -F "year=2022" \
  -F "plate=REMOTE20260411B" \
  -F "color=gris grafito" \
  -F "is_primary=true"
```

#### Respuestas

- `200 OK`: vehiculo actualizado
- `404 Not Found`: vehiculo no encontrado
- `409 Conflict`: placa duplicada
- `503 Service Unavailable`: base de datos no disponible

#### Reglas

- `client_id` es obligatorio
- el backend valida que el vehiculo pertenezca a ese `client_id`
- si el vehiculo no pertenece al cliente indicado, responde `404 Not Found`

### `POST /api/mecanicos`

Registra un mecanico asociado al sistema.

#### Body JSON

```json
{
  "full_name": "Carlos Perez",
  "phone": "77799911",
  "email": "carlos@example.com",
  "specialty": "Electricidad automotriz",
  "status": "disponible"
}
```

#### Validaciones

- `full_name`: entre 3 y 160 caracteres
- `phone`: entre 7 y 40 caracteres
- `email`: debe ser un correo valido
- `specialty`: entre 2 y 120 caracteres
- `status`: uno de `disponible`, `ocupado` o `fuera_de_servicio`

### `GET /api/mecanicos`

Lista todos los mecanicos registrados.

Ejemplo:

```bash
curl http://localhost:8787/api/mecanicos
```

### `PUT /api/mecanicos/{mecanico_id}`

Actualiza un mecanico existente usando la misma estructura JSON de creacion.

Ejemplo:

```bash
curl -X PUT http://localhost:8787/api/mecanicos/1 \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Carlos Perez",
    "phone": "77799911",
    "email": "carlos@example.com",
    "specialty": "Electricidad automotriz",
    "status": "ocupado"
  }'
```

### `DELETE /api/mecanicos/{mecanico_id}`

Elimina un mecanico por su identificador.

Ejemplo:

```bash
curl -X DELETE http://localhost:8787/api/mecanicos/1
```

## Persistencia

Los registros de talleres se guardan en PostgreSQL en la tabla:

- `workshop_registrations`

Columnas principales:

- `id`
- `workshop_name`
- `contact_name`
- `phone`
- `email`
- `zone`
- `specialty`
- `latitude`
- `longitude`
- `timezone`
- `utc_offset_minutes`
- `created_at`

Los registros de clientes se guardan en PostgreSQL en la tabla:

- `clients`

El administrador `administrador@acb.com` no forma parte de esta tabla porque su acceso es virtual y exclusivo del sistema.

Los registros de mecanicos se guardan en PostgreSQL en la tabla:

- `mecanicos` (tabla real canónica)

## CORS

El backend acepta solicitudes desde estos origenes de desarrollo:

- `localhost`
- `127.0.0.1`
- rangos privados `10.x.x.x`, `172.16.x.x` a `172.31.x.x` y `192.168.x.x`
- otras direcciones IPv4 cuando se accede por IP en desarrollo local

## Nota

La tabla `workshop_registrations` se crea automaticamente al iniciar el backend.

## Módulo Recepción de Vehículos

Roles operativos del módulo:

- `admin`
- `secretaria`
- `mecanico`
- `client`

Credenciales de prueba:

- `secretaria@acb.com` / `secretaria123`
- `mecanico@acb.com` / `mecanico123`

Permisos por endpoint:

- `POST /api/recepciones`: `secretaria`
- `GET /api/recepciones`: `admin`, `secretaria`, `mecanico`
- `GET /api/recepciones/{id}`: `admin`, `secretaria`, `mecanico`, `client` propietario
- `PUT /api/recepciones/{id}`: `admin`, `secretaria`
- `GET /api/recepciones/{id}/ficha`: `admin`, `secretaria`, `mecanico`
- `GET /api/emergencias/{id}/ficha-recepcion`: `admin`, `secretaria`
- `GET /api/mobile/emergencias/{id}/ficha-recepcion`: `mecanico` asignado
- `POST /api/recepciones/{id}/diagnostico`: `mecanico`
- `POST /api/recepciones/{id}/observaciones`: `mecanico`
- `POST /api/recepciones/{id}/finalizar`: `mecanico` asignado, `admin` con `admin_override=true`
- `POST /api/recepciones/{id}/entregar`: `admin`, `secretaria`
- `GET /api/recepciones/{id}/estado`: `admin`, `secretaria`, `mecanico`, `client` propietario
- `GET /api/emergencias?emergency_status=cerrada`: `admin`, `secretaria`

Regla de pertenencia para `client`:

- El acceso se valida con `clientes_recepcion.mobile_client_id = current_user.id`.

Regla de visibilidad para `mecanico`:

- En el listado, un mecánico ve fichas sin asignar o fichas asignadas a su propio usuario.
- En detalle/ficha/estado, si la ficha está asignada a otro mecánico, el acceso es rechazado.

Compatibilidad legacy:

- El contrato canónico para gestión operativa es `/api/mecanicos`.
- El runtime de Google Cloud todavía mantiene el alias oculto `/api/technicians` por compatibilidad legacy.
- Los clientes nuevos no deben usar `/api/technicians`.

### `POST /api/auth/login` para secretaria

```bash
curl -X POST http://localhost:8787/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "secretaria@acb.com",
    "password": "secretaria123",
    "account_type": "client"
  }'
```

### `POST /api/auth/login` para mecánico

```bash
curl -X POST http://localhost:8787/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "mecanico@acb.com",
    "password": "mecanico123",
    "account_type": "client"
  }'
```

### `POST /api/recepciones`

Crea cliente de recepción, vehículo, ficha, accesorios y problemas reportados.

```json
{
  "cliente": {
    "full_name": "Juan Perez",
    "identity_card": "1234567",
    "phone": "70000001",
    "email": "juan@mail.com",
    "address": "Zona Norte",
    "mobile_client_id": 7
  },
  "vehiculo": {
    "plate": "1234ABC",
    "brand": "Toyota",
    "model": "Corolla",
    "year": 2018,
    "color": "Blanco",
    "vin": "VIN123",
    "engine_number": "ENG123"
  },
  "ficha": {
    "assigned_mecanico_id": 5,
    "kilometraje": 85420,
    "nivel_combustible": "1/2",
    "observaciones_generales": "Recepción inicial"
  },
  "accesorios": [
    {
      "name": "Llanta de auxilio",
      "quantity": 1,
      "notes": "ok"
    }
  ],
  "problemas": [
    {
      "description": "Ruido en motor",
      "priority": "alta",
      "reported_by": "secretaria"
    }
  ]
}
```

Respuesta resumida:

```json
{
  "id": 2,
  "codigo_ficha": "REC-20260525011249-4E55",
  "status": "registrada",
  "cliente_id": 2,
  "vehiculo_id": 2,
  "fecha_recepcion": "2026-05-25T01:12:49.221222Z",
  "assigned_mecanico_id": 5,
  "created_at": "2026-05-25T01:12:49.221222Z"
}
```

### `GET /api/recepciones`

Filtros soportados:

- `status`
- `plate`
- `codigo_ficha`
- `identity_card`
- `assigned_mecanico_id`
- `limit` default `20`, máximo `100`
- `offset` default `0`

Ejemplo:

```bash
curl "http://localhost:8787/api/recepciones?status=en_trabajo&limit=10&offset=0" \
  -H "Authorization: Bearer TOKEN_SECRETARIA"
```

Respuesta:

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

### `PUT /api/recepciones/{id}`

Actualiza la ficha completa básica.

```json
{
  "cliente": {
    "full_name": "Juan Perez Editado",
    "identity_card": "1234567",
    "phone": "70000009",
    "email": "juan@mail.com",
    "address": "Zona Sur",
    "mobile_client_id": 7
  },
  "vehiculo": {
    "plate": "1234ABC",
    "brand": "Toyota",
    "model": "Corolla XEI",
    "year": 2019,
    "color": "Plata",
    "vin": "VIN123",
    "engine_number": "ENG123"
  },
  "ficha": {
    "status": "en_diagnostico",
    "assigned_mecanico_id": 5,
    "kilometraje": 86000,
    "nivel_combustible": "1/4",
    "observaciones_generales": "Actualizada por secretaria"
  },
  "accesorios": [
    {
      "name": "Botiquin",
      "quantity": 1,
      "notes": "maletero"
    }
  ],
  "problemas": [
    {
      "description": "Ruido en motor al acelerar",
      "priority": "alta",
      "reported_by": "secretaria"
    }
  ]
}
```

### `POST /api/recepciones/{id}/diagnostico`

Registra el diagnóstico técnico inicial de una ficha.

#### Roles permitidos

- `mecanico`

#### Reglas

- Solo el mecánico autenticado puede registrar su propio diagnóstico.
- La ficha debe estar en estado `registrada` o `en_diagnostico`.
- El backend valida que el usuario autenticado tenga rol `mecanico` y perfil técnico vinculado.

```json
{
  "diagnostic_text": "Desgaste en correa",
  "estimated_work": "Cambio de correa",
  "estimated_cost": 350
}
```

Errores típicos:

- `403 Forbidden`: usuario sin permisos o mecánico no autorizado
- `404 Not Found`: ficha no encontrada
- `409 Conflict`: estado inválido o conflicto de negocio
- `503 Service Unavailable`: base de datos no disponible

### `POST /api/recepciones/{id}/observaciones`

Registra observaciones de trabajo y avance técnico.

#### Roles permitidos

- `mecanico`

#### Reglas

- La ficha debe estar en `en_diagnostico` o `en_trabajo`.
- `work_status` debe pertenecer al conjunto permitido por backend.
- El backend valida perfil técnico vinculado para el usuario autenticado.

```json
{
  "observation_text": "Trabajo iniciado",
  "work_status": "en_proceso"
}
```

Errores típicos:

- `403 Forbidden`: usuario sin permisos o mecánico no autorizado
- `404 Not Found`: ficha no encontrada
- `409 Conflict`: estado inválido o conflicto de negocio
- `503 Service Unavailable`: base de datos no disponible

### `POST /api/recepciones/{id}/finalizar`

Finaliza técnicamente una ficha de recepción.

#### Roles permitidos

- `mecanico` asignado
- `admin` con confirmación explícita

#### Reglas

- `secretaria` no puede finalizar trabajo técnico.
- `mecanico` solo puede finalizar si está asignado a la ficha.
- `admin` debe enviar `admin_override=true`.
- Para finalizar, la ficha debe tener al menos un diagnóstico.
- Para finalizar, la ficha debe tener al menos una observación.

```json
{
  "admin_override": false
}
```

Errores típicos:

- `403 Forbidden`: rol no permitido o falta `admin_override`
- `404 Not Found`: ficha no encontrada
- `409 Conflict`: faltan diagnóstico u observación, o la ficha ya no permite cierre técnico
- `503 Service Unavailable`: base de datos no disponible

### `POST /api/recepciones/{id}/entregar`

Registra la entrega administrativa de una ficha ya finalizada.

#### Roles permitidos

- `admin`
- `secretaria`

#### Reglas

- Solo puede entregarse una ficha en estado `finalizada`.
- Si la ficha ya fue entregada, el backend responde conflicto.
- Si la ficha está vinculada a una emergencia, la entrega también:
- finaliza la asignación técnica asociada
- cierra la emergencia con `emergency_status = cerrada`
- registra `closed_at` y `closed_by_user_id`
- devuelve el estado del mecánico a `disponible`

Errores típicos:

- `404 Not Found`: ficha no encontrada
- `409 Conflict`: ficha no finalizada o ya entregada
- `503 Service Unavailable`: base de datos no disponible

### `GET /api/recepciones/{id}/estado`

```json
{
  "ficha_id": 2,
  "codigo_ficha": "REC-20260525011249-4E55",
  "status": "en_trabajo",
  "vehicle": "Toyota Corolla XEI 2019",
  "plate": "1234ABC",
  "last_diagnostic": "Desgaste en correa",
  "last_observation": "Trabajo iniciado",
  "updated_at": "2026-05-25T01:13:38.853771Z"
}
```

### `GET /api/emergencias/{id}/ficha-recepcion`

Devuelve la ficha de recepción vinculada a una emergencia para uso operativo web.

#### Roles permitidos

- `admin`
- `secretaria`
- `mecanico` asignado

#### Errores típicos

- `404 Not Found`: la emergencia no tiene ficha asociada

### `GET /api/mobile/emergencias/{id}/ficha-recepcion`

Devuelve la ficha de recepción vinculada a una emergencia para el mecánico asignado.

#### Roles permitidos

- `mecanico`

#### Reglas

- Solo el mecánico asignado puede consultar la ficha.

### Cierre de Emergencia desde Recepción

Cuando una ficha vinculada a una emergencia se entrega correctamente:

- la ficha pasa a `entregada`
- la emergencia asociada pasa a `cerrada`
- se registran `closed_at` y `closed_by_user_id`
- la asignación técnica se marca como finalizada
- el mecánico asociado vuelve a estado `disponible`

Esto se refleja luego en:

- `GET /api/emergencias?emergency_status=cerrada`
- `GET /api/emergencias/{id}/ficha-recepcion`
