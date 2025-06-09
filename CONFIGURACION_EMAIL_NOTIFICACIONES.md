# Configuración de Notificaciones por Email

## 📧 Funcionalidad Implementada

Se ha implementado una funcionalidad que envía automáticamente un correo electrónico al administrador cuando un cliente termina de realizar una operación y sube su constancia.

### ¿Qué sucede cuando un cliente sube su constancia?

1. **El cliente completa su transacción** y sube la constancia (comprobante de pago/transferencia)
2. **El estado de la transacción cambia a "PENDIENTE"** automáticamente
3. **Se envía un correo automático al administrador** con todos los detalles de la orden
4. **La orden aparece en el panel de administración** como siempre

## ⚙️ Configuración Requerida

Para que las notificaciones funcionen correctamente, necesitas configurar las siguientes variables en tu archivo `.env`:

### 1. Configuración de Email (ya existe)
```env
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicacion
DEFAULT_FROM_EMAIL=tu_email@gmail.com
```

### 2. **NUEVA:** Email del Administrador
```env
ADMIN_EMAIL=admin@versotek.io
```

**IMPORTANTE:** Si no configuras `ADMIN_EMAIL`, se usará `EMAIL_HOST_USER` como email del administrador por defecto.

## 📋 Contenido del Email de Notificación

El correo incluye:

- **Detalles de la orden**: ID, cliente, tipo de operación
- **Información financiera**: Monedas, cantidades, tasa de cambio
- **Fecha y hora** de la transacción
- **Estado actual**: PENDIENTE
- **Botón directo** al panel de administración para revisar la orden

## 🚀 ¿Cómo Activar las Notificaciones?

### Opción 1: Usar el mismo email (más simple)
Si quieres que las notificaciones lleguen al mismo email que envía los correos:

**No necesitas hacer nada adicional** - funcionará automáticamente.

### Opción 2: Usar un email diferente (recomendado)
Si quieres que las notificaciones lleguen a un email específico del administrador:

1. Agrega esta línea a tu archivo `.env`:
```env
ADMIN_EMAIL=admin@versotek.io
```

2. Reinicia el servidor Django:
```bash
python manage.py runserver
```

## 🔧 Prueba de Funcionamiento

Para probar que funciona:

1. **Como cliente**: Crea una nueva transacción y sube una constancia
2. **Revisa tu email**: Deberías recibir un correo con el asunto "Nueva Orden Pendiente #[ID]"
3. **Verifica en admin**: La orden debe aparecer en el panel de administración

## 📧 Ejemplo del Email

El email tendrá un diseño profesional con:

```
🔔 Nueva Orden Pendiente
Un cliente ha subido su constancia y necesita atención

📋 Detalles de la Orden #123
👤 Cliente: Juan Pérez (juan@email.com)
🔄 Tipo de Operación: Cripto a Soles/Dólares
💰 Desde: 100.00 USDT
💎 Hacia: 380.50 PEN
📅 Fecha: 15/01/2025 14:30
📊 Estado: PENDIENTE

[Botón] 🔧 Ver en Admin Panel
```

## 🛠️ Características Técnicas

- **Diseño responsive**: Se ve bien en móvil y escritorio
- **Fallo silencioso**: Si el email no se envía, no interrumpe el proceso del cliente
- **Logs detallados**: Se registra todo en el archivo `registro.log`
- **Template HTML**: Email con diseño profesional y fallback a texto plano

## 🔍 Solución de Problemas

### Si no recibes emails:

1. **Verifica las credenciales de email** en `.env`
2. **Revisa el archivo `registro.log`** para ver errores
3. **Confirma que ADMIN_EMAIL está configurado** correctamente
4. **Verifica que Gmail permite aplicaciones menos seguras** o usa contraseña de aplicación

### Configuración de Gmail:
- Usa una **contraseña de aplicación** en lugar de tu contraseña normal
- Habilita la **autenticación de 2 factores**
- Genera una contraseña específica para la aplicación

## 🎯 Beneficios

- ✅ **Notificación inmediata** cuando hay nuevas órdenes
- ✅ **No perderás ninguna orden** pendiente
- ✅ **Respuesta más rápida** a los clientes
- ✅ **Mejor experiencia del usuario**
- ✅ **Sistema automático** sin intervención manual

---

¡La funcionalidad ya está lista y funcionando! Solo necesitas configurar el email del administrador en tu archivo `.env`. 