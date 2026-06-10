# AUDITORIA DE AUTENTICACION Y SEGURIDAD DEL BACKEND

## Resumen ejecutivo
El backend FastAPI actual no implementa autenticacion real de API para proteger recursos. Hoy el sistema:

- genera `access_token` aleatorios con `secrets.token_urlsafe(32)`
- no usa JWT real
- no define expiracion del token
- no maneja refresh token
- no implementa logout de sesion
- no valida `Authorization: Bearer ...` en endpoints de negocio
- no usa `Depends`, `Security`, `HTTPBearer`, `OAuth2` ni `get_current_user`

En la practica, casi todos los endpoints relevantes del backend estan publicos desde el punto de vista de autorizacion. El frontend guarda un token, pero el backend no lo exige para CRUDs sensibles.

El riesgo mas grave hoy es el flujo de recuperacion y cambio de contraseña:

- `forgot-password` permite resetear la clave solo con conocer el correo
- `workshops/change-password` puede activar o cambiar clave de un taller sin token de recuperacion
- no hay OTP, correo firmado, nonce, expiracion ni prueba de identidad

Para convertir este backend en `Microservicio 1: Gestion Empresarial Core`, el primer frente obligatorio es:

1. introducir autenticacion real con tokens verificables
2. proteger endpoints sensibles
3. separar permisos por rol
4. rehacer por completo `forgot-password`

## Archivos revisados

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1)
- [backend/app/security.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/security.py:1)
- [backend/app/config.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/config.py:1)
- [backend/app/schemas.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/schemas.py:1)
- [backend/app/db.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/db.py:1)
- [backend/app/routes/auth.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/routes/auth.py:1)
- [backend/API.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/API.md:1)
- [backend/.env.example](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/.env.example:1)

## Hallazgos por tema

## 1. Autenticacion actual

### Login
El login activo vive en [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2169).

Caracteristicas actuales:

- endpoint: `POST /api/auth/login`
- autentica tres tipos:
  - admin protegido por configuracion
  - workshop
  - client
- el request acepta `account_type`, pero se usa sobre todo como ayuda para el frontend, no como capa de seguridad robusta

### Generacion del token
El backend no genera JWT. Genera un string aleatorio:

- `access_token=secrets.token_urlsafe(32)`

Eso ocurre en:

- admin: [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2196)
- workshop: [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2248)
- client: [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2274)

### Payload del token
No existe payload de token. El `access_token` no codifica:

- `sub`
- `role`
- `exp`
- `iat`
- `iss`
- `aud`

No hay firma ni trazabilidad del token dentro del backend.

### Expiracion
No existe expiracion de token.

### Refresh token
No existe refresh token.

### Logout
No existe endpoint de logout ni invalidez de sesion.

### Lockout de login
Hay limitacion de intentos solo para:

- admin
- workshop

Implementado en [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:526).

No se aplica al flujo de `client`.

## 2. Proteccion de endpoints

### Verificacion tecnica
No se encontraron referencias activas a:

- `Depends(...)`
- `Security(...)`
- `HTTPBearer`
- `OAuth2PasswordBearer`
- `get_current_user`
- validacion de `Authorization` o `Bearer`

Tampoco se encontraron `include_router(...)` activos en `main.py`, por lo que los routers alternos no parecen estar cableados a la app principal.

### Implicacion
El backend actual no protege realmente los endpoints con token. El cliente puede guardar un token, pero el backend no lo exige antes de devolver o modificar recursos.

## Tabla de endpoints y nivel de proteccion actual

| Endpoint | Archivo | Proteccion actual | Observacion |
|---|---|---|---|
| `POST /api/auth/login` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2169) | Publico | Entrega token aleatorio no verificable |
| `POST /api/auth/account-type` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2279) | Publico | Permite enumeracion de cuentas |
| `POST/PUT /api/auth/forgot-password` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2297) | Publico | Resetea clave solo con correo |
| `POST /api/devices/fcm-token` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1302) | Publico | Solo valida que `user_id` exista |
| `GET /api/workshops` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1868) | Publico | Lista datos operativos |
| `PUT /api/workshops/{id}` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1933) | Publico | Modifica talleres/sucursales sin auth |
| `PUT /api/workshops/{id}/approval-status` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1953) | Publico | Aprobacion sin control de rol |
| `DELETE /api/workshops/{id}` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1988) | Publico | Eliminacion sin auth |
| `POST /api/workshops/change-password` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1877) | Publico | Cambio de clave sin sesion/token |
| `POST/PUT /api/workshops/forgot-password` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1911) | Publico | Reset inseguro |
| `POST /api/clientes` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1999) | Publico | Registro permitido |
| `GET /api/clientes` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2041) | Publico | Expone clientes sin auth |
| `PUT /api/clientes/{id}` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2114) | Publico | Modifica clientes sin auth |
| `PUT /api/clientes/{id}/status` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2101) | Publico | Suspende/reactiva sin auth |
| `DELETE /api/clientes/{id}` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2158) | Publico | Eliminacion sin auth |
| `POST /api/clientes/change-password` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2050) | Publico | Cambia clave solo con correo + clave actual |
| `POST/PUT /api/clientes/forgot-password` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2079) | Publico | Reset inseguro |
| `POST /api/technicians` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2344) | Publico | Alta sin auth |
| `GET /api/technicians` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2362) | Publico | Lectura sin auth |
| `PUT /api/technicians/{id}` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2371) | Publico | Edicion sin auth |
| `DELETE /api/technicians/{id}` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2394) | Publico | Eliminacion sin auth |
| `GET/POST/PUT/DELETE /api/vehicles` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1516) | Publico | CRUD accesible sin token |
| `GET/POST/PUT/DELETE /api/emergencias` | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1327) | Publico | Flujo central del negocio sin auth real |

