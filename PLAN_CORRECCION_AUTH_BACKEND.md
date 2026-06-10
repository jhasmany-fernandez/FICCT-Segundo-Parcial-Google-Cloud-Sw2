# PLAN DE CORRECCION DE AUTENTICACION Y AUTORIZACION DEL BACKEND

## Objetivo
Definir una estrategia tecnica, gradual y segura para corregir autenticacion, autorizacion y recuperacion de contraseña del backend FastAPI que sera usado como `Microservicio 1: Gestion Empresarial Core`.

## Restricciones de este plan

- No se modifica codigo en esta etapa.
- No se realizan commits.
- No se cambian contratos todavia.
- El plan prioriza compatibilidad temporal con:
  - frontend web core
  - app movil React Native

## 1. Estado actual resumido

### Login actual
Hoy el login esta centralizado en `backend/app/main.py` y autentica:

- `admin`
- `workshop`
- `client`

El flujo actual:

1. recibe `email`, `password` y opcionalmente `account_type`
2. valida admin protegido desde configuracion
3. valida talleres desde base de datos
4. valida clientes desde base de datos
5. devuelve `access_token` y `token_type`

### Como se generan tokens hoy
El sistema no usa JWT real. Genera:

- `access_token = secrets.token_urlsafe(32)`

Problemas:

- no hay firma
- no hay `exp`
- no hay `sub`
- no hay `role` dentro del token
- no hay refresh token
- no hay almacenamiento ni revocacion

### Endpoints actualmente desprotegidos
La auditoria confirmo que no hay:

- `Depends(get_current_user)`
- `HTTPBearer`
- `OAuth2PasswordBearer`
- validacion `Authorization: Bearer`

Por tanto hoy estan desprotegidos endpoints sensibles como:

- `clientes`
- `workshops`
- `technicians`
- `vehicles`
- `emergencias`
- `devices/fcm-token`
- `workshops/approval-status`

### Problemas actuales de forgot-password
El sistema permite cambiar o resetear contraseñas solo con conocer el correo.

Problemas detectados:

- no hay OTP
- no hay token temporal firmado
- no hay expiracion
- no hay invalidacion de un solo uso
- se revela demasiado sobre existencia o no de cuentas

### Riesgos actuales con tokens FCM
Hoy el registro FCM:

- no requiere autenticacion
- recibe `user_id` desde el cliente
- solo valida que el `client` exista

Riesgo:

- cualquier actor puede registrar un token para otro usuario
- posible suplantacion de dispositivo
- notificaciones enviadas a receptores incorrectos

## 2. Modelo objetivo de autenticacion

## JWT access token
Se recomienda migrar a `JWT access token` firmado desde backend.

Payload minimo recomendado:

- `sub`: id del usuario autenticado
- `role`: rol efectivo
- `email`
- `type`: `access`
- `iat`
- `exp`
- `iss`

### Expiracion recomendada

- access token web/mobile: `15` a `30` minutos

### Refresh token
Decision recomendada:

- `si`, pero no necesariamente en la primera entrega

Estrategia segura:

- Fase inicial: access token con expiracion corta
- Fase posterior: refresh token rotatorio si el frontend/mobile lo necesita

Si se posterga temporalmente:

- documentarlo como decision explicita
- exigir nuevo login tras vencimiento del token

### Usuario autenticado por dependencia
Crear una dependencia base:

- `get_current_user`

Responsabilidad:

- extraer `Authorization`
- validar `Bearer`
- decodificar JWT
- verificar expiracion
- construir contexto autenticado

### Refresh token si aplica
Si se implementa:

- token separado del access token
- `type=refresh`
- almacenamiento hasheado o versionado en BD
- rotacion por uso

### Logout
Decision recomendada:

- fase 1: logout manejado desde frontend eliminando token local
- fase 2: si hay refresh token, invalidar refresh token en backend

### Proteccion real de endpoints
Meta obligatoria:

- endpoints sensibles deben rechazar requests sin token valido
- endpoints deben validar rol antes de procesar cambios

## 3. Modelo objetivo de roles

Roles minimos recomendados:

- `ADMIN`
- `OPERADOR`
- `TECNICO`
- `CLIENTE`

## Permisos por rol

### ADMIN

- administrar usuarios y roles
- crear/editar/desactivar sucursales
- aprobar estados operativos
- ver todo el sistema
- gestionar tecnicos
- ver clientes, vehiculos, emergencias, bitacora y dashboard global

### OPERADOR

- gestionar operacion diaria
- ver sucursales
- crear y actualizar emergencias
- asignar tecnicos
- consultar clientes y vehiculos
- ver dashboard operativo
- no debe gestionar credenciales maestras ni roles globales

### TECNICO

- ver emergencias asignadas
- actualizar estado tecnico de su trabajo
- registrar seguimiento basico
- subir evidencias asociadas a su trabajo
- no debe administrar clientes, sucursales ni usuarios globales

