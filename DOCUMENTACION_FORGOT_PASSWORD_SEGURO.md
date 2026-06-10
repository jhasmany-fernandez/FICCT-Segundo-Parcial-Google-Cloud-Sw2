# DOCUMENTACION DE FORGOT-PASSWORD SEGURO

## Objetivo
Documentar el nuevo flujo seguro de recuperacion de contraseña implementado en backend para convivir temporalmente con el flujo legacy actual, sin romper frontend ni posibles clientes externos durante la transicion.

## 1. Resumen del problema anterior

Antes de este cambio, el sistema permitia restablecer contraseñas directamente con solo conocer el correo y enviar una nueva clave.

Problemas principales del flujo anterior:

- no existia token temporal
- no existia expiracion
- no existia invalidacion de un solo uso
- no existia prueba de posesion del correo
- se revelaba demasiada informacion sobre la existencia y estado de la cuenta

En otras palabras, el flujo viejo era un cambio directo de contraseña por correo conocido, no una recuperacion segura.

## 2. Endpoints nuevos implementados

Se agregaron los siguientes endpoints nuevos:

- `POST /api/auth/forgot-password/request`
- `POST /api/auth/forgot-password/reset`

Estos endpoints conviven con el flujo anterior por compatibilidad temporal.

## 3. Flujo seguro paso a paso

## Paso 1. Solicitud de recuperacion

El cliente llama:

- `POST /api/auth/forgot-password/request`

El backend:

1. normaliza el correo
2. busca una cuenta elegible
3. responde siempre con un mensaje generico
4. si la cuenta existe y esta activa:
   - genera un token temporal con `secrets.token_urlsafe(32)`
   - calcula su hash SHA-256
   - guarda solo el hash
   - registra expiracion
   - registra la cuenta asociada

## Paso 2. Generacion de token temporal

El token temporal:

- se genera aleatoriamente
- no se persiste en texto plano
- se asocia a:
  - `account_type`
  - `account_id`
- expira por configuracion

## Paso 3. Almacenamiento de hash

La persistencia usa la tabla:

- `password_reset_tokens`

Campos relevantes:

- `id`
- `account_type`
- `account_id`
- `token_hash`
- `expires_at`
- `used_at`
- `created_at`

## Paso 4. Expiracion

La expiracion actual configurada es:

- `15` minutos

Si el token ya expiro, el reset se rechaza.

## Paso 5. Reset de contraseña

El cliente llama:

- `POST /api/auth/forgot-password/reset`

El backend:

1. recibe token y nueva contraseña
2. valida el token contra el hash almacenado
3. verifica que no este usado
4. verifica que no este expirado
5. identifica `account_type` y `account_id`
6. actualiza la contraseña correspondiente
7. marca el token como usado

## Paso 6. Marcado del token como usado

Una vez consumido con exito:

- `used_at` deja de ser `null`
- el mismo token ya no puede volver a utilizarse

## 4. Request y response de los endpoints nuevos

## `POST /api/auth/forgot-password/request`

### Request

```json
{
  "email": "usuario@correo.com"
}
```

### Response esperada

Siempre responde con mensaje generico:

```json
{
  "message": "Si la cuenta existe, se enviarán instrucciones de recuperación."
}
```

### Response en development

Para pruebas manuales, en entorno `development` puede incluir:

```json
{
  "message": "Si la cuenta existe, se enviarán instrucciones de recuperación.",
  "reset_token": "token-temporal"
}
```

## `POST /api/auth/forgot-password/reset`

### Request

```json
{
  "token": "token-temporal",
  "new_password": "NuevaClave123"
}
```

Tambien acepta compatibilidad de campo:

- `newPassword`
- `password`

### Response exitosa

```json
{
  "message": "Contraseña actualizada correctamente."
}
```

### Response de error controlado

Para token invalido, expirado o ya usado:

```json
{
  "detail": "Token de recuperación inválido, expirado o ya utilizado"
}
```

## 5. Comportamiento en development

En `development`:

- el endpoint `request` devuelve `reset_token`
- esto existe solo para facilitar pruebas manuales y validacion local

Esto permite probar el flujo completo sin integrar todavia envio real de correo.

## 6. Comportamiento esperado en production

En `production` el comportamiento esperado es:

- no devolver `reset_token`
- no exponer el token plano en la respuesta
- enviar instrucciones por email o por otro canal seguro

La API debe mantener la misma respuesta generica, pero el token debe viajar solo por el canal de entrega seguro.

## 7. Seguridad del flujo nuevo

El flujo nuevo fue diseñado con estas reglas:

- no revelar si el usuario existe o no en el endpoint `request`
- no guardar nunca el token plano
- guardar solo el hash del token
- no permitir reutilizacion
- no devolver `password_hash`
- no loguear el token plano
- rechazar token expirado
- rechazar token ya usado

## 8. Estado del endpoint viejo

El endpoint antiguo sigue activo temporalmente:

- `POST|PUT /api/auth/forgot-password`

Estado recomendado:

- considerarlo flujo `legacy`
- considerarlo `deprecated` a nivel funcional

Motivo:

- frontend actual y posibles clientes externos todavia pueden depender de ese contrato
- el flujo nuevo debe convivir hasta completar la migracion

Plan esperado:

- mantenerlo temporalmente
- migrar frontend y mobile al flujo nuevo
- retirar o desactivar el flujo viejo despues

## 9. Validaciones realizadas

Se validaron los siguientes escenarios:

- email inexistente:
  - `POST /api/auth/forgot-password/request` responde `200` generico
- email existente:
  - `POST /api/auth/forgot-password/request` responde `200` generico
  - en `development` devuelve `reset_token`
- token invalido:
  - `POST /api/auth/forgot-password/reset` responde `400`
- token valido:
  - `POST /api/auth/forgot-password/reset` responde `200`
  - la contraseña se actualiza
- reuso de token:
  - segundo uso del mismo token responde `400`
- login con contraseña nueva:
  - funciona correctamente
- login con contraseña anterior:
  - falla correctamente
- frontend build:
  - sigue pasando sin cambios

## 10. Pendientes

Quedan pendientes las siguientes tareas para cerrar la migracion:

- conectar frontend al flujo nuevo
- eliminar o desactivar el flujo viejo cuando ya no se use
- integrar envio real de email o canal seguro
- agregar limpieza de tokens expirados
- evaluar invalidacion adicional de otros tokens activos si se requiere

## Cierre

El backend ya dispone de un flujo seguro nuevo de recuperacion con token temporal, hash y expiracion, sin romper compatibilidad con el sistema actual.

El siguiente paso natural es migrar la UI al flujo nuevo y luego retirar el mecanismo legacy de cambio directo por correo.
