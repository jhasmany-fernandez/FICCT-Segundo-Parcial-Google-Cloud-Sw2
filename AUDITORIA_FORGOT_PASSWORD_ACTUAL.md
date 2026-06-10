# AUDITORIA DEL FLUJO ACTUAL DE FORGOT-PASSWORD

## Objetivo
Documentar exactamente como funciona hoy la recuperacion de contraseña en backend y frontend antes de modificar codigo, para implementar una version segura sin romper la pantalla actual ni contratos heredados durante la transicion.

## Archivos revisados

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:348)
- [backend/API.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/API.md:408)
- [frontend/src/app/pages/forgot-password-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/forgot-password-page.component.ts:1)
- [PLAN_FORGOT_PASSWORD_SEGURO.md](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/PLAN_FORGOT_PASSWORD_SEGURO.md:1)

## Resumen ejecutivo

Hoy el sistema no implementa un verdadero flujo de recuperacion de contraseña. En la practica, el backend permite cambiar la contraseña directamente con solo conocer el correo y enviar una nueva clave.

El frontend actual esta acoplado a ese comportamiento:

- muestra un formulario unico con correo y nueva contraseña
- espera que el cambio ocurra inmediatamente
- intenta primero el endpoint de clientes
- si recibe `404`, intenta el endpoint de talleres o sucursales legacy

Por eso, reemplazar de golpe el comportamiento de los endpoints actuales romperia la pantalla existente y posiblemente clientes externos que dependan del mismo contrato.

## Backend auditado

## Endpoint unificado actual

Ruta:

- `POST|PUT /api/auth/forgot-password`

Handler:

- `forgot_password`

Implementacion:

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2345)

### Metodos HTTP permitidos

- `POST`
- `PUT`

### Payload recibido

Schema:

- `UnifiedForgotPasswordRequest`

Campos:

- `email`
- `newPassword` o `new_password` o `password`
- `confirmPassword` o `confirm_password`

Implementacion del schema:

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:394)

### Validaciones actuales del schema

- `email` debe ser `EmailStr`
- `new_password` minimo 6 caracteres
- `confirm_password` minimo 6 caracteres
- `new_password` y `confirm_password` deben coincidir

No valida:

- identidad real del solicitante
- token temporal
- OTP
- expiracion
- un solo uso
- rate limiting especifico

### Flujo actual paso a paso

1. Normaliza el correo a minusculas y sin espacios.
2. Busca primero un cliente con `get_client_by_email`.
3. Si encuentra cliente:
   - verifica que `status == "active"`
   - hashea la nueva contraseña con `hash_password`
   - actualiza directamente con `update_client_password`
   - responde exito de cliente
4. Si no encuentra cliente, busca un taller con `get_workshop_by_email`.
5. Si encuentra taller:
   - verifica que `approval_status == "activo"`
   - hashea la nueva contraseña con `hash_password`
   - actualiza directamente con `update_workshop_password`
   - responde exito de taller
6. Si no encuentra ninguna cuenta:
   - responde `404`

### Funciones auxiliares usadas

- `get_client_by_email`
- `get_workshop_by_email`
- `update_client_password`
- `update_workshop_password`
- `hash_password`

### Respuesta actual

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

### Errores actuales

- `403 Forbidden`
  - cliente suspendido: `"Cuenta suspendida"`
  - taller no activo: `"El taller todavía no fue habilitado por el administrador"`
- `404 Not Found`
  - `"No existe una cuenta con ese correo"`
- `422 Unprocessable Entity`
  - payload invalido o contraseñas no coinciden

## Endpoints legacy relacionados

### Clientes

Ruta:

- `POST|PUT /api/clientes/forgot-password`

Handler:

- `forgot_client_password`

Implementacion:

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2098)

Comportamiento:

- busca cliente por correo
- valida `status == "active"`
- cambia la contraseña directamente con `update_client_password`
- devuelve:

```json
{
  "message": "La contraseña del cliente fue restablecida correctamente"
}
```

### Workshops o sucursales legacy

Ruta:

- `POST|PUT /api/workshops/forgot-password`

Handler:

- `forgot_workshop_password`

Implementacion:

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1928)

Comportamiento:

- busca taller por correo
- valida `approval_status == "activo"`
- cambia la contraseña directamente con `update_workshop_password`
- devuelve:

```json
{
  "message": "La contraseña del taller fue restablecida correctamente"
}
```

### Cambio inicial de contraseña de workshop

Ruta:

- `POST /api/workshops/change-password`

Handler:

- `change_workshop_password`

Implementacion:

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:1894)

Este endpoint no es forgot-password puro, pero la pantalla actual tambien lo usa cuando el login detecta contraseña temporal inicial. En ese caso:

- busca workshop por correo
- verifica si aun usa la contraseña inicial temporal
- actualiza contraseña
- cambia `approval_status` a `activo`

## Flujo actual real de recuperacion

## Escenario 1: cliente

1. El usuario abre `/forgot-password`.
2. Ingresa correo, nueva contraseña y confirmacion.
3. El frontend hace `POST /api/clientes/forgot-password`.
4. Si el cliente existe y esta activo, el backend cambia la contraseña inmediatamente.
5. El frontend muestra el `message` y navega a `/login`.

## Escenario 2: workshop o sucursal legacy

1. El usuario abre `/forgot-password`.
2. Ingresa correo, nueva contraseña y confirmacion.
3. El frontend hace primero `POST /api/clientes/forgot-password`.
4. Si recibe `404`, intenta `POST /api/workshops/forgot-password`.
5. Si el workshop existe y esta activo, el backend cambia la contraseña inmediatamente.
6. El frontend muestra el `message` y navega a `/login`.

## Escenario 3: login inicial de workshop

1. Desde login, el frontend redirige a `/forgot-password?source=workshop-initial-login&email=...`.
2. La pantalla cambia titulo y copy.
3. El frontend llama `POST /api/workshops/change-password`.
4. Si el backend detecta que el workshop aun usa la contraseña temporal, actualiza la contraseña y activa la cuenta.

## Payload actual usado por frontend

El frontend envia siempre:

```json
{
  "email": "usuario@correo.com",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

Observaciones:

- usa `camelCase`
- el backend lo acepta por aliases
- el frontend usa `POST`, no `PUT`
- espera cambio inmediato de contraseña, no envio de instrucciones

## Frontend auditado

Archivo principal:

- [frontend/src/app/pages/forgot-password-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/forgot-password-page.component.ts:1)

## Pantalla actual

La pantalla mezcla en un solo paso:

- identificacion por correo
- nueva contraseña
- confirmacion de contraseña

### Textos visibles

Modo normal:

- titulo: `¿Olvidaste tu contraseña?`
- copy: `Ingresa tu correo electronico y registra una nueva contrasena para recuperar el acceso como cliente o sucursal.`
- boton: `Cambiar contraseña`

Modo workshop inicial:

- titulo: `Registrar nueva contraseña`
- copy: `Registra una nueva contrasena para la sucursal antes de continuar con el inicio de sesion.`
- mensaje adicional: `Detectamos un ingreso con contrasena temporal. Antes de acceder al sistema, debes registrar una nueva contrasena para el correo indicado.`

## Servicio o API usada

URLs configuradas en la pantalla:

- `/api/workshops/change-password`
- `/api/workshops/forgot-password`
- `/api/clientes/forgot-password`

No usa:

- `/api/auth/forgot-password`

## Tipo de request usado

Solo usa:

- `POST`

No usa:

- `PUT`

## Respuesta que espera

La pantalla espera:

```ts
{ message: string }
```

Luego:

- muestra `response.message`
- limpia el formulario
- navega a `/login`

## Dependencia exacta del frontend

El frontend depende hoy de tres comportamientos inseguros pero reales:

1. que `/api/clientes/forgot-password` cambie la contraseña directamente
2. que `/api/workshops/forgot-password` cambie la contraseña directamente
3. que el endpoint de clientes devuelva `404` cuando el correo no pertenece a un cliente, para entonces intentar el endpoint de workshops

Eso significa que cambiar el contrato actual a respuesta neutral o a flujo por token en esos endpoints romperia la pantalla actual.

## Riesgos actuales

## Riesgos de seguridad exactos

- cualquier persona que conozca un correo valido puede cambiar la contraseña sin demostrar identidad
- no existe token temporal ni prueba de posesion del correo
- no existe expiracion
- no existe invalidacion de un solo uso
- no existe limitacion de intentos especifica para recovery
- no existe auditoria dedicada de solicitudes de recuperacion

## Riesgos de enumeracion

El flujo actual filtra demasiada informacion:

- `404` cuando la cuenta no existe
- `403` si la cuenta existe pero esta suspendida o no activa
- mensajes diferentes para cliente y taller

Eso permite inferir:

- si el correo existe
- si pertenece a cliente o workshop
- si la cuenta esta activa

## Riesgos operativos

- un atacante puede tomar cuentas remotamente
- un tercero puede bloquear al usuario legitimo cambiando la clave antes
- el frontend depende de errores `404` para decidir el siguiente endpoint
- el endpoint unificado `/api/auth/forgot-password` tiene un contrato distinto al usado por Angular, lo que complica una sustitucion directa

## Compatibilidad y riesgo de cambio

## Que pasaria si cambiamos ya el endpoint actual

Si se cambia de golpe el comportamiento de:

- `/api/clientes/forgot-password`
- `/api/workshops/forgot-password`

la pantalla Angular actual dejaria de funcionar correctamente porque:

- ya no obtendria cambio inmediato de contraseña
- seguiria mostrando un formulario de nueva contraseña en un solo paso
- seguiria esperando un `message` de exito final
- seguiria usando `404` del endpoint de clientes como señal para intentar workshops

Si se cambia solo `/api/auth/forgot-password`, el impacto en Angular seria bajo porque hoy no lo consume. Pero podria afectar:

- integraciones externas
- una app mobile no visible en este repositorio
- pruebas manuales o scripts que usen el endpoint unificado documentado

## Que conviene mantener temporalmente

Durante la transicion conviene mantener activos temporalmente:

- `/api/clientes/forgot-password`
- `/api/workshops/forgot-password`
- `/api/auth/forgot-password`

Ademas conviene mantener tambien:

- `/api/workshops/change-password`

porque cumple un rol distinto de activacion inicial y ya esta integrado en login.

## Que endpoint nuevo conviene crear primero

El mejor primer endpoint nuevo es:

- `POST /api/auth/forgot-password/request`

Razones:

- no rompe la pantalla actual
- no obliga a cambiar aun los endpoints legacy
- permite introducir el modelo seguro de token temporal
- habilita pruebas controladas antes de tocar el reseteo real

## Propuesta de transicion segura

## Fase 1

Agregar:

- `POST /api/auth/forgot-password/request`

Comportamiento:

- recibe email o identifier
- responde siempre neutral
- si la cuenta existe, genera token y lo persiste hasheado
- en desarrollo, emite el token por log controlado

Sin tocar todavia:

- `/api/clientes/forgot-password`
- `/api/workshops/forgot-password`
- `/api/auth/forgot-password`

## Fase 2

Agregar:

- `POST /api/auth/forgot-password/reset`

Comportamiento:

- recibe token temporal y nueva contraseña
- valida expiracion
- valida un solo uso
- cambia contraseña de forma segura

## Fase 3

Adaptar la pantalla Angular a flujo de dos pasos:

1. solicitud
2. reset con token

## Fase 4

Marcar como deprecated:

- `/api/clientes/forgot-password`
- `/api/workshops/forgot-password`
- `/api/auth/forgot-password`

## Fase 5

Retirar el reseteo directo por correo cuando frontend y posibles clientes externos ya migren.

## Primer cambio de codigo recomendado

El primer cambio seguro recomendado es:

1. crear persistencia para tokens de recuperacion
2. agregar `POST /api/auth/forgot-password/request`
3. responder neutralmente siempre
4. generar token seguro y guardar solo su hash
5. registrar expiracion y metadata basica
6. dejar intacta la pantalla actual mientras se valida el flujo nuevo

No conviene como primer cambio:

- reemplazar el comportamiento actual de `/api/clientes/forgot-password`
- reemplazar el comportamiento actual de `/api/workshops/forgot-password`
- rediseñar de golpe la pantalla Angular

## Conclusion

La auditoria confirma que hoy no existe recuperacion de contraseña segura, sino un cambio directo de contraseña por conocimiento del correo.

El backend ya expone los puntos de mayor riesgo y el frontend esta estrechamente acoplado a ese comportamiento. Por eso, la ruta correcta no es reemplazar el flujo actual de golpe, sino introducir primero un flujo nuevo y seguro en paralelo, migrar la UI despues y retirar los endpoints legacy al final.