## 3. Roles y permisos actuales

### Roles detectados

- `admin`
- `workshop`
- `client`

No se detectaron roles activos para:

- operador_core
- jefe_sucursal
- tecnico_vehicular
- cliente_movil separado por permisos

### Como se usan hoy

- `admin` es un usuario virtual definido por configuracion en [config.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/config.py:4)
- `workshop` sale del login de talleres
- `client` vive en tabla `clients`

### Problema principal
El rol se devuelve en la respuesta de login, pero no existe una capa backend que use ese rol para bloquear o permitir endpoints.

### Riesgos actuales por falta de autorizacion

- cualquier consumidor puede listar clientes, talleres, tecnicos y vehiculos
- cualquier consumidor puede modificar o eliminar recursos de terceros
- cualquier consumidor puede aprobar o rechazar talleres
- cualquier consumidor puede registrar FCM para otro `user_id`

## 4. Seguridad de contraseñas

### Hashing usado
Se usa:

- `PBKDF2-HMAC-SHA256`
- `100_000` iteraciones
- `salt` aleatorio de `16` bytes en hexadecimal

Implementado en [security.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/security.py:17) y duplicado en [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:500).

### Verificacion
La verificacion usa:

- recalculo del digest
- `secrets.compare_digest`

### Evaluacion
El hashing base es aceptable para este estado del proyecto.

### Debilidades relacionadas

- la contraseña del admin protegido existe en configuracion y `.env`
- la contraseña inicial de taller tambien existe en configuracion y `.env`
- hay duplicacion de funciones de seguridad entre `security.py` y `main.py`

## 5. Forgot password

### Como funciona hoy

Flujos activos:

- `POST/PUT /api/auth/forgot-password`
- `POST/PUT /api/clientes/forgot-password`
- `POST/PUT /api/workshops/forgot-password`
- `POST /api/workshops/change-password`

### Comportamiento actual

- basta conocer el correo
- se envia `newPassword` y `confirmPassword`
- no hay OTP
- no hay token firmado
- no hay correo de recuperacion
- no hay expiracion temporal
- no hay invalidacion por un solo uso

### Riesgos puntuales

- [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2297): `auth/forgot-password` resetea cliente o taller automaticamente si el correo existe
- [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1911): `workshops/forgot-password` resetea clave sin autenticacion adicional
- [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1877): `workshops/change-password` puede activar/cambiar clave de taller con solo email y nueva clave, sin prueba de identidad

### Propuesta segura de flujo

1. Solicitud de recuperacion por correo.
2. Generar token aleatorio firmado o registro de reset en BD.
3. Guardar:
   - `user_id`
   - `purpose`
   - `expires_at`
   - `used_at`
   - hash del token
4. Enviar enlace o OTP al correo/telefono.
5. Confirmar el token en endpoint separado.
6. Permitir cambio de contraseña solo con token valido y no usado.
7. Invalidar todos los tokens previos al usar uno.
8. Registrar auditoria de recuperacion.

## 6. Tokens FCM

### Registro actual
El endpoint es:

- `POST /api/devices/fcm-token`

Implementado en [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1302).

### Como se asocia

- se recibe `user_id`
- se valida solo que ese `client` exista con `ensure_client_exists`
- se hace `upsert` por `fcm_token`

### Problemas

- no requiere autenticacion
- cualquier actor puede registrar un token para cualquier `user_id` existente
- el modelo actual parece pensado solo para `clients`, no para tecnicos ni operadores
- el mismo backend puede terminar enviando notificaciones al token equivocado si el `user_id` fue suplantado

### Evaluacion
FCM hoy no esta ligado a identidad autenticada, sino a un `user_id` enviado por el cliente.

## 7. CORS y configuracion

### Configuracion actual
Configurado en [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1245).

