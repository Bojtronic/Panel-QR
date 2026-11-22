# Panel QR

Panel QR es un sistema interno para que los colaboradores autorizados
encuentren la documentación técnica correcta de un panel eléctrico desde un
teléfono, una tableta o una computadora.

## ¿Qué problema resuelve?

La información de un equipo suele estar repartida en carpetas, correos o
archivos con nombres difíciles de identificar. Esto hace más lenta la consulta
durante una revisión o un mantenimiento, y aumenta el riesgo de usar una
versión antigua.

Panel QR vincula cada panel con un código QR permanente. Al escanearlo o buscar
su código, el usuario autenticado llega a la ficha del equipo y consulta los
documentos disponibles. Actualizar un documento no requiere cambiar el QR: el
sistema conserva las versiones anteriores y marca la más reciente como vigente.

## ¿Qué permite hacer?

- Identificar un panel por QR o localizarlo por código, nombre o ubicación.
- Consultar información de ubicación, grupo y estado del equipo.
- Abrir fichas técnicas, diagramas, procedimientos y otros documentos desde el
  navegador.
- Consultar la versión vigente y revisar el historial documental.
- Administrar usuarios, roles y acceso a grupos o paneles.
- Registrar acciones relevantes para trazabilidad y auditoría.

El acceso a la documentación no es público: el usuario debe iniciar sesión y
solo puede consultar los paneles que tiene autorizados.

## Roles de ejemplo

- **ADMIN:** administra paneles, usuarios, permisos y auditoría.
- **TECNICO:** consulta los paneles y documentos que le fueron asignados.

Los roles y asignaciones pueden ajustarse desde la aplicación.

## Organización del proyecto

- [APP/](./APP): aplicación web y guía
  de instalación y puesta en marcha.
- [BD/](./BD): scripts PostgreSQL,
  datos de demostración y guía para PgAdmin 4 o línea de comandos.
- [Recursos/](./Recursos): documento de
  planeamiento y mockups de referencia.

## Ponerlo en marcha

Para instalar dependencias, configurar la base de datos, crear las cuentas de
demostración y ejecutar el sitio, sigue primero la guía de
[APP/README.md](./APP/README.md). La guía de [BD/README.md](./BD/README.md)
explica cómo preparar la base desde PgAdmin 4 (Windows) o `psql` (Linux).

La aplicación de demostración incluye tres cuentas y una contraseña común de
prueba. Antes de usarla con información real, sustituye esas credenciales,
configura HTTPS y define el almacenamiento autorizado para los documentos.

## Alcance

Esta versión es una base funcional para validar el flujo del negocio. Incluye
almacenamiento local de documentos PDF e imágenes y deja el diseño preparado
para evaluar repositorios externos en una etapa posterior. La cámara requiere
un navegador compatible y un contexto seguro; la búsqueda manual sigue
disponible.
