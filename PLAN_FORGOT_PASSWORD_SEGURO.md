# PLAN DE FORGOT-PASSWORD SEGURO

## Objetivo
Definir una migracion segura del flujo actual de recuperacion de contraseña del backend FastAPI para llevarlo desde un reseteo directo por correo a un mecanismo con token temporal, expiracion y un solo uso, sin romper todavia frontend ni posibles clientes mobile.

## Alcance

- No modifica codigo en esta etapa.
- No realiza commits.
- No rompe el flujo actual mientras se implementa la migracion.
- Se basa en el backend FastAPI actual como `Microservicio 1: Gestion Empresarial Core`.

## 1. Estado actual

## Endpoint unificado actual

Endpoint:

- `POST|PUT /api/auth/forgot-password`

Implementacion:

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:2345)

### Request payload actual

Schema actual:

- `UnifiedForgotPasswordRequest`

Campos:

- `email`
- `newPassword` o `new_password` o `password`
- `confirmPassword` o `confirm_password`

Implementacion del schema:

- [backend/app/main.py](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/backend/app/main.py:394)

### Respuesta actual

Devuelve un `message` exitoso distinto segun el tipo de cuenta:

- cliente: `"La contraseña del cliente fue restablecida correctamente"`
- taller: `"La contraseña del taller fue restablecida correctamente"`

### Comportamiento actual

El backend:

1. recibe correo y nueva contraseña
2. busca primero en clientes
3. si existe cliente y esta activo, cambia la contraseña de inmediato
4. si no existe cliente, busca taller
5. si existe taller y esta activo, cambia la contraseña de inmediato
6. si no existe, responde `404`

No existe:

- token de recuperacion
- OTP
- correo firmado
- link temporal
- expiracion
- control de un solo uso
- prueba de identidad real

## Endpoints legacy relacionados

- `POST /api/clientes/forgot-password`
- `POST /api/workshops/forgot-password`
- `POST /api/workshops/change-password`
- `POST /api/clientes/change-password`

Los mas inseguros para recovery son:

- `POST|PUT /api/auth/forgot-password`
- `POST|PUT /api/clientes/forgot-password`
- `POST|PUT /api/workshops/forgot-password`

## 2. Riesgos actuales

### Riesgo principal

Cualquier actor que conozca un correo valido puede cambiar la contraseña de la cuenta sin demostrar identidad.

### Riesgos concretos

- toma remota de cuentas por conocimiento del correo
- enumeracion de usuarios por mensajes `404` y `403`
- distincion entre cliente y taller por respuestas
- abuso automatizado por bots
- reseteo ilimitado sin rate limit especifico por recovery
- falta de auditoria de eventos de recuperacion
- posibilidad de bloquear operacion real del usuario legitimo

### Riesgo en frontend actual

El frontend Angular actual no hace un flujo de solicitud de recuperacion. Hace directamente cambio de contraseña por correo desde:

- [frontend/src/app/pages/forgot-password-page.component.ts](/home/jhasmany/Repository/Ingenieria Software 2/Segundo Parcial/FICCT-Segundo-Parcial-Sw2-Web/frontend/src/app/pages/forgot-password-page.component.ts:1)

Flujo actual del frontend:

1. pide `email`
2. pide `newPassword`
3. pide `confirmPassword`
4. intenta primero `POST /api/clientes/forgot-password`
5. si recibe `404`, intenta `POST /api/workshops/forgot-password`
6. si viene de login inicial de taller, usa `POST /api/workshops/change-password`

Eso significa que hoy la UI esta acoplada a un reset directo y no a un challenge temporal.

## 3. Qué usa frontend actualmente

Endpoints consumidos por Angular:

- `POST /api/clientes/forgot-password`
- `POST /api/workshops/forgot-password`
- `POST /api/workshops/change-password`

No consume hoy:

- `POST /api/auth/forgot-password`

Eso vuelve importante mantener compatibilidad temporal no solo con el endpoint unificado, sino tambien con los endpoints legacy especificos.

## 4. Qué podria usar mobile

No se detecta una app React Native dentro de este repositorio.

Por lo tanto:

- no hay evidencia local de contrato mobile implementado
- pero cualquier cliente mobile existente podria estar consumiendo alguno de estos endpoints publicos:
  - `/api/auth/forgot-password`
  - `/api/clientes/forgot-password`
  - `/api/workshops/forgot-password`

Conclusion operativa:

- el plan debe asumir compatibilidad temporal con esos contratos mientras se introduce el flujo seguro nuevo

## 5. Flujo objetivo seguro

## Endpoint 1: solicitud de recuperacion

Endpoint nuevo propuesto:

- `POST /api/auth/forgot-password/request`

### Request

Body:

```json
{
  "identifier": "usuario@correo.com"
}
```

o bien:

```json
{
  "email": "usuario@correo.com"
}
```

En una fase posterior puede admitir:

- `phone`

### Comportamiento

1. Normalizar email o telefono.
2. Buscar usuario elegible para recovery.
3. Siempre responder de forma neutral.
4. Si la cuenta existe:
   - generar token aleatorio seguro
   - guardar solo hash del token
   - registrar expiracion
   - registrar metadata basica
   - simular envio por log o consola en desarrollo
5. Si no existe:
   - no revelar nada
   - responder exactamente igual

### Respuesta recomendada

Codigo:

- `200 OK`

Payload:

```json
{
  "message": "Si la cuenta existe, se enviaron instrucciones de recuperación."
}
```

## Endpoint 2: reset seguro

Endpoint nuevo propuesto:

- `POST /api/auth/forgot-password/reset`

### Request

```json
{
  "token": "token-temporal-recibido",
  "newPassword": "NuevaClave123",
  "confirmPassword": "NuevaClave123"
}
```

### Comportamiento

1. Validar formato del token.
2. Hashear token recibido.
3. Buscar token activo en almacenamiento.
4. Verificar:
   - no expirado
   - no usado
   - proposito correcto
5. Cargar usuario asociado.
6. Cambiar contraseña usando el mismo hashing actual.
7. Marcar token como usado.
8. Invalidar otros tokens activos del mismo usuario para password reset.
9. Registrar auditoria del evento.

### Respuesta recomendada

Codigo:

- `200 OK`

Payload:

```json
{
  "message": "La contraseña fue restablecida correctamente."
}
```

### Errores recomendados

- `400 Bad Request`: token malformado o passwords invalidas
- `410 Gone` o `400`: token expirado o ya usado
- `404` no es recomendable para distinguir existencia de token

## 6. Cambios de base de datos necesarios

Se necesita persistencia para tokens temporales de recuperacion.

## Tabla sugerida

Nombre sugerido:

- `password_reset_tokens`

Campos sugeridos:

- `id`
- `user_id`
- `account_type`
- `email_snapshot`
- `token_hash`
- `purpose`
- `expires_at`
- `used_at`
- `created_at`
- `requested_ip`
- `requested_user_agent`
- `delivery_channel`

### Recomendaciones de integridad

- indice por `token_hash`
- indice por `user_id`, `purpose`, `used_at`
- `purpose` fijo en esta fase: `password_reset`

### Nota sobre modelo de usuario

Como el sistema todavia usa cuentas separadas de:

- `clients`
- `workshops`
- admin protegido por configuracion

el campo `account_type` es necesario en la fase transitoria para resolver el destino correcto del reset.

## 7. Migracion necesaria

Si aplica persistencia relacional en PostgreSQL, se recomienda:

1. crear nueva tabla `password_reset_tokens`
2. no tocar todavia tablas `clients` ni `workshop_registrations`
3. no renombrar dominio `workshop` aun
4. introducir limpieza programada de tokens expirados despues

### Estrategia de migracion

- Fase 1: crear tabla nueva sin tocar contratos existentes
- Fase 2: agregar endpoints nuevos
- Fase 3: adaptar frontend al flujo nuevo
- Fase 4: marcar endpoints legacy como deprecated
- Fase 5: desactivar reset directo legacy

## 8. Endpoints nuevos propuestos

### Nuevos

- `POST /api/auth/forgot-password/request`
- `POST /api/auth/forgot-password/reset`

### Opcionales despues

- `POST /api/auth/forgot-password/verify`

Este endpoint intermedio solo seria necesario si se quiere:

- validar token antes de mostrar formulario final
- soportar links web de recuperacion

No es obligatorio en la primera entrega segura.

## 9. Estrategia de compatibilidad temporal

## Principio

No romper todavia el frontend ni posibles clientes mobile.

## Compatibilidad recomendada

### Opcion recomendada

Mantener activos temporalmente:

- `/api/auth/forgot-password`
- `/api/clientes/forgot-password`
- `/api/workshops/forgot-password`

pero:

- marcarlos como `deprecated`
- registrar advertencia en logs
- documentar fecha objetivo de retiro