### CLIENTE

- ver su propio perfil
- ver sus propios vehiculos
- registrar sus propias emergencias
- consultar estado de sus emergencias
- registrar/actualizar su propio token FCM
- no debe ver recursos de otros usuarios

## 4. Endpoints por nivel de proteccion

| Endpoint | Estado actual | Proteccion objetivo | Roles permitidos | Prioridad |
|---|---|---|---|---|
| `GET /api/health` | Publico | Publico | Todos | Alta |
| `GET /docs` | Publico | Publico en dev, restringible en prod | Todos o entorno interno | Media |
| `POST /api/auth/login` | Publico | Publico | Todos | Alta |
| `POST /api/auth/account-type` | Publico | Publico con respuesta neutral o eliminar | Publico | Media |
| `POST /api/auth/forgot-password` | Publico e inseguro | Publico, pero con flujo seguro de solicitud | Publico | Alta |
| `POST /api/auth/reset-password` | No existe | Publico con token valido | Publico con token temporal | Alta |
| `GET /api/workshops` | Publico | Protegido | ADMIN, OPERADOR | Alta |
| `PUT /api/workshops/{id}` | Publico | Protegido | ADMIN, OPERADOR | Alta |
| `PUT /api/workshops/{id}/approval-status` | Publico | Protegido | ADMIN | Alta |
| `DELETE /api/workshops/{id}` | Publico | Protegido | ADMIN | Alta |
| `GET /api/clientes` | Publico | Protegido | ADMIN, OPERADOR | Alta |
| `PUT /api/clientes/{id}` | Publico | Protegido | ADMIN, OPERADOR, CLIENTE solo self | Alta |
| `PUT /api/clientes/{id}/status` | Publico | Protegido | ADMIN | Alta |
| `DELETE /api/clientes/{id}` | Publico | Protegido | ADMIN | Alta |
| `GET /api/vehicles` | Publico | Protegido | ADMIN, OPERADOR, CLIENTE self | Alta |
| `POST /api/vehicles` | Publico | Protegido | ADMIN, OPERADOR, CLIENTE self | Alta |
| `PUT /api/vehicles/{id}` | Publico | Protegido | ADMIN, OPERADOR, CLIENTE self | Alta |
| `DELETE /api/vehicles/{id}` | Publico | Protegido | ADMIN, OPERADOR, CLIENTE self | Alta |
| `GET /api/emergencias` | Publico | Protegido | ADMIN, OPERADOR, TECNICO segun asignacion, CLIENTE self | Alta |
| `POST /api/emergencias` | Publico | Protegido | CLIENTE, OPERADOR, ADMIN | Alta |
| `PUT /api/emergencias/{id}` | Publico | Protegido | ADMIN, OPERADOR | Alta |
| `DELETE /api/emergencias/{id}` | Publico | Protegido | ADMIN | Alta |
| `GET /api/technicians` | Publico | Protegido | ADMIN, OPERADOR | Alta |
| `POST /api/technicians` | Publico | Protegido | ADMIN, OPERADOR | Alta |
| `PUT /api/technicians/{id}` | Publico | Protegido | ADMIN, OPERADOR | Alta |
| `DELETE /api/technicians/{id}` | Publico | Protegido | ADMIN | Alta |
| `POST /api/devices/fcm-token` | Publico | Protegido | CLIENTE, TECNICO, OPERADOR, ADMIN autenticados | Alta |
| `DELETE /api/devices/fcm-token/{id}` o revocacion equivalente | No existe | Protegido | Dueño del token o ADMIN | Media |

## 5. Forgot-password seguro

## Flujo propuesto

### Paso 1. Solicitar recuperacion
Endpoint sugerido:

- `POST /api/auth/forgot-password`

Body:

- email o telefono

Respuesta:

- siempre neutral
- ejemplo: `"Si la cuenta existe, se enviaron instrucciones de recuperacion"`

### Paso 2. Generar token temporal
Backend debe:

- generar token aleatorio seguro
- guardar solo `hash` del token
- asociarlo a la cuenta
- definir `expires_at`
- marcar `used_at = null`

### Paso 3. Persistencia de token
Campos sugeridos:

- `id`
- `user_id`
- `account_type`
- `token_hash`
- `purpose = password_reset`
- `expires_at`
- `used_at`
- `created_at`
- `requested_ip`

### Paso 4. Entrega del token
Canal:

- email
- SMS/WhatsApp si en futuro aplica

### Paso 5. Reset seguro
Endpoint sugerido:

- `POST /api/auth/reset-password`

Body:

- token
- `newPassword`
- `confirmPassword`

Validaciones:

- token existente
- no expirado
- no usado
- contraseñas validas

### Paso 6. Invalidez posterior
Despues de usar el token:

- marcar `used_at`
- invalidar otros tokens activos del mismo usuario