Permite:

- `localhost`
- `127.0.0.1`
- redes privadas RFC1918
- cualquier IPv4 publica por regex

### Riesgo
Para desarrollo puede ser funcional, pero para produccion es excesivamente abierto.

### Variables de entorno relacionadas

No se detecto una variable tipo:

- `CORS_ALLOWED_ORIGINS`
- `ALLOWED_ORIGIN_REGEX`

La politica CORS esta codificada en el backend.

## Tabla de riesgos encontrados

| Riesgo | Severidad | Evidencia | Impacto |
|---|---|---|---|
| Endpoints CRUD sensibles sin autenticacion real | Alta | `main.py` sin `Depends` ni validacion Bearer | Lectura, modificacion y borrado por terceros |
| Token de login no verificable ni persistido | Alta | `secrets.token_urlsafe(32)` en login | El token no protege recursos ni representa sesion real |
| `auth/forgot-password` cambia clave solo con correo | Alta | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2297) | Toma de cuenta remota |
| `workshops/change-password` sin prueba de identidad | Alta | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1877) | Cambio o activacion de cuenta de taller |
| `workshops/{id}/approval-status` publico | Alta | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1953) | Escalamiento a aprobacion de sucursales |
| `clientes`, `technicians`, `vehicles`, `workshops` publicos | Alta | CRUDs en `main.py` | Exposicion y manipulacion de datos |
| Registro FCM con `user_id` arbitrario | Alta | [main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1307) | Suplantacion de dispositivo y notificaciones |
| Credenciales privilegiadas en configuracion | Alta | [config.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/config.py:4) | Compromiso total si se filtra `.env` |
| CORS demasiado amplio | Media | regex de origen en `main.py` | Aumenta superficie de abuso desde navegadores |
| Enumeracion de cuentas por `account-type` y errores diferenciados | Media | `auth/account-type`, 403/404 especificos | Facilita reconocimiento de usuarios |
| Lockout no aplicado a clientes | Media | login solo bloquea admin/workshop | Fuerza bruta sobre clientes |
| Duplicacion de logica de auth en `routes/auth.py` y `main.py` | Media | archivo alterno no cableado | Drift y errores futuros |
| `token_type` inconsistente (`bearer` vs `Bearer`) | Baja | `routes/auth.py` y `main.py` | Inconsistencia de contrato |

## Recomendaciones tecnicas

1. Implementar JWT real con:
   - `sub`
   - `role`
   - `exp`
   - `iat`
   - `iss`
2. Crear dependencia `get_current_user`.
3. Crear dependencias por rol:
   - `require_admin`
   - `require_operator`
   - `require_workshop_or_admin`
   - `require_client_self_or_admin`
4. Proteger primero:
   - `clientes`
   - `workshops`
   - `technicians`
   - `vehicles`
   - `emergencias`
   - `devices/fcm-token`
5. Rehacer totalmente `forgot-password`.
6. Mover CORS a configuracion por entorno.
7. Eliminar credenciales por defecto del admin en docs publicas.
8. Centralizar seguridad en un solo modulo y eliminar duplicacion de funciones.
9. Agregar auditoria/log de eventos de autenticacion y reseteo.
10. Introducir refresh token o expiraciones cortas mas rotacion controlada.

## Orden recomendado de correccion

1. Introducir validacion real de tokens en backend.
2. Proteger endpoints sensibles con dependencias FastAPI.
3. Definir RBAC minimo para Core y mobile.
4. Corregir `forgot-password`.
5. Corregir `devices/fcm-token` para usar identidad autenticada, no `user_id` arbitrario.
6. Cerrar CORS por entorno.
7. Refactorizar `main.py` para separar auth/authorization en modulo dedicado.

## Primer cambio de codigo seguro recomendado

El primer cambio seguro recomendado es:

`implementar autenticacion Bearer real y aplicar proteccion al menos a /api/clientes, /api/workshops, /api/technicians y /api/devices/fcm-token`

### Por que este primero

- reduce de inmediato la mayor superficie de exposicion
- no exige aun renombrar dominio `workshop`
- prepara el backend para web y mobile
- evita que el token siga siendo solo decorativo

### Secuencia sugerida

1. Agregar emision de JWT valido en `login`.
2. Agregar dependencia `get_current_user`.
3. Aplicar `Depends(get_current_user)` a endpoints sensibles.
4. Agregar dependencias por rol.
5. Ajustar frontend/mobile al nuevo contrato.

## Nota adicional sobre `routes/auth.py`
Existe un archivo alterno [backend/app/routes/auth.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/routes/auth.py:1), pero no se detecto `include_router(...)` activo en `main.py`. Eso sugiere una refactorizacion incompleta. Para evitar drift, el backend deberia consolidar una sola implementacion de autenticacion.