### Comportamiento transitorio sugerido

Fase transitoria 1:

- endpoints nuevos conviven con los legacy
- frontend nuevo empieza a consumir `/request` y `/reset`
- mobile puede seguir usando legacy mientras migra

Fase transitoria 2:

- los legacy dejan de cambiar contraseña directamente
- pasan a responder mensaje que instruya usar el flujo seguro
- o internamente llaman al flujo nuevo solo en entornos de compatibilidad controlada

Fase final:

- retiro completo de reset directo por correo

## 10. Impacto en frontend

## Estado actual del frontend

La pantalla actual combina en un mismo formulario:

- identificador
- nueva contraseña
- confirmacion

Eso no encaja con un flujo de token temporal.

## Cambio recomendado en frontend

Dividir la UX en dos pasos:

### Paso 1

Formulario de solicitud:

- correo
- boton `Enviar instrucciones`

### Paso 2

Formulario de reset:

- token recibido o token tomado desde query param
- nueva contraseña
- confirmacion

### Compatibilidad temporal

Mientras se migra:

- mantener la ruta `/forgot-password`
- permitir modo legacy solo si se activa por flag o query param
- preferir que la UI nueva use los endpoints nuevos

## 11. Impacto en mobile

Como no hay cliente mobile en este repo, el plan debe asumir contrato HTTP compatible.

### Recomendacion

- documentar endpoints nuevos primero
- permitir coexistencia temporal con legacy
- evitar retirar de golpe `/api/auth/forgot-password`

### Riesgos mobile

- si una app mobile ya usa reset directo, se rompera si se reemplaza de golpe
- si depende de mensajes `404` o `403`, la respuesta neutral del flujo nuevo requerira ajustes

## 12. Riesgos de implementacion

- romper la pantalla Angular actual si se elimina pronto `/clientes/forgot-password`
- dejar rutas legacy activas demasiado tiempo y mantener superficie insegura
- introducir tabla nueva sin estrategia de limpieza de expirados
- no versionar bien la transicion entre clientes legacy y nuevos
- olvidar loggear el token en desarrollo y bloquear pruebas manuales

## 13. Pruebas manuales recomendadas

### Flujo nuevo request

1. `POST /api/auth/forgot-password/request` con correo existente
2. verificar respuesta `200` neutral
3. verificar creacion del token hasheado en BD
4. verificar emision del token plano solo por log o canal de desarrollo

### Flujo nuevo request con cuenta inexistente

1. enviar correo inexistente
2. verificar misma respuesta `200`
3. verificar que no revela si la cuenta existe

### Flujo reset

1. usar token valido
2. enviar nueva contraseña y confirmacion
3. verificar cambio de contraseña
4. verificar que el token quede marcado como usado

### Token expirado

1. usar token vencido
2. verificar rechazo controlado

### Reuso

1. usar token una vez con exito
2. intentar reutilizarlo
3. verificar rechazo

### Compatibilidad temporal

1. validar que frontend viejo todavia puede funcionar en entorno transitorio
2. validar que login con nueva contraseña sigue funcionando

## 14. Primer cambio de codigo seguro recomendado

El primer cambio seguro recomendado no es reemplazar el endpoint actual.

El primer cambio seguro es:

1. crear el schema y persistencia para `password_reset_tokens`
2. crear solo `POST /api/auth/forgot-password/request`
3. responder neutralmente
4. generar token y guardarlo hasheado
5. simular envio por log en desarrollo

### Por que este primero

- no rompe el frontend actual
- no elimina contratos existentes
- introduce la base segura del nuevo flujo
- permite probar la persistencia y expiracion antes de tocar el cambio real de contraseña

### Segundo cambio seguro

- agregar `POST /api/auth/forgot-password/reset`

### Tercer cambio

- adaptar frontend Angular a flujo de dos pasos

### Cuarto cambio

- marcar legacy como deprecated y planificar retiro

## 15. Recomendacion final

La migracion segura del recovery no debe empezar quitando el endpoint actual, sino agregando primero el flujo nuevo y dejando una ventana de compatibilidad.

Secuencia recomendada:

1. tabla `password_reset_tokens`
2. endpoint `request`
3. endpoint `reset`
4. adaptacion frontend
5. compatibilidad temporal para mobile
6. deprecacion
7. retiro del reset directo legacy

Ese orden reduce el riesgo operativo y elimina gradualmente la vulnerabilidad mas critica sin romper acceso de usuarios reales durante la transicion.