### Regla critica
Nunca revelar:

- si el correo existe o no
- si pertenece a cliente o tecnico o admin

## 6. Tokens FCM

## Modelo seguro recomendado

### Registro
Endpoint recomendado:

- `POST /api/devices/fcm-token`

Debe requerir autenticacion.

No debe aceptar `user_id` desde el cliente como fuente de verdad.

Debe asociar el token a:

- `current_user.id`
- `current_user.role`

### Actualizacion
Permitir:

- actualizar mismo token con nueva plataforma o estado
- reemplazar token previo del mismo dispositivo

### Revocacion
Crear endpoint de baja:

- `DELETE /api/devices/fcm-token/{device_id}`

o:

- `POST /api/devices/fcm-token/revoke`

### Reglas

- un usuario autenticado registra sus propios tokens
- un admin puede revocar si hace falta
- no se aceptan tokens anonimos
- si cambia el login del usuario, revocar token anterior si aplica

## 7. Orden de implementacion

## Fase 1: crear dependencias de autenticacion

Objetivo:

- emitir JWT real
- crear `get_current_user`
- centralizar lectura de token

Resultado esperado:

- backend ya puede autenticar requests

## Fase 2: proteger endpoints criticos

Objetivo:

- proteger primero CRUDs de alto impacto

Endpoints recomendados:

- `clientes`
- `workshops`
- `technicians`
- `vehicles`
- `devices/fcm-token`

## Fase 3: agregar roles

Objetivo:

- pasar de roles sueltos a permisos explicitamente aplicados

Resultado:

- `ADMIN`
- `OPERADOR`
- `TECNICO`
- `CLIENTE`

## Fase 4: corregir forgot-password

Objetivo:

- retirar reset inseguro por correo
- introducir flujo tokenizado

## Fase 5: proteger tokens FCM

Objetivo:

- mover FCM a identidad autenticada
- agregar revocacion

## Fase 6: pruebas

Objetivo:

- validar web
- validar mobile
- validar no regresion en login

## 8. Primer cambio de codigo seguro

### Archivo a tocar primero

- `backend/app/main.py`

### Funcion a crear primero

- `get_current_user`

Subfunciones recomendadas:

- `create_access_token`
- `decode_access_token`
- `extract_bearer_token`

### Primer endpoint a probar

- `GET /api/clientes`

Motivo:

- hoy esta publico
- es de alto impacto
- permite validar rapidamente que la proteccion ya funciona

### Secuencia minima segura

1. Agregar configuracion JWT.
2. Modificar `login` para devolver JWT real.
3. Crear `get_current_user`.
4. Aplicar dependencia solo a `GET /api/clientes` en primer paso.
5. Validar compatibilidad del frontend.
6. Extender luego al resto de CRUDs.

### Validacion con Docker

Comandos recomendados:

1. `docker compose up --build`
2. `curl http://localhost:8787/api/health`
3. login:
   - `POST /api/auth/login`
4. probar acceso sin token:
   - `GET /api/clientes`
   - debe responder `401` o `403`
5. probar acceso con token valido:
   - debe responder `200`

## 9. Riesgos

### Riesgo de romper frontend

- el frontend actual guarda token pero el backend no lo usa
- al activar auth real, frontend debe enviar `Authorization`

Mitigacion:

- introducir primero una ruta protegida piloto
- adaptar gradualmente `session.ts` y servicios API

### Riesgo de romper mobile

- la app movil puede depender del contrato actual de login

Mitigacion:

- mantener estructura base de respuesta
- agregar campos antes de quitar compatibilidad

### Riesgo de bloquear endpoints publicos

- `health`
- `docs`
- registro inicial de cuentas si todavia aplica

Mitigacion:

- definir explicitamente que endpoints deben seguir publicos

### Riesgo por usuarios existentes

- usuarios actuales no tienen refresh token
- roles actuales son `admin`, `workshop`, `client`

Mitigacion:

- mapear temporalmente:
  - `admin -> ADMIN`
  - `workshop -> OPERADOR` o rol transitorio
  - `client -> CLIENTE`

## 10. Criterios de aceptacion

- login sigue funcionando
- `GET /api/health` sigue publico
- `GET /docs` sigue accesible segun entorno definido
- endpoints criticos rechazan requests sin token
- un usuario autenticado puede acceder a sus recursos permitidos
- los roles se respetan
- `forgot-password` deja de permitir reset con solo correo
- FCM queda ligado al usuario autenticado

## Recomendacion final

La correccion debe hacerse en capas, no en una sola gran refactorizacion.

Orden recomendado:

1. JWT real
2. dependencia `get_current_user`
3. proteccion de CRUDs criticos
4. RBAC minimo
5. forgot-password seguro
6. FCM autenticado

Ese orden reduce el riesgo de romper el sistema actual y permite validar web y mobile paso a paso.
